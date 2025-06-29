import { useState } from 'react';
import { PlayerInfo } from '@/types/api';
import { useWerewolfAttack } from '@/hooks/useWerewolfAttack';

interface WerewolfPanelProps {
  roomId: string;
  playerId: string;
  isNightPhase: boolean;
  className?: string;
}

export default function WerewolfPanel({ 
  roomId, 
  playerId, 
  isNightPhase, 
  className = '' 
}: WerewolfPanelProps) {
  const [selectedTarget, setSelectedTarget] = useState<string>('');
  
  const {
    availableTargets,
    attackResult,
    isAttacking,
    canAttack,
    attack,
    error
  } = useWerewolfAttack(roomId, playerId);

  const handleAttack = async () => {
    if (!selectedTarget) return;
    await attack(selectedTarget);
  };

  if (!isNightPhase) {
    return null;
  }

  return (
    <div className={`p-4 bg-red-900/70 border border-red-600/50 rounded-lg backdrop-blur-sm ${className}`}>
      <h3 className="text-lg font-semibold mb-4 text-red-200 flex items-center gap-2">
        🐺 人狼の襲撃
      </h3>

      {/* エラー表示 */}
      {error && (
        <div className="mb-4 p-3 bg-red-800/50 border border-red-500/50 rounded-lg">
          <p className="text-red-200 text-sm">❌ {error}</p>
        </div>
      )}

      {/* 攻撃結果表示 */}
      {attackResult && (
        <div className="mb-4 p-3 bg-red-800/50 border border-red-500/50 rounded-lg">
          <p className="text-red-200 text-sm">✅ {attackResult.message}</p>
        </div>
      )}

      {/* 攻撃対象選択 */}
      {canAttack && !attackResult && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-red-200 mb-2">
              襲撃対象を選択してください:
            </label>
            
            {availableTargets.length === 0 ? (
              <div className="p-3 bg-gray-800/50 border border-gray-600/50 rounded-lg">
                <p className="text-gray-400 text-sm">襲撃可能な対象がいません</p>
              </div>
            ) : (
              <div className="space-y-2">
                {availableTargets.map((target) => (
                  <label 
                    key={target.player_id}
                    className="flex items-center gap-3 p-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-600/50 rounded-lg cursor-pointer transition-colors"
                  >
                    <input
                      type="radio"
                      name="attack_target"
                      value={target.player_id}
                      checked={selectedTarget === target.player_id}
                      onChange={(e) => setSelectedTarget(e.target.value)}
                      className="w-4 h-4 text-red-600 bg-gray-700 border-gray-600 focus:ring-red-500"
                    />
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-xs font-bold text-white">
                        {target.character_name.charAt(0)}
                      </div>
                      <span className="text-white font-medium">{target.character_name}</span>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* 攻撃実行ボタン */}
          <button
            onClick={handleAttack}
            disabled={!selectedTarget || isAttacking}
            className="w-full px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isAttacking ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                襲撃中...
              </>
            ) : (
              <>
                🗡️ 襲撃実行
              </>
            )}
          </button>
        </div>
      )}

      {/* 既に攻撃済みの場合 */}
      {!canAttack && attackResult && (
        <div className="p-3 bg-gray-800/50 border border-gray-600/50 rounded-lg">
          <p className="text-gray-400 text-sm">✅ 今夜の襲撃は完了しました。朝を待ちましょう。</p>
        </div>
      )}

      {/* 操作方法の説明 */}
      {canAttack && !attackResult && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-700/30 rounded-lg">
          <p className="text-red-300 text-xs">
            💡 村人陣営のプレイヤーを選択して襲撃してください。
            <br />
            ボディガードに守られている場合、攻撃は無効になります。
          </p>
        </div>
      )}
    </div>
  );
}