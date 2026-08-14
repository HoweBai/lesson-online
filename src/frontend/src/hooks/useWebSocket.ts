/** Custom React hook for managing WebSocket connections with auto-reconnect. */

import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketOptions {
  onOpen?: () => void;
  onMessage?: (data: string) => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectionDelay?: number; // ms between reconnect attempts
  token?: string; // JWT token passed as WebSocket subprotocol
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
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const connect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    const protocols = optionsRef.current.token
      ? ['token', optionsRef.current.token]
      : undefined;
    const ws = new WebSocket(url, protocols);
    socketRef.current = ws;
    const { onOpen, onMessage, onClose, onError, reconnectionDelay } = optionsRef.current;

    ws.onopen = () => {
      setIsConnected(true);
      onOpen?.();
    };

    ws.onmessage = (event) => {
      onMessage(event.data);
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      onClose?.();

      if (event.code !== 1000) {
        reconnectTimeoutRef.current = setTimeout(() => connect(), reconnectionDelay || 3000);
      }
    };

    ws.onerror = (error) => {
      onError?.(error);
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: string | ArrayBuffer | Blob) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(message);
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);

  const closeWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (socketRef.current) {
      socketRef.current.close(1000, 'Manual close');
      socketRef.current = null;
      setIsConnected(false);
    }
  }, []);

  return {
    socket: socketRef.current,
    isConnected,
    send: sendMessage,
    close: closeWebSocket,
    reconnect: connect
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
