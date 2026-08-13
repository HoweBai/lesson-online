"""WebSocket routes for Claude Chat interaction."""

from fastapi import APIRouter, WebSocket, WebSocketException, status, Depends
from fastapi.websockets import WebSocketDisconnect
from jose import JWTError, jwt
import uuid
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import defaultdict

from ..database import get_db, Session, SessionLocal
from ..services.auth_service import get_current_user
from ..models.user import User
from ..models.chapter import Chapter
from ..models.chat_history import ChatHistory
from ..services.llm_adapter import ClaudeAdapter, OpenAIAAdapter
from ..services.claude_config_service import ClaudeConfigService
from ..services.crypto_service import SecureCryptoService

logger = logging.getLogger(__name__)

# Store active WebSocket connections: {tutorial_id: {channel_id: WebSocket}}
active_connections: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)

# Store chat history: {tutorial_id: {channel_id: [messages]}}
chat_history: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

# Session state: {session_id: {user_id, tutorial_id, channel_id, last_active}}
sessions: Dict[str, Dict[str, Any]] = {}

# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 30

router = APIRouter(prefix="/ws", tags=["websocket"])


class ChatSession:
    """Manages a WebSocket chat session."""

    def __init__(self, websocket: WebSocket, tutorial_id: str, channel_id: str, user_id: str):
        self.websocket = websocket
        self.tutorial_id = tutorial_id
        self.channel_id = channel_id
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.last_active = datetime.utcnow()
        self.message_count = 0
        self.is_alive = True

    async def send(self, message: Dict[str, Any]):
        """Send a message to the client."""
        if not self.is_alive:
            return
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.is_alive = False

    async def receive(self) -> Optional[Dict]:
        """Receive a message from the client."""
        if not self.is_alive:
            return None
        try:
            data = await asyncio.wait_for(self.websocket.receive_text(), timeout=HEARTBEAT_INTERVAL * 2)
            self.last_active = datetime.utcnow()
            return json.loads(data)
        except asyncio.TimeoutError:
            return None
        except WebSocketDisconnect:
            self.is_alive = False
            return None
        except Exception as e:
            logger.error(f"Receive error: {e}")
            self.is_alive = False
            return None


