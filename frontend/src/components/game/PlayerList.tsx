import { useState, useEffect } from 'react';

import { PlayerInfo } from '@/types/api';
import AnimatedCard, { AnimatedPlayerCard } from '@/components/ui/AnimatedCard';
import { useStaggerAnimation } from '@/hooks/useAnimations';

interface PlayerListProps {
  players: PlayerInfo[];
  currentPlayerId?: string;
  gameStatus: string;
  totalPlayers: number;
  onGeneratePersona: (playerId: string, keywords: string) => Promise<void>;
  onStartGame?: () => Promise<void>;
  isLoading?: boolean;
}

export default function PlayerList({
  players,
  currentPlayerId,
  gameStatus,
  totalPlayers,
  onGeneratePersona,
  onStartGame,
  isLoading = false
}: PlayerListProps) {
  const [personaKeywords, setPersonaKeywords] = useState<{[playerId: string]: string}>({});
  const [generatingPersona, setGeneratingPersona] = useState<string | null>(null);
  
  // アニメーション制御
  const { showItems, isVisible } = useStaggerAnimation();

  // プレイヤーリストが更新された時にステガーアニメーションを開始
  useEffect(() => {
    const playerIds = players.map(p => p.player_id);
    showItems(playerIds, 100); // 100msずつずらしてアニメーション
  }, [players, showItems]);

  const handleGeneratePersona = async (playerId: string) => {
    const keywords = personaKeywords[playerId];
    if (!keywords?.trim()) return;

    try {
      setGeneratingPersona(playerId);
      await onGeneratePersona(playerId, keywords);
      // 成功時にキーワードをクリア
      setPersonaKeywords(prev => ({
        ...prev,
        [playerId]: ''
      }));
    } catch (error) {
      // エラーハンドリングは親コンポーネントで行う
    } finally {
      setGeneratingPersona(null);
    }
  };

  const handleBulkGeneratePersona = async () => {
    const unsetPersonaPlayers = players.filter(p => !p.is_human && !p.character_persona);
    
    try {
      // 全プレイヤーを順次生成（並列だとAPI制限に引っかかる可能性があるため）
      for (const player of unsetPersonaPlayers) {
        const keywords = personaKeywords[player.player_id];
        if (keywords?.trim()) {
          setGeneratingPersona(player.player_id);
          await onGeneratePersona(player.player_id, keywords);
        }
      }
      
      // 成功後、全てのキーワードをクリア
      setPersonaKeywords(prev => {
        const newKeywords = { ...prev };
        unsetPersonaPlayers.forEach(player => {
          newKeywords[player.player_id] = '';
        });
        return newKeywords;
      });
    } catch (error) {
      console.error('Failed to bulk generate personas:', error);
    } finally {
      setGeneratingPersona(null);
    }
  };

  const canStartGame = gameStatus === 'waiting' && players.length === totalPlayers;
  const hasUnsetPersonas = players.some(p => !p.character_persona); // 全プレイヤー（人間含む）をチェック

  return (
    <div className="p-4 bg-gray-800/70 border border-gray-600/50 rounded-lg backdrop-blur-sm">
      <h2 className="text-xl font-semibold mb-4 text-white">
        プレイヤー ({players.length}/{totalPlayers})
      </h2>
      
      {/* プレイヤー一覧 */}
      <div className="space-y-3">
        {players.map((player, index) => (
          <AnimatedPlayerCard
            key={player.player_id}
            isEliminated={!player.is_alive}
            isRevealed={gameStatus === 'finished'}
            playerRole={player.role}
            className={`transition-all duration-300 ${
              isVisible(player.player_id) ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}
            onReveal={() => console.log(`${player.character_name}の役職が公開されました`)}
          >
            <div className="flex items-center gap-3 p-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                player.is_human ? 'bg-blue-500 text-white' : 'bg-gray-500 text-white'
              } ${!player.is_alive ? 'opacity-60 grayscale' : ''}`}>
                {player.character_name.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`font-medium truncate text-white ${!player.is_alive ? 'opacity-60' : ''}`}>
                  {player.character_name}
                  {player.player_id === currentPlayerId && " (あなた)"}
                </p>
                <div className="flex gap-1 flex-wrap">
                  <span className={`px-2 py-1 text-xs rounded ${
                    player.is_human ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {player.is_human ? "人間" : "AI"}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded ${
                    player.is_alive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {player.is_alive ? "生存" : "脱落"}
                  </span>
                  {player.role && (gameStatus === 'finished' || player.player_id === currentPlayerId) && (
                    <span className="px-2 py-1 text-xs rounded bg-yellow-500/20 text-yellow-400">
                      {player.role}
                    </span>
                  )}
                  {player.character_persona && (
                    <div className="w-full mt-2">
                      <div className="p-3 bg-gradient-to-r from-slate-800/90 to-slate-700/90 border border-slate-400/50 rounded-lg backdrop-blur-sm shadow-lg">
                        <p className="text-xs font-semibold text-slate-200 mb-1">ペルソナ:</p>
                        {player.character_persona.name && (
                          <p className="text-sm font-bold text-blue-200 mb-2">
                            キャラクター名: {player.character_persona.name}
                          </p>
                        )}
                        <p className="text-sm text-white leading-relaxed">
                          <span className="font-medium">{player.character_persona.age}歳の{player.character_persona.gender}</span>。
                          <span className="text-slate-100">{player.character_persona.personality}</span>。
                          <span className="text-slate-100">{player.character_persona.speech_style}で話す</span>。
                          {player.character_persona.background && (
                            <span className="block mt-2 text-xs text-slate-200 bg-slate-700/50 px-2 py-1 rounded">
                              背景: {player.character_persona.background}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </AnimatedPlayerCard>
        ))}
      </div>

      {/* ペルソナ生成（待機中のみ） */}
      {gameStatus === 'waiting' && (
        <div className="mt-6 space-y-3">
          <h3 className="font-semibold text-lg">プレイヤーペルソナ設定</h3>
          
          {players.filter(p => !p.character_persona).length === 0 ? (
            <div className="text-sm text-green-200 p-4 bg-green-600/20 rounded-lg border border-green-500/30 backdrop-blur-sm">
              ✅ すべてのプレイヤーにペルソナが設定されました
            </div>
          ) : (
            <>
              <div className="text-sm text-blue-200 mb-4 p-3 bg-blue-600/20 rounded-lg border border-blue-500/30 backdrop-blur-sm">
                💡 各プレイヤーのキャラクター特徴を入力して、ペルソナを生成できます
                <br />
                <span className="text-xs text-blue-300">✨ 人間プレイヤーも公平性のためペルソナ設定が可能です</span>
              </div>
              
              <div className="space-y-4">
                {/* 各プレイヤーのキーワード入力 */}
                {players.filter(p => !p.character_persona).map((player) => (
                  <div key={player.player_id} className="space-y-2 p-4 bg-gradient-to-r from-gray-700/60 to-gray-600/60 rounded-lg border border-gray-500/40 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                        player.is_human ? 'bg-blue-500 text-white' : 'bg-gray-500 text-white'
                      }`}>
                        {player.character_name.charAt(0)}
                      </div>
                      <span className="font-medium text-white">{player.character_name}</span>
                      <span className={`px-2 py-1 text-xs rounded ${
                        player.is_human ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'
                      }`}>
                        {player.is_human ? "人間" : "AI"}
                      </span>
                      {player.player_id === currentPlayerId && (
                        <span className="px-2 py-1 text-xs rounded bg-green-500/20 text-green-400">
                          あなた
                        </span>
                      )}
                      {generatingPersona === player.player_id && (
                        <span className="px-2 py-1 text-xs rounded bg-yellow-500/20 text-yellow-400">
                          生成中...
                        </span>
                      )}
                    </div>
                    
                    <textarea
                      className="w-full p-3 bg-gray-700/80 border border-gray-400/50 rounded-lg resize-none focus:border-red-400 focus:ring-2 focus:ring-red-400/30 text-sm text-white placeholder-gray-300 backdrop-blur-sm transition-all"
                      rows={2}
                      placeholder={player.is_human 
                        ? "例: 慎重派, 会社員, 20代, 論理的思考" 
                        : "例: 冷静沈着, 探偵, 30代, 鋭い観察力"
                      }
                      value={personaKeywords[player.player_id] || ''}
                      onChange={(e) => setPersonaKeywords(prev => ({
                        ...prev,
                        [player.player_id]: e.target.value
                      }))}
                      disabled={generatingPersona !== null}
                    />
                  </div>
                ))}
                
                {/* 一括生成ボタン */}
                <div className="pt-2">
                  <button
                    onClick={handleBulkGeneratePersona}
                    disabled={
                      generatingPersona !== null ||
                      !players.filter(p => !p.is_human && !p.character_persona).some(p => personaKeywords[p.player_id]?.trim())
                    }
                    className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {generatingPersona ? null : <span>🎭</span>}
                    {generatingPersona ? 'ペルソナ生成中...' : 'すべてのペルソナを一括生成'}
                  </button>
                  
                  {players.filter(p => !p.is_human && !p.character_persona).some(p => personaKeywords[p.player_id]?.trim()) && (
                    <p className="text-xs text-gray-300 mt-2 text-center">
                      💡 キーワードが入力されたキャラクターのペルソナを順次生成します
                    </p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ゲーム開始ボタン */}
      {gameStatus === 'waiting' && onStartGame && (
        <div className="mt-6">
          {!canStartGame && (
            <div className="mb-3 p-3 bg-yellow-900/20 rounded-lg border border-yellow-500/30">
              <p className="text-sm text-yellow-200">
                {players.length < totalPlayers 
                  ? `ゲーム開始には${totalPlayers - players.length}人の参加が必要です`
                  : hasUnsetPersonas
                  ? 'すべてのプレイヤーにペルソナを設定してください（公平性のため）'
                  : 'ゲーム開始の準備が整いました'
                }
              </p>
            </div>
          )}
          
          <button
            onClick={onStartGame}
            disabled={isLoading || !canStartGame || hasUnsetPersonas}
            className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            {isLoading ? 'ゲーム開始中...' : 'ゲーム開始'}
          </button>
        </div>
      )}

      {/* ゲーム状態情報 */}
      {gameStatus !== 'waiting' && (
        <div className="mt-4 p-3 bg-blue-900/20 rounded-lg border border-blue-500/30">
          <p className="text-sm text-blue-200">
            ゲーム進行中 - 生存者: {players.filter(p => p.is_alive).length}人
          </p>
        </div>
      )}
    </div>
  );
}