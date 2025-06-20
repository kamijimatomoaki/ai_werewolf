// フェーズ遷移アニメーション定義

export interface PhaseTransitionConfig {
  from: string;
  to: string;
  duration: number;
  animation: string;
  description: string;
}

export const phaseTransitions: PhaseTransitionConfig[] = [
  {
    from: 'waiting',
    to: 'day_discussion',
    duration: 2000,
    animation: 'sunrise',
    description: 'ゲーム開始 - 朝が来ました'
  },
  {
    from: 'day_discussion',
    to: 'day_vote',
    duration: 1500,
    animation: 'gavel',
    description: '投票フェーズへ移行'
  },
  {
    from: 'day_vote',
    to: 'night',
    duration: 2000,
    animation: 'sunset',
    description: '夜が訪れました...'
  },
  {
    from: 'night',
    to: 'day_discussion',
    duration: 2000,
    animation: 'sunrise',
    description: '朝になりました'
  },
  {
    from: 'day_vote',
    to: 'finished',
    duration: 2500,
    animation: 'victory',
    description: 'ゲーム終了'
  },
  {
    from: 'night',
    to: 'finished',
    duration: 2500,
    animation: 'victory',
    description: 'ゲーム終了'
  }
];

export const animationVariants = {
  sunrise: {
    initial: { 
      opacity: 0, 
      background: 'linear-gradient(to bottom, #1e3a8a, #3730a3)' // 夜空
    },
    animate: { 
      opacity: 1, 
      background: 'linear-gradient(to bottom, #fbbf24, #f59e0b)' // 朝焼け
    },
    exit: { 
      opacity: 0,
      background: 'linear-gradient(to bottom, #60a5fa, #3b82f6)' // 昼空
    }
  },
  sunset: {
    initial: { 
      opacity: 0, 
      background: 'linear-gradient(to bottom, #60a5fa, #3b82f6)' // 昼空
    },
    animate: { 
      opacity: 1, 
      background: 'linear-gradient(to bottom, #f97316, #ea580c)' // 夕焼け
    },
    exit: { 
      opacity: 0,
      background: 'linear-gradient(to bottom, #1e3a8a, #3730a3)' // 夜空
    }
  },
  gavel: {
    initial: { 
      scale: 0.8, 
      rotate: -10,
      opacity: 0 
    },
    animate: { 
      scale: 1, 
      rotate: 0,
      opacity: 1 
    },
    exit: { 
      scale: 1.1, 
      rotate: 10,
      opacity: 0 
    }
  },
  victory: {
    initial: { 
      scale: 0,
      rotate: -180,
      opacity: 0 
    },
    animate: { 
      scale: 1,
      rotate: 0,
      opacity: 1 
    },
    exit: { 
      scale: 1.2,
      rotate: 180,
      opacity: 0 
    }
  }
};

export const getPhaseIcon = (phase: string): string => {
  switch (phase) {
    case 'waiting': return '⏳';
    case 'day_discussion': return '🌅';
    case 'day_vote': return '🗳️';
    case 'night': return '🌙';
    case 'finished': return '🏁';
    default: return '❓';
  }
};

export const getPhaseColor = (phase: string): string => {
  switch (phase) {
    case 'waiting': return '#6b7280'; // gray
    case 'day_discussion': return '#f59e0b'; // amber
    case 'day_vote': return '#3b82f6'; // blue
    case 'night': return '#6366f1'; // indigo
    case 'finished': return '#10b981'; // emerald
    default: return '#6b7280';
  }
};

export const findTransition = (from: string, to: string): PhaseTransitionConfig | null => {
  return phaseTransitions.find(t => t.from === from && t.to === to) || null;
};