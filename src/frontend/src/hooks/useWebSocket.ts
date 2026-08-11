/** Custom React hook for managing WebSocket connections with auto-reconnect. */

import { useState, useEffect, useCallback, RefObject } from 'react';

interface WebSocketOptions {
  onOpen?: () => void;
  onMessage?: (data: string) => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectionDelay?: number; // ms between reconnect attempts
}

interface UseWebSocketResult {
  socket: WebSocket | null;
  isConnected: boolean;
  send: (message: string | ArrayBuffer | Blob) => void;
  close: (code?: number, reason?: string) => void;
  reconnect: () => void;
}

export function useWebSocket(
  url: string,
  options: Partial<WebSocketOptions> = {}
): UseWebSocketResult {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const {
    onOpen = () => {},
    onMessage = () => {},
    onClose = () => {},
    onError = () => {},
    reconnectionDelay = 3000
  } = options;

  const connect = useCallback(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected:', url);
      setIsConnected(true);
      onOpen();
    };

    ws.onmessage = (event) => {
      onMessage(event.data);
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      setIsConnected(false);
      onClose();

      // Auto-reconnect logic
      setTimeout(() => connect(), reconnectionDelay);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError(error);
    };

    setSocket(ws);
    return ws;
  }, [url, onOpen, onMessage, onClose, onError, reconnectionDelay]);

  // Connect on mount and clean up on unmount
  useEffect(() => {
    connect();
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, [connect, socket]);

  const sendMessage = useCallback((message: string | ArrayBuffer | Blob) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(message);
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, [socket]);

  const closeWebSocket = useCallback((code?: number, reason?: string) => {
    if (socket) {
      socket.close(code, reason);
      setSocket(null);
    }
  }, [socket]);

  // Reconnect helper (useful if you want manual control over reconnects)
  const reconnect = useCallback(() => {
    if (!socket || socket.readyState !== WebSocket.CLOSED) {
      connect();
    }
  }, [socket, connect]);

  return {
    socket,
    isConnected,
    send: sendMessage,
    close: closeWebSocket,
    reconnect
  };
}

// Example usage:
/*
const { socket, isConnected, send, close } = useWebSocket('wss://api.example.com/ws', {
  onOpen: () => console.log('Connected!'),
  onMessage: (data) => {
    const msg = JSON.parse(data);
    // handle message
  }
});

// Send a message when button is clicked:
<button onClick={() => send(JSON.stringify({ type: 'greet', name: 'Alice' }))}>
  Greet
</button>
*/
