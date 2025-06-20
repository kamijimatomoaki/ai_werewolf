import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface PlayerInfo {
  player_id: string;
  character_name: string;
  is_alive: boolean;
  role?: string;
}

interface BodyguardProtectionResult {
  protector: string;
  target: string;
  message: string;
  success: boolean;
}

interface UseBodyguardProtectionReturn {
  availableTargets: PlayerInfo[];
  protectionResult: BodyguardProtectionResult | null;
  isProtecting: boolean;
  canProtect: boolean;
  protect: (targetId: string) => Promise<void>;
  error: string | null;
}

export function useBodyguardProtection(roomId: string, playerId: string): UseBodyguardProtectionReturn {
  const [availableTargets, setAvailableTargets] = useState<PlayerInfo[]>([]);
  const [protectionResult, setProtectionResult] = useState<BodyguardProtectionResult | null>(null);
  const [isProtecting, setIsProtecting] = useState(false);
  const [canProtect, setCanProtect] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { socket } = useWebSocket();

  // 守り可能な対象を取得
  const fetchAvailableTargets = useCallback(async () => {
    try {
      const response = await fetch(`/api/players/${playerId}/available_targets`);
      if (response.ok) {
        const data = await response.json();
        // ボディガードは自分以外の生存者を守ることができる
        const targets = data.targets?.filter((target: PlayerInfo) => 
          target.player_id !== playerId && target.is_alive
        ) || [];
        setAvailableTargets(targets);
      } else {
        throw new Error('Failed to fetch available targets');
      }
    } catch (err) {
      console.error('Error fetching available targets:', err);
      setError('対象プレイヤーの取得に失敗しました');
    }
  }, [playerId]);

  // ボディガード保護を実行
  const protect = useCallback(async (targetId: string) => {
    if (!canProtect || isProtecting) return;

    setIsProtecting(true);
    setError(null);

    try {
      const response = await fetch(`/api/rooms/${roomId}/bodyguard_protect?protector_id=${playerId}`, {
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
        setProtectionResult(result);
        setCanProtect(false);
        
        // 成功時にターゲットリストをクリア（もう選択する必要がないため）
        setAvailableTargets([]);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Protection failed');
      }
    } catch (err) {
      console.error('Protection error:', err);
      setError(err instanceof Error ? err.message : '守りに失敗しました');
    } finally {
      setIsProtecting(false);
    }
  }, [roomId, canProtect, isProtecting]);

  // WebSocket イベントリスナー
  useEffect(() => {
    if (!socket) return;

    const handleProtectionResult = (data: any) => {
      if (data.protector_id === playerId) {
        setProtectionResult(data.result);
        setCanProtect(false);
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
          setProtectionResult(null);
          setCanProtect(true);
          setError(null);
          fetchAvailableTargets();
        } else {
          // 夜フェーズ以外では対象リストをクリア
          setAvailableTargets([]);
          setCanProtect(false);
        }
      }
    };

    socket.on('bodyguard_protection_result', handleProtectionResult);
    socket.on('game_state_updated', handleGameStateUpdate);
    socket.on('phase_changed', handlePhaseChange);

    return () => {
      socket.off('bodyguard_protection_result', handleProtectionResult);
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
    setProtectionResult(null);
    setCanProtect(true);
    setError(null);
    setIsProtecting(false);
  }, [playerId, roomId]);

  return {
    availableTargets,
    protectionResult,
    isProtecting,
    canProtect,
    protect,
    error
  };
}

export default useBodyguardProtection;