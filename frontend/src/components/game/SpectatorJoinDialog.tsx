import React, { useState } from 'react';

interface SpectatorJoinDialogProps {
  isOpen: boolean;
  roomName: string;
  onClose: () => void;
  onJoin: (spectatorName: string) => Promise<void>;
}

export default function SpectatorJoinDialog({ isOpen, roomName, onClose, onJoin }: SpectatorJoinDialogProps) {
  const [spectatorName, setSpectatorName] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleJoin = async () => {
    if (!spectatorName.trim()) {
      setError('観戦者名を入力してください');
      return;
    }

    setIsJoining(true);
    setError(null);

    try {
      await onJoin(spectatorName.trim());
      setSpectatorName('');
      onClose();
    } catch (err: any) {
      setError(err.message || '観戦参加に失敗しました');
    } finally {
      setIsJoining(false);
    }
  };

  const handleClose = () => {
    if (!isJoining) {
      setSpectatorName('');
      setError(null);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-lg">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">👁️</span>
                <span className="text-lg font-semibold">観戦参加</span>
              </div>
              <p className="text-sm text-gray-600">
                「{roomName}」を観戦します
              </p>
            </div>
            {!isJoining && (
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            )}
          </div>
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">観戦者名</label>
              <input
                type="text"
                placeholder="観戦者名を入力してください"
                value={spectatorName}
                onChange={(e) => {
                  setSpectatorName(e.target.value);
                  if (error) setError(null);
                }}
                maxLength={20}
                disabled={isJoining}
                autoFocus
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  error ? 'border-red-500' : 'border-gray-300'
                } ${
                  isJoining ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
                }`}
              />
              {error && (
                <p className="text-sm text-red-600 mt-1">{error}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                最大20文字まで入力できます
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-800 mb-2">観戦モードについて</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• ゲームの進行をリアルタイムで観戦できます</li>
                <li>• プレイヤーの役職は表示されません</li>
                <li>• 他の観戦者とチャットができます</li>
                <li>• ゲームに影響を与えることはできません</li>
              </ul>
            </div>
          </div>
        
          <div className="flex justify-end gap-3">
            <button
              onClick={handleClose}
              disabled={isJoining}
              className="px-4 py-2 border border-gray-300 text-gray-700 hover:bg-gray-50 rounded transition-colors disabled:opacity-50"
            >
              キャンセル
            </button>
            <button
              onClick={handleJoin}
              disabled={!spectatorName.trim() || isJoining}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
            >
              {isJoining ? '参加中...' : '観戦開始'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SpectatorJoinDialog;