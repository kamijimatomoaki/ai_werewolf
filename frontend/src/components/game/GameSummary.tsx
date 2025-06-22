import { useState, useEffect } from 'react';

interface GameSummaryProps {
  roomId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface SummaryData {
  room_id: string;
  day_number: number;
  current_phase: string;
  summary: {
    llm_summary: string;
    player_status: {
      生存者: Array<{ name: string; type: string }>;
      死亡者: Array<{ name: string; type: string }>;
    };
    daily_activities: Record<string, any>;
    current_phase: {
      day: number;
      phase: string;
      round?: number;
    };
  };
}

const InfoIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
  </svg>
);

const UserIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
);

const ClockIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export default function GameSummary({ roomId, isOpen, onClose }: GameSummaryProps) {
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'players' | 'activity'>('overview');

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/rooms/${roomId}/summary`);
      if (!response.ok) {
        throw new Error('サマリーの取得に失敗しました');
      }
      
      const data = await response.json();
      setSummaryData(data);
    } catch (err: any) {
      setError(err.message || 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && roomId) {
      fetchSummary();
    }
  }, [isOpen, roomId]);

  if (!isOpen) return null;

  const getPhaseLabel = (phase: string) => {
    switch (phase) {
      case 'waiting': return '待機中';
      case 'day_discussion': return '昼の議論';
      case 'day_vote': return '投票中';
      case 'night': return '夜';
      default: return phase;
    }
  };

  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'waiting': return 'success';
      case 'day_discussion': return 'warning';
      case 'day_vote': return 'danger';
      case 'night': return 'secondary';
      default: return 'default';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden bg-gray-900 border border-gray-700 rounded-lg">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-3">
              <InfoIcon className="w-6 h-6 text-blue-400" />
              <h2 className="text-xl font-bold text-white">ゲーム状況サマリー</h2>
            </div>
            <button
              className="px-3 py-1 text-sm border border-red-500 text-red-400 hover:bg-red-500 hover:text-white rounded transition-colors"
              onClick={onClose}
            >
              閉じる
            </button>
          </div>

          {loading && (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-300">サマリーを生成中...</span>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-900/50 border border-red-700 rounded-lg mb-4">
              <p className="text-red-200">{error}</p>
              <button
                className="mt-2 px-3 py-1 text-sm border border-red-500 text-red-400 hover:bg-red-500 hover:text-white rounded transition-colors"
                onClick={fetchSummary}
              >
                再試行
              </button>
            </div>
          )}

          {summaryData && (
            <div className="max-h-[70vh] overflow-y-auto scrollbar-thin">
              {/* Tab Navigation */}
              <div className="border-b border-gray-700 mb-4">
                <div className="flex space-x-8">
                  <button
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'overview'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                    }`}
                    onClick={() => setActiveTab('overview')}
                  >
                    概要
                  </button>
                  <button
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'players'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                    }`}
                    onClick={() => setActiveTab('players')}
                  >
                    プレイヤー
                  </button>
                  <button
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'activity'
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                    }`}
                    onClick={() => setActiveTab('activity')}
                  >
                    活動履歴
                  </button>
                </div>
              </div>

              {/* Tab Content */}
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  {/* 現在の状況 */}
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <ClockIcon className="w-5 h-5 text-orange-400" />
                      <h3 className="font-semibold text-white">現在の状況</h3>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <p className="text-gray-400 text-sm">ゲーム日数</p>
                        <p className="text-white font-medium">{summaryData.summary.current_phase.day}日目</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-sm">フェーズ</p>
                        <span className={`inline-block px-2 py-1 text-xs rounded ${
                          getPhaseColor(summaryData.summary.current_phase.phase) === 'success' ? 'bg-green-500/20 text-green-400' :
                          getPhaseColor(summaryData.summary.current_phase.phase) === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                          getPhaseColor(summaryData.summary.current_phase.phase) === 'danger' ? 'bg-red-500/20 text-red-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {getPhaseLabel(summaryData.summary.current_phase.phase)}
                        </span>
                      </div>
                      {summaryData.summary.current_phase.round && (
                        <div>
                          <p className="text-gray-400 text-sm">ラウンド</p>
                          <p className="text-white font-medium">{summaryData.summary.current_phase.round}/3</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AIサマリー */}
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <h3 className="font-semibold text-white mb-3">状況分析</h3>
                    <p className="text-gray-300 leading-relaxed">
                      {summaryData.summary.llm_summary}
                    </p>
                  </div>
                </div>
              )}

              {activeTab === 'players' && (
                <div className="space-y-4">
                  {/* 生存者 */}
                  <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <UserIcon className="w-5 h-5 text-green-400" />
                      <h3 className="font-semibold text-white">生存者 ({summaryData.summary.player_status.生存者.length}人)</h3>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {summaryData.summary.player_status.生存者.map((player, index) => (
                        <div key={index} className="flex items-center gap-2 p-2 bg-gray-700 rounded">
                          <span className="text-white text-sm">{player.name}</span>
                          <span className={`px-2 py-1 text-xs rounded ${
                            player.type === "人間" ? "bg-blue-500/20 text-blue-400" : "bg-gray-500/20 text-gray-400"
                          }`}>
                            {player.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 死亡者 */}
                  {summaryData.summary.player_status.死亡者.length > 0 && (
                    <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                      <div className="flex items-center gap-2 mb-3">
                        <UserIcon className="w-5 h-5 text-red-400" />
                        <h3 className="font-semibold text-white">死亡者 ({summaryData.summary.player_status.死亡者.length}人)</h3>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {summaryData.summary.player_status.死亡者.map((player, index) => (
                          <div key={index} className="flex items-center gap-2 p-2 bg-gray-700 rounded opacity-60">
                            <span className="text-gray-300 text-sm line-through">{player.name}</span>
                            <span className={`px-2 py-1 text-xs rounded ${
                              player.type === "人間" ? "bg-blue-500/20 text-blue-400" : "bg-gray-500/20 text-gray-400"
                            }`}>
                              {player.type}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'activity' && (
                <div className="space-y-4">
                  {Object.entries(summaryData.summary.daily_activities).map(([day, activities]: [string, any]) => (
                    <div key={day} className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                      <h3 className="font-semibold text-white mb-3">{day}</h3>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-3">
                        <div>
                          <p className="text-gray-400 text-sm">発言数</p>
                          <p className="text-white font-medium">{activities.発言数}回</p>
                        </div>
                        <div>
                          <p className="text-gray-400 text-sm">投票数</p>
                          <p className="text-white font-medium">{activities.投票数}票</p>
                        </div>
                      </div>
                      {activities.重要イベント.length > 0 && (
                        <div>
                          <p className="text-gray-400 text-sm mb-2">重要な出来事</p>
                          <div className="space-y-1">
                            {activities.重要イベント.map((event: string, index: number) => (
                              <p key={index} className="text-gray-300 text-sm bg-gray-700 p-2 rounded">
                                {event}
                              </p>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}