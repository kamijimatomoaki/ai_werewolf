// カードアニメーション定義

export interface CardFlipConfig {
  duration: number;
  delay?: number;
  staggerDelay?: number;
}

export const cardAnimations = {
  // プレイヤーカードのフリップアニメーション
  playerReveal: {
    initial: { 
      rotateY: 0,
      scale: 1,
      opacity: 1 
    },
    animate: { 
      rotateY: 180,
      scale: 1.05,
      opacity: 1 
    },
    exit: { 
      rotateY: 360,
      scale: 1,
      opacity: 1 
    }
  },

  // 役職公開アニメーション
  roleReveal: {
    initial: { 
      rotateY: 0,
      scale: 1,
      borderColor: '#e5e7eb',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    },
    animate: { 
      rotateY: 180,
      scale: 1.1,
      borderColor: '#f59e0b',
      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
    },
    exit: { 
      rotateY: 360,
      scale: 1,
      borderColor: '#10b981',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
    }
  },

  // 脱落プレイヤーアニメーション
  playerEliminated: {
    initial: { 
      opacity: 1,
      scale: 1,
      filter: 'grayscale(0%) blur(0px)',
      rotateZ: 0
    },
    animate: { 
      opacity: 0.6,
      scale: 0.95,
      filter: 'grayscale(100%) blur(1px)',
      rotateZ: -2
    },
    exit: { 
      opacity: 0.3,
      scale: 0.9,
      filter: 'grayscale(100%) blur(2px)',
      rotateZ: -5
    }
  },

  // カードホバー効果
  cardHover: {
    initial: { 
      scale: 1,
      rotateY: 0,
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    },
    hover: { 
      scale: 1.02,
      rotateY: 2,
      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
    }
  },

  // 新規プレイヤー追加アニメーション
  playerJoin: {
    initial: { 
      opacity: 0,
      scale: 0.8,
      y: 20
    },
    animate: { 
      opacity: 1,
      scale: 1,
      y: 0
    }
  },

  // プレイヤー退出アニメーション
  playerLeave: {
    initial: { 
      opacity: 1,
      scale: 1,
      x: 0
    },
    exit: { 
      opacity: 0,
      scale: 0.8,
      x: -100
    }
  }
};

export const staggerAnimation = {
  container: {
    initial: {},
    animate: {
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2
      }
    }
  },
  item: {
    initial: { 
      opacity: 0,
      y: 20,
      scale: 0.9
    },
    animate: { 
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 10
      }
    }
  }
};

export const flipCardVariants = {
  front: {
    rotateY: 0,
    transition: { duration: 0.6 }
  },
  back: {
    rotateY: 180,
    transition: { duration: 0.6 }
  }
};

// カード用のCSS-in-JS スタイル
export const cardStyles = {
  flipContainer: {
    perspective: '1000px',
    transformStyle: 'preserve-3d' as const
  },
  flipCard: {
    transition: 'transform 0.6s cubic-bezier(0.4, 0.0, 0.2, 1)',
    transformStyle: 'preserve-3d' as const,
    backfaceVisibility: 'hidden' as const
  },
  flipCardBack: {
    transform: 'rotateY(180deg)',
    position: 'absolute' as const,
    top: 0,
    left: 0,
    width: '100%',
    height: '100%'
  }
};