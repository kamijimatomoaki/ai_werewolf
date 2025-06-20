import { useState, useEffect, useCallback } from 'react';
import { findTransition, PhaseTransitionConfig } from '@/animations/phaseTransitions';

interface UseAnimationsReturn {
  isAnimating: boolean;
  currentTransition: PhaseTransitionConfig | null;
  startPhaseTransition: (from: string, to: string) => Promise<void>;
  animationSettings: {
    enabled: boolean;
    reducedMotion: boolean;
  };
  toggleAnimations: () => void;
}

export function useAnimations(): UseAnimationsReturn {
  const [isAnimating, setIsAnimating] = useState(false);
  const [currentTransition, setCurrentTransition] = useState<PhaseTransitionConfig | null>(null);
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);

  // ユーザーの動作軽減設定を検出
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // ローカルストレージからアニメーション設定を読み込み
  useEffect(() => {
    const saved = localStorage.getItem('werewolf-animations-enabled');
    if (saved !== null) {
      setAnimationsEnabled(JSON.parse(saved));
    }
  }, []);

  // フェーズ遷移アニメーションを開始
  const startPhaseTransition = useCallback(async (from: string, to: string): Promise<void> => {
    const transition = findTransition(from, to);
    if (!transition || !animationsEnabled || reducedMotion) {
      return Promise.resolve();
    }

    setIsAnimating(true);
    setCurrentTransition(transition);

    return new Promise((resolve) => {
      setTimeout(() => {
        setIsAnimating(false);
        setCurrentTransition(null);
        resolve();
      }, transition.duration);
    });
  }, [animationsEnabled, reducedMotion]);

  // アニメーション有効/無効を切り替え
  const toggleAnimations = useCallback(() => {
    const newValue = !animationsEnabled;
    setAnimationsEnabled(newValue);
    localStorage.setItem('werewolf-animations-enabled', JSON.stringify(newValue));
  }, [animationsEnabled]);

  return {
    isAnimating,
    currentTransition,
    startPhaseTransition,
    animationSettings: {
      enabled: animationsEnabled && !reducedMotion,
      reducedMotion
    },
    toggleAnimations
  };
}

// フェーズ変更時のアニメーション制御
export function usePhaseTransition() {
  const [previousPhase, setPreviousPhase] = useState<string>('');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const { startPhaseTransition, animationSettings } = useAnimations();

  const handlePhaseChange = useCallback(async (newPhase: string) => {
    if (previousPhase && previousPhase !== newPhase && animationSettings.enabled) {
      setIsTransitioning(true);
      await startPhaseTransition(previousPhase, newPhase);
      setIsTransitioning(false);
    }
    setPreviousPhase(newPhase);
  }, [previousPhase, startPhaseTransition, animationSettings.enabled]);

  return {
    isTransitioning,
    handlePhaseChange,
    animationSettings
  };
}

// カードフリップアニメーション制御
export function useCardFlip() {
  const [flippedCards, setFlippedCards] = useState<Set<string>>(new Set());
  const [isFlipping, setIsFlipping] = useState(false);

  const flipCard = useCallback((cardId: string, duration: number = 600) => {
    setIsFlipping(true);
    setFlippedCards(prev => new Set(prev).add(cardId));

    setTimeout(() => {
      setIsFlipping(false);
    }, duration);
  }, []);

  const resetCard = useCallback((cardId: string) => {
    setFlippedCards(prev => {
      const newSet = new Set(prev);
      newSet.delete(cardId);
      return newSet;
    });
  }, []);

  const resetAllCards = useCallback(() => {
    setFlippedCards(new Set());
  }, []);

  return {
    flippedCards,
    isFlipping,
    flipCard,
    resetCard,
    resetAllCards,
    isCardFlipped: (cardId: string) => flippedCards.has(cardId)
  };
}

// ステージャーアニメーション制御
export function useStaggerAnimation() {
  const [visibleItems, setVisibleItems] = useState<Set<string>>(new Set());

  const showItem = useCallback((itemId: string, delay: number = 0) => {
    setTimeout(() => {
      setVisibleItems(prev => new Set(prev).add(itemId));
    }, delay);
  }, []);

  const hideItem = useCallback((itemId: string) => {
    setVisibleItems(prev => {
      const newSet = new Set(prev);
      newSet.delete(itemId);
      return newSet;
    });
  }, []);

  const showItems = useCallback((itemIds: string[], staggerDelay: number = 100) => {
    itemIds.forEach((id, index) => {
      showItem(id, index * staggerDelay);
    });
  }, [showItem]);

  const resetAll = useCallback(() => {
    setVisibleItems(new Set());
  }, []);

  return {
    visibleItems,
    showItem,
    hideItem,
    showItems,
    resetAll,
    isVisible: (itemId: string) => visibleItems.has(itemId)
  };
}

export default useAnimations;