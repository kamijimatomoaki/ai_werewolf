import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface PlayerInfo {
  player_id: string;
  character_name: string;
  is_alive: boolean;
  role?: string;
}

interface WerewolfAttackResult {
  attacker: string;
  target: string;
  message: string;
  success: boolean;
}

interface UseWerewolfAttackReturn {
  availableTargets: PlayerInfo[];
  attackResult: WerewolfAttackResult | null;
  isAttacking: boolean;
  canAttack: boolean;
  attack: (targetId: string) => Promise<void>;
  error: string | null;
}

export function useWerewolfAttack(roomId: string, playerId: string): UseWerewolfAttackReturn {
  const [availableTargets, setAvailableTargets] = useState<PlayerInfo[]>([]);
  const [attackResult, setAttackResult] = useState<WerewolfAttackResult | null>(null);
  const [isAttacking, setIsAttacking] = useState(false);
  const [canAttack, setCanAttack] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { socket } = useWebSocket();

  // 攻撃可能な対象を取得
  const fetchAvailableTargets = useCallback(async () => {
    try {
      const response = await fetch(`/api/players/${playerId}/available_targets`);
      if (response.ok) {
        const data = await response.json();
        // 人狼は村人陣営のみを攻撃対象とする
        const targets = data.targets?.filter((target: PlayerInfo) => 
          target.player_id !== playerId && target.is_alive
        ) || [];
        setAvailableTargets(targets);
        setError(null); // 成功時はエラーをクリア
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch available targets');
      }
    } catch (err) {
      console.error('Error fetching available targets:', err);
      setError(err instanceof Error ? err.message : '対象プレイヤーの取得に失敗しました');
    }
  }, [playerId]);

  // 人狼攻撃を実行
  const attack = useCallback(async (targetId: string) => {
    if (!canAttack || isAttacking) return;

    setIsAttacking(true);
    setError(null);

    try {
      const response = await fetch(`/api/rooms/${roomId}/werewolf_attack?attacker_id=${playerId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_player_id: targetId
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setAttackResult(result);
        setCanAttack(false);
        
        // 成功時にターゲットリストをクリア（もう選択する必要がないため）
        setAvailableTargets([]);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Attack failed');
      }
    } catch (err) {
      console.error('Attack error:', err);
      setError(err instanceof Error ? err.message : '攻撃に失敗しました');
    } finally {
      setIsAttacking(false);
    }
  }, [roomId, playerId, canAttack, isAttacking]);

  // WebSocket イベントリスナー
  useEffect(() => {
    if (!socket) return;

    const handleAttackResult = (data: any) => {
      if (data.attacker_id === playerId) {
        setAttackResult(data.result);
        setCanAttack(false);
      }
    };

    const handleGameStateUpdate = (data: any) => {
      // ゲーム状態が更新された場合、対象リストを再取得
      if (data.room_id === roomId) {
        fetchAvailableTargets();
      }
    };

    const handlePhaseChange = (data: any) => {
      if (data.room_id === roomId) {
        if (data.new_phase === 'night') {
          // 夜フェーズに入ったら状態をリセット
          setAttackResult(null);
          setCanAttack(true);
          setError(null);
          fetchAvailableTargets();
        } else {
          // 夜フェーズ以外では対象リストをクリア
          setAvailableTargets([]);
          setCanAttack(false);
        }
      }
    };

    socket.on('werewolf_attack_result', handleAttackResult);
    socket.on('game_state_updated', handleGameStateUpdate);
    socket.on('phase_changed', handlePhaseChange);

    return () => {
      socket.off('werewolf_attack_result', handleAttackResult);
      socket.off('game_state_updated', handleGameStateUpdate);
      socket.off('phase_changed', handlePhaseChange);
    };
  }, [socket, playerId, roomId, fetchAvailableTargets]);

  // 初期データ取得
  useEffect(() => {
    fetchAvailableTargets();
  }, [fetchAvailableTargets]);

  // プレイヤーIDやルームIDが変更された場合の状態リセット
  useEffect(() => {
    setAttackResult(null);
    setCanAttack(true);
    setError(null);
    setIsAttacking(false);
  }, [playerId, roomId]);

  return {
    availableTargets,
    attackResult,
    isAttacking,
    canAttack,
    attack,
    error
  };
}

export default useWerewolfAttack;