// API型定義ファイル - バックエンドのFastAPIサービスとの連携用

export interface PersonaOutput {
  name?: string;
  gender: string;
  age: number;
  personality: string;
  speech_style: string;
  background: string;
}

export interface PlayerInfo {
  player_id: string;
  is_human: boolean;
  is_alive: boolean;
  character_name: string;
  character_persona?: PersonaOutput;
  role?: string;
}

export interface RoomSummary {
  room_id: string;
  room_name?: string;
  status: string;
  total_players: number;
  human_players: number;
  ai_players: number;
  is_private: boolean;
}

export interface RoomInfo {
  room_id: string;
  room_name?: string;
  status: string;
  total_players: number;
  human_players: number;
  ai_players: number;
  day_number: number;
  current_round?: number;
  turn_order?: string[];
  current_turn_index?: number;
  players: PlayerInfo[];
  is_private: boolean;
}

export interface RoomCreate {
  room_name?: string;
  total_players: number;
  human_players: number;
  ai_players: number;
  is_private: boolean;
}

export interface SpeakInput {
  statement: string;
}

export interface GameLogInfo {
  log_id: string;
  event_type: string;
  content?: string;
  created_at: string;
  actor?: {
    player_id: string;
    character_name: string;
  };
}

export interface PersonaInput {
  keywords: string;
}