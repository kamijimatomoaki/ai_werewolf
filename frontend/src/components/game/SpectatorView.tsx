import React, { useState, useEffect } from 'react';
import { Card, CardBody, CardHeader } from '@heroui/card';
import { Button } from '@heroui/button';
import { Chip } from '@heroui/chip';
import { Input } from '@heroui/input';
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
        <Card className="border-red-200 bg-red-50">
          <CardBody className="text-center">
            <h3 className="text-lg font-semibold text-red-800 mb-2">エラーが発生しました</h3>
            <p className="text-red-600 mb-4">{error}</p>
            <div className="space-x-3">
              <Button color="primary" onPress={refreshRoomView}>
                再試行
              </Button>
              <Button variant="bordered" onPress={onLeaveSpectator}>
                ロビーに戻る
              </Button>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (!roomView) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card>
          <CardBody className="text-center">
            <p className="text-gray-600">観戦情報が見つかりません</p>
            <Button className="mt-4" onPress={onLeaveSpectator}>
              ロビーに戻る
            </Button>
          </CardBody>
        </Card>
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
          <Chip color="secondary" variant="flat">
            {spectators.length}人が観戦中
          </Chip>
        </div>
        <Button 
          color="danger" 
          variant="bordered" 
          onPress={handleLeave}
        >
          観戦終了
        </Button>
      </div>

      {/* ゲーム情報 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-semibold">{roomView.room_name}</h2>
              <div className="flex items-center gap-2">
                <span className="text-lg">{getPhaseIcon(roomView.status)}</span>
                <Chip 
                  color={roomView.status === 'finished' ? 'success' : 'primary'} 
                  variant="flat"
                >
                  {getPhaseLabel(roomView.status)}
                </Chip>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>{roomView.day_number}日目</span>
              <span>生存: {roomView.living_players}/{roomView.total_players}</span>
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* メインコンテンツ */}
        <div className="lg:col-span-2 space-y-6">
          {/* プレイヤー一覧 */}
          <Card>
            <CardHeader>
              <h3 className="text-lg font-semibold">プレイヤー一覧</h3>
            </CardHeader>
            <CardBody>
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
                      <Chip 
                        size="sm" 
                        color={player.is_human ? 'primary' : 'secondary'}
                        variant="flat"
                      >
                        {player.is_human ? '人間' : 'AI'}
                      </Chip>
                      {!player.is_alive && (
                        <Chip size="sm" color="default" variant="flat">
                          脱落
                        </Chip>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>

          {/* ゲームログ */}
          <Card>
            <CardHeader>
              <h3 className="text-lg font-semibold">ゲーム進行</h3>
            </CardHeader>
            <CardBody>
              <GameLog 
                logs={roomView.public_logs} 
                className="max-h-96 overflow-y-auto"
              />
            </CardBody>
          </Card>
        </div>

        {/* サイドバー */}
        <div className="space-y-6">
          {/* 観戦者一覧 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold">観戦者</h3>
                <Chip size="sm" color="secondary" variant="flat">
                  {spectators.length}
                </Chip>
              </div>
            </CardHeader>
            <CardBody>
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
            </CardBody>
          </Card>

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