// UI マイクロインタラクション定義

export const uiAnimations = {
  // ボタンアニメーション
  button: {
    initial: { scale: 1 },
    hover: { 
      scale: 1.05,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 10
      }
    },
    tap: { 
      scale: 0.95,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 17
      }
    }
  },

  // プライマリボタン
  primaryButton: {
    initial: { 
      scale: 1,
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    },
    hover: { 
      scale: 1.02,
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 10
      }
    },
    tap: { 
      scale: 0.98,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 17
      }
    }
  },

  // ローディングスピナー
  loadingSpinner: {
    animate: {
      rotate: 360,
      transition: {
        duration: 1,
        repeat: Infinity,
        ease: "linear"
      }
    }
  },

  // 通知ポップアップ
  notification: {
    initial: { 
      opacity: 0,
      y: -50,
      scale: 0.9
    },
    animate: { 
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 500,
        damping: 30
      }
    },
    exit: { 
      opacity: 0,
      y: -20,
      scale: 0.95,
      transition: {
        duration: 0.2
      }
    }
  },

  // トーストメッセージ
  toast: {
    initial: { 
      opacity: 0,
      x: 300,
      scale: 0.9
    },
    animate: { 
      opacity: 1,
      x: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 500,
        damping: 30
      }
    },
    exit: { 
      opacity: 0,
      x: 300,
      scale: 0.9,
      transition: {
        duration: 0.3
      }
    }
  },

  // モーダルアニメーション
  modal: {
    initial: { 
      opacity: 0,
      scale: 0.8,
      y: 20
    },
    animate: { 
      opacity: 1,
      scale: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 30
      }
    },
    exit: { 
      opacity: 0,
      scale: 0.8,
      y: 20,
      transition: {
        duration: 0.2
      }
    }
  },

  // モーダルオーバーレイ
  modalOverlay: {
    initial: { opacity: 0 },
    animate: { 
      opacity: 1,
      transition: { duration: 0.3 }
    },
    exit: { 
      opacity: 0,
      transition: { duration: 0.2 }
    }
  },

  // カード入場アニメーション
  cardEntry: {
    initial: { 
      opacity: 0,
      y: 20,
      scale: 0.95
    },
    animate: { 
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25
      }
    }
  },

  // リスト項目のスライドイン
  listItem: {
    initial: { 
      opacity: 0,
      x: -20
    },
    animate: { 
      opacity: 1,
      x: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25
      }
    }
  },

  // フェードイン/アウト
  fadeInOut: {
    initial: { opacity: 0 },
    animate: { 
      opacity: 1,
      transition: { duration: 0.3 }
    },
    exit: { 
      opacity: 0,
      transition: { duration: 0.2 }
    }
  },

  // スライドアップ
  slideUp: {
    initial: { 
      opacity: 0,
      y: 30
    },
    animate: { 
      opacity: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 25
      }
    },
    exit: { 
      opacity: 0,
      y: -30,
      transition: {
        duration: 0.2
      }
    }
  },

  // プルス効果
  pulse: {
    animate: {
      scale: [1, 1.05, 1],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: "easeInOut"
      }
    }
  },

  // バウンス効果
  bounce: {
    animate: {
      y: [0, -10, 0],
      transition: {
        duration: 0.6,
        repeat: Infinity,
        ease: "easeInOut"
      }
    }
  }
};

// スタッガーアニメーション設定
export const staggerVariants = {
  container: {
    animate: {
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1
      }
    }
  },
  item: {
    initial: { opacity: 0, y: 20 },
    animate: { 
      opacity: 1, 
      y: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25
      }
    }
  }
};

// 設定可能なアニメーション設定
export const animationSettings = {
  // アニメーション有効/無効フラグ
  enabled: true,
  
  // 速度設定
  speed: {
    fast: 0.2,
    normal: 0.3,
    slow: 0.5
  },
  
  // イージング設定
  easing: {
    smooth: "ease-in-out",
    bounce: "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
    sharp: "cubic-bezier(0.4, 0, 0.2, 1)"
  }
};