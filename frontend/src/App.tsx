import { useState, useEffect } from "react";
import { usePlayer } from '@/contexts/PlayerContext';
import RoomList from '@/components/RoomList';
import GameRoom from '@/components/GameRoom';
import SpectatorLayout from '@/components/layout/SpectatorLayout';
import ErrorBoundary from '@/components/ui/ErrorBoundary';
import backgroundImage from '@/assets/background.jpg';

type AppView = 'lobby' | 'room' | 'spectator';

function App() {
  const { playerId, roomId } = usePlayer();
  const [currentView, setCurrentView] = useState<AppView>('lobby');
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null);
  const [currentSpectatorId, setCurrentSpectatorId] = useState<string | null>(null);

  // セッション復元時の自動リダイレクト
  useEffect(() => {
    if (playerId && roomId) {
      console.log('🔄 Auto-redirecting to room on session restore:', roomId);
      setCurrentRoomId(roomId);
      setCurrentView('room');
    }
  }, [playerId, roomId]);

  // 部屋に参加
  const handleRoomJoin = (roomId: string) => {
    setCurrentRoomId(roomId);
    setCurrentView('room');
    setCurrentSpectatorId(null);
  };

  // 観戦者として参加
  const handleSpectatorJoin = (roomId: string, spectatorId: string) => {
    setCurrentRoomId(roomId);
    setCurrentSpectatorId(spectatorId);
    setCurrentView('spectator');
  };

  // ロビーに戻る
  const handleBackToLobby = () => {
    setCurrentView('lobby');
    setCurrentRoomId(null);
    setCurrentSpectatorId(null);
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-gray-800 via-gray-900 to-black text-white relative overflow-hidden">
        {/* 背景画像 */}
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-15"
          style={{ backgroundImage: `url(${backgroundImage})` }}
        />
        {/* ソフトなオーバーレイ */}
        <div className="absolute inset-0 bg-gradient-to-br from-red-900/20 via-purple-900/10 to-blue-900/20" />
        
        {/* メインコンテンツ */}
        <div className="relative z-10">
          {currentView === 'lobby' ? (
            <RoomList 
              onRoomJoin={handleRoomJoin} 
              onSpectatorJoin={handleSpectatorJoin}
            />
          ) : currentView === 'room' ? (
            currentRoomId && (
              <GameRoom 
                roomId={currentRoomId}
                onBackToLobby={handleBackToLobby}
              />
            )
          ) : currentView === 'spectator' ? (
            currentRoomId && currentSpectatorId && (
              <SpectatorLayout
                roomId={currentRoomId}
                spectatorId={currentSpectatorId}
                onBackToLobby={handleBackToLobby}
              />
            )
          ) : null}
        </div>
      </div>
    </ErrorBoundary>
  );
}

export default App;