import { useState } from 'react';
import { Button } from "@heroui/button";
import { Card } from "@heroui/card";
import { Avatar } from "@heroui/avatar";
import { Chip } from "@heroui/chip";
import { Divider } from "@heroui/divider";
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
    <Card className={`p-4 bg-purple-50 border-purple-200 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <EyeIcon className="w-6 h-6 text-purple-600" />
        <div>
          <h3 className="text-lg font-semibold text-purple-800">占い師の能力</h3>
          <p className="text-sm text-purple-600">一人を選んで占ってください</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded-lg">
          <p className="text-red-700 text-sm font-medium">エラー: {error}</p>
        </div>
      )}

      {/* 占い結果表示 */}
      {investigationResult && (
        <div className="mb-4 p-4 bg-white border border-purple-200 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <CheckIcon className="w-5 h-5 text-green-600" />
            <h4 className="font-semibold text-purple-800">占い結果</h4>
          </div>
          <div className="space-y-2">
            <p className="text-sm">
              <span className="font-medium">{investigationResult.target}</span> を占いました
            </p>
            <div className="flex items-center gap-2">
              <span className="text-sm">結果:</span>
              <Chip 
                color={investigationResult.result === '人狼' ? 'danger' : 'success'}
                variant="flat"
                size="sm"
              >
                {investigationResult.result}
              </Chip>
            </div>
            <p className="text-xs text-gray-600">{investigationResult.message}</p>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={clearResult}
            className="mt-2"
          >
            結果を閉じる
          </Button>
        </div>
      )}

      {/* 占い対象選択 */}
      {canInvestigate && availableTargets.length > 0 ? (
        <div className="space-y-4">
          <h4 className="font-medium text-purple-700">占い対象を選択:</h4>
          
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {availableTargets.map((target) => (
              <div
                key={target.player_id}
                className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                  selectedTargetId === target.player_id
                    ? 'bg-purple-100 border-purple-300 shadow-md'
                    : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                } ${isInvestigating ? 'opacity-50 cursor-not-allowed' : ''}`}
                onClick={() => handleTargetSelect(target.player_id)}
              >
                <div className="flex items-center gap-3">
                  <Avatar 
                    name={target.character_name} 
                    size="sm"
                    color={target.is_human ? "primary" : "secondary"}
                  />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">
                      {target.character_name}
                    </p>
                    <div className="flex gap-1 mt-1">
                      <Chip size="sm" variant="flat" color={target.is_human ? "primary" : "secondary"}>
                        {target.is_human ? "人間" : "AI"}
                      </Chip>
                    </div>
                  </div>
                  {selectedTargetId === target.player_id && (
                    <CheckIcon className="w-5 h-5 text-purple-600" />
                  )}
                </div>
              </div>
            ))}
          </div>

          <Divider />

          <div className="flex gap-3">
            <Button
              color="secondary"
              onClick={handleInvestigate}
              isLoading={isInvestigating}
              isDisabled={!selectedTargetId || !canInvestigate}
              className="flex-1"
              startContent={<EyeIcon className="w-4 h-4" />}
            >
              {isInvestigating ? '占い中...' : '占う'}
            </Button>
            
            {selectedTargetId && (
              <Button
                variant="bordered"
                onClick={() => setSelectedTargetId('')}
                isDisabled={isInvestigating}
              >
                選択解除
              </Button>
            )}
          </div>
        </div>
      ) : !canInvestigate && !investigationResult ? (
        <div className="text-center py-6">
          <div className="text-gray-500 mb-2">
            <EyeIcon className="w-8 h-8 mx-auto opacity-50" />
          </div>
          <p className="text-sm text-gray-600">今夜は既に占いを行いました</p>
        </div>
      ) : availableTargets.length === 0 ? (
        <div className="text-center py-6">
          <div className="text-gray-500 mb-2">
            <EyeIcon className="w-8 h-8 mx-auto opacity-50" />
          </div>
          <p className="text-sm text-gray-600">占える対象がいません</p>
        </div>
      ) : null}

      {/* 占い師としての説明 */}
      {canInvestigate && (
        <div className="mt-4 p-3 bg-purple-100 rounded-lg">
          <p className="text-xs text-purple-700">
            💡 占った相手が「人狼」か「村人」かを知ることができます。
            一晩に一人だけ占うことができます。
          </p>
        </div>
      )}
    </Card>
  );
}