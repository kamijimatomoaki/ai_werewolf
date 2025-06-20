import { useState, useEffect } from 'react';
import { apiService } from '@/services/api';
import { PlayerInfo } from '@/types/api';

export interface SeerInvestigateResult {
  investigator: string;
  target: string;
  result: string; // "人狼" または "村人"
  message: string;
}

interface UseSeerInvestigationProps {
  roomId: string;
  playerId: string;
  isActive: boolean; // 夜フェーズかつ占い師の時のみtrue
}

interface UseSeerInvestigationReturn {
  availableTargets: PlayerInfo[];
  investigationResult: SeerInvestigateResult | null;
  isInvestigating: boolean;
  canInvestigate: boolean;
  error: string | null;
  investigate: (targetId: string) => Promise<void>;
  clearResult: () => void;
  refreshTargets: () => Promise<void>;
}

export function useSeerInvestigation({
  roomId,
  playerId,
  isActive
}: UseSeerInvestigationProps): UseSeerInvestigationReturn {
  const [availableTargets, setAvailableTargets] = useState<PlayerInfo[]>([]);
  const [investigationResult, setInvestigationResult] = useState<SeerInvestigateResult | null>(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [canInvestigate, setCanInvestigate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 占い可能な対象を取得
  const refreshTargets = async () => {
    if (!isActive) {
      setAvailableTargets([]);
      setCanInvestigate(false);
      return;
    }

    try {
      setError(null);
      const response = await apiService.getAvailableInvestigateTargets(playerId);
      setAvailableTargets(response.available_targets);
      setCanInvestigate(response.can_investigate);
    } catch (err: any) {
      setError(err.message || '占い対象の取得に失敗しました');
      setAvailableTargets([]);
      setCanInvestigate(false);
    }
  };

  // 占いを実行
  const investigate = async (targetId: string) => {
    if (!canInvestigate || isInvestigating) return;

    try {
      setIsInvestigating(true);
      setError(null);
      
      const result = await apiService.seerInvestigate(roomId, playerId, targetId);
      setInvestigationResult(result);
      setCanInvestigate(false); // 占い後は再度占えない
      
      // 対象リストを更新
      await refreshTargets();
    } catch (err: any) {
      setError(err.message || '占いに失敗しました');
    } finally {
      setIsInvestigating(false);
    }
  };

  // 結果をクリア
  const clearResult = () => {
    setInvestigationResult(null);
    setError(null);
  };

  // isActiveが変わったら対象を更新
  useEffect(() => {
    refreshTargets();
  }, [isActive, playerId, roomId]);

  // 非アクティブ時は状態をクリア
  useEffect(() => {
    if (!isActive) {
      setInvestigationResult(null);
      setError(null);
    }
  }, [isActive]);

  return {
    availableTargets,
    investigationResult,
    isInvestigating,
    canInvestigate,
    error,
    investigate,
    clearResult,
    refreshTargets
  };
}