@router.websocket("/claude/{tutorial_id}/{channel_id}")
async def claude_chat(websocket: WebSocket, tutorial_id: str, channel_id: str):
    """WebSocket endpoint for Claude AI chat interaction."""
    # Accept connection without immediate auth (auth via query param)
    await websocket.accept()

    # Extract token from query params
    query_params = websocket.query_params
    token = query_params.get("token", "")

    # Authenticate if token provided
    user_id = None
    if token:
        try:
            from ..services.auth_service import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
        except JWTError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return

    # Create session
    session = ChatSession(websocket, tutorial_id, channel_id, user_id or "anonymous")
    key = f"{tutorial_id}:{channel_id}"

    # Add to active connections
    active_connections[tutorial_id][channel_id] = websocket
    sessions[session.session_id] = {
        "user_id": user_id,
        "tutorial_id": tutorial_id,
        "channel_id": channel_id,
        "session_id": session.session_id,
        "connected_at": datetime.utcnow(),
        "last_active": datetime.utcnow()
    }

    # Send connection confirmed
    await session.send({
        "type": "connected",
        "session_id": session.session_id,
        "tutorial_id": tutorial_id,
        "channel_id": channel_id,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Send chat history from database
    db = SessionLocal()
    try:
        stored_history = ChatHistory.get_history(db, tutorial_id, channel_id, 50)
        if stored_history:
            stored_messages = [
                {
                    "id": str(h.id),
                    "sender": h.sender,
                    "content": h.content,
                    "timestamp": h.created_at.isoformat() if h.created_at else datetime.utcnow().isoformat()
                }
                for h in stored_history
            ]
            await session.send({
                "type": "history",
                "messages": stored_messages,
                "timestamp": datetime.utcnow().isoformat()
            })
    finally:
        db.close()

    logger.info(f"WebSocket connected: tutorial={tutorial_id}, channel={channel_id}, session={session.session_id}")

    try:
        while session.is_alive:
            # Send heartbeat
            heartbeat = await session.receive()

            if heartbeat is None:
                # Timeout or disconnect
                break

            msg_type = heartbeat.get("type")

            if msg_type == "ping":
                # Heartbeat response
                await session.send({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
                continue

            if msg_type == "user_message":
                user_content = heartbeat.get("content", "")
                if not user_content:
                    await session.send({
                        "type": "error",
                        "message": "Message content is required"
                    })
                    continue

                # Store user message
                user_msg = {
                    "id": str(uuid.uuid4()),
                    "sender": "user",
                    "content": user_content,
                    "timestamp": datetime.utcnow().isoformat()
                }
                chat_history[tutorial_id][channel_id].append(user_msg)

                # Store user message to database
                if user_id:
                    db = SessionLocal()
                    try:
                        ChatHistory.create(
                            db=db,
                            tutorial_id=tutorial_id,
                            channel_id=channel_id,
                            sender='user',
                            content=user_content
                        )
                    finally:
                        db.close()

                # Send acknowledgment
                await session.send({
                    "type": "message_received",
                    "message_id": user_msg["id"],
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Generate AI response
                await session.send({
                    "type": "typing",
                    "timestamp": datetime.utcnow().isoformat()
                })

                try:
                    response = await generate_ai_response(
                        user_content,
                        tutorial_id,
                        channel_id,
                        user_id
                    )

                    ai_msg = {
                        "id": str(uuid.uuid4()),
                        "sender": "ai",
                        "content": response,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    chat_history[tutorial_id][channel_id].append(ai_msg)

                    # Store AI response to database
                    if user_id:
                        db = SessionLocal()
                        try:
                            ChatHistory.create(
                                db=db,
                                tutorial_id=tutorial_id,
                                channel_id=channel_id,
                                sender='ai',
                                content=response
                            )
                        finally:
                            db.close()

                    await session.send({
                        "type": "ai_response",
                        "message": ai_msg
                    })

                except Exception as e:
                    logger.error(f"AI response error: {e}")
                    await session.send({
                        "type": "error",
                        "message": f"Failed to generate response: {str(e)}"
                    })

            elif msg_type == "request_chapter":
                chapter_num = heartbeat.get("chapter_number", 1)
                await session.send({
                    "type": "chapter_requested",
                    "chapter_number": chapter_num,
                    "timestamp": datetime.utcnow().isoformat()
                })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up
        await cleanup_session(session)


async def cleanup_session(session: ChatSession):
    """Clean up session resources."""
    key = f"{session.tutorial_id}:{session.channel_id}"
    if session.tutorial_id in active_connections:
        if session.channel_id in active_connections[session.tutorial_id]:
            del active_connections[session.tutorial_id][session.channel_id]
        if not active_connections[session.tutorial_id]:
            del active_connections[session.tutorial_id]

    if session.session_id in sessions:
        del sessions[session.session_id]

    session.is_alive = False
    logger.info(f"WebSocket cleaned up: session={session.session_id}")


async def generate_ai_response(
    user_input: str,
    tutorial_id: str,
    channel_id: str,
    user_id: Optional[str]
) -> str:
    """Generate AI response using Claude API."""
    db: Session = None
    try:
        from ..database import SessionLocal
        db = SessionLocal()

        # Get user's Claude config
        config_service = None
        if user_id:
            from ..services.crypto_service import SecureCryptoService
            import os
            master_key_hex = os.getenv("CRYPTO_KEY_HEX", "0" * 64)
            master_key = bytes.fromhex(master_key_hex)[:32]
            crypto = SecureCryptoService(master_key)
            config_service = ClaudeConfigService(crypto, db)
            config = config_service.get_default_config(user_id)

            if not config:
                return "Please configure your Claude API in the settings first. Go to /claude-config to add your API key."

            # Build context from tutorial
            tutorial_context = await get_tutorial_context(db, tutorial_id)

            # Create LLM adapter
            model_name = config.get("model_name", "claude-3-opus-20240925").lower()
            if "openai" in model_name or "gpt-" in model_name:
                adapter = OpenAIAAdapter(config)
            else:
                adapter = ClaudeAdapter(config)

            # Build prompt
            prompt = build_chat_prompt(user_input, tutorial_context)

            # Generate response
            response = await adapter.chat([{"role": "user", "content": prompt}])

            adapter.close()
            return response or "I received your message but couldn't generate a response."

        else:
            # Anonymous user - provide generic response
            return "Please log in to chat with Claude AI. You need to configure your API key first."

    except Exception as e:
        logger.error(f"AI response generation error: {e}")
        return f"Sorry, I encountered an error: {str(e)}"
    finally:
        if db:
            db.close()


async def get_tutorial_context(db: Session, tutorial_id: str) -> str:
    """Get tutorial context for AI response."""
    from ..models.tutorial import Tutorial
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        return "No tutorial context available."

    outline = tutorial.outline or {}
    chapters = db.query(Chapter).filter(
        Chapter.tutorial_id == tutorial_id
    ).order_by(Chapter.chapter_number).all()

    context = f"Tutorial: {tutorial.title}\n"
    context += f"Status: {tutorial.status}\n"
    context += f"Total chapters: {tutorial.total_chapters or 0}\n"
    context += f"Current chapter: {tutorial.current_chapter or 1}\n\n"

    if outline.get("chapters"):
        context += "Outline:\n"
        for ch in outline["chapters"][:5]:
            context += f"  - {ch.get('chapter_number', '?')}. {ch.get('title', 'Untitled')}\n"

    context += "\nGenerated chapters:\n"
    for ch in chapters[:3]:
        context += f"  - Chapter {ch.chapter_number}: {ch.title}\n"

    return context


def build_chat_prompt(user_input: str, tutorial_context: str) -> str:
    """Build prompt for AI response."""
    return f"""You are an AI teaching assistant for a personalized learning platform. You help students understand tutorial content.

Tutorial Context:
{tutorial_context}

Student Question: {user_input}

Please provide a helpful, educational response that:
1. Addresses the student's question directly
2. Relates to the tutorial content when applicable
3. Uses clear, encouraging language
4. Provides examples when helpful
5. Is appropriate for the student's learning level

Keep your response concise but informative."""


@router.get("/status")
async def get_websocket_status():
    """Get WebSocket connection status."""
    return {
        "status": "online",
        "active_sessions": len(sessions),
        "active_connections": sum(
            len(channels) for channels in active_connections.values()
        ),
        "tutorial_channels": {
            tid: list(channels.keys())
            for tid, channels in active_connections.items()
        }
    }


@router.get("/history/{tutorial_id}/{channel_id}")
async def get_chat_history(
    tutorial_id: str,
    channel_id: str,
    limit: int = 50
):
    """Get chat history for a tutorial channel."""
    history = chat_history.get(tutorial_id, {}).get(channel_id, [])
    return {
        "tutorial_id": tutorial_id,
        "channel_id": channel_id,
        "messages": history[-limit:],
        "total": len(history)
    }


@router.delete("/history/{tutorial_id}/{channel_id}")
async def clear_chat_history(
    tutorial_id: str,
    channel_id: str
):
    """Clear chat history for a tutorial channel."""
    if tutorial_id in chat_history and channel_id in chat_history[tutorial_id]:
        chat_history[tutorial_id][channel_id] = []
        return {"message": "History cleared"}
    return {"message": "No history to clear"}
