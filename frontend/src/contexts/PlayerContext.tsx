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
  verifySession: () => Promise<boolean>;
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

  // ローカルストレージからセッション情報を復元
  useEffect(() => {
    const savedSession = localStorage.getItem('werewolf_session');
    if (savedSession) {
      const session = JSON.parse(savedSession);
      setPlayerId(session.playerId);
      setPlayerName(session.playerName);
      setRoomId(session.roomId);
      setSessionToken(session.sessionToken);
    }
  }, []);

  // セッション情報をローカルストレージに保存
  const saveSession = (session: JoinRoomResponse) => {
    setPlayerId(session.player_id);
    setPlayerName(session.player_name);
    setRoomId(session.room_id);
    setSessionToken(session.session_token);
    
    localStorage.setItem('werewolf_session', JSON.stringify({
      playerId: session.player_id,
      playerName: session.player_name,
      roomId: session.room_id,
      sessionToken: session.session_token,
    }));
  };

  // 部屋に参加
  const joinRoom = async (roomId: string, playerName: string) => {
    try {
      const response = await apiService.joinRoom(roomId, playerName);
      saveSession(response);
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
    localStorage.removeItem('werewolf_session');
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

  const isAuthenticated = !!(playerId && sessionToken);

  const value: PlayerContextType = {
    playerId,
    playerName,
    roomId,
    sessionToken,
    isAuthenticated,
    joinRoom,
    logout,
    verifySession,
  };

  return (
    <PlayerContext.Provider value={value}>
      {children}
    </PlayerContext.Provider>
  );
};