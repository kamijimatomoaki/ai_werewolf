// APIサービス - FastAPIバックエンドとの通信

import { 
  RoomSummary, 
  RoomInfo, 
  RoomCreate, 
  PlayerInfo, 
  PersonaInput, 
  SpeakInput, 
  GameLogInfo 
} from '@/types/api';

export interface JoinRoomResponse {
  player_id: string;
  player_name: string;
  room_id: string;
  session_token: string;
}

export interface VoteRequest {
  voter_id: string;
  target_id: string;
}

export interface VoteResult {
  vote_counts: { [key: string]: number };
  voted_out_player_id?: string;
  tied_vote: boolean;
  message: string;
}

export interface SeerInvestigateResult {
  investigator: string;
  target: string;
  result: string; // "人狼" または "村人"
  message: string;
}

export interface AvailableTargetsResponse {
  available_targets: PlayerInfo[];
  can_investigate: boolean;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// デバッグ用: 実際に使用されているAPI URLをログ出力
console.log('API_BASE_URL:', API_BASE_URL);
console.log('VITE_API_BASE_URL env var:', import.meta.env.VITE_API_BASE_URL);

class ApiService {
  // 部屋管理
  async getRooms(skip: number = 0, limit: number = 10): Promise<RoomSummary[]> {
    const response = await fetch(`${API_BASE_URL}/rooms?skip=${skip}&limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch rooms');
    return response.json();
  }

  async createRoom(roomData: RoomCreate, hostName: string = 'ホスト'): Promise<RoomInfo> {
    const response = await fetch(`${API_BASE_URL}/rooms?host_name=${encodeURIComponent(hostName)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(roomData),
    });
    if (!response.ok) throw new Error('Failed to create room');
    return response.json();
  }

  async getRoom(roomId: string): Promise<RoomInfo> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}`);
    if (!response.ok) throw new Error('Failed to fetch room');
    return response.json();
  }

  async startGame(roomId: string): Promise<RoomInfo> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/start`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to start game');
    return response.json();
  }

  // プレイヤー管理
  async getPlayer(playerId: string): Promise<PlayerInfo> {
    const response = await fetch(`${API_BASE_URL}/players/${playerId}`);
    if (!response.ok) throw new Error('Failed to fetch player');
    return response.json();
  }

  async generatePersona(playerId: string, keywords: string): Promise<PlayerInfo> {
    const response = await fetch(`${API_BASE_URL}/players/${playerId}/generate_persona`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ keywords } as PersonaInput),
    });
    if (!response.ok) throw new Error('Failed to generate persona');
    return response.json();
  }

  // ゲーム進行
  async speak(roomId: string, playerId: string, statement: string): Promise<RoomInfo> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/speak?player_id=${playerId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ statement } as SpeakInput),
    });
    if (!response.ok) throw new Error('Failed to speak');
    return response.json();
  }

  async getGameLogs(roomId: string): Promise<GameLogInfo[]> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/logs`);
    if (!response.ok) throw new Error('Failed to fetch game logs');
    return response.json();
  }

  // プレイヤー参加
  async joinRoom(roomId: string, playerName: string): Promise<JoinRoomResponse> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/join?player_name=${encodeURIComponent(playerName)}`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to join room');
    return response.json();
  }

  // セッション検証
  async verifySession(sessionToken: string): Promise<{ player_id: string; player_name: string; room_id: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/verify?session_token=${encodeURIComponent(sessionToken)}`);
    if (!response.ok) throw new Error('Session verification failed');
    return response.json();
  }

  // 投票
  async vote(roomId: string, voterId: string, targetId: string): Promise<VoteResult> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/vote`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ voter_id: voterId, target_id: targetId } as VoteRequest),
    });
    if (!response.ok) throw new Error('Failed to vote');
    return response.json();
  }

  // 投票フェーズへの移行
  async transitionToVote(roomId: string): Promise<RoomInfo> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/transition_to_vote`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to transition to vote');
    return response.json();
  }

  // 夜のアクション
  async nightAction(roomId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/night_action`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to execute night action');
    return response.json();
  }

  // 占い師機能
  async getAvailableInvestigateTargets(playerId: string): Promise<AvailableTargetsResponse> {
    const response = await fetch(`${API_BASE_URL}/players/${playerId}/available_targets`);
    if (!response.ok) throw new Error('Failed to fetch available targets');
    return response.json();
  }

  async seerInvestigate(roomId: string, investigatorId: string, targetId: string): Promise<SeerInvestigateResult> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/seer_investigate?investigator_id=${investigatorId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ target_player_id: targetId }),
    });
    if (!response.ok) throw new Error('Failed to investigate');
    return response.json();
  }

  // ヘルスチェック（ネットワーク状態確認用）
  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) throw new Error('Health check failed');
    return response.json();
  }

  // データベース初期化（開発用）
  async initializeDatabase(): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/initdb`);
    if (!response.ok) throw new Error('Failed to initialize database');
    return response.json();
  }

  // AI自動進行
  async autoProgress(roomId: string): Promise<{ 
    message: string;
    chained_speakers?: Array<{
      player_name: string;
      statement: string;
    }>;
  }> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/auto_progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('Failed to auto progress');
    return response.json();
  }

  // ゲームサマリー取得
  async getGameSummary(roomId: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/summary`);
      
      if (!response.ok) {
        let errorMessage = 'Failed to get game summary';
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          // JSON パースに失敗した場合はデフォルトメッセージを使用
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
      
      return response.json();
    } catch (error) {
      console.error('API getGameSummary error:', error);
      throw error;
    }
  }
}

export const apiService = new ApiService();