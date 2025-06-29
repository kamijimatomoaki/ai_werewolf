import { useState, useEffect } from 'react';
import { apiService } from '@/services/api';

interface GameEndModalProps {
  roomId: string;
  isOpen: boolean;
  onClose: () => void;
  onBackToLobby: () => void;
}

interface Player {
  player_id: string;
  character_name: string;
  role: string;
  is_alive: boolean;
  is_human: boolean;
  faction: string;
  is_winner: boolean;
}

interface GameEndData {
  room_id: string;
  game_result: {
    game_over: boolean;
    winner: string;
    winner_faction: string;
    victory_message: string;
    final_day: number;
    total_days: number;
  };
  players: Player[];
  game_statistics: {
    total_players: number;
    human_players: number;
    ai_players: number;
    werewolves_count: number;
    villagers_count: number;
  };
  important_events: Array<{
    day: number;
    phase: string;
    event_type: string;
    content: string;
    timestamp: string;
  }>;
  game_summary: string;
  timestamp: string;
}

const RoleIcon = ({ role }: { role: string }) => {
  const roleConfig = {
    werewolf: { icon: '🐺', color: 'text-red-400', bgColor: 'bg-red-900/30' },
    seer: { icon: '🔮', color: 'text-blue-400', bgColor: 'bg-blue-900/30' },
    bodyguard: { icon: '🛡️', color: 'text-green-400', bgColor: 'bg-green-900/30' },
    madman: { icon: '🎭', color: 'text-purple-400', bgColor: 'bg-purple-900/30' },
    villager: { icon: '👤', color: 'text-gray-400', bgColor: 'bg-gray-900/30' }
  };
  
  const config = roleConfig[role as keyof typeof roleConfig] || roleConfig.villager;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${config.color} ${config.bgColor}`}>
      {config.icon} {role}
    </span>
  );
};

export default function GameEndModal({ roomId, isOpen, onClose, onBackToLobby }: GameEndModalProps) {
  const [gameEndData, setGameEndData] = useState<GameEndData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'players' | 'events'>('summary');

  const fetchGameResult = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/rooms/${roomId}/game_result`);
      if (!response.ok) {
        throw new Error('Failed to fetch game result');
      }
      
      const data = await response.json();
      setGameEndData(data);
    } catch (err: any) {
      console.error('Game result fetch error:', err);
      setError(err.message || 'ゲーム結果の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && roomId) {
      fetchGameResult();
    }
  }, [isOpen, roomId]);

  if (!isOpen) return null;

  const getRoleDisplayName = (role: string) => {
    const roleNames = {
      werewolf: '人狼',
      seer: '占い師',
      bodyguard: 'ボディガード',
      madman: '狂人',
      villager: '村人'
    };
    return roleNames[role as keyof typeof roleNames] || role;
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden bg-gray-900 border border-gray-700 rounded-lg">
        <div className="p-6">
          {/* ヘッダー */}
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-3">
              <div className="text-2xl">🎉</div>
              <div>
                <h2 className="text-xl font-bold text-white">ゲーム終了</h2>
                {gameEndData && (
                  <p className="text-sm text-gray-400">
                    {gameEndData.game_result.total_days}日間の戦いが終了
                  </p>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                className="px-3 py-1 text-sm border border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white rounded transition-colors"
                onClick={onBackToLobby}
              >
                ロビーに戻る
              </button>
              <button
                className="px-3 py-1 text-sm border border-red-500 text-red-400 hover:bg-red-500 hover:text-white rounded transition-colors"
                onClick={onClose}
              >
                閉じる
              </button>
            </div>
          </div>

          {loading && (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-300">結果を読み込み中...</span>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-900/50 border border-red-700 rounded-lg mb-4">
              <p className="text-red-200">{error}</p>
              <button
                className="mt-2 px-3 py-1 text-sm border border-red-500 text-red-400 hover:bg-red-500 hover:text-white rounded transition-colors"
                onClick={fetchGameResult}
              >
                再試行
              </button>
            </div>
          )}

          {gameEndData && (
            <div className="max-h-[70vh] overflow-y-auto scrollbar-thin">
              {/* 勝利情報 */}
              <div className="mb-6 p-4 bg-gradient-to-r from-yellow-900/30 to-orange-900/30 border border-yellow-600/50 rounded-lg">
                <div className="text-center">
                  <h3 className="text-2xl font-bold text-yellow-400 mb-2">
                    🏆 {gameEndData.game_result.winner_faction} 勝利！
                  </h3>
                  <p className="text-gray-300">{gameEndData.game_result.victory_message}</p>
                </div>
              </div>

              {/* タブナビゲーション */}
              <div className="border-b border-gray-700 mb-4">
                <div className="flex space-x-8">
                  <button
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'summary'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                    }`}
                    onClick={() => setActiveTab('summary')}
                  >
                    総括
                  </button>
                  <button
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'players'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                    }`}
                    onClick={() => setActiveTab('players')}
                  >
                    役職開示
                  </button>
                  <button
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'events'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                    }`}
                    onClick={() => setActiveTab('events')}
                  >
                    重要な出来事
                  </button>
                </div>
              </div>

              {/* タブコンテンツ */}
              {activeTab === 'summary' && (
                <div className="space-y-4">
                  {/* ゲーム統計 */}
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <h3 className="font-semibold text-white mb-3">ゲーム統計</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-400">総プレイヤー</p>
                        <p className="text-white font-medium">{gameEndData.game_statistics.total_players}人</p>
                      </div>
                      <div>
                        <p className="text-gray-400">人間</p>
                        <p className="text-white font-medium">{gameEndData.game_statistics.human_players}人</p>
                      </div>
                      <div>
                        <p className="text-gray-400">AI</p>
                        <p className="text-white font-medium">{gameEndData.game_statistics.ai_players}人</p>
                      </div>
                      <div>
                        <p className="text-gray-400">期間</p>
                        <p className="text-white font-medium">{gameEndData.game_result.total_days}日</p>
                      </div>
                    </div>
                  </div>

                  {/* AIサマリー */}
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <h3 className="font-semibold text-white mb-3">ゲーム総括</h3>
                    <p className="text-gray-300 leading-relaxed">
                      {gameEndData.game_summary}
                    </p>
                  </div>
                </div>
              )}

              {activeTab === 'players' && (
                <div className="space-y-4">
                  {/* 勝利者 */}
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                      🏆 勝利者
                    </h3>
                    <div className="space-y-2">
                      {gameEndData.players.filter(p => p.is_winner).map((player) => (
                        <div key={player.player_id} className="flex items-center justify-between p-3 bg-green-900/20 border border-green-600/30 rounded">
                          <div className="flex items-center gap-3">
                            <span className="text-white font-medium">{player.character_name}</span>
                            <RoleIcon role={player.role} />
                            <span className="text-xs text-gray-400">
                              {player.is_human ? '人間' : 'AI'}
                            </span>
                          </div>
                          <span className="text-green-400 text-sm">{player.faction}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 敗北者 */}
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                      💔 敗北者
                    </h3>
                    <div className="space-y-2">
                      {gameEndData.players.filter(p => !p.is_winner).map((player) => (
                        <div key={player.player_id} className="flex items-center justify-between p-3 bg-gray-700/50 border border-gray-600/30 rounded">
                          <div className="flex items-center gap-3">
                            <span className={`font-medium ${player.is_alive ? 'text-white' : 'text-gray-400 line-through'}`}>
                              {player.character_name}
                            </span>
                            <RoleIcon role={player.role} />
                            <span className="text-xs text-gray-400">
                              {player.is_human ? '人間' : 'AI'}
                            </span>
                            {!player.is_alive && (
                              <span className="text-xs text-red-400">死亡</span>
                            )}
                          </div>
                          <span className="text-gray-400 text-sm">{player.faction}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'events' && (
                <div className="space-y-4">
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <h3 className="font-semibold text-white mb-3">重要な出来事</h3>
                    {gameEndData.important_events.length > 0 ? (
                      <div className="space-y-2">
                        {gameEndData.important_events.map((event, index) => (
                          <div key={index} className="p-3 bg-gray-700 rounded border-l-4 border-blue-500">
                            <div className="flex justify-between items-start">
                              <p className="text-gray-300 text-sm">{event.content}</p>
                              <span className="text-xs text-gray-500 ml-2">
                                {event.day}日目 {event.phase}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-400 text-center py-4">記録された重要な出来事はありません</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}