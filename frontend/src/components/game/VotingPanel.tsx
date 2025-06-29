import { useState } from 'react';

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
  const safePlayers = players || [];
  const votableTargets = safePlayers.filter(p => p.is_alive && p.player_id !== currentPlayerId);

  return (
    <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg backdrop-blur-sm">
      <div className="flex items-center gap-3 mb-4">
        <VoteIcon className="w-6 h-6 text-red-400" />
        <div>
          <h3 className="text-lg font-semibold text-red-200">
            {voteResult?.is_revote ? '再投票フェーズ' : '投票フェーズ'}
          </h3>
          <p className="text-sm text-red-300">
            {voteResult?.is_revote ? '同票のため再投票を行います。処刑したいプレイヤーに投票してください' : '処刑したいプレイヤーに投票してください'}
          </p>
        </div>
      </div>

      {/* 投票結果表示（再投票時は除く） */}
      {voteResult && !voteResult.is_revote ? (
        <div className="space-y-4">
          <h4 className="font-semibold text-red-200">投票結果</h4>
          
          {/* 投票数表示 */}
          <div className="space-y-2">
            {Object.entries(voteResult.vote_counts).map(([playerId, count]) => {
              const player = players.find(p => p.player_id === playerId);
              return (
                <div key={playerId} className="flex justify-between items-center p-3 bg-gradient-to-r from-gray-800/80 to-gray-700/80 border border-gray-600/50 rounded-lg backdrop-blur-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-500 text-white flex items-center justify-center text-xs font-bold">
                      {(player?.character_name || '不明').charAt(0)}
                    </div>
                    <span className="font-medium text-gray-200">{player?.character_name || '不明'}</span>
                  </div>
                  <span className="px-2 py-1 text-xs rounded bg-red-500/20 text-red-400">
                    {count}票
                  </span>
                </div>
              );
            })}
          </div>

          <hr className="border-gray-600" />

          {/* 処刑結果 */}
          {voteResult.voted_out_player_id && (
            <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/50">
              <div className="flex items-center gap-2 mb-2">
                <WarningIcon className="w-5 h-5 text-red-400" />
                <h5 className="font-semibold text-red-200">処刑決定</h5>
              </div>
              <p className="text-red-300">
                <span className="font-medium">
                  {players.find(p => p.player_id === voteResult.voted_out_player_id)?.character_name}
                </span>
                が投票により処刑されました
              </p>
            </div>
          )}

          {/* 同票の場合 */}
          {voteResult.tied_vote && (
            <div className="p-4 bg-orange-900/30 rounded-lg border border-orange-500/50">
              <div className="flex items-center gap-2 mb-2">
                <WarningIcon className="w-5 h-5 text-orange-400" />
                <h5 className="font-semibold text-orange-200">同票</h5>
              </div>
              <p className="text-orange-300">
                同票のため誰も処刑されませんでした
              </p>
            </div>
          )}

          <p className="text-sm text-gray-300 bg-gray-800/50 p-3 rounded border border-gray-600/50">
            {voteResult.message}
          </p>
        </div>
      ) : (
        /* 投票UI */
        <div className="space-y-4">
          {votableTargets.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-400">投票できる対象がいません</p>
            </div>
          ) : (
            <>
              {/* 投票対象一覧 */}
              <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin">
                {votableTargets.map((player) => (
                  <div
                    key={player.player_id}
                    className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                      selectedVoteTarget === player.player_id
                        ? 'bg-red-900/40 border-red-500/60 shadow-md'
                        : 'bg-gray-800/50 border-gray-600/50 hover:bg-gray-700/50 hover:border-gray-500/50'
                    } ${isVoting || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    onClick={() => handleTargetSelect(player.player_id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-bold">
                        {player.character_name.charAt(0)}
                      </div>
                      <div className="flex-1">
                        <span className="font-medium text-white">{player.character_name}</span>
                        <div className="flex gap-1 mt-1">
                          <span className={`px-2 py-1 text-xs rounded ${
                            player.is_human ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            {player.is_human ? "人間" : "AI"}
                          </span>
                        </div>
                      </div>
                      {selectedVoteTarget === player.player_id && (
                        <span className="px-2 py-1 text-xs rounded bg-red-500/30 text-red-300">
                          選択中
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <hr className="border-gray-600" />

              {/* 投票ボタン */}
              <div className="space-y-3">
                {selectedVoteTarget && (
                  <div className="p-3 bg-red-900/30 rounded-lg border border-red-500/50">
                    <p className="text-sm text-red-300">
                      <span className="font-medium">
                        {players.find(p => p.player_id === selectedVoteTarget)?.character_name}
                      </span>
                      に投票しますか？
                    </p>
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={handleVote}
                    disabled={isVoting || !selectedVoteTarget || isLoading}
                    className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors flex items-center justify-center gap-2"
                  >
                    <VoteIcon className="w-4 h-4" />
                    {isVoting ? '投票中...' : '投票する'}
                  </button>

                  {selectedVoteTarget && (
                    <button
                      onClick={() => setSelectedVoteTarget('')}
                      disabled={isVoting || isLoading}
                      className="px-4 py-2 border border-orange-500/50 text-orange-300 hover:bg-orange-500/20 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors"
                    >
                      選択解除
                    </button>
                  )}
                </div>
              </div>

            </>
          )}
        </div>
      )}
    </div>
  );
}