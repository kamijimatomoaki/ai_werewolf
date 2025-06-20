import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

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

interface SpectatorInfo {
  spectator_id: string;
  spectator_name: string;
  joined_at: string;
  is_active: boolean;
}

interface SpectatorChatMessage {
  message_id: string;
  spectator_name: string;
  message: string;
  timestamp: string;
}

interface UseSpectatorModeReturn {
  roomView: SpectatorRoomView | null;
  spectators: SpectatorInfo[];
  chatMessages: SpectatorChatMessage[];
  isLoading: boolean;
  sendChatMessage: (message: string) => Promise<void>;
  refreshRoomView: () => Promise<void>;
  leaveSpectatorMode: () => Promise<void>;
  error: string | null;
}

export function useSpectatorMode(roomId: string, spectatorId: string): UseSpectatorModeReturn {
  const [roomView, setRoomView] = useState<SpectatorRoomView | null>(null);
  const [spectators, setSpectators] = useState<SpectatorInfo[]>([]);
  const [chatMessages, setChatMessages] = useState<SpectatorChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { socket } = useWebSocket();

  // 観戦者用ゲーム情報を取得
  const fetchRoomView = useCallback(async () => {
    try {
      const response = await fetch(`/api/rooms/${roomId}/spectators/view`);
      if (response.ok) {
        const data = await response.json();
        setRoomView(data);
      } else {
        throw new Error('Failed to fetch room view');
      }
    } catch (err) {
      console.error('Error fetching room view:', err);
      setError('ゲーム情報の取得に失敗しました');
    }
  }, [roomId]);

  // 観戦者一覧を取得
  const fetchSpectators = useCallback(async () => {
    try {
      const response = await fetch(`/api/rooms/${roomId}/spectators`);
      if (response.ok) {
        const data = await response.json();
        setSpectators(data);
      } else {
        throw new Error('Failed to fetch spectators');
      }
    } catch (err) {
      console.error('Error fetching spectators:', err);
    }
  }, [roomId]);

  // チャット履歴を取得
  const fetchChatHistory = useCallback(async () => {
    try {
      const response = await fetch(`/api/rooms/${roomId}/spectators/chat`);
      if (response.ok) {
        const data = await response.json();
        setChatMessages(data);
      } else {
        throw new Error('Failed to fetch chat history');
      }
    } catch (err) {
      console.error('Error fetching chat history:', err);
    }
  }, [roomId]);

  // 初期データを取得
  const refreshRoomView = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchRoomView(),
        fetchSpectators(),
        fetchChatHistory()
      ]);
    } catch (err) {
      console.error('Error refreshing data:', err);
      setError('データの更新に失敗しました');
    } finally {
      setIsLoading(false);
    }
  }, [fetchRoomView, fetchSpectators, fetchChatHistory]);

  // チャットメッセージを送信
  const sendChatMessage = useCallback(async (message: string) => {
    try {
      const response = await fetch(`/api/rooms/${roomId}/spectators/${spectatorId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          spectator_name: 'Current Spectator', // 実際の名前は後で修正
          message: message
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send message');
      }

      // メッセージ送信成功後、チャット履歴を更新
      await fetchChatHistory();
    } catch (err) {
      console.error('Error sending chat message:', err);
      throw err;
    }
  }, [roomId, spectatorId, fetchChatHistory]);

  // 観戦モードを退出
  const leaveSpectatorMode = useCallback(async () => {
    try {
      const response = await fetch(`/api/spectators/${spectatorId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to leave spectator mode');
      }
    } catch (err) {
      console.error('Error leaving spectator mode:', err);
      throw err;
    }
  }, [spectatorId]);

  // WebSocket イベントリスナー
  useEffect(() => {
    if (!socket) return;

    const handleSpectatorJoined = (data: any) => {
      if (data.room_id === roomId) {
        fetchSpectators();
      }
    };

    const handleSpectatorLeft = (data: any) => {
      if (data.room_id === roomId) {
        fetchSpectators();
      }
    };

    const handleSpectatorChat = (data: SpectatorChatMessage) => {
      setChatMessages(prev => [...prev, data]);
    };

    const handleGameStateUpdate = (data: any) => {
      if (data.room_id === roomId) {
        fetchRoomView();
      }
    };

    const handlePhaseChange = (data: any) => {
      if (data.room_id === roomId) {
        fetchRoomView();
      }
    };

    const handlePlayerAction = (data: any) => {
      if (data.room_id === roomId) {
        fetchRoomView();
      }
    };

    socket.on('spectator_joined', handleSpectatorJoined);
    socket.on('spectator_left', handleSpectatorLeft);
    socket.on('spectator_chat', handleSpectatorChat);
    socket.on('game_state_updated', handleGameStateUpdate);
    socket.on('phase_changed', handlePhaseChange);
    socket.on('player_spoke', handlePlayerAction);
    socket.on('vote_completed', handlePlayerAction);
    socket.on('night_action_completed', handlePlayerAction);

    return () => {
      socket.off('spectator_joined', handleSpectatorJoined);
      socket.off('spectator_left', handleSpectatorLeft);
      socket.off('spectator_chat', handleSpectatorChat);
      socket.off('game_state_updated', handleGameStateUpdate);
      socket.off('phase_changed', handlePhaseChange);
      socket.off('player_spoke', handlePlayerAction);
      socket.off('vote_completed', handlePlayerAction);
      socket.off('night_action_completed', handlePlayerAction);
    };
  }, [socket, roomId, fetchRoomView, fetchSpectators]);

  // 初期データ取得
  useEffect(() => {
    refreshRoomView();
  }, [refreshRoomView]);

  // roomIdやspectatorIdが変更された場合の状態リセット
  useEffect(() => {
    setRoomView(null);
    setSpectators([]);
    setChatMessages([]);
    setError(null);
  }, [roomId, spectatorId]);

  return {
    roomView,
    spectators,
    chatMessages,
    isLoading,
    sendChatMessage,
    refreshRoomView,
    leaveSpectatorMode,
    error
  };
}

export default useSpectatorMode;