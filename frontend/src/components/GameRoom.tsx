import { useState, useEffect, useCallback, useMemo } from 'react';

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
import GameSummary from '@/components/game/GameSummary';
import { usePhaseTransition } from '@/hooks/useAnimations';
import { RoomInfo, PlayerInfo, GameLogInfo } from '@/types/api';

interface GameRoomProps {
  roomId: string;
  onBackToLobby: () => void;
}

export default function GameRoom({ roomId, onBackToLobby }: GameRoomProps) {
  const { playerId: currentPlayerId, roomId: storedRoomId, playerName, logout, updatePlayerId } = usePlayer();
  const { isConnected, connectionStatus } = useWebSocket();
  const [room, setRoom] = useState<RoomInfo | null>(null);
  const [logs, setLogs] = useState<GameLogInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 削除: statement, personaKeywords, selectedVoteTarget は各コンポーネントで管理
  const [voteResult, setVoteResult] = useState<VoteResult | null>(null);
  const [connectionWarningShown, setConnectionWarningShown] = useState(false);
  const [autoProgressInProgress, setAutoProgressInProgress] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  
  // フェーズ遷移アニメーション
  const { isTransitioning, handlePhaseChange, animationSettings } = usePhaseTransition();

  // 部屋情報とログを取得
  const fetchRoomData = async (skipAutoProgress = false) => {
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
      
      // プレイヤーID同期チェック（自動修正機能付き）
      if (currentPlayerId && playerName && roomData.players) {
        const actualPlayer = roomData.players.find(p => p.character_name === playerName && p.is_human);
        if (actualPlayer && actualPlayer.player_id !== currentPlayerId) {
          console.warn(`🔧 Player ID mismatch detected - applying auto-fix:`, {
            storedPlayerId: currentPlayerId,
            actualPlayerId: actualPlayer.player_id,
            playerName: playerName,
            action: 'auto_fixing'
          });
          // Player IDを自動修正
          updatePlayerId(actualPlayer.player_id);
        }
      }
      
      // AI自動進行のチェック（無限ループ防止）
      if (!skipAutoProgress) {
        checkForAIAutoProgress(roomData);
      }
    } catch (err: any) {
      setError(err.message || 'データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // AI自動進行のチェック（改良版）
  const checkForAIAutoProgress = useCallback(async (roomData: any) => {
    // 既に自動進行中の場合はスキップ
    if (autoProgressInProgress) {
      console.log('Auto progress already in progress, skipping');
      return;
    }
    
    // 強制状態同期（デバッグ用）
    if (roomData?.status === 'day_discussion') {
      console.log('🔍 Room state debug:', {
        currentTurnIndex: roomData.current_turn_index,
        turnOrder: roomData.turn_order,
        currentPlayerInTurn: roomData.turn_order?.[roomData.current_turn_index],
        myPlayerId: currentPlayerId
      });
    }
    
    // 基本的な検証
    if (!roomData || !roomData.players) {
      console.log('Invalid room data for auto progress');
      return;
    }
    
    // 発言フェーズでのAI自動進行
    if (roomData.status === 'day_discussion' && 
        roomData.turn_order && 
        roomData.current_turn_index !== undefined) {
      
      // インデックス範囲チェック
      if (roomData.current_turn_index >= roomData.turn_order.length) {
        console.error(`Invalid turn index: ${roomData.current_turn_index} >= ${roomData.turn_order.length}`);
        // 自動修復を試行
        setAutoProgressInProgress(true);
        setTimeout(async () => {
          try {
            const result = await apiService.autoProgress(roomId);
            console.log('Auto progress index fix result:', result);
            await fetchRoomData(true); // 無限ループ防止
          } catch (error) {
            console.error('Auto progress index fix failed:', error);
          } finally {
            setAutoProgressInProgress(false);
          }
        }, 1000);
        return;
      }
      
      const currentPlayerId = roomData.turn_order[roomData.current_turn_index];
      const currentPlayer = roomData.players.find((p: any) => p.player_id === currentPlayerId);
      
      if (!currentPlayer) {
        console.error(`Current player not found: ${currentPlayerId}`);
        return;
      }
      
      if (!currentPlayer.is_alive) {
        console.log(`Current player ${currentPlayer.character_name} is dead, auto-advancing`);
        setAutoProgressInProgress(true);
        setTimeout(async () => {
          try {
            const result = await apiService.autoProgress(roomId);
            console.log('Dead player auto progress result:', result);
            await fetchRoomData(true); // 無限ループ防止
          } catch (error) {
            console.error('Dead player auto progress failed:', error);
          } finally {
            setAutoProgressInProgress(false);
          }
        }, 1000);
        return;
      }
      
      if (currentPlayer && !currentPlayer.is_human) {
        console.log(`AI player turn detected: ${currentPlayer.character_name} (Round: ${roomData.current_round || 1})`);
        // Backend should handle AI progression automatically now
        // Only trigger frontend fallback after extended waiting period
        setAutoProgressInProgress(true);
        setTimeout(async () => {
          try {
            // Check if AI player is still current after longer wait (backend should have processed by now)
            const currentRoomData = await apiService.getRoom(roomId);
            const stillCurrentPlayer = currentRoomData.turn_order[currentRoomData.current_turn_index] === currentPlayerId;
            
            let fallbackTriggered = false;
            if (stillCurrentPlayer && currentRoomData.status === roomData.status) {
              console.log('Backend auto-progression might have failed, triggering frontend fallback');
              const result = await apiService.autoProgress(roomId);
              console.log('Fallback auto progress result:', result);
              fallbackTriggered = true;
              
              // 連鎖発言の確認
              if (result.chained_speakers && result.chained_speakers.length > 0) {
                console.log(`AI chained speeches detected: ${result.chained_speakers.length} additional speakers`);
                // 連鎖発言があった場合は短い間隔で更新
                setTimeout(() => {
                  fetchRoomData();
                }, 1000);
                return; // 早期リターンで通常の更新処理をスキップ
              }
            } else {
              console.log('Backend auto-progression already processed, no fallback needed');
            }
            
            // 無限ループを防ぐため、autoProgressをスキップして取得
            await fetchRoomData(true);
            
            // 結果に応じて次のアクションを判断
            if (fallbackTriggered) {
              // 少し待ってから再度チェック（ただし頻度を抑制）
              setTimeout(() => {
                fetchRoomData();
              }, 2000); // 2秒に短縮
            }
          } catch (error) {
            console.error('AI auto progress failed:', error);
          } finally {
            setAutoProgressInProgress(false);
          }
        }, 8000); // Backend auto-progression fallback timeout increased to 8 seconds
      }
    }
    
    // 投票フェーズでのAI自動投票 (Backend should handle this automatically)
    if (roomData.status === 'day_vote') {
      const aiPlayers = roomData.players.filter((p: any) => p.is_alive && !p.is_human);
      if (aiPlayers.length > 0) {
        console.log(`AI auto vote check for ${aiPlayers.length} AI players - Backend should handle automatically`);
        // Reduced frontend intervention for voting phase
        setAutoProgressInProgress(true);
        setTimeout(async () => {
          try {
            // Only trigger if backend hasn't processed voting after extended wait
            const currentRoomData = await apiService.getRoom(roomId);
            if (currentRoomData.status === 'day_vote') {
              console.log('Backend auto-voting fallback triggered');
              const result = await apiService.autoProgress(roomId);
              console.log('Fallback auto vote result:', result);
            } else {
              console.log('Backend already processed voting phase');
            }
            await fetchRoomData(true); // 無限ループ防止
          } catch (error) {
            console.error('AI auto vote failed:', error);
          } finally {
            setAutoProgressInProgress(false);
          }
        }, 6000); // Longer wait for backend processing
      }
    }
  }, [roomId, autoProgressInProgress]);

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
      console.log('🗣️ New speech WebSocket event received:', data);
      console.log('🔄 Triggering fetchRoomData in 100ms...');
      // 即座にデータを更新（WebSocket通知への依存度を上げる）
      setTimeout(() => {
        console.log('🔄 Executing fetchRoomData now...');
        fetchRoomData();
      }, 100); // 短いディレイで確実に更新
    } else {
      console.log('🚫 New speech event for different room:', data.room_id, 'vs', roomId);
    }
  }, [roomId, fetchRoomData]);

  const handlePlayerJoined = useCallback((data: { player_name: string; sid: string }) => {
    console.log('Player joined:', data);
    fetchRoomData(); // プレイヤーリストを更新
  }, []);

  const handleRoomUpdated = useCallback((data: { room_id: string; room_data: RoomInfo }) => {
    if (data.room_id === roomId) {
      console.log('🔄 Room updated via WebSocket:', data);
      // 安全な差分データ更新
      if (data.room_data) {
        setRoom(data.room_data);
        // ログも更新（安全にチェック）
        if (data.room_data.logs && Array.isArray(data.room_data.logs)) {
          setLogs(data.room_data.logs);
        }
        
        // ターン状態の強制デバッグ
        console.log('🎯 Turn state after WebSocket update:', {
          currentTurnIndex: data.room_data.current_turn_index,
          turnOrder: data.room_data.turn_order,
          currentPlayerInTurn: data.room_data.turn_order?.[data.room_data.current_turn_index],
          myPlayerId: currentPlayerId
        });
      }
    }
  }, [roomId, currentPlayerId]);

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

  // 完全ゲーム状態通知ハンドラー
  const handleCompleteGameState = useCallback((data: any) => {
    if (data.room_id === roomId) {
      console.log('Complete game state received:', {
        turnIndex: data.current_turn_index,
        turnOrder: data.turn_order,
        status: data.status,
        playersCount: data.players?.length
      });
      
      // 状態を直接更新
      setRoom(prevRoom => {
        if (!prevRoom) return prevRoom;
        
        return {
          ...prevRoom,
          current_turn_index: data.current_turn_index,
          turn_order: data.turn_order,
          status: data.status,
          day_number: data.day_number,
          players: data.players || prevRoom.players
        };
      });
      
      // 確実にログも更新（AI発言後の自動更新を保証）
      setTimeout(() => fetchRoomData(), 200);
    }
  }, [roomId, fetchRoomData]);

  // WebSocketイベントリスナーの設定
  useEffect(() => {
    if (isConnected) {
      // 部屋に参加
      websocketService.joinRoom(roomId);
      
      // 強化されたイベントリスナーを登録
      websocketService.on('game_started', handleGameStarted);
      websocketService.on('new_speech', handleNewSpeech);
      websocketService.on('player_joined', handlePlayerJoined);
      websocketService.on('room_updated', handleRoomUpdated);
      websocketService.on('vote_phase_started', handleVotePhaseStarted);
      websocketService.on('vote_cast', handleVoteCast);
      websocketService.on('night_phase_started', handleNightPhaseStarted);
      
      // 新しい完全ゲーム状態リスナー
      websocketService.on('complete_game_state', handleCompleteGameState);
    }

    // 強化されたクリーンアップ
    return () => {
      websocketService.off('game_started', handleGameStarted);
      websocketService.off('new_speech', handleNewSpeech);
      websocketService.off('player_joined', handlePlayerJoined);
      websocketService.off('room_updated', handleRoomUpdated);
      websocketService.off('vote_phase_started', handleVotePhaseStarted);
      websocketService.off('vote_cast', handleVoteCast);
      websocketService.off('night_phase_started', handleNightPhaseStarted);
      websocketService.off('complete_game_state', handleCompleteGameState);
    };
  }, [isConnected, roomId, handleGameStarted, handleNewSpeech, handlePlayerJoined, handleRoomUpdated, handleVotePhaseStarted, handleVoteCast, handleNightPhaseStarted, handleCompleteGameState]);

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

  // 部屋ID不一致チェックと修正
  useEffect(() => {
    if (storedRoomId && storedRoomId !== roomId) {
      console.warn(`🚨 Room ID mismatch detected:`, {
        urlRoomId: roomId,
        storedRoomId: storedRoomId,
        action: 'updating_stored_room_id'
      });
      // 新しい部屋IDでlocalStorageを更新（ログアウトしない）
      localStorage.setItem('room_id', roomId);
      console.log(`✅ Updated stored room_id to: ${roomId}`);
    }
    
    // 部屋データを取得（認証状態に関係なく）
    fetchRoomData();
  }, [roomId, storedRoomId, onBackToLobby]);

  // ステータス表示
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'waiting': return 'success';
      case 'day_discussion': return 'warning';
      case 'day_vote': return 'danger';
      case 'night': return 'secondary';
      case 'finished': return 'success';
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

  // 強化された現在の発言者取得
  const getCurrentSpeaker = (): PlayerInfo | null => {
    if (!room?.turn_order || 
        room.current_turn_index === undefined || 
        room.current_turn_index < 0 || 
        room.current_turn_index >= room.turn_order.length) {
      console.log('getCurrentSpeaker: Invalid turn state');
      return null;
    }
    const currentPlayerId = room.turn_order[room.current_turn_index];
    const speaker = room.players.find(p => p.player_id === currentPlayerId) || null;
    
    if (speaker) {
      console.log('Current speaker:', speaker.character_name, speaker.player_id);
    } else {
      console.log('No speaker found for player ID:', currentPlayerId);
    }
    
    return speaker;
  };

  if (!room) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-900 text-white min-h-screen">
        <button onClick={onBackToLobby} className="mb-4 px-4 py-2 border border-gray-300 hover:bg-gray-50 text-white rounded transition-colors">
          ← ロビーに戻る
        </button>
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

  // 安全なisMyTurn判定システム（useMemoを使わない）
  const currentSpeaker = getCurrentSpeaker();
  
  // useMemoを使わずに直接計算（React Error #310を回避）
  const getIsMyTurn = () => {
    // フォルバックチェック
    if (!room?.turn_order || 
        room.current_turn_index === undefined ||
        room.current_turn_index < 0 ||
        room.current_turn_index >= room.turn_order.length ||
        !currentPlayerId) {
      console.log('isMyTurn: Invalid state', {
        hasTurnOrder: !!room?.turn_order,
        turnIndex: room?.current_turn_index,
        turnOrderLength: room?.turn_order?.length,
        hasCurrentPlayerId: !!currentPlayerId
      });
      return false;
    }
    
    const currentTurnPlayerId = room.turn_order[room.current_turn_index];
    const result = currentTurnPlayerId === currentPlayerId;
    
    console.log('isMyTurn calculation:', {
      currentTurnIndex: room.current_turn_index,
      currentTurnPlayerId,
      myPlayerId: currentPlayerId,
      isMyTurn: result,
      gameStatus: room.status
    });
    
    return result;
  };
  
  const isMyTurn = getIsMyTurn();
  
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
        <button onClick={onBackToLobby} className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-white rounded transition-colors">
          ← ロビーに戻る
        </button>
        <div className="text-center">
          <h1 className="text-2xl font-bold">
            {room.room_name || `部屋 ${room.room_id.slice(0, 8)}`}
          </h1>
          <div className="flex items-center gap-2 justify-center mt-2">
            <span className={`px-2 py-1 text-xs rounded font-medium ${
              getStatusColor(room.status) === 'success' ? 'bg-green-100 text-green-800' :
              getStatusColor(room.status) === 'warning' ? 'bg-yellow-100 text-yellow-800' :
              getStatusColor(room.status) === 'danger' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {getStatusLabel(room.status)}
            </span>
            {room.status !== 'waiting' && (
              <div className="flex gap-2">
                <span className="px-2 py-1 text-xs rounded font-medium border border-gray-300 text-gray-200">
                  {room.day_number}日目
                </span>
                {room.status === 'day_discussion' && room.current_round && (
                  <span className="px-2 py-1 text-xs rounded font-medium bg-blue-600/20 border border-blue-400/50 text-blue-200">
                    ラウンド {room.current_round}/3
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ConnectionStatus compact={true} showReconnectButton={false} />
          <button
            className="px-3 py-1 text-sm border border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white rounded transition-colors"
            onClick={() => setShowSummary(true)}
          >
            📊 サマリー
          </button>
          <button 
            className="px-3 py-1 text-sm bg-gray-600 text-white hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
            onClick={fetchRoomData} 
            disabled={loading}
          >
            {loading ? '更新中...' : '更新'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-900 border border-red-700 rounded-lg text-red-200">
          <p className="font-semibold">エラー: {error}</p>
        </div>
      )}

      {/* 接続状態警告 */}
      {!isConnected && (
        <div className="mb-4 p-4 bg-orange-900 border border-orange-700 rounded-lg">
          <ConnectionStatus showReconnectButton={true} />
        </div>
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
        <div className="lg:col-span-2 h-full overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800 flex flex-col space-y-4">
          {/* 強化されたゲーム制御コンポーネント */}
          {process.env.NODE_ENV === 'development' && (
            <div className="bg-gray-800 p-3 rounded border text-xs">
              <div className="text-yellow-400 font-bold mb-2">デバッグ情報:</div>
              <div>Game Status: <span className="text-green-400">{room.status}</span></div>
              <div>Turn Index: <span className="text-green-400">{room.current_turn_index}</span></div>
              <div>Turn Order Length: <span className="text-green-400">{room.turn_order?.length || 0}</span></div>
              <div>Current Speaker: <span className="text-green-400">{currentSpeaker?.character_name || 'None'}</span></div>
              <div>Is My Turn: <span className={isMyTurn ? 'text-green-400' : 'text-red-400'}>{isMyTurn ? 'YES' : 'NO'}</span></div>
              <div>My Player ID: <span className="text-blue-400">{currentPlayerId}</span></div>
              <div>Current Turn Player ID: <span className="text-blue-400">{room.turn_order?.[room.current_turn_index || 0] || 'None'}</span></div>
            </div>
          )}
          
          <GameControls
            gameStatus={room.status}
            isMyTurn={isMyTurn}
            currentPlayer={currentSpeaker}
            currentRound={room.current_round}
            onSpeak={handleSpeak}
            isLoading={loading}
            currentPlayerId={currentPlayerId}
            allPlayers={room.players}
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
            <div className="mb-4 p-4 bg-blue-900 border border-blue-700 rounded-lg">
              <h3 className="font-semibold mb-3 text-blue-200">夜フェーズ</h3>
              <p className="text-blue-300 mb-4">人狼が活動する時間です...</p>
              
              <button
                onClick={handleNightAction}
                disabled={loading}
                className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white rounded transition-colors"
              >
                {loading ? '処理中...' : '朝を迎える'}
              </button>
            </div>
          )}
          
          {/* 夜フェーズ（占い師以外の役職向けメッセージ） */}
          {room.status === 'night' && !shouldShowSeerPanel && currentPlayer?.is_alive && (
            <div className="mb-4 p-4 bg-gray-800 border border-gray-700 rounded-lg">
              <h4 className="font-medium text-gray-200 mb-2">夜の時間</h4>
              <p className="text-sm text-gray-300">
                {currentPlayer?.role === 'werewolf' 
                  ? '人狼たちが相談する時間です...' 
                  : '静かに朝を待ちましょう...'}
              </p>
            </div>
          )}

          {/* ゲームログ */}
          <GameLog
            logs={logs}
            onRefresh={fetchRoomData}
            isLoading={loading}
          />
        </div>
      </div>
      
      {/* ゲームサマリーモーダル */}
      <GameSummary
        roomId={roomId}
        isOpen={showSummary}
        onClose={() => setShowSummary(false)}
      />
    </div>
  );
}