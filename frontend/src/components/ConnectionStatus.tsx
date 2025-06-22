import React from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useOfflineDetection } from '@/hooks/useOfflineDetection';
import OfflineIndicator from '@/components/ui/OfflineIndicator';

interface ConnectionStatusProps {
  showReconnectButton?: boolean;
  compact?: boolean;
}

export function ConnectionStatus({ showReconnectButton = true, compact = false }: ConnectionStatusProps) {
  const { connectionStatus, isConnected, reconnectAttempts, maxReconnectAttempts, reconnect } = useWebSocket(false);
  const { isOffline, isReconnecting, connectionQuality, retryConnection } = useOfflineDetection();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'success';
      case 'connecting': return 'warning';
      case 'reconnecting': return 'warning';
      case 'disconnected': return 'default';
      case 'error': return 'danger';
      default: return 'default';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'connected': return '接続中';
      case 'connecting': return '接続中...';
      case 'reconnecting': return '再接続中...';
      case 'disconnected': return '切断';
      case 'error': return 'エラー';
      default: return status;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return '🟢';
      case 'connecting': return '🟡';
      case 'reconnecting': return '🟡';
      case 'disconnected': return '⚫';
      case 'error': return '🔴';
      default: return '⚪';
    }
  };

  const handleReconnect = async () => {
    try {
      await reconnect();
    } catch (error) {
      console.error('Reconnection failed:', error);
    }
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {/* ネットワーク状態表示 */}
        <OfflineIndicator
          isOffline={isOffline}
          isReconnecting={isReconnecting}
          connectionQuality={connectionQuality}
          onRetry={retryConnection}
          compact={true}
        />
        
        {/* WebSocket接続状態表示 */}
        {!isOffline && (
          <>
            <span className="text-sm">{getStatusIcon(connectionStatus)}</span>
            <span className={`px-2 py-1 text-xs rounded ${
              getStatusColor(connectionStatus) === 'success' ? 'bg-green-500/20 text-green-400' :
              getStatusColor(connectionStatus) === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
              getStatusColor(connectionStatus) === 'danger' ? 'bg-red-500/20 text-red-400' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {getStatusLabel(connectionStatus)}
            </span>
            {connectionStatus === 'reconnecting' && (
              <span className="text-xs text-gray-500">
                ({reconnectAttempts}/{maxReconnectAttempts})
              </span>
            )}
          </>
        )}
      </div>
    );
  }

  // オフライン時は専用のインジケーターを表示
  if (isOffline || connectionQuality !== 'good') {
    return (
      <OfflineIndicator
        isOffline={isOffline}
        isReconnecting={isReconnecting}
        connectionQuality={connectionQuality}
        onRetry={retryConnection}
      />
    );
  }

  return (
    <Card className="p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg">{getStatusIcon(connectionStatus)}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">リアルタイム通信</span>
              <span className={`px-2 py-1 text-xs rounded ${
                getStatusColor(connectionStatus) === 'success' ? 'bg-green-500/20 text-green-400' :
                getStatusColor(connectionStatus) === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                getStatusColor(connectionStatus) === 'danger' ? 'bg-red-500/20 text-red-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {getStatusLabel(connectionStatus)}
              </span>
            </div>
            
            {connectionStatus === 'reconnecting' && (
              <p className="text-sm text-gray-600 mt-1">
                再接続を試行中... ({reconnectAttempts}/{maxReconnectAttempts})
              </p>
            )}
            
            {connectionStatus === 'error' && (
              <p className="text-sm text-red-600 mt-1">
                接続に問題があります
              </p>
            )}
            
            {connectionStatus === 'disconnected' && (
              <p className="text-sm text-gray-600 mt-1">
                サーバーとの接続が切断されています
              </p>
            )}
          </div>
        </div>
        
        {showReconnectButton && !isConnected && (
          <Button 
            size="sm" 
            color="primary" 
            variant="bordered"
            onClick={handleReconnect}
            isDisabled={connectionStatus === 'connecting' || connectionStatus === 'reconnecting'}
          >
            再接続
          </Button>
        )}
      </div>
    </Card>
  );
}

export default ConnectionStatus;