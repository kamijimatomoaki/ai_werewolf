import React from 'react';
import { Card } from "@heroui/card";
import { Button } from "@heroui/button";
import { Chip } from "@heroui/chip";

// アイコンコンポーネント
const WifiOffIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l6 6 2-2 6-6m2 13.5A9 9 0 1 1 4.5 15a9 9 0 0 1 15 2.5z" />
  </svg>
);

const WifiIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
  </svg>
);

const RefreshIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const SignalIcon = ({ className, strength }: { className?: string; strength: number }) => (
  <div className={`flex items-end gap-0.5 ${className}`}>
    <div className={`w-1 h-2 ${strength >= 1 ? 'bg-current' : 'bg-gray-300'} rounded-sm`} />
    <div className={`w-1 h-3 ${strength >= 2 ? 'bg-current' : 'bg-gray-300'} rounded-sm`} />
    <div className={`w-1 h-4 ${strength >= 3 ? 'bg-current' : 'bg-gray-300'} rounded-sm`} />
    <div className={`w-1 h-5 ${strength >= 4 ? 'bg-current' : 'bg-gray-300'} rounded-sm`} />
  </div>
);

interface OfflineIndicatorProps {
  isOffline: boolean;
  isReconnecting: boolean;
  connectionQuality?: 'good' | 'poor' | 'offline';
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

export default function OfflineIndicator({
  isOffline,
  isReconnecting,
  connectionQuality = 'good',
  onRetry,
  className = '',
  compact = false
}: OfflineIndicatorProps) {
  // 接続品質に基づく表示設定
  const getConnectionDisplay = () => {
    if (isOffline) {
      return {
        icon: <WifiOffIcon className="w-5 h-5" />,
        color: 'danger' as const,
        text: 'オフライン',
        description: 'インターネット接続が利用できません'
      };
    }

    if (isReconnecting) {
      return {
        icon: <RefreshIcon className="w-5 h-5 animate-spin" />,
        color: 'warning' as const,
        text: '再接続中',
        description: 'サーバーに再接続しています...'
      };
    }

    switch (connectionQuality) {
      case 'poor':
        return {
          icon: <SignalIcon className="w-5 h-5 text-orange-500" strength={2} />,
          color: 'warning' as const,
          text: '接続不安定',
          description: '接続が不安定です。一部機能が正常に動作しない可能性があります'
        };
      case 'good':
        return {
          icon: <WifiIcon className="w-5 h-5" />,
          color: 'success' as const,
          text: 'オンライン',
          description: '接続は正常です'
        };
      case 'offline':
        return {
          icon: <WifiOffIcon className="w-5 h-5" />,
          color: 'danger' as const,
          text: 'オフライン',
          description: 'サーバーに接続できません'
        };
      default:
        return {
          icon: <WifiIcon className="w-5 h-5" />,
          color: 'default' as const,
          text: '不明',
          description: '接続状態を確認中...'
        };
    }
  };

  const connectionDisplay = getConnectionDisplay();

  // オンライン時のコンパクト表示（接続良好時は最小限の表示）
  if (compact && connectionQuality === 'good' && !isOffline && !isReconnecting) {
    return (
      <div className={`flex items-center gap-1 text-sm text-green-600 ${className}`}>
        {connectionDisplay.icon}
        <span className="hidden sm:inline">{connectionDisplay.text}</span>
      </div>
    );
  }

  // コンパクト表示（問題がある場合）
  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Chip
          color={connectionDisplay.color}
          variant="flat"
          size="sm"
          startContent={connectionDisplay.icon}
        >
          {connectionDisplay.text}
        </Chip>
        {onRetry && (isOffline || connectionQuality === 'poor') && (
          <Button
            size="sm"
            variant="ghost"
            onClick={onRetry}
            isLoading={isReconnecting}
            className="min-w-0 px-2"
          >
            <RefreshIcon className="w-4 h-4" />
          </Button>
        )}
      </div>
    );
  }

  // フル表示（問題がある場合のみ表示）
  if (!isOffline && connectionQuality === 'good' && !isReconnecting) {
    return null;
  }

  return (
    <Card className={`p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {connectionDisplay.icon}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-gray-900">
              {connectionDisplay.text}
            </h4>
            <Chip
              color={connectionDisplay.color}
              variant="flat"
              size="sm"
            >
              {isReconnecting ? '再接続中' : connectionDisplay.text}
            </Chip>
          </div>
          
          <p className="text-sm text-gray-600 mb-3">
            {connectionDisplay.description}
          </p>

          {/* アクションボタン */}
          {onRetry && (isOffline || connectionQuality === 'poor') && (
            <div className="flex gap-2">
              <Button
                size="sm"
                color={connectionDisplay.color}
                variant="bordered"
                onClick={onRetry}
                isLoading={isReconnecting}
                startContent={!isReconnecting ? <RefreshIcon className="w-4 h-4" /> : undefined}
              >
                {isReconnecting ? '再接続中...' : '再接続'}
              </Button>
              
              {isOffline && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => window.location.reload()}
                  className="text-gray-600"
                >
                  ページ再読み込み
                </Button>
              )}
            </div>
          )}

          {/* オフライン時の追加情報 */}
          {isOffline && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
              <h5 className="text-sm font-medium text-gray-700 mb-1">
                オフライン時の利用について
              </h5>
              <ul className="text-xs text-gray-600 space-y-1">
                <li>• 既に表示されているデータは引き続き閲覧できます</li>
                <li>• 新しいデータの取得や送信はできません</li>
                <li>• 接続が復旧すると自動的に同期されます</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}