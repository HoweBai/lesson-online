/**
 * Claude Chat Sidebar - Right-side panel for interacting with Claude AI.
 * Uses WebSocket for real-time communication.
 */

import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: number;
}

interface ClaudeChatSidebarProps {
  tutorialId?: string;
  onChapterGenerated?: () => void;
}

const ClaudeChatSidebar = ({ tutorialId = 'default', onChapterGenerated }: ClaudeChatSidebarProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to WebSocket on mount
  useEffect(() => {
    const wsUrl = `wss://api.yourplatform.com/ws/claude/${tutorialId}/default`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Claude Chat connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'ai_response') {
          setMessages(prev => [...prev, {
            id: data.id || uuidv4(),
            sender: 'ai',
            content: data.content,
            timestamp: Date.now()
          }]);
        } else if (data.type === 'chapter_generated') {
          onChapterGenerated?.();
          // Show notification toast
          const toast = document.createElement('div');
          toast.className = 'toast toast-success';
          toast.textContent = 'Chapter generated successfully!';
          document.body.appendChild(toast);
          setTimeout(() => toast.remove(), 3000);
        } else if (data.type === 'error') {
          // Show error message
          alert(`Error: ${data.message}`);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Reconnect after delay
      setTimeout(() => {
        window.location.reload();
      }, 5000);
    };

    wsRef.current = ws;

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [tutorialId, onChapterGenerated]);

  const sendMessage = () => {
    if (!input.trim() || !wsRef.current) return;

    const message: ChatMessage = {
      id: uuidv4(),
      sender: 'user',
      content: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, message]);
    setInput('');

    wsRef.current?.send(JSON.stringify({
      type: 'user_message',
      content: input,
      timestamp: Date.now()
    }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className={`fixed right-0 top-0 h-full bg-gray-900 border-l border-gray-700 transition-all duration-300 ${
      isConnected ? 'w-96' : 'w-16'
    }`}>
      {/* Header */}
      <div className="p-3 bg-gray-800 flex items-center justify-between">
        {!isConnected ? (
          <button onClick={() => window.location.reload()} className="text-red-400 hover:text-white" title="Reconnect">
            🔴 Offline
          </button>
        ) : (
          <span className="text-green-400">● Online</span>
        )}
        <h3 className="text-white font-semibold text-sm truncate">🤖 Claude Assistant</h3>
        <button className="text-gray-400 hover:text-white" title="Collapse">
          ‹
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-gray-900">
        {messages.length === 0 ? (
          <div className="text-gray-500 text-center py-8 text-sm">
            Ready to chat with Claude<br/>Ask anything about your tutorial
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xs sm:max-w-md px-3 py-2 rounded-lg text-sm ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white ml-4'
                  : 'bg-gray-700 text-gray-100 mr-4'
              }`}>
                {msg.content}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-gray-700 bg-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question..."
            disabled={!isConnected}
            className={`flex-1 px-3 py-2 rounded-lg focus:outline-none focus:ring-2 ${
              isConnected
                ? 'bg-gray-700 text-white placeholder-gray-400 focus:bg-gray-600 focus:ring-blue-500'
                : 'bg-gray-900 text-gray-500 cursor-not-allowed'
            }`}
          />
          {isConnected && (
            <button
              onClick={sendMessage}
              disabled={!input.trim()}
              className="px-4 py-2 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-600 disabled:text-gray-400 transition-colors"
            >
              Send
            </button>
          )}
        </div>
        {!isConnected && (
          <div className="mt-2 text-xs text-red-400 text-center">
            Connected offline - check server status
          </div>
        )}
      </div>
    </div>
  );
};

export default ClaudeChatSidebar;
