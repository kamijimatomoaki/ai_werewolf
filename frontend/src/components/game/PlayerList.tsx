import { useState, useEffect } from 'react';
import { Button } from "@heroui/button";
import { Card } from "@heroui/card";
import { Input } from "@heroui/input";
import { Avatar } from "@heroui/avatar";
import { Chip } from "@heroui/chip";

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

  const canStartGame = gameStatus === 'waiting' && players.length === totalPlayers;
  const hasUnsetPersonas = players.some(p => !p.is_human && !p.character_persona);

  return (
    <Card className="p-4">
      <h2 className="text-xl font-semibold mb-4">
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
              <Avatar 
                name={player.character_name}
                size="sm"
                color={player.is_human ? "primary" : "secondary"}
                className={!player.is_alive ? 'opacity-60 grayscale' : ''}
              />
              <div className="flex-1 min-w-0">
                <p className={`font-medium truncate ${!player.is_alive ? 'opacity-60' : ''}`}>
                  {player.character_name}
                  {player.player_id === currentPlayerId && " (あなた)"}
                </p>
                <div className="flex gap-1 flex-wrap">
                  <Chip size="sm" variant="flat" color={player.is_human ? "primary" : "secondary"}>
                    {player.is_human ? "人間" : "AI"}
                  </Chip>
                  <Chip 
                    size="sm" 
                    variant="flat" 
                    color={player.is_alive ? "success" : "danger"}
                  >
                    {player.is_alive ? "生存" : "脱落"}
                  </Chip>
                  {player.role && gameStatus !== 'waiting' && (
                    <Chip size="sm" variant="flat" color="warning">
                      {player.role}
                    </Chip>
                  )}
                  {player.character_persona && (
                    <Chip size="sm" variant="flat" color="secondary">
                      ペルソナ設定済み
                    </Chip>
                  )}
                </div>
              </div>
            </div>
          </AnimatedPlayerCard>
        ))}
      </div>

      {/* AIペルソナ生成（待機中のみ） */}
      {gameStatus === 'waiting' && (
        <div className="mt-6 space-y-3">
          <h3 className="font-semibold">AIペルソナ生成</h3>
          
          {players.filter(p => !p.is_human && !p.character_persona).length === 0 ? (
            <div className="text-sm text-gray-600 p-3 bg-green-50 rounded-lg border border-green-200">
              ✅ すべてのAIプレイヤーにペルソナが設定されました
            </div>
          ) : (
            <div className="text-sm text-gray-600 mb-3">
              AIプレイヤーにキャラクター設定を生成します
            </div>
          )}

          {players.filter(p => !p.is_human && !p.character_persona).map((player) => (
            <div key={player.player_id} className="space-y-2 p-3 bg-white rounded-lg border">
              <div className="flex items-center gap-2 mb-2">
                <Avatar name={player.character_name} size="sm" color="secondary" />
                <span className="font-medium">{player.character_name}</span>
              </div>
              
              <Input
                size="sm"
                placeholder="例: 冷静沈着, 探偵, 30代"
                value={personaKeywords[player.player_id] || ''}
                onChange={(e) => setPersonaKeywords(prev => ({
                  ...prev,
                  [player.player_id]: e.target.value
                }))}
                isDisabled={generatingPersona === player.player_id}
              />
              
              <Button
                size="sm"
                color="secondary"
                onClick={() => handleGeneratePersona(player.player_id)}
                isDisabled={
                  !personaKeywords[player.player_id]?.trim() || 
                  generatingPersona !== null
                }
                isLoading={generatingPersona === player.player_id}
                className="w-full"
              >
                {generatingPersona === player.player_id ? 'ペルソナ生成中...' : 'ペルソナ生成'}
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* ゲーム開始ボタン */}
      {gameStatus === 'waiting' && onStartGame && (
        <div className="mt-6">
          {!canStartGame && (
            <div className="mb-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <p className="text-sm text-yellow-700">
                {players.length < totalPlayers 
                  ? `ゲーム開始には${totalPlayers - players.length}人の参加が必要です`
                  : hasUnsetPersonas
                  ? 'すべてのAIプレイヤーにペルソナを設定してください'
                  : 'ゲーム開始の準備が整いました'
                }
              </p>
            </div>
          )}
          
          <Button
            color="primary"
            className="w-full"
            onClick={onStartGame}
            isLoading={isLoading}
            isDisabled={!canStartGame || hasUnsetPersonas}
            size="lg"
          >
            {isLoading ? 'ゲーム開始中...' : 'ゲーム開始'}
          </Button>
        </div>
      )}

      {/* ゲーム状態情報 */}
      {gameStatus !== 'waiting' && (
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm text-blue-700">
            ゲーム進行中 - 生存者: {players.filter(p => p.is_alive).length}人
          </p>
        </div>
      )}
    </Card>
  );
}