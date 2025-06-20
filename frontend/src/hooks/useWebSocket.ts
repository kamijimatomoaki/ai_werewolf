import { useState, useEffect, useCallback } from 'react';
import { websocketService, ConnectionStatus } from '@/services/websocket';

export interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  reconnect: () => Promise<void>;
  connect: (serverUrl?: string) => Promise<void>;
  disconnect: () => void;
}

/**
 * WebSocket接続を管理するReactフック
 */
export function useWebSocket(autoConnect: boolean = true, serverUrl?: string): UseWebSocketReturn {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(
    websocketService.getConnectionStatus()
  );
  const [reconnectAttempts, setReconnectAttempts] = useState(
    websocketService.getReconnectAttempts()
  );

  // 接続状態の監視
  useEffect(() => {
    const handleStatusChange = (status: ConnectionStatus) => {
      setConnectionStatus(status);
      setReconnectAttempts(websocketService.getReconnectAttempts());
    };

    websocketService.onConnectionStatusChange(handleStatusChange);

    // 自動接続
    if (autoConnect && !websocketService.isConnected()) {
      websocketService.connect(serverUrl).catch(error => {
        console.error('Auto-connect failed:', error);
      });
    }

    return () => {
      websocketService.offConnectionStatusChange(handleStatusChange);
    };
  }, [autoConnect, serverUrl]);

  // 手動接続
  const connect = useCallback(async (url?: string) => {
    try {
      await websocketService.connect(url || serverUrl);
    } catch (error) {
      console.error('Manual connect failed:', error);
      throw error;
    }
  }, [serverUrl]);

  // 再接続
  const reconnect = useCallback(async () => {
    try {
      await websocketService.reconnect();
    } catch (error) {
      console.error('Manual reconnect failed:', error);
      throw error;
    }
  }, []);

  // 切断
  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  return {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    reconnectAttempts,
    maxReconnectAttempts: websocketService.getMaxReconnectAttempts(),
    reconnect,
    connect,
    disconnect,
  };
}