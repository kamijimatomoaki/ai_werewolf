import React, { useState, useEffect } from 'react';
import SpectatorChat from '@/components/game/SpectatorChat';
import GameLog from '@/components/game/GameLog';
import { useSpectatorMode } from '@/hooks/useSpectatorMode';

interface SpectatorPlayerInfo {
  player_id: string;
  character_name: string;
  is_alive: boolean;
  is_human: boolean;
}

interface SpectatorRoomView {
  room_id: string;
  room_name: string;
  status: string;
  day_number: number;
  total_players: number;
  living_players: number;
  players: SpectatorPlayerInfo[];
  public_logs: any[];
}

interface SpectatorViewProps {
  roomId: string;
  spectatorId: string;
  onLeaveSpectator: () => void;
}

export function SpectatorView({ roomId, spectatorId, onLeaveSpectator }: SpectatorViewProps) {
  const {
    roomView,
    spectators,
    chatMessages,
    isLoading,
    sendChatMessage,
    refreshRoomView,
    leaveSpectatorMode,
    error
  } = useSpectatorMode(roomId, spectatorId);

  const [chatMessage, setChatMessage] = useState('');

  const handleSendChat = async () => {
    if (!chatMessage.trim()) return;
    
    try {
      await sendChatMessage(chatMessage.trim());
      setChatMessage('');
    } catch (err) {
      console.error('Failed to send chat message:', err);
    }
  };

  const handleLeave = async () => {
    try {
      await leaveSpectatorMode();
      onLeaveSpectator();
    } catch (err) {
      console.error('Failed to leave spectator mode:', err);
    }
  };

  const getPhaseIcon = (status: string) => {
    switch (status) {
      case 'waiting': return '⏳';
      case 'day_discussion': return '🌅';
      case 'day_vote': return '🗳️';
      case 'night': return '🌙';
      case 'finished': return '🏁';
      default: return '❓';
    }
  };

  const getPhaseLabel = (status: string) => {
    switch (status) {
      case 'waiting': return '開始待ち';
      case 'day_discussion': return '昼の議論';
      case 'day_vote': return '投票フェーズ';
      case 'night': return '夜フェーズ';
      case 'finished': return 'ゲーム終了';
      default: return status;
    }
  };

  if (isLoading && !roomView) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">観戦情報を読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="border border-red-200 bg-red-50 rounded-lg">
          <div className="p-6 text-center">
            <h3 className="text-lg font-semibold text-red-800 mb-2">エラーが発生しました</h3>
            <p className="text-red-600 mb-4">{error}</p>
            <div className="space-x-3">
              <button onClick={refreshRoomView} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
                再試行
              </button>
              <button onClick={onLeaveSpectator} className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg transition-colors">
                ロビーに戻る
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!roomView) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-white border border-gray-200 rounded-lg">
          <div className="p-6 text-center">
            <p className="text-gray-600">観戦情報が見つかりません</p>
            <button onClick={onLeaveSpectator} className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
              ロビーに戻る
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* ヘッダー */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl">👁️</span>
            <h1 className="text-2xl font-bold">観戦モード</h1>
          </div>
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
            {spectators.length}人が観戦中
          </span>
        </div>
        <button 
          onClick={handleLeave}
          className="px-4 py-2 border border-red-300 hover:bg-red-50 text-red-700 rounded-lg transition-colors"
        >
          観戦終了
        </button>
      </div>

      {/* ゲーム情報 */}
      <div className="mb-6 bg-white border border-gray-200 rounded-lg">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-semibold">{roomView.room_name}</h2>
              <div className="flex items-center gap-2">
                <span className="text-lg">{getPhaseIcon(roomView.status)}</span>
                <span 
                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    roomView.status === 'finished' 
                      ? 'bg-green-100 text-green-800 border border-green-200' 
                      : 'bg-blue-100 text-blue-800 border border-blue-200'
                  }`}
                >
                  {getPhaseLabel(roomView.status)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>{roomView.day_number}日目</span>
              <span>生存: {roomView.living_players}/{roomView.total_players}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* メインコンテンツ */}
        <div className="lg:col-span-2 space-y-6">
          {/* プレイヤー一覧 */}
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">プレイヤー一覧</h3>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {roomView.players.map((player) => (
                  <div
                    key={player.player_id}
                    className={`
                      p-3 border rounded-lg text-center
                      ${player.is_alive 
                        ? 'border-green-200 bg-green-50' 
                        : 'border-gray-300 bg-gray-100 opacity-60'
                      }
                    `}
                  >
                    <div className="flex items-center justify-center gap-2 mb-1">
                      <span className={`w-3 h-3 rounded-full ${
                        player.is_alive ? 'bg-green-500' : 'bg-gray-400'
                      }`}></span>
                      <span className="font-medium text-sm">
                        {player.character_name}
                      </span>
                    </div>
                    <div className="flex items-center justify-center gap-1">
                      <span 
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          player.is_human 
                            ? 'bg-blue-100 text-blue-800 border border-blue-200' 
                            : 'bg-gray-100 text-gray-800 border border-gray-200'
                        }`}
                      >
                        {player.is_human ? '人間' : 'AI'}
                      </span>
                      {!player.is_alive && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                          脱落
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ゲームログ */}
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">ゲーム進行</h3>
            </div>
            <div className="p-4">
              <GameLog 
                logs={roomView.public_logs} 
                className="max-h-96 overflow-y-auto"
              />
            </div>
          </div>
        </div>

        {/* サイドバー */}
        <div className="space-y-6">
          {/* 観戦者一覧 */}
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold">観戦者</h3>
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                  {spectators.length}
                </span>
              </div>
            </div>
            <div className="p-4">
              {spectators.length === 0 ? (
                <p className="text-gray-500 text-sm text-center">
                  他に観戦者はいません
                </p>
              ) : (
                <div className="space-y-2">
                  {spectators.map((spectator) => (
                    <div 
                      key={spectator.spectator_id}
                      className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg"
                    >
                      <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-xs font-medium text-blue-600">
                          {spectator.spectator_name[0]}
                        </span>
                      </div>
                      <span className="text-sm">{spectator.spectator_name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 観戦者チャット */}
          <SpectatorChat
            roomId={roomId}
            spectatorId={spectatorId}
            messages={chatMessages}
            onSendMessage={sendChatMessage}
          />
        </div>
      </div>
    </div>
  );
}

export default SpectatorView;