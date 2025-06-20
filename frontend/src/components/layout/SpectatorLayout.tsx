import React from 'react';
import SpectatorView from '@/components/game/SpectatorView';
import ErrorBoundary from '@/components/ui/ErrorBoundary';

interface SpectatorLayoutProps {
  roomId: string;
  spectatorId: string;
  onBackToLobby: () => void;
}

export function SpectatorLayout({ roomId, spectatorId, onBackToLobby }: SpectatorLayoutProps) {
  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-purple-500 to-blue-600">
        <SpectatorView
          roomId={roomId}
          spectatorId={spectatorId}
          onLeaveSpectator={onBackToLobby}
        />
      </div>
    </ErrorBoundary>
  );
}

export default SpectatorLayout;