import { useState, useEffect, useCallback } from 'react';
import { Button } from "@heroui/button";
import { Card } from "@heroui/card";
import { Chip } from "@heroui/chip";

import { apiService, VoteResult } from '@/services/api';
import { websocketService } from '@/services/websocket';
import { usePlayer } from '@/contexts/PlayerContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import ConnectionStatus from '@/components/ConnectionStatus';
import SeerPanel from '@/components/game/SeerPanel';
import BodyguardPanel from '@/components/game/BodyguardPanel';
import PlayerList from '@/components/game/PlayerList';
import GameControls from '@/components/game/GameControls';
import VotingPanel from '@/components/game/VotingPanel';
import GameLog from '@/components/game/GameLog';
import PhaseTransition from '@/components/game/PhaseTransition';
import { usePhaseTransition } from '@/hooks/useAnimations';
import { RoomInfo, PlayerInfo, GameLogInfo } from '@/types/api';

interface GameRoomProps {
  roomId: string;
  onBackToLobby: () => void;
}

export default function GameRoom({ roomId, onBackToLobby }: GameRoomProps) {
  const { playerId: currentPlayerId } = usePlayer();
  const { isConnected, connectionStatus } = useWebSocket();
  const [room, setRoom] = useState<RoomInfo | null>(null);
  const [logs, setLogs] = useState<GameLogInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 削除: statement, personaKeywords, selectedVoteTarget は各コンポーネントで管理
  const [voteResult, setVoteResult] = useState<VoteResult | null>(null);
  const [connectionWarningShown, setConnectionWarningShown] = useState(false);
  
  // フェーズ遷移アニメーション
  const { isTransitioning, handlePhaseChange, animationSettings } = usePhaseTransition();

  // 部屋情報とログを取得
  const fetchRoomData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [roomData, logsData] = await Promise.all([
        apiService.getRoom(roomId),
        apiService.getGameLogs(roomId)
      ]);
      
      // フェーズ変更をチェック
      if (room && roomData.status !== room.status) {
        await handlePhaseChange(roomData.status);
      }
      
      setRoom(roomData);
      setLogs(logsData);
      
      // AI自動進行のチェック
      checkForAIAutoProgress(roomData);
    } catch (err: any) {
      setError(err.message || 'データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // AI自動進行のチェック
  const checkForAIAutoProgress = useCallback(async (roomData: any) => {
    // 昼の議論フェーズかつ、現在のプレイヤーがAIの場合、自動進行を呼び出す
    if (roomData.status === 'day_discussion' && 
        roomData.turn_order && 
        roomData.current_turn_index !== undefined) {
      
      const currentPlayerId = roomData.turn_order[roomData.current_turn_index];
      const currentPlayer = roomData.players.find((p: any) => p.player_id === currentPlayerId);
      
      if (currentPlayer && !currentPlayer.is_human) {
        // AIプレイヤーの番の場合、3秒待ってから自動進行を呼び出す
        console.log(`AI player turn detected: ${currentPlayer.character_name}`);
        setTimeout(async () => {
          try {
            await apiService.autoProgress(roomId);
          } catch (error) {
            console.error('AI auto progress failed:', error);
          }
        }, 3000); // 3秒の遅延を追加してUI更新を待つ
      }
    }
  }, [roomId]);

  // ゲーム開始
  const handleStartGame = async () => {
    try {
      setLoading(true);
      const updatedRoom = await apiService.startGame(roomId);
      setRoom(updatedRoom);
      // ログも更新
      const logsData = await apiService.getGameLogs(roomId);
      setLogs(logsData);
    } catch (err: any) {
      setError(err.message || 'ゲーム開始に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 発言
  const handleSpeak = async (statement: string) => {
    if (!statement.trim() || !currentPlayerId) return;
    
    try {
      setLoading(true);
      const updatedRoom = await apiService.speak(roomId, currentPlayerId, statement);
      setRoom(updatedRoom);
      
      // ログを更新
      const logsData = await apiService.getGameLogs(roomId);
      setLogs(logsData);
    } catch (err: any) {
      setError(err.message || '発言に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // ペルソナ生成
  const handleGeneratePersona = async (playerId: string, keywords: string) => {
    try {
      setLoading(true);
      await apiService.generatePersona(playerId, keywords);
      // 部屋情報を更新
      await fetchRoomData();
    } catch (err: any) {
      setError(err.message || 'ペルソナ生成に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 投票処理
  const handleVote = async (targetId: string) => {
    if (!targetId || !currentPlayerId) return;
    
    try {
      setLoading(true);
      const result = await apiService.vote(roomId, currentPlayerId, targetId);
      setVoteResult(result);
      
      // 部屋情報を更新
      await fetchRoomData();
    } catch (err: any) {
      setError(err.message || '投票に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 投票フェーズへの移行
  const handleTransitionToVote = async () => {
    try {
      setLoading(true);
      const updatedRoom = await apiService.transitionToVote(roomId);
      setRoom(updatedRoom);
      await fetchRoomData();
    } catch (err: any) {
      setError(err.message || '投票フェーズへの移行に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 夜のアクション実行
  const handleNightAction = async () => {
    try {
      setLoading(true);
      await apiService.nightAction(roomId);
      await fetchRoomData();
    } catch (err: any) {
      setError(err.message || '夜のアクションに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // WebSocketイベントハンドラ
  const handleGameStarted = useCallback((data: { room_id: string; message: string }) => {
    if (data.room_id === roomId) {
      console.log('Game started:', data.message);
      fetchRoomData(); // 部屋データを更新
    }
  }, [roomId]);

  const handleNewSpeech = useCallback((data: { room_id: string; speaker_id: string; statement: string }) => {
    if (data.room_id === roomId) {
      console.log('New speech:', data);
      fetchRoomData(); // 部屋データとログを更新
    }
  }, [roomId]);

  const handlePlayerJoined = useCallback((data: { player_name: string; sid: string }) => {
    console.log('Player joined:', data);
    fetchRoomData(); // プレイヤーリストを更新
  }, []);

  const handleRoomUpdated = useCallback((data: { room_id: string; room_data: any }) => {
    if (data.room_id === roomId) {
      console.log('Room updated:', data);
      fetchRoomData();
    }
  }, [roomId]);

  const handleVotePhaseStarted = useCallback((data: { room_id: string; message: string }) => {
    if (data.room_id === roomId) {
      console.log('Vote phase started:', data.message);
      fetchRoomData();
    }
  }, [roomId]);

  const handleVoteCast = useCallback((data: { room_id: string; voter_id: string; target_id: string }) => {
    if (data.room_id === roomId) {
      console.log('Vote cast:', data);
      fetchRoomData();
    }
  }, [roomId]);

  const handleNightPhaseStarted = useCallback((data: { room_id: string; message: string }) => {
    if (data.room_id === roomId) {
      console.log('Night phase started:', data.message);
      fetchRoomData();
    }
  }, [roomId]);

  // WebSocketイベントリスナーの設定
  useEffect(() => {
    if (isConnected) {
      // 部屋に参加
      websocketService.joinRoom(roomId);
      
      // イベントリスナーを登録
      websocketService.on('game_started', handleGameStarted);
      websocketService.on('new_speech', handleNewSpeech);
      websocketService.on('player_joined', handlePlayerJoined);
      websocketService.on('room_updated', handleRoomUpdated);
      websocketService.on('vote_phase_started', handleVotePhaseStarted);
      websocketService.on('vote_cast', handleVoteCast);
      websocketService.on('night_phase_started', handleNightPhaseStarted);
    }

    // クリーンアップ
    return () => {
      websocketService.off('game_started', handleGameStarted);
      websocketService.off('new_speech', handleNewSpeech);
      websocketService.off('player_joined', handlePlayerJoined);
      websocketService.off('room_updated', handleRoomUpdated);
      websocketService.off('vote_phase_started', handleVotePhaseStarted);
      websocketService.off('vote_cast', handleVoteCast);
      websocketService.off('night_phase_started', handleNightPhaseStarted);
    };
  }, [isConnected, roomId, handleGameStarted, handleNewSpeech, handlePlayerJoined, handleRoomUpdated, handleVotePhaseStarted, handleVoteCast, handleNightPhaseStarted]);

  // 接続状態の監視と警告表示
  useEffect(() => {
    if (!isConnected && !connectionWarningShown && room) {
      setConnectionWarningShown(true);
      setError('リアルタイム通信が切断されました。自動で再接続を試行しています。');
    }
    
    if (isConnected && connectionWarningShown) {
      setConnectionWarningShown(false);
      setError(null);
    }
  }, [isConnected, connectionWarningShown, room]);

  // 初期化時にデータを取得
  useEffect(() => {
    fetchRoomData();
  }, [roomId]);

  // ステータス表示
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'waiting': return 'success';
      case 'day_discussion': return 'warning';
      case 'day_vote': return 'danger';
      case 'night': return 'secondary';
      default: return 'default';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'waiting': return '待機中';
      case 'day_discussion': return '昼の議論';
      case 'day_vote': return '投票中';
      case 'night': return '夜';
      default: return status;
    }
  };

  // 現在の発言者を取得
  const getCurrentSpeaker = (): PlayerInfo | null => {
    if (!room?.turn_order || room.current_turn_index === undefined) return null;
    const currentPlayerId = room.turn_order[room.current_turn_index];
    return room.players.find(p => p.player_id === currentPlayerId) || null;
  };

  if (!room) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-900 text-white min-h-screen">
        <Button onClick={onBackToLobby} className="mb-4">
          ← ロビーに戻る
        </Button>
        {loading ? (
          <div className="text-center py-8 text-gray-300">読み込み中...</div>
        ) : (
          <div className="text-center py-8 text-red-400">
            部屋が見つかりません
          </div>
        )}
      </div>
    );
  }

  const currentSpeaker = getCurrentSpeaker();
  const isMyTurn = currentSpeaker?.player_id === currentPlayerId;
  
  // 現在のプレイヤー情報を取得
  const currentPlayer = room?.players.find(p => p.player_id === currentPlayerId);
  
  // 占い師UIを表示するかどうか
  const shouldShowSeerPanel = room?.status === 'night' && 
                              currentPlayer?.role === 'seer' && 
                              currentPlayer?.is_alive && 
                              currentPlayerId;

  // ボディガードUIを表示するかどうか
  const shouldShowBodyguardPanel = room?.status === 'night' && 
                                  currentPlayer?.role === 'bodyguard' && 
                                  currentPlayer?.is_alive && 
                                  currentPlayerId;

  return (
    <div className="max-w-6xl mx-auto p-6 bg-gray-900 text-white min-h-screen">
      {/* ヘッダー */}
      <div className="flex justify-between items-center mb-6">
        <Button onClick={onBackToLobby} variant="bordered">
          ← ロビーに戻る
        </Button>
        <div className="text-center">
          <h1 className="text-2xl font-bold">
            {room.room_name || `部屋 ${room.room_id.slice(0, 8)}`}
          </h1>
          <div className="flex items-center gap-2 justify-center mt-2">
            <Chip color={getStatusColor(room.status)} variant="flat">
              {getStatusLabel(room.status)}
            </Chip>
            {room.status !== 'waiting' && (
              <Chip variant="bordered">
                {room.day_number}日目
              </Chip>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ConnectionStatus compact={true} showReconnectButton={false} />
          <Button color="secondary" onClick={fetchRoomData} isLoading={loading}>
            更新
          </Button>
        </div>
      </div>

      {error && (
        <Card className="mb-4 p-4 bg-red-900 border-red-700 text-red-200">
          <p className="font-semibold">エラー: {error}</p>
        </Card>
      )}

      {/* 接続状態警告 */}
      {!isConnected && (
        <Card className="mb-4 p-4 bg-orange-900 border-orange-700">
          <ConnectionStatus showReconnectButton={true} />
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-12rem)]">
        {/* プレイヤー一覧 - 独立スクロール */}
        <div className="lg:col-span-1 h-full overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
          <PlayerList
            players={room.players}
            currentPlayerId={currentPlayerId}
            gameStatus={room.status}
            totalPlayers={room.total_players}
            onGeneratePersona={handleGeneratePersona}
            onStartGame={handleStartGame}
            isLoading={loading}
          />
        </div>

        {/* ゲーム進行エリア - 独立スクロール */}
        <div className="lg:col-span-2 h-full overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800 flex flex-col">
          {/* ゲーム制御コンポーネント */}
          <GameControls
            gameStatus={room.status}
            isMyTurn={isMyTurn}
            currentPlayer={currentSpeaker}
            onSpeak={handleSpeak}
            onTransitionToVote={handleTransitionToVote}
            isLoading={loading}
          />

          {/* 投票フェーズUI */}
          {room.status === 'day_vote' && currentPlayerId && (
            <VotingPanel
              players={room.players}
              currentPlayerId={currentPlayerId}
              voteResult={voteResult}
              onVote={handleVote}
              isLoading={loading}
            />
          )}

          {/* 占い師UI（夜フェーズ） */}
          {shouldShowSeerPanel && (
            <SeerPanel
              roomId={roomId}
              playerId={currentPlayerId}
              isActive={shouldShowSeerPanel}
              className="mb-4"
            />
          )}

          {/* ボディガードUI（夜フェーズ） */}
          {shouldShowBodyguardPanel && (
            <BodyguardPanel
              roomId={roomId}
              playerId={currentPlayerId}
              isActive={shouldShowBodyguardPanel}
              className="mb-4"
            />
          )}

          {/* 夜フェーズUI（管理者用） */}
          {room.status === 'night' && !shouldShowSeerPanel && !shouldShowBodyguardPanel && currentPlayer?.is_human && (
            <Card className="mb-4 p-4 bg-blue-900 border-blue-700">
              <h3 className="font-semibold mb-3 text-blue-200">夜フェーズ</h3>
              <p className="text-blue-300 mb-4">人狼が活動する時間です...</p>
              
              <Button
                color="secondary"
                onClick={handleNightAction}
                isLoading={loading}
                className="w-full"
              >
                朝を迎える
              </Button>
            </Card>
          )}
          
          {/* 夜フェーズ（占い師以外の役職向けメッセージ） */}
          {room.status === 'night' && !shouldShowSeerPanel && currentPlayer?.is_alive && (
            <Card className="mb-4 p-4 bg-gray-800 border-gray-700">
              <h4 className="font-medium text-gray-200 mb-2">夜の時間</h4>
              <p className="text-sm text-gray-300">
                {currentPlayer?.role === 'werewolf' 
                  ? '人狼たちが相談する時間です...' 
                  : '静かに朝を待ちましょう...'}
              </p>
            </Card>
          )}

          {/* ゲームログ */}
          <GameLog
            logs={logs}
            onRefresh={fetchRoomData}
            isLoading={loading}
          />
        </div>
      </div>
    </div>
  );
}