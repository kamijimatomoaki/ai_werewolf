import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Switch コンポーネントの代替実装
const Switch = ({ children, isSelected, onValueChange, size }: { 
  children: React.ReactNode; 
  isSelected: boolean; 
  onValueChange: (checked: boolean) => void; 
  size?: string 
}) => (
  <label className="flex items-center gap-2 cursor-pointer">
    <input
      type="checkbox"
      checked={isSelected}
      onChange={(e) => onValueChange(e.target.checked)}
      className="rounded"
    />
    {children}
  </label>
);

import { GameLogInfo } from '@/types/api';

// アイコンコンポーネント
const ChatIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
  </svg>
);

const RefreshIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const FilterIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
  </svg>
);

interface GameLogProps {
  logs: GameLogInfo[];
  autoScroll?: boolean;
  maxHeight?: string;
  onRefresh?: () => Promise<void>;
  isLoading?: boolean;
}

interface LogFilter {
  speech: boolean;
  vote: boolean;
  gameEvents: boolean;
  nightActions: boolean;
}

const LOG_EVENT_TYPES = {
  speech: ['speech'],
  vote: ['vote', 'execution'],
  gameEvents: ['game_start', 'game_end', 'phase_transition'],
  nightActions: ['attack', 'investigate', 'protect']
};

const LOG_EVENT_COLORS = {
  speech: 'primary',
  vote: 'danger',
  execution: 'danger',
  game_start: 'success',
  game_end: 'warning',
  phase_transition: 'secondary',
  attack: 'danger',
  investigate: 'secondary',
  protect: 'success'
} as const;

