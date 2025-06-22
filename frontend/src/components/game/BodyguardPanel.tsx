import React, { useState, useEffect } from 'react';
import { useBodyguardProtection } from '@/hooks/useBodyguardProtection';

interface PlayerInfo {
  player_id: string;
  character_name: string;
  is_alive: boolean;
  role?: string;
}

interface BodyguardPanelProps {
  roomId: string;
  playerId: string;
  isActive: boolean; // 夜フェーズかつボディガードの場合
  className?: string;
}

export function BodyguardPanel({ roomId, playerId, isActive, className = "" }: BodyguardPanelProps) {
  const {
    availableTargets,
    protectionResult,
    isProtecting,
    canProtect,
    protect,
    error
  } = useBodyguardProtection(roomId, playerId);

  const [selectedTargetId, setSelectedTargetId] = useState<string>('');

  const handleProtect = async () => {
    if (!selectedTargetId) return;
    
    try {
      await protect(selectedTargetId);
      setSelectedTargetId(''); // 成功後にリセット
    } catch (err) {
      console.error('Protection failed:', err);
    }
  };

  const handleTargetSelect = (targetId: string) => {
    setSelectedTargetId(targetId);
  };

  // 非アクティブ時は何も表示しない
  if (!isActive) {
    return null;
  }

  return (
    <div className={`w-full max-w-2xl mx-auto bg-white border border-gray-200 rounded-lg ${className}`}>
      <div className="p-4 pb-2 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="text-2xl">🛡️</div>
          <div>
            <h3 className="text-lg font-semibold">ボディガード - 守り</h3>
            <p className="text-sm text-gray-600">
              今夜守るプレイヤーを選択してください
            </p>
          </div>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        {/* エラー表示 */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}

        {/* 守り結果表示 */}
        {protectionResult && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <div className="text-lg">✅</div>
              <h4 className="font-semibold text-green-800">守り完了</h4>
            </div>
            <p className="text-green-700">{protectionResult.message}</p>
            <p className="text-sm text-green-600 mt-1">
              {protectionResult.target}を今夜の攻撃から守ります
            </p>
          </div>
        )}

        {/* まだ守りを実行していない場合 */}
        {!protectionResult && (
          <>
            {/* 対象選択 */}
            <div>
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <span>守る対象を選択</span>
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                  {availableTargets.length}人
                </span>
              </h4>
              
              {availableTargets.length === 0 ? (
                <div className="p-4 bg-gray-50 rounded-lg text-center">
                  <p className="text-gray-600">守ることができる対象がいません</p>
                </div>
              ) : (
                <div className="grid gap-2">
                  {availableTargets.map((target) => (
                    <div
                      key={target.player_id}
                      className={`
                        p-3 border rounded-lg cursor-pointer transition-all
                        ${selectedTargetId === target.player_id 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }
                      `}
                      onClick={() => handleTargetSelect(target.player_id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <span className="text-sm font-medium text-blue-600">
                              {target.character_name[0]}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium">{target.character_name}</p>
                            <p className="text-xs text-gray-500">プレイヤー</p>
                          </div>
                        </div>
                        
                        {selectedTargetId === target.player_id && (
                          <div className="text-blue-500">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 実行ボタン */}
            <div className="flex justify-center pt-2">
              <button
                onClick={handleProtect}
                disabled={!selectedTargetId || !canProtect || isProtecting}
                className="min-w-32 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                {isProtecting ? '守り中...' : '守りを実行'}
              </button>
            </div>

            {/* 制限事項の説明 */}
            <div className="text-xs text-gray-500 space-y-1">
              <p>• 自分を守ることはできません</p>
              <p>• 同じプレイヤーを連続で守ることはできません</p>
              <p>• 一晩に一度だけ守ることができます</p>
            </div>
          </>
        )}

        {/* 守り完了後のメッセージ */}
        {protectionResult && (
          <div className="text-center text-sm text-gray-600">
            他のプレイヤーの行動完了をお待ちください...
          </div>
        )}
      </div>
    </div>
  );
}

export default BodyguardPanel;