import { useState } from 'react';
import { Button } from "@heroui/button";
import { Card } from "@heroui/card";
import { Avatar } from "@heroui/avatar";
import { Chip } from "@heroui/chip";
import { Divider } from "@heroui/divider";

import { PlayerInfo } from '@/types/api';
import { VoteResult } from '@/services/api';

// アイコンコンポーネント
const VoteIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const WarningIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
  </svg>
);

interface VotingPanelProps {
  players: PlayerInfo[];
  currentPlayerId: string;
  voteResult?: VoteResult;
  onVote: (targetId: string) => Promise<void>;
  isLoading?: boolean;
}

export default function VotingPanel({
  players,
  currentPlayerId,
  voteResult,
  onVote,
  isLoading = false
}: VotingPanelProps) {
  const [selectedVoteTarget, setSelectedVoteTarget] = useState<string>('');
  const [isVoting, setIsVoting] = useState(false);

  const handleVote = async () => {
    if (!selectedVoteTarget) return;

    try {
      setIsVoting(true);
      await onVote(selectedVoteTarget);
      setSelectedVoteTarget(''); // 投票後は選択をクリア
    } catch (error) {
      // エラーハンドリングは親コンポーネントで行う
    } finally {
      setIsVoting(false);
    }
  };

  const handleTargetSelect = (playerId: string) => {
    if (isVoting || isLoading) return;
    setSelectedVoteTarget(playerId === selectedVoteTarget ? '' : playerId);
  };

  // 投票可能なプレイヤー（自分以外の生存者）
  const votableTargets = players.filter(p => p.is_alive && p.player_id !== currentPlayerId);

  return (
    <Card className="p-4 bg-red-50 border-red-200">
      <div className="flex items-center gap-3 mb-4">
        <VoteIcon className="w-6 h-6 text-red-600" />
        <div>
          <h3 className="text-lg font-semibold text-red-800">投票フェーズ</h3>
          <p className="text-sm text-red-600">処刑したいプレイヤーに投票してください</p>
        </div>
      </div>

      {/* 投票結果表示 */}
      {voteResult ? (
        <div className="space-y-4">
          <h4 className="font-semibold text-red-800">投票結果</h4>
          
          {/* 投票数表示 */}
          <div className="space-y-2">
            {Object.entries(voteResult.vote_counts).map(([playerId, count]) => {
              const player = players.find(p => p.player_id === playerId);
              return (
                <div key={playerId} className="flex justify-between items-center p-3 bg-gradient-to-r from-gray-800/80 to-gray-700/80 border border-gray-600/50 rounded-lg backdrop-blur-sm">
                  <div className="flex items-center gap-3">
                    <Avatar name={player?.character_name || '不明'} size="sm" />
                    <span className="font-medium text-gray-200">{player?.character_name || '不明'}</span>
                  </div>
                  <Chip size="sm" color="danger" variant="flat">
                    {count}票
                  </Chip>
                </div>
              );
            })}
          </div>

          <Divider />

          {/* 処刑結果 */}
          {voteResult.voted_out_player_id && (
            <div className="p-4 bg-red-100 rounded-lg border border-red-300">
              <div className="flex items-center gap-2 mb-2">
                <WarningIcon className="w-5 h-5 text-red-700" />
                <h5 className="font-semibold text-red-800">処刑決定</h5>
              </div>
              <p className="text-red-700">
                <span className="font-medium">
                  {players.find(p => p.player_id === voteResult.voted_out_player_id)?.character_name}
                </span>
                が投票により処刑されました
              </p>
            </div>
          )}

          {/* 同票の場合 */}
          {voteResult.tied_vote && (
            <div className="p-4 bg-orange-100 rounded-lg border border-orange-300">
              <div className="flex items-center gap-2 mb-2">
                <WarningIcon className="w-5 h-5 text-orange-700" />
                <h5 className="font-semibold text-orange-800">同票</h5>
              </div>
              <p className="text-orange-700">
                同票のため誰も処刑されませんでした
              </p>
            </div>
          )}

          <p className="text-sm text-gray-600 bg-white p-3 rounded border">
            {voteResult.message}
          </p>
        </div>
      ) : (
        /* 投票UI */
        <div className="space-y-4">
          {votableTargets.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-500">投票できる対象がいません</p>
            </div>
          ) : (
            <>
              {/* 投票対象一覧 */}
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {votableTargets.map((player) => (
                  <div
                    key={player.player_id}
                    className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                      selectedVoteTarget === player.player_id
                        ? 'bg-red-100 border-red-300 shadow-md'
                        : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                    } ${isVoting || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    onClick={() => handleTargetSelect(player.player_id)}
                  >
                    <div className="flex items-center gap-3">
                      <Avatar name={player.character_name} size="sm" />
                      <div className="flex-1">
                        <span className="font-medium">{player.character_name}</span>
                        <div className="flex gap-1 mt-1">
                          <Chip size="sm" variant="flat" color={player.is_human ? "primary" : "secondary"}>
                            {player.is_human ? "人間" : "AI"}
                          </Chip>
                        </div>
                      </div>
                      {selectedVoteTarget === player.player_id && (
                        <Chip size="sm" color="danger" variant="flat">
                          選択中
                        </Chip>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <Divider />

              {/* 投票ボタン */}
              <div className="space-y-3">
                {selectedVoteTarget && (
                  <div className="p-3 bg-red-100 rounded-lg border border-red-200">
                    <p className="text-sm text-red-700">
                      <span className="font-medium">
                        {players.find(p => p.player_id === selectedVoteTarget)?.character_name}
                      </span>
                      に投票しますか？
                    </p>
                  </div>
                )}

                <div className="flex gap-3">
                  <Button
                    color="danger"
                    onClick={handleVote}
                    isLoading={isVoting}
                    isDisabled={!selectedVoteTarget || isLoading}
                    className="flex-1"
                    startContent={<VoteIcon className="w-4 h-4" />}
                  >
                    {isVoting ? '投票中...' : '投票する'}
                  </Button>

                  {selectedVoteTarget && (
                    <Button
                      variant="bordered"
                      color="warning"
                      onClick={() => setSelectedVoteTarget('')}
                      isDisabled={isVoting || isLoading}
                      className="border-orange-500/50 text-orange-300 hover:bg-orange-500/20"
                    >
                      選択解除
                    </Button>
                  )}
                </div>
              </div>

              {/* 投票のヒント */}
              <div className="p-3 bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-lg backdrop-blur-sm">
                <p className="text-xs text-blue-200">
                  💡 これまでの議論を振り返り、最も怪しいと思うプレイヤーに投票しましょう。
                  投票は一度しかできません。
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
}