import React, { useEffect, useState } from 'react';
import { Card, CardBody } from '@heroui/card';
import { 
  PhaseTransitionConfig, 
  getPhaseIcon, 
  getPhaseColor,
  animationVariants 
} from '@/animations/phaseTransitions';

interface PhaseTransitionProps {
  transition: PhaseTransitionConfig;
  onTransitionComplete: () => void;
  className?: string;
}

export function PhaseTransition({ 
  transition, 
  onTransitionComplete, 
  className = "" 
}: PhaseTransitionProps) {
  const [stage, setStage] = useState<'initial' | 'animate' | 'exit'>('initial');
  const [showMessage, setShowMessage] = useState(false);

  useEffect(() => {
    const timer1 = setTimeout(() => {
      setStage('animate');
      setShowMessage(true);
    }, 100);

    const timer2 = setTimeout(() => {
      setStage('exit');
    }, transition.duration - 500);

    const timer3 = setTimeout(() => {
      onTransitionComplete();
    }, transition.duration);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [transition.duration, onTransitionComplete]);

  const getBackgroundGradient = () => {
    const variant = animationVariants[transition.animation as keyof typeof animationVariants];
    if (variant && variant[stage]) {
      return variant[stage].background || '';
    }
    return 'linear-gradient(to bottom, #60a5fa, #3b82f6)';
  };

  const getAnimationStyle = () => {
    const variant = animationVariants[transition.animation as keyof typeof animationVariants];
    if (variant && variant[stage]) {
      const { background, ...styles } = variant[stage];
      return styles;
    }
    return {};
  };

  const getPhaseLabel = (phase: string) => {
    switch (phase) {
      case 'waiting': return '開始待ち';
      case 'day_discussion': return '昼の議論';
      case 'day_vote': return '投票フェーズ';
      case 'night': return '夜フェーズ';
      case 'finished': return 'ゲーム終了';
      default: return phase;
    }
  };

  return (
    <div 
      className={`fixed inset-0 z-50 flex items-center justify-center ${className}`}
      style={{
        background: getBackgroundGradient(),
        transition: 'background 1s ease-in-out'
      }}
    >
      {/* オーバーレイ効果 */}
      <div className="absolute inset-0 bg-black bg-opacity-20" />
      
      {/* メインコンテンツ */}
      <div 
        className="relative z-10"
        style={{
          ...getAnimationStyle(),
          transition: 'all 1s cubic-bezier(0.4, 0.0, 0.2, 1)'
        }}
      >
        <Card className="w-96 mx-auto bg-white/90 backdrop-blur-sm border-0 shadow-2xl">
          <CardBody className="text-center p-8">
            {/* フェーズアイコン */}
            <div className="mb-6">
              <div 
                className="text-6xl mb-4 inline-block"
                style={{
                  transform: stage === 'animate' ? 'scale(1.1)' : 'scale(1)',
                  transition: 'transform 0.5s ease-out'
                }}
              >
                {getPhaseIcon(transition.from)}
              </div>
              <div className="text-4xl opacity-50 mx-4 inline-block">→</div>
              <div 
                className="text-6xl mb-4 inline-block"
                style={{
                  transform: stage === 'animate' ? 'scale(1.2)' : 'scale(1)',
                  transition: 'transform 0.5s ease-out 0.2s'
                }}
              >
                {getPhaseIcon(transition.to)}
              </div>
            </div>

            {/* フェーズ名 */}
            <div className="mb-4">
              <div className="text-lg text-gray-600 mb-2">
                {getPhaseLabel(transition.from)}
              </div>
              <div className="text-2xl font-bold" style={{ color: getPhaseColor(transition.to) }}>
                {getPhaseLabel(transition.to)}
              </div>
            </div>

            {/* 遷移メッセージ */}
            <div 
              className={`transition-all duration-1000 ${
                showMessage ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
              }`}
            >
              <p className="text-gray-700 text-lg font-medium">
                {transition.description}
              </p>
            </div>

            {/* プログレスバー */}
            <div className="mt-6">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="h-2 rounded-full transition-all duration-1000 ease-out"
                  style={{
                    backgroundColor: getPhaseColor(transition.to),
                    width: stage === 'initial' ? '0%' : 
                           stage === 'animate' ? '70%' : '100%'
                  }}
                />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* パーティクル効果（条件付き） */}
      {(transition.animation === 'victory' || transition.animation === 'sunrise') && (
        <div className="absolute inset-0 pointer-events-none">
          {Array.from({ length: 20 }).map((_, i) => (
            <div
              key={i}
              className="absolute w-2 h-2 bg-yellow-300 rounded-full opacity-70"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animation: `twinkle ${2 + Math.random() * 3}s infinite ${Math.random() * 2}s`,
                animationDelay: `${Math.random() * 2}s`
              }}
            />
          ))}
        </div>
      )}

      {/* CSS アニメーション定義 */}
      <style jsx>{`
        @keyframes twinkle {
          0%, 100% { 
            opacity: 0.3; 
            transform: scale(0.8); 
          }
          50% { 
            opacity: 1; 
            transform: scale(1.2); 
          }
        }
      `}</style>
    </div>
  );
}

export default PhaseTransition;