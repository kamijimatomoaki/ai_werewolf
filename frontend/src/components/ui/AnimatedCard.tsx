import React, { useState, useEffect } from 'react';
import { cardAnimations, cardStyles } from '@/animations/cardAnimations';

interface AnimatedCardProps {
  children: React.ReactNode;
  isFlipped?: boolean;
  flipDuration?: number;
  hoverEffect?: boolean;
  eliminatedEffect?: boolean;
  className?: string;
  onFlipComplete?: () => void;
  backContent?: React.ReactNode;
  flipTrigger?: 'hover' | 'click' | 'manual';
}

export function AnimatedCard({
  children,
  isFlipped = false,
  flipDuration = 600,
  hoverEffect = true,
  eliminatedEffect = false,
  className = "",
  onFlipComplete,
  backContent,
  flipTrigger = 'manual'
}: AnimatedCardProps) {
  const [flipped, setFlipped] = useState(isFlipped);
  const [isHovered, setIsHovered] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    setFlipped(isFlipped);
  }, [isFlipped]);

  const handleFlip = () => {
    if (flipTrigger === 'click' && !isAnimating) {
      setIsAnimating(true);
      setFlipped(!flipped);
      
      setTimeout(() => {
        setIsAnimating(false);
        onFlipComplete?.();
      }, flipDuration);
    }
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (flipTrigger === 'hover' && !isAnimating) {
      setFlipped(true);
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (flipTrigger === 'hover' && !isAnimating) {
      setFlipped(false);
    }
  };

  const getCardStyle = () => {
    let style: React.CSSProperties = {
      ...cardStyles.flipContainer,
      transition: `transform ${flipDuration}ms cubic-bezier(0.4, 0.0, 0.2, 1)`,
    };

    // フリップ効果
    if (flipped) {
      style.transform = 'rotateY(180deg)';
    }

    // ホバー効果
    if (hoverEffect && isHovered && !flipped) {
      style.transform = 'scale(1.02) rotateY(2deg)';
      style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)';
    }

    // 脱落効果
    if (eliminatedEffect) {
      style.opacity = 0.6;
      style.filter = 'grayscale(100%) blur(1px)';
      style.transform = (style.transform || '') + ' scale(0.95) rotate(-2deg)';
    }

    return style;
  };

  return (
    <div
      className={`relative ${className}`}
      style={cardStyles.flipContainer}
      onClick={handleFlip}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* フロント面 */}
      <div
        className={`w-full h-full bg-white border border-gray-200 rounded-lg p-4 ${flipTrigger === 'click' ? 'cursor-pointer' : ''}`}
        style={{
          ...getCardStyle(),
          backfaceVisibility: 'hidden',
          zIndex: flipped ? 1 : 2
        }}
      >
        {children}
      </div>

      {/* バック面（バックコンテンツがある場合） */}
      {backContent && (
        <div
          className="absolute inset-0 w-full h-full bg-white border border-gray-200 rounded-lg p-4"
          style={{
            ...getCardStyle(),
            ...cardStyles.flipCardBack,
            backfaceVisibility: 'hidden',
            zIndex: flipped ? 2 : 1
          }}
        >
          {backContent}
        </div>
      )}

      {/* ローディングオーバーレイ（アニメーション中） */}
      {isAnimating && (
        <div className="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center z-10 rounded-lg">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}

// プレイヤーカード専用のアニメーションコンポーネント
interface AnimatedPlayerCardProps {
  children: React.ReactNode;
  isEliminated?: boolean;
  isRevealed?: boolean;
  playerRole?: string;
  className?: string;
  onReveal?: () => void;
}

export function AnimatedPlayerCard({
  children,
  isEliminated = false,
  isRevealed = false,
  playerRole,
  className = "",
  onReveal
}: AnimatedPlayerCardProps) {
  const [showRole, setShowRole] = useState(false);

  useEffect(() => {
    if (isRevealed && playerRole) {
      setTimeout(() => {
        setShowRole(true);
        onReveal?.();
      }, 300);
    }
  }, [isRevealed, playerRole, onReveal]);

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'werewolf': return '🐺';
      case 'seer': return '🔮';
      case 'bodyguard': return '🛡️';
      case 'villager': return '👤';
      default: return '❓';
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'werewolf': return 'bg-red-500';
      case 'seer': return 'bg-purple-500';
      case 'bodyguard': return 'bg-blue-500';
      case 'villager': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const backContent = playerRole ? (
    <div className="flex flex-col items-center justify-center h-full p-4">
      <div className="text-4xl mb-2">{getRoleIcon(playerRole)}</div>
      <div className={`px-3 py-1 rounded-full text-white text-sm font-medium ${getRoleColor(playerRole)}`}>
        {playerRole}
      </div>
    </div>
  ) : undefined;

  return (
    <AnimatedCard
      isFlipped={showRole}
      eliminatedEffect={isEliminated}
      backContent={backContent}
      className={className}
      onFlipComplete={() => {
        if (isRevealed) {
          onReveal?.();
        }
      }}
    >
      {children}
    </AnimatedCard>
  );
}

export default AnimatedCard;