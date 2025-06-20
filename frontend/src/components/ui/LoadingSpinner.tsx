import React from 'react';
import { uiAnimations } from '@/animations/uiAnimations';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  variant?: 'spinner' | 'dots' | 'pulse' | 'bars';
  message?: string;
  className?: string;
}

export function LoadingSpinner({
  size = 'md',
  color = 'primary',
  variant = 'spinner',
  message,
  className = ""
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  };

  const colorClasses = {
    primary: 'border-blue-500',
    secondary: 'border-purple-500',
    success: 'border-green-500',
    warning: 'border-yellow-500',
    danger: 'border-red-500'
  };

  const renderSpinner = () => {
    switch (variant) {
      case 'spinner':
        return (
          <div
            className={`${sizeClasses[size]} border-2 ${colorClasses[color]} border-t-transparent rounded-full animate-spin`}
          />
        );

      case 'dots':
        return (
          <div className="flex space-x-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={`w-2 h-2 ${colorClasses[color].replace('border-', 'bg-')} rounded-full animate-bounce`}
                style={{
                  animationDelay: `${i * 0.1}s`,
                  animationDuration: '0.6s'
                }}
              />
            ))}
          </div>
        );

      case 'pulse':
        return (
          <div className="relative">
            <div
              className={`${sizeClasses[size]} ${colorClasses[color].replace('border-', 'bg-')} rounded-full animate-pulse`}
            />
            <div
              className={`absolute inset-0 ${sizeClasses[size]} ${colorClasses[color].replace('border-', 'bg-')} rounded-full animate-ping opacity-30`}
            />
          </div>
        );

      case 'bars':
        return (
          <div className="flex space-x-1 items-end">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className={`w-1 ${colorClasses[color].replace('border-', 'bg-')} rounded-sm animate-pulse`}
                style={{
                  height: `${12 + (i % 2) * 8}px`,
                  animationDelay: `${i * 0.1}s`,
                  animationDuration: '1s'
                }}
              />
            ))}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      {renderSpinner()}
      {message && (
        <p className="mt-3 text-sm text-gray-600 animate-pulse">
          {message}
        </p>
      )}
    </div>
  );
}

// ゲーム専用のローディングコンポーネント
interface GameLoadingProps {
  phase?: string;
  message?: string;
  progress?: number;
  className?: string;
}

export function GameLoading({
  phase = 'loading',
  message = 'ゲームを読み込み中...',
  progress,
  className = ""
}: GameLoadingProps) {
  const getPhaseIcon = () => {
    switch (phase) {
      case 'joining': return '🚪';
      case 'starting': return '🎮';
      case 'loading': return '⏳';
      case 'connecting': return '🔗';
      default: return '⏳';
    }
  };

  const getPhaseColor = () => {
    switch (phase) {
      case 'joining': return 'primary';
      case 'starting': return 'success';
      case 'loading': return 'secondary';
      case 'connecting': return 'warning';
      default: return 'primary';
    }
  };

  return (
    <div className={`flex flex-col items-center justify-center p-8 ${className}`}>
      {/* アニメーション付きアイコン */}
      <div 
        className="text-4xl mb-4 animate-bounce"
        style={{
          animationDuration: '1s'
        }}
      >
        {getPhaseIcon()}
      </div>

      {/* スピナー */}
      <LoadingSpinner 
        size="lg" 
        color={getPhaseColor()} 
        variant="spinner"
      />

      {/* メッセージ */}
      <p className="mt-4 text-lg text-gray-700 text-center animate-pulse">
        {message}
      </p>

      {/* プログレスバー（進捗がある場合） */}
      {typeof progress === 'number' && (
        <div className="w-64 mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>進捗</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                getPhaseColor() === 'primary' ? 'bg-blue-500' :
                getPhaseColor() === 'success' ? 'bg-green-500' :
                getPhaseColor() === 'secondary' ? 'bg-purple-500' :
                'bg-yellow-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// フルスクリーンローディングオーバーレイ
interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
  progress?: number;
  onCancel?: () => void;
}

export function LoadingOverlay({
  isVisible,
  message = '処理中...',
  progress,
  onCancel
}: LoadingOverlayProps) {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-sm w-full mx-4 shadow-2xl">
        <GameLoading
          message={message}
          progress={progress}
          className="mb-4"
        />
        
        {onCancel && (
          <button
            onClick={onCancel}
            className="w-full mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            キャンセル
          </button>
        )}
      </div>
    </div>
  );
}

export default LoadingSpinner;