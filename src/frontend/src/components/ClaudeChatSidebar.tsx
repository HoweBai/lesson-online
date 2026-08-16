/**
 * Claude Chat Sidebar - Right-side panel for interacting with Claude AI.
 * Uses WebSocket for real-time communication.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useToast } from '../hooks/useToast';
import { useWebSocket } from '../hooks/useWebSocket';

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
  const toast = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);

  const getToken = useCallback(() => localStorage.getItem('auth_token') || '', []);

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/claude/${tutorialId}/default`;

  const handleMessage = useCallback((data: string) => {
    try {
      const msg = JSON.parse(data);
      switch (msg.type) {
        case 'connected':
          break;

        case 'history':
          if (msg.messages && Array.isArray(msg.messages)) {
            setMessages(msg.messages.map((m: any) => ({
              id: m.id || uuidv4(),
              sender: m.sender || 'ai',
              content: m.content,
              timestamp: m.timestamp || Date.now()
            })));
          }
          break;

        case 'typing':
          setIsTyping(true);
          break;

        case 'ai_response':
          setIsTyping(false);
          setMessages(prev => [...prev, {
            id: msg.id || uuidv4(),
            sender: 'ai',
            content: msg.content,
            timestamp: Date.now()
          }]);
          break;

        case 'message_received':
          // Acknowledge receipt, no UI change needed
          break;

        case 'error':
          toast.error(`Error: ${msg.message}`);
          break;

        case 'chapter_generated':
          onChapterGenerated?.();
          toast.success('Chapter generated successfully!');
          break;

        default:
          break;
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  }, [toast, onChapterGenerated]);

  const { send, isConnected, close } = useWebSocket(wsUrl, {
    token: getToken(),
    onOpen: () => {},
    onMessage: handleMessage,
    onClose: () => {}
  });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const sendMessage = useCallback(() => {
    if (!input.trim() || !isConnected) return;

    const message: ChatMessage = {
      id: uuidv4(),
      sender: 'user',
      content: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, message]);
    setInput('');
    setIsTyping(true);

    send(JSON.stringify({
      type: 'user_message',
      content: input,
      timestamp: Date.now()
    }));
  }, [input, isConnected, send]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleSidebar = () => setIsOpen(prev => !prev);
  const closeSidebar = () => {
    setIsOpen(false);
    close();
  };

  return (
    <>
      {/* Toggle Button - Fixed Position */}
      <button
        onClick={toggleSidebar}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-r from-primary-600 to-accent-600 text-white shadow-lg hover:shadow-xl flex items-center justify-center text-2xl transition-all hover:scale-105"
        title={isOpen ? 'Close chat' : 'Open Claude chat'}
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Sidebar Panel */}
      <div
        ref={sidebarRef}
        className={`fixed right-0 top-0 h-full bg-gray-900 border-l border-gray-700 transition-all duration-300 z-40 flex flex-col ${
          isOpen ? 'w-96' : 'w-0'
        } overflow-hidden`}
      >
        {/* Header */}
        <div className="p-3 bg-gray-800 flex items-center justify-between flex-shrink-0">
          <span className={`text-sm font-medium ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
            ● {isConnected ? 'Online' : 'Offline'}
          </span>
          <h3 className="text-white font-semibold text-sm truncate flex-1 mx-2">🤖 Claude Assistant</h3>
          <button
            onClick={closeSidebar}
            className="text-gray-400 hover:text-white transition-colors"
            title="Close"
          >
            ‹
          </button>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-gray-900">
          {messages.length === 0 && !isTyping ? (
            <div className="text-gray-500 text-center py-8 text-sm">
              Ready to chat with Claude<br/>Ask anything about your tutorial
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-xs sm:max-w-md px-3 py-2 rounded-lg text-sm ${
                    msg.sender === 'user'
                      ? 'bg-blue-600 text-white ml-4'
                      : 'bg-gray-700 text-gray-100 mr-4'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-gray-700 text-gray-100 px-3 py-2 rounded-lg text-sm mr-4">
                    <span className="inline-flex gap-1 items-center">
                      <span className="animate-bounce">●</span>
                      <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>●</span>
                      <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>●</span>
                    </span>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-3 border-t border-gray-700 bg-gray-800 flex-shrink-0">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your question..."
              disabled={!isConnected}
              className="flex-1 px-3 py-2 rounded-lg focus:outline-none focus:ring-2 bg-gray-700 text-white placeholder-gray-400 focus:bg-gray-600 focus:ring-blue-500 disabled:opacity-50"
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
              Connecting... check server status
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default ClaudeChatSidebar;
