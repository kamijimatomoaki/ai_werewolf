import { useState } from "react";
import RoomList from '@/components/RoomList';
import GameRoom from '@/components/GameRoom';
import SpectatorLayout from '@/components/layout/SpectatorLayout';
import ErrorBoundary from '@/components/ui/ErrorBoundary';

type AppView = 'lobby' | 'room' | 'spectator';

function App() {
  const [currentView, setCurrentView] = useState<AppView>('lobby');
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null);
  const [currentSpectatorId, setCurrentSpectatorId] = useState<string | null>(null);

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
      <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600">
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
    </ErrorBoundary>
  );
}

export default App;