export default function GameLog({
  logs,
  autoScroll = true,
  maxHeight = 'max-h-96',
  onRefresh,
  isLoading = false
}: GameLogProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<LogFilter>({
    speech: true,
    vote: true,
    gameEvents: true,
    nightActions: true
  });
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(autoScroll);
  const [showFilter, setShowFilter] = useState(false);

  // 自動スクロール
  useEffect(() => {
    if (isAutoScrollEnabled && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isAutoScrollEnabled]);

  // ログのフィルタリング
  const filteredLogs = logs.filter(log => {
    const eventType = log.event_type;
    
    if (LOG_EVENT_TYPES.speech.includes(eventType) && !filter.speech) return false;
    if (LOG_EVENT_TYPES.vote.includes(eventType) && !filter.vote) return false;
    if (LOG_EVENT_TYPES.gameEvents.includes(eventType) && !filter.gameEvents) return false;
    if (LOG_EVENT_TYPES.nightActions.includes(eventType) && !filter.nightActions) return false;
    
    return true;
  });

  const handleRefresh = async () => {
    if (onRefresh) {
      await onRefresh();
    }
  };

  const getEventTypeColor = (eventType: string): "primary" | "secondary" | "success" | "warning" | "danger" | "default" => {
    return LOG_EVENT_COLORS[eventType as keyof typeof LOG_EVENT_COLORS] || 'default';
  };

  const getEventTypeLabel = (eventType: string): string => {
    const labels: { [key: string]: string } = {
      speech: '発言',
      vote: '投票',
      execution: '処刑',
      game_start: 'ゲーム開始',
      game_end: 'ゲーム終了',
      phase_transition: 'フェーズ移行',
      attack: '襲撃',
      investigate: '占い',
      protect: '守り'
    };
    return labels[eventType] || eventType;
  };

  const formatTime = (dateString: string): string => {
    return new Date(dateString).toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="p-4 bg-gray-800/70 border border-gray-600/50 rounded-lg backdrop-blur-sm">
      {/* ヘッダー */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <ChatIcon className="w-5 h-5 text-white" />
          <h2 className="text-xl font-semibold text-white">ゲームログ</h2>
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-700/80 text-gray-200 border border-gray-500/50">
            {filteredLogs.length}件
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilter(!showFilter)}
            className="px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-transparent hover:bg-gray-700/50 rounded transition-colors flex items-center gap-2"
          >
            <FilterIcon className="w-4 h-4" />
            フィルタ
          </button>

          {onRefresh && (
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-transparent hover:bg-gray-700/50 rounded transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshIcon className="w-4 h-4" />
              更新
            </button>
          )}
        </div>
      </div>

      {/* フィルタ設定 */}
      {showFilter && (
        <div className="p-3 mb-4 bg-gray-700/50 border border-gray-600/50 rounded-lg">
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-white">表示するログの種類:</h4>
            <div className="grid grid-cols-2 gap-2">
              <Switch
                size="sm"
                isSelected={filter.speech}
                onValueChange={(checked) => setFilter(prev => ({ ...prev, speech: checked }))}
              >
                <span className="text-sm text-gray-200">発言</span>
              </Switch>
              <Switch
                size="sm"
                isSelected={filter.vote}
                onValueChange={(checked) => setFilter(prev => ({ ...prev, vote: checked }))}
              >
                <span className="text-sm text-gray-200">投票</span>
              </Switch>
              <Switch
                size="sm"
                isSelected={filter.gameEvents}
                onValueChange={(checked) => setFilter(prev => ({ ...prev, gameEvents: checked }))}
              >
                <span className="text-sm text-gray-200">ゲームイベント</span>
              </Switch>
              <Switch
                size="sm"
                isSelected={filter.nightActions}
                onValueChange={(checked) => setFilter(prev => ({ ...prev, nightActions: checked }))}
              >
                <span className="text-sm text-gray-200">夜のアクション</span>
              </Switch>
            </div>
            <div className="pt-2 border-t border-gray-600">
              <Switch
                size="sm"
                isSelected={isAutoScrollEnabled}
                onValueChange={setIsAutoScrollEnabled}
              >
                <span className="text-sm text-gray-200">自動スクロール</span>
              </Switch>
            </div>
          </div>
        </div>
      )}

      {/* ログ表示エリア */}
      <div 
        ref={logContainerRef}
        className={`space-y-3 overflow-y-auto ${maxHeight}`}
      >
        {filteredLogs.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-300">
              {logs.length === 0 ? 'まだログがありません' : 'フィルタ条件に一致するログがありません'}
            </p>
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div key={log.log_id} className="border-l-4 border-blue-400/50 pl-4 py-2 bg-gray-700/50 rounded-r-lg backdrop-blur-sm">
              {/* ログヘッダー */}
              <div className="flex items-center gap-2 text-sm text-gray-300 mb-1">
                <span 
                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    getEventTypeColor(log.event_type) === 'primary' ? 'bg-blue-600/20 text-blue-300 border border-blue-400/50' :
                    getEventTypeColor(log.event_type) === 'secondary' ? 'bg-gray-600/20 text-gray-300 border border-gray-400/50' :
                    getEventTypeColor(log.event_type) === 'success' ? 'bg-green-600/20 text-green-300 border border-green-400/50' :
                    getEventTypeColor(log.event_type) === 'warning' ? 'bg-yellow-600/20 text-yellow-300 border border-yellow-400/50' :
                    getEventTypeColor(log.event_type) === 'danger' ? 'bg-red-600/20 text-red-300 border border-red-400/50' :
                    'bg-gray-600/20 text-gray-300 border border-gray-400/50'
                  }`}
                >
                  {getEventTypeLabel(log.event_type)}
                </span>
                
                {log.actor && (
                  <span className="font-medium text-white">{log.actor.character_name}</span>
                )}
                
                <span className="text-xs text-gray-400">
                  {formatTime(log.created_at)}
                </span>
              </div>

              {/* ログ内容 */}
              {log.content && (
                <div className="prose prose-sm max-w-none prose-invert">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {log.content}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* ログ統計 */}
      {logs.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-600/50 text-xs text-gray-400">
          <div className="flex justify-between">
            <span>総ログ数: {logs.length}件</span>
            <span>表示中: {filteredLogs.length}件</span>
          </div>
        </div>
      )}
    </div>
  );
}