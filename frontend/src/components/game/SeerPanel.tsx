import { useState } from 'react';
// アイコンをSVGコンポーネントとして定義
const EyeIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.64 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.64 0-8.573-3.007-9.963-7.178z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const CheckIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
  </svg>
);

import { PlayerInfo } from '@/types/api';
import { useSeerInvestigation, SeerInvestigateResult } from '@/hooks/useSeerInvestigation';

interface SeerPanelProps {
  roomId: string;
  playerId: string;
  isActive: boolean; // 夜フェーズかつ占い師の場合のみtrue
  className?: string;
}

export default function SeerPanel({ roomId, playerId, isActive, className }: SeerPanelProps) {
  const [selectedTargetId, setSelectedTargetId] = useState<string>('');
  
  const {
    availableTargets,
    investigationResult,
    isInvestigating,
    canInvestigate,
    error,
    investigate,
    clearResult
  } = useSeerInvestigation({ roomId, playerId, isActive });

  const handleInvestigate = async () => {
    if (!selectedTargetId || !canInvestigate) return;
    
    try {
      await investigate(selectedTargetId);
      setSelectedTargetId(''); // 選択をクリア
    } catch (err) {
      // エラーはフックで管理される
    }
  };

  const handleTargetSelect = (targetId: string) => {
    if (isInvestigating || !canInvestigate) return;
    setSelectedTargetId(targetId === selectedTargetId ? '' : targetId);
  };

  if (!isActive) {
    return null; // 非アクティブ時は何も表示しない
  }

  return (
    <div className={`p-4 bg-purple-900/20 border border-purple-500/50 rounded-lg backdrop-blur-sm ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <EyeIcon className="w-6 h-6 text-purple-400" />
        <div>
          <h3 className="text-lg font-semibold text-purple-200">占い師の能力</h3>
          <p className="text-sm text-purple-300">一人を選んで占ってください</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg">
          <p className="text-red-300 text-sm font-medium">エラー: {error}</p>
        </div>
      )}

      {/* 占い結果表示 */}
      {investigationResult && (
        <div className="mb-4 p-4 bg-gray-800/70 border border-purple-500/50 rounded-lg backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-2">
            <CheckIcon className="w-5 h-5 text-green-400" />
            <h4 className="font-semibold text-purple-200">占い結果</h4>
          </div>
          <div className="space-y-2">
            <p className="text-sm">
              <span className="font-medium">{investigationResult.target}</span> を占いました
            </p>
            <div className="flex items-center gap-2">
              <span className="text-sm">結果:</span>
              <span 
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  investigationResult.result === '人狼' 
                    ? 'bg-red-900/30 text-red-300 border border-red-500/50' 
                    : 'bg-green-900/30 text-green-300 border border-green-500/50'
                }`}
              >
                {investigationResult.result}
              </span>
            </div>
            <p className="text-xs text-gray-300">{investigationResult.message}</p>
          </div>
          <button
            onClick={clearResult}
            className="mt-2 px-3 py-1 text-sm text-gray-300 hover:text-white bg-transparent hover:bg-gray-700/50 rounded transition-colors"
          >
            結果を閉じる
          </button>
        </div>
      )}

      {/* 占い対象選択 */}
      {canInvestigate && availableTargets.length > 0 ? (
        <div className="space-y-4">
          <h4 className="font-medium text-purple-200">占い対象を選択:</h4>
          
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {availableTargets.map((target) => (
              <div
                key={target.player_id}
                className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                  selectedTargetId === target.player_id
                    ? 'bg-purple-900/40 border-purple-500/60 shadow-md'
                    : 'bg-gray-800/50 border-gray-600/50 hover:bg-gray-700/50 hover:border-gray-500/50'
                } ${isInvestigating ? 'opacity-50 cursor-not-allowed' : ''}`}
                onClick={() => handleTargetSelect(target.player_id)}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                    target.is_human ? 'bg-blue-500' : 'bg-gray-500'
                  }`}>
                    {target.character_name.charAt(0)}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-white">
                      {target.character_name}
                    </p>
                    <div className="flex gap-1 mt-1">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        target.is_human 
                          ? 'bg-blue-500/20 text-blue-400 border border-blue-400/50' 
                          : 'bg-gray-500/20 text-gray-400 border border-gray-400/50'
                      }`}>
                        {target.is_human ? "人間" : "AI"}
                      </span>
                    </div>
                  </div>
                  {selectedTargetId === target.player_id && (
                    <CheckIcon className="w-5 h-5 text-purple-400" />
                  )}
                </div>
              </div>
            ))}
          </div>

          <hr className="border-gray-600" />

          <div className="flex gap-3">
            <button
              onClick={handleInvestigate}
              disabled={!selectedTargetId || !canInvestigate || isInvestigating}
              className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <EyeIcon className="w-4 h-4" />
              {isInvestigating ? '占い中...' : '占う'}
            </button>
            
            {selectedTargetId && (
              <button
                onClick={() => setSelectedTargetId('')}
                disabled={isInvestigating}
                className="px-4 py-2 border border-gray-500/50 hover:bg-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed text-gray-300 rounded-lg transition-colors"
              >
                選択解除
              </button>
            )}
          </div>
        </div>
      ) : !canInvestigate && !investigationResult ? (
        <div className="text-center py-6">
          <div className="text-gray-500 mb-2">
            <EyeIcon className="w-8 h-8 mx-auto opacity-50" />
          </div>
          <p className="text-sm text-gray-300">今夜は既に占いを行いました</p>
        </div>
      ) : availableTargets.length === 0 ? (
        <div className="text-center py-6">
          <div className="text-gray-500 mb-2">
            <EyeIcon className="w-8 h-8 mx-auto opacity-50" />
          </div>
          <p className="text-sm text-gray-300">占える対象がいません</p>
        </div>
      ) : null}

      {/* 占い師としての説明 */}
      {canInvestigate && (
        <div className="mt-4 p-3 bg-purple-900/20 rounded-lg border border-purple-500/30">
          <p className="text-xs text-purple-300">
            💡 占った相手が「人狼」か「村人」かを知ることができます。
            一晩に一人だけ占うことができます。
          </p>
        </div>
      )}
    </div>
  );
}