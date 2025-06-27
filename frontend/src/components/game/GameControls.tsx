import { useState } from 'react';

import { PlayerInfo } from '@/types/api';

interface GameControlsProps {
  gameStatus: string;
  isMyTurn: boolean;
  currentPlayer?: PlayerInfo;
  currentRound?: number;
  onSpeak: (statement: string) => Promise<void>;
  onStartGame?: () => Promise<void>;
  isLoading?: boolean;
  currentPlayerId?: string | null;
  allPlayers?: PlayerInfo[];
}

export default function GameControls({
  gameStatus,
  isMyTurn,
  currentPlayer,
  currentRound,
  onSpeak,
  onStartGame,
  isLoading = false,
  currentPlayerId,
  allPlayers = []
}: GameControlsProps) {
  const [statement, setStatement] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);

  // 現在のプレイヤーが人間かどうかを判定
  const myPlayerInfo = allPlayers.find(p => p.player_id === currentPlayerId);
  const isHumanPlayer = myPlayerInfo?.is_human ?? false;

  const handleSpeak = async () => {
    if (!statement.trim()) return;

    try {
      setIsSpeaking(true);
      await onSpeak(statement);
      setStatement(''); // 成功時にクリア
    } catch (error) {
      // エラーハンドリングは親コンポーネントで行う
    } finally {
      setIsSpeaking(false);
    }
  };


  // 現在の発言者表示
  if (gameStatus === 'day_discussion' && currentPlayer) {
    return (
      <div className="space-y-4">
        {/* 現在の発言者表示 */}
        <div className="p-4 bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30 rounded-lg backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-yellow-500 text-white flex items-center justify-center text-xs font-bold">
              {currentPlayer.character_name.charAt(0)}
            </div>
            <div>
              <p className="font-semibold text-yellow-200">現在の発言者</p>
              <p className="text-lg text-white">{currentPlayer.character_name}</p>
              {!isMyTurn && (
                <p className="text-sm text-yellow-300">
                  {currentPlayer.character_name} の発言を待っています...
                </p>
              )}
            </div>
          </div>
        </div>

        {/* 発言入力（自分のターンの時） */}
        {isMyTurn && currentPlayerId && isHumanPlayer && (
          <div className="p-4 bg-gray-800/70 border border-gray-600/50 rounded-lg backdrop-blur-sm">
            <h3 className="font-semibold mb-3 text-white">あなたの発言</h3>
            <textarea
              placeholder="議論に参加しましょう..."
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              className="w-full mb-3 p-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 resize-none"
              rows={3}
              maxLength={500}
              disabled={isSpeaking || isLoading}
            />
            
            <div className="flex justify-between items-center mb-3">
              <span className="text-sm text-gray-300">
                {statement.length}/500文字
              </span>
              {statement.length > 450 && (
                <span className="text-sm text-orange-400">
                  文字数制限に注意
                </span>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleSpeak}
                disabled={isSpeaking || !statement.trim() || isLoading}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
              >
                {isSpeaking ? '発言中...' : '発言する'}
              </button>
              
            </div>

            {/* 発言のヒントとラウンド情報 */}
            <div className="mt-3 p-3 bg-gray-700/80 rounded-lg border border-gray-600/50">
              {currentRound && (
                <div className="mb-2 p-2 bg-blue-600/20 border border-blue-400/30 rounded text-center">
                  <span className="text-sm font-medium text-blue-200">
                    ラウンド {currentRound} / 3
                  </span>
                  <p className="text-xs text-blue-300 mt-1">
                    各プレイヤーは1ラウンドにつき1回発言できます
                  </p>
                </div>
              )}
              <p className="text-xs text-gray-300">
                💡 他のプレイヤーの発言をよく聞いて、疑問点があれば質問してみましょう。
                相手の反応から何かが見えてくるかもしれません。
                3ラウンド終了後、自動的に投票フェーズに移行します。
              </p>
            </div>
          </div>
        )}

        {/* 認証エラーメッセージ */}
        {isMyTurn && !currentPlayerId && (
          <div className="p-4 bg-red-900/70 border border-red-600/50 rounded-lg backdrop-blur-sm">
            <div className="text-center">
              <p className="text-red-200 mb-2 font-semibold">
                ⚠️ 認証エラー
              </p>
              <p className="text-red-300 text-sm mb-3">
                プレイヤー認証が正しく行われていません。ページを再読み込みして、部屋に再参加してください。
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
              >
                ページ再読み込み
              </button>
            </div>
          </div>
        )}

        {/* AIプレイヤーの場合のメッセージ */}
        {isMyTurn && currentPlayerId && !isHumanPlayer && (
          <div className="p-4 bg-blue-900/70 border border-blue-600/50 rounded-lg backdrop-blur-sm">
            <div className="text-center">
              <p className="text-blue-200 mb-2 font-semibold">
                🤖 AIプレイヤーのターン
              </p>
              <p className="text-blue-300 text-sm">
                AI発言を自動生成中です...
              </p>
            </div>
          </div>
        )}


        {/* 待機中のメッセージ */}
        {!isMyTurn && (
          <div className="p-4 bg-gray-800/70 border border-gray-600/50 rounded-lg backdrop-blur-sm">
            <div className="text-center">
              <p className="text-gray-200 mb-2">
                {currentPlayer.character_name} の発言を待っています
              </p>
              <div className="flex justify-center">
                <div className="animate-pulse flex space-x-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 待機中の場合
  if (gameStatus === 'waiting' && onStartGame) {
    return (
      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="text-center">
          <h3 className="font-semibold text-green-800 mb-2">ゲーム開始準備</h3>
          <p className="text-sm text-green-700 mb-4">
            プレイヤーが揃い次第ゲームを開始できます
          </p>
          <button
            onClick={onStartGame}
            disabled={isLoading}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            {isLoading ? 'ゲーム開始中...' : 'ゲーム開始'}
          </button>
        </div>
      </div>
    );
  }

  // その他の状態では何も表示しない
  return null;
}