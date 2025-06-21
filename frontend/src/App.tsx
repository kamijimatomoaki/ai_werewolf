import { useState } from "react";
import RoomList from '@/components/RoomList';
import GameRoom from '@/components/GameRoom';
import SpectatorLayout from '@/components/layout/SpectatorLayout';
import ErrorBoundary from '@/components/ui/ErrorBoundary';
import backgroundImage from '@/assets/background.jpg';

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
      <div className="min-h-screen bg-gray-900 text-white relative overflow-hidden">
        {/* 背景画像 */}
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-20"
          style={{ backgroundImage: `url(${backgroundImage})` }}
        />
        {/* ダークオーバーレイ */}
        <div className="absolute inset-0 bg-black bg-opacity-60" />
        
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