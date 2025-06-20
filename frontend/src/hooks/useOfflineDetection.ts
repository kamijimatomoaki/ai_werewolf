import { useState, useEffect, useCallback } from 'react';
import { apiService } from '@/services/api';

interface UseOfflineDetectionReturn {
  isOffline: boolean;
  isReconnecting: boolean;
  connectionQuality: 'good' | 'poor' | 'offline';
  retryConnection: () => void;
  lastChecked: Date | null;
}

const HEALTH_CHECK_INTERVAL = 30000; // 30秒
const OFFLINE_CHECK_INTERVAL = 5000; // 5秒（オフライン時）
const CONNECTION_TIMEOUT = 10000; // 10秒

export function useOfflineDetection(): UseOfflineDetectionReturn {
  const [isOffline, setIsOffline] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [connectionQuality, setConnectionQuality] = useState<'good' | 'poor' | 'offline'>('good');
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  // ネットワーク状態を確認
  const checkNetworkStatus = useCallback(async (): Promise<boolean> => {
    try {
      // ブラウザのnavigator.onLineを最初にチェック
      if (!navigator.onLine) {
        return false;
      }

      // APIサーバーへのヘルスチェック
      const startTime = Date.now();
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CONNECTION_TIMEOUT);

      try {
        await apiService.healthCheck();
        clearTimeout(timeoutId);
        
        const responseTime = Date.now() - startTime;
        
        // レスポンス時間に基づいて接続品質を判定
        if (responseTime < 1000) {
          setConnectionQuality('good');
        } else if (responseTime < 3000) {
          setConnectionQuality('poor');
        } else {
          setConnectionQuality('poor');
        }
        
        setLastChecked(new Date());
        return true;
      } catch (error) {
        clearTimeout(timeoutId);
        setConnectionQuality('offline');
        return false;
      }
    } catch (error) {
      setConnectionQuality('offline');
      return false;
    }
  }, []);

  // 接続状態を更新
  const updateConnectionStatus = useCallback(async () => {
    if (isReconnecting) return; // 再接続中は重複チェックを避ける

    const isOnline = await checkNetworkStatus();
    
    if (isOnline !== !isOffline) {
      setIsOffline(!isOnline);
      
      if (isOnline) {
        console.log('🟢 Connection restored');
        setIsReconnecting(false);
      } else {
        console.log('🔴 Connection lost');
      }
    }
  }, [isOffline, isReconnecting, checkNetworkStatus]);

  // 手動再接続
  const retryConnection = useCallback(async () => {
    if (isReconnecting) return;

    console.log('🔄 Manual reconnection attempt...');
    setIsReconnecting(true);
    
    try {
      const isOnline = await checkNetworkStatus();
      setIsOffline(!isOnline);
      
      if (isOnline) {
        console.log('✅ Manual reconnection successful');
      } else {
        console.log('❌ Manual reconnection failed');
      }
    } finally {
      setIsReconnecting(false);
    }
  }, [isReconnecting, checkNetworkStatus]);

  // ブラウザのネットワーク状態イベントリスナー
  useEffect(() => {
    const handleOnline = () => {
      console.log('🌐 Browser detected online');
      updateConnectionStatus();
    };

    const handleOffline = () => {
      console.log('🌐 Browser detected offline');
      setIsOffline(true);
      setConnectionQuality('offline');
    };

    // ブラウザネイティブのイベントリスナー
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 初期状態チェック
    updateConnectionStatus();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [updateConnectionStatus]);

  // 定期的なヘルスチェック
  useEffect(() => {
    const interval = setInterval(() => {
      updateConnectionStatus();
    }, isOffline ? OFFLINE_CHECK_INTERVAL : HEALTH_CHECK_INTERVAL);

    return () => clearInterval(interval);
  }, [isOffline, updateConnectionStatus]);

  // Visibility API - タブがアクティブになった時のチェック
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('👁️ Tab became visible, checking connection...');
        updateConnectionStatus();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [updateConnectionStatus]);

  return {
    isOffline,
    isReconnecting,
    connectionQuality,
    retryConnection,
    lastChecked
  };
}