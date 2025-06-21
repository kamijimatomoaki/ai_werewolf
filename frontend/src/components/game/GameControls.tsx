import { useState } from 'react';
import { Button } from "@heroui/button";
import { Card } from "@heroui/card";
import { Textarea } from "@heroui/input";
import { Avatar } from "@heroui/avatar";

import { PlayerInfo } from '@/types/api';

interface GameControlsProps {
  gameStatus: string;
  isMyTurn: boolean;
  currentPlayer?: PlayerInfo;
  onSpeak: (statement: string) => Promise<void>;
  onTransitionToVote?: () => Promise<void>;
  onStartGame?: () => Promise<void>;
  isLoading?: boolean;
}

export default function GameControls({
  gameStatus,
  isMyTurn,
  currentPlayer,
  onSpeak,
  onTransitionToVote,
  onStartGame,
  isLoading = false
}: GameControlsProps) {
  const [statement, setStatement] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);

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

  const handleTransitionToVote = async () => {
    if (!onTransitionToVote) return;
    
    try {
      await onTransitionToVote();
    } catch (error) {
      // エラーハンドリングは親コンポーネントで行う
    }
  };

  // 現在の発言者表示
  if (gameStatus === 'day_discussion' && currentPlayer) {
    return (
      <div className="space-y-4">
        {/* 現在の発言者表示 */}
        <Card className="p-4 bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Avatar name={currentPlayer.character_name} size="sm" color="warning" />
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
        </Card>

        {/* 発言入力（自分のターンの時） */}
        {isMyTurn && (
          <Card className="p-4 bg-gray-800/70 border-gray-600/50 backdrop-blur-sm">
            <h3 className="font-semibold mb-3 text-white">あなたの発言</h3>
            <Textarea
              placeholder="議論に参加しましょう..."
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              className="mb-3"
              rows={3}
              maxLength={500}
              isDisabled={isSpeaking || isLoading}
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
              <Button
                color="primary"
                onClick={handleSpeak}
                isLoading={isSpeaking}
                isDisabled={!statement.trim() || isLoading}
                className="flex-1"
              >
                {isSpeaking ? '発言中...' : '発言する'}
              </Button>
              
              {onTransitionToVote && (
                <Button
                  color="warning"
                  variant="bordered"
                  onClick={handleTransitionToVote}
                  isLoading={isLoading}
                  isDisabled={isSpeaking}
                >
                  投票フェーズへ
                </Button>
              )}
            </div>

            {/* 発言のヒント */}
            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600">
                💡 他のプレイヤーの発言をよく聞いて、疑問点があれば質問してみましょう。
                相手の反応から何かが見えてくるかもしれません。
              </p>
            </div>
          </Card>
        )}

        {/* 待機中のメッセージ */}
        {!isMyTurn && (
          <Card className="p-4 bg-gray-50">
            <div className="text-center">
              <p className="text-gray-600 mb-2">
                {currentPlayer.character_name} の発言を待っています
              </p>
              <div className="flex justify-center">
                <div className="animate-pulse flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>
    );
  }

  // 待機中の場合
  if (gameStatus === 'waiting' && onStartGame) {
    return (
      <Card className="p-4 bg-green-50 border-green-200">
        <div className="text-center">
          <h3 className="font-semibold text-green-800 mb-2">ゲーム開始準備</h3>
          <p className="text-sm text-green-700 mb-4">
            プレイヤーが揃い次第ゲームを開始できます
          </p>
          <Button
            color="success"
            onClick={onStartGame}
            isLoading={isLoading}
            size="lg"
          >
            {isLoading ? 'ゲーム開始中...' : 'ゲーム開始'}
          </Button>
        </div>
      </Card>
    );
  }

  // その他の状態では何も表示しない
  return null;
}