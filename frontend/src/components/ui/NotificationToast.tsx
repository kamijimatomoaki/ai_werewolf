import React, { useEffect, useState } from 'react';
import { uiAnimations } from '@/animations/uiAnimations';

interface NotificationToastProps {
  id: string;
  type?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  message: string;
  duration?: number;
  isVisible?: boolean;
  onClose?: (id: string) => void;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function NotificationToast({
  id,
  type = 'info',
  title,
  message,
  duration = 5000,
  isVisible = true,
  onClose,
  action,
  className = ""
}: NotificationToastProps) {
  const [show, setShow] = useState(isVisible);
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    setShow(isVisible);
  }, [isVisible]);

  useEffect(() => {
    if (show && duration > 0) {
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          const newProgress = prev - (100 / (duration / 100));
          return newProgress <= 0 ? 0 : newProgress;
        });
      }, 100);

      const timer = setTimeout(() => {
        handleClose();
      }, duration);

      return () => {
        clearInterval(progressInterval);
        clearTimeout(timer);
      };
    }
  }, [show, duration]);

  const handleClose = () => {
    setShow(false);
    setTimeout(() => {
      onClose?.(id);
    }, 300);
  };

  const getTypeStyles = () => {
    switch (type) {
      case 'success':
        return {
          icon: '✅',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          progressColor: 'bg-green-500'
        };
      case 'warning':
        return {
          icon: '⚠️',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          textColor: 'text-yellow-800',
          progressColor: 'bg-yellow-500'
        };
      case 'error':
        return {
          icon: '❌',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          progressColor: 'bg-red-500'
        };
      default:
        return {
          icon: 'ℹ️',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          textColor: 'text-blue-800',
          progressColor: 'bg-blue-500'
        };
    }
  };

  const styles = getTypeStyles();

  if (!show) return null;

  return (
    <div
      className={`transition-all duration-300 transform ${
        show ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      } ${className}`}
    >
      <div 
        className={`w-80 ${styles.bgColor} ${styles.borderColor} border border-gray-200 rounded-lg shadow-lg`}
      >
        <div className="p-4">
          <div className="flex items-start space-x-3">
            {/* アイコン */}
            <div className="text-lg mt-0.5">
              {styles.icon}
            </div>

            {/* コンテンツ */}
            <div className="flex-1 min-w-0">
              {title && (
                <h4 className={`font-medium ${styles.textColor} mb-1`}>
                  {title}
                </h4>
              )}
              <p className={`text-sm ${styles.textColor}`}>
                {message}
              </p>

              {/* アクションボタン */}
              {action && (
                <div className="mt-3">
                  <button
                    onClick={action.onClick}
                    className="px-3 py-1.5 text-sm border border-blue-300 hover:bg-blue-50 text-blue-700 rounded transition-colors"
                  >
                    {action.label}
                  </button>
                </div>
              )}
            </div>

            {/* 閉じるボタン */}
            <button
              onClick={handleClose}
              className={`text-lg ${styles.textColor} hover:opacity-70 transition-opacity`}
            >
              ×
            </button>
          </div>

          {/* プログレスバー */}
          {duration > 0 && (
            <div className="mt-3">
              <div className="w-full bg-gray-200 rounded-full h-1">
                <div
                  className={`h-1 rounded-full transition-all duration-100 ease-linear ${styles.progressColor}`}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// トーストコンテナー
interface ToastContainerProps {
  toasts: NotificationToastProps[];
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  onRemoveToast: (id: string) => void;
}

export function ToastContainer({
  toasts,
  position = 'top-right',
  onRemoveToast
}: ToastContainerProps) {
  const getPositionClasses = () => {
    switch (position) {
      case 'top-left':
        return 'top-4 left-4';
      case 'bottom-right':
        return 'bottom-4 right-4';
      case 'bottom-left':
        return 'bottom-4 left-4';
      default:
        return 'top-4 right-4';
    }
  };

  return (
    <div className={`fixed ${getPositionClasses()} z-50 space-y-2`}>
      {toasts.map((toast) => (
        <NotificationToast
          key={toast.id}
          {...toast}
          onClose={onRemoveToast}
        />
      ))}
    </div>
  );
}

// ゲーム専用通知
interface GameNotificationProps {
  type: 'phase_change' | 'player_action' | 'game_event' | 'system';
  phase?: string;
  player?: string;
  message: string;
  onClose?: () => void;
}

export function GameNotification({
  type,
  phase,
  player,
  message,
  onClose
}: GameNotificationProps) {
  const getGameIcon = () => {
    switch (type) {
      case 'phase_change':
        switch (phase) {
          case 'day_discussion': return '🌅';
          case 'day_vote': return '🗳️';
          case 'night': return '🌙';
          case 'finished': return '🏁';
          default: return '⏰';
        }
      case 'player_action': return '👤';
      case 'game_event': return '⚡';
      case 'system': return '⚙️';
      default: return 'ℹ️';
    }
  };

  const getGameType = () => {
    switch (type) {
      case 'phase_change': return 'info';
      case 'player_action': return 'success';
      case 'game_event': return 'warning';
      case 'system': return 'info';
      default: return 'info';
    }
  };

  const formatMessage = () => {
    if (player && type === 'player_action') {
      return `${player}: ${message}`;
    }
    return message;
  };

  return (
    <NotificationToast
      id={`game-${Date.now()}`}
      type={getGameType()}
      message={formatMessage()}
      duration={4000}
      onClose={onClose}
      className="animate-slide-in-right"
    />
  );
}

export default NotificationToast;