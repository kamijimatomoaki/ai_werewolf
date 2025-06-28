import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService, JoinRoomResponse } from '@/services/api';

interface PlayerContextType {
  playerId: string | null;
  playerName: string | null;
  roomId: string | null;
  sessionToken: string | null;
  isAuthenticated: boolean;
  joinRoom: (roomId: string, playerName: string) => Promise<void>;
  logout: () => void;
  clearRoomSession: () => void;
  verifySession: () => Promise<boolean>;
  updatePlayerId: (newPlayerId: string) => void;
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined);

export const usePlayer = () => {
  const context = useContext(PlayerContext);
  if (context === undefined) {
    throw new Error('usePlayer must be used within a PlayerProvider');
  }
  return context;
};

interface PlayerProviderProps {
  children: React.ReactNode;
}

export const PlayerProvider: React.FC<PlayerProviderProps> = ({ children }) => {
  const [playerId, setPlayerId] = useState<string | null>(null);
  const [playerName, setPlayerName] = useState<string | null>(null);
  const [roomId, setRoomId] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);

  // セッション情報をローカルストレージから復元
  useEffect(() => {
    const storedPlayerId = localStorage.getItem('player_id');
    const storedPlayerName = localStorage.getItem('player_name');
    const storedRoomId = localStorage.getItem('room_id');
    const storedSessionToken = localStorage.getItem('session_token');

    console.log('🔑 PlayerContext session restoration:', {
      storedPlayerId,
      storedPlayerName,
      storedRoomId,
      storedSessionToken: storedSessionToken ? '***' : null,
      allConditionsMet: !!(storedPlayerId && storedPlayerName && storedRoomId && storedSessionToken)
    });

    if (storedPlayerId && storedPlayerName && storedRoomId && storedSessionToken) {
      console.log('✅ Restoring player session...');
      setPlayerId(storedPlayerId);
      setPlayerName(storedPlayerName);
      setRoomId(storedRoomId);
      setSessionToken(storedSessionToken);
    } else {
      console.log('❌ Cannot restore player session - missing data');
    }
  }, []);

  // 部屋に参加
  const joinRoom = async (roomId: string, playerName: string) => {
    try {
      const response = await apiService.joinRoom(roomId, playerName);
      // apiService.joinRoomが既にローカルストレージに保存しているので、ここではstateを更新するだけ
      setPlayerId(response.player_id);
      setPlayerName(response.player_name);
      setRoomId(response.room_id);
      setSessionToken(response.session_token);
    } catch (error) {
      console.error('Failed to join room:', error);
      throw error;
    }
  };

  // ログアウト
  const logout = () => {
    setPlayerId(null);
    setPlayerName(null);
    setRoomId(null);
    setSessionToken(null);
    localStorage.removeItem('player_id');
    localStorage.removeItem('player_name');
    localStorage.removeItem('room_id');
    localStorage.removeItem('session_token');
  };

  // 部屋セッションのみクリア（プレイヤー名は保持）
  const clearRoomSession = () => {
    setPlayerId(null);
    setRoomId(null);
    setSessionToken(null);
    localStorage.removeItem('player_id');
    localStorage.removeItem('room_id');
    localStorage.removeItem('session_token');
    // player_name は保持して再利用可能にする
    console.log('🔄 Room session cleared, player name preserved for re-joining');
  };

  // セッション検証
  const verifySession = async (): Promise<boolean> => {
    if (!sessionToken) {
      return false;
    }

    try {
      const response = await apiService.verifySession(sessionToken);
      // セッションが有効な場合、情報を更新
      setPlayerId(response.player_id);
      setPlayerName(response.player_name);
      setRoomId(response.room_id);
      return true;
    } catch (error) {
      console.error('Session verification failed:', error);
      logout(); // 無効なセッションをクリア
      return false;
    }
  };

  // Player ID更新機能（ゲーム進行中のID不一致修正用）
  const updatePlayerId = (newPlayerId: string) => {
    console.log('🔧 Updating player ID:', {
      oldPlayerId: playerId,
      newPlayerId: newPlayerId
    });
    setPlayerId(newPlayerId);
    localStorage.setItem('player_id', newPlayerId);
  };

  const isAuthenticated = !!(playerId && sessionToken);

  const value: PlayerContextType = {
    playerId,
    playerName,
    roomId,
    sessionToken,
    isAuthenticated,
    joinRoom,
    logout,
    clearRoomSession,
    verifySession,
    updatePlayerId,
  };

  return (
    <PlayerContext.Provider value={value}>
      {children}
    </PlayerContext.Provider>
  );
};