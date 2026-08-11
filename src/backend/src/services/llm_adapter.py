"""LLM Integration Layer - Unified adapter for Claude and OpenAI models."""

import httpx
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import asyncio
import logging

logger = logging.getLogger(__name__)

class LLMAdapter(ABC):
    """Unified LLM adapter interface supporting Claude, OpenAI, and third-party models."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=300.0),
            headers={"Accept": "application/json"}
        )
        self.retry_attempts = 3
        self.backoff_factor = 0.5

    @abstractmethod
    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        """Chat mode returning generated text."""
        pass

    @abstractmethod
    async def generate_content(self, prompt: str, context: Optional[Any] = None) -> str:
        """Content generation mode."""
        pass

    async def _make_request_with_retry(self, endpoint: str, payload: Dict,
                                       headers: Dict[str, str]) -> Dict:
        """Request with exponential backoff retry logic."""
        last_exception = None

        for attempt in range(self.retry_attempts):
            try:
                response = await self.http_client.post(
                    endpoint, json=payload, headers=headers, timeout=300.0
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPError as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    await asyncio.sleep(wait_time)

        raise RuntimeError(f"All {self.retry_attempts} attempts failed: {last_exception}")

    def close(self):
        self.http_client.close()


class ClaudeAdapter(LLMAdapter):
    """Adapter for Claude Anthropic API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config["base_url"].rstrip("/")
        self.api_key = config["api_key"]
        self.model = config.get("model_name", "claude-3-opus-20240925")
        self.system_prompt = config.get("system_prompt", "")

    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        endpoint = f"{self.base_url}/v1/messages"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "x-anthropic-api-version": "2023-06-01"
        }

        claude_messages = []
        for msg in messages:
            if msg["role"] == "user":
                claude_messages.append({
                    "role": "user",
                    "content": [{"type": "text", "text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                claude_messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": msg["content"]}]
                })

        payload = {
            "model": self.model,
            "messages": claude_messages,
            "max_tokens": 8192,
            "temperature": 0.7
        }

        if self.system_prompt:
            payload["system"] = self.system_prompt

        result = await self._make_request_with_retry(endpoint, payload, headers)
        return result.get("content", [{}])[0].get("text", "")

    async def generate_content(self, prompt: str, context=None) -> str:
        return self.chat([{"role": "user", "content": prompt}])


class OpenAIAAdapter(LLMAdapter):
    """Adapter for OpenAI API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        base = config.get("base_url", "https://api.openai.com/v1")
        self.base_url = base.rstrip("/")
        self.api_key = config["api_key"]
        self.model = config.get("model_name", "gpt-4o-2024-07-18")

    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7
        }

        result = await self._make_request_with_retry(endpoint, payload, headers)
        return result["choices"][0]["message"]["content"]
