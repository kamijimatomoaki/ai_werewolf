# =================================================================
# FastAPI Game Logic Service - AI Werewolf Online (バグ修正・機能追加版)
# =================================================================
#
# 修正点:
# - `Room`モデルに`created_at`カラムを再追加し、部屋一覧取得APIのエラーを修正。
# - 部屋の公開・非公開設定を追加 (`is_private`フラグ)。
# - 部屋一覧APIでは公開部屋のみを返すように修正。
# - 特定のプレイヤー情報を取得するAPI(`GET /api/players/{player_id}`)を新設。
# - 会話履歴を取得するAPI (`GET /api/rooms/{room_id}/logs`) を新設。

import os
import uuid
import json
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

import socketio
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (Boolean, Column, DateTime, create_engine,
                        ForeignKey, Integer, String, Text, text, JSON)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker, joinedload
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import logging

# --- Enhanced Logging Setup ---
import sys
from datetime import datetime

# ログフォーマットを改善
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

# コンソール用ハンドラー
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)

# ファイル用ハンドラー（オプション）
try:
    file_handler = logging.FileHandler('werewolf_game.log')
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)
except Exception:
    file_handler = None

# ルートロガー設定
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
if file_handler:
    root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

# デバッグ情報収集用
class GameDebugInfo:
    """ゲームデバッグ情報の収集と管理"""
    
    def __init__(self):
        self.session_start = datetime.now(timezone.utc)
        self.api_calls = []
        self.errors = []
        self.game_events = []
    
    def log_api_call(self, endpoint: str, method: str, params: dict = None):
        self.api_calls.append({
            'timestamp': datetime.now(timezone.utc),
            'endpoint': endpoint,
            'method': method,
            'params': params or {}
        })
    
    def log_error(self, error: str, context: str = None):
        self.errors.append({
            'timestamp': datetime.now(timezone.utc),
            'error': error,
            'context': context
        })
    
    def log_game_event(self, event_type: str, room_id: str, details: dict = None):
        self.game_events.append({
            'timestamp': datetime.now(timezone.utc),
            'event_type': event_type,
            'room_id': room_id,
            'details': details or {}
        })
    
    def get_summary(self) -> dict:
        return {
            'session_duration': str(datetime.now(timezone.utc) - self.session_start),
            'api_calls_count': len(self.api_calls),
            'errors_count': len(self.errors),
            'game_events_count': len(self.game_events),
            'recent_errors': self.errors[-5:],
            'recent_events': self.game_events[-10:]
        }

# グローバルデバッグインスタンス
debug_info = GameDebugInfo()

# AI NPC エージェント有効化
try:
    from npc_agent.agent import root_agent
    logger.info("AI NPC agent enabled successfully")
except ImportError as e:
    root_agent = None
    logger.warning(f"AI NPC agent could not be imported: {e}")

# --- Configuration ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION")

if not DATABASE_URL:
    logger.warning("DATABASE_URL not set, using SQLite in-memory database")
    DATABASE_URL = "sqlite:///./werewolf_game.db"
if not GOOGLE_PROJECT_ID or not GOOGLE_LOCATION:
    logger.warning("WARNING: GOOGLE_PROJECT_ID or GOOGLE_LOCATION environment variable not set. AI persona generation will not work.")
else:
    vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
    logger.info(f"Vertex AI configured successfully for project {GOOGLE_PROJECT_ID} in {GOOGLE_LOCATION}.")


# --- Database Setup (SQLAlchemy) ---
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Database engine created successfully.")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# --- Database Models (`models.py` に相当) ---
class Room(Base):
    __tablename__ = "rooms"
    room_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_name = Column(String, nullable=True)
    status = Column(String, default='waiting')
    total_players = Column(Integer, default=5)
    human_players = Column(Integer, default=1)
    ai_players = Column(Integer, default=4)
    day_number = Column(Integer, default=1)
    turn_order = Column(JSON, nullable=True)
    current_turn_index = Column(Integer, default=0)
    # 【追加】公開・非公開設定
    is_private = Column(Boolean, default=False, nullable=False)
    # 【修正】created_at を再追加
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")
    game_logs = relationship("GameLog", back_populates="room", cascade="all, delete-orphan")

class Player(Base):
    __tablename__ = "players"
    player_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.room_id"), nullable=False)
    is_human = Column(Boolean, default=True)
    is_alive = Column(Boolean, default=True)
    character_name = Column(String, nullable=False, default="名無しの村人")
    character_persona = Column(JSON, nullable=True)
    role = Column(String, nullable=True)
    room = relationship("Room", back_populates="players")

class GameLog(Base):
    __tablename__ = "game_logs"
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.room_id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    phase = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    actor_player_id = Column(UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    room = relationship("Room", back_populates="game_logs")
    actor = relationship("Player")

class PlayerSession(Base):
    __tablename__ = "player_sessions"
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=False)
    session_token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    player = relationship("Player")

class Spectator(Base):
    __tablename__ = "spectators"
    spectator_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.room_id"), nullable=False)
    spectator_name = Column(String, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    room = relationship("Room")

class SpectatorMessage(Base):
    __tablename__ = "spectator_messages"
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.room_id"), nullable=False)
    spectator_id = Column(UUID(as_uuid=True), ForeignKey("spectators.spectator_id"), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    room = relationship("Room")
    spectator = relationship("Spectator")

# 起動時にテーブルを自動作成
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified at startup")
except Exception as e:
    logger.warning(f"Failed to create database tables at startup: {e}")

# --- Pydantic Schemas (`schemas.py` に相当) ---
class PersonaInput(BaseModel):
    keywords: str = Field(description="キャラクター特徴のキーワード", examples=["冷静沈着, 探偵, 30代"])

class DiscussionRequest(BaseModel):
    current_day: int
    current_phase: str
    speaker_persona: dict
    discussion_history: List[dict]
    living_player_names: List[str]

class DiscussionResponse(BaseModel):
    speaker: str
    text: str

class VoteRequest(BaseModel):
    voter_id: str
    target_id: str

class VoteResult(BaseModel):
    vote_counts: Dict[str, int]
    voted_out_player_id: Optional[str]
    tied_vote: bool
    message: str

class NightActionRequest(BaseModel):
    actor_id: str
    action_type: str  # 'attack', 'investigate', 'protect'
    target_id: Optional[str]

class NightActionResult(BaseModel):
    success: bool
    message: str
    victim_id: Optional[str]
    investigation_result: Optional[str]

class JoinRoomRequest(BaseModel):
    player_name: str
    room_id: str

class JoinRoomResponse(BaseModel):
    player_id: str
    player_name: str
    room_id: str
    session_token: str

class PersonaOutput(BaseModel):
    gender: str
    age: int
    personality: str
    speech_style: str
    background: str

class PlayerBase(BaseModel):
    character_name: str

class PlayerInfo(PlayerBase):
    model_config = ConfigDict(from_attributes=True)
    player_id: uuid.UUID
    is_human: bool
    is_alive: bool
    character_persona: Optional[PersonaOutput] = None
    role: Optional[str] = None

class RoomBase(BaseModel):
    room_name: Optional[str] = None
    total_players: int = Field(5, ge=5, le=12)
    human_players: int = Field(1, ge=1)
    ai_players: int = Field(4, ge=0)
    # 【追加】部屋作成時に公開・非公開を指定
    is_private: bool = False

class RoomCreate(RoomBase):
    pass

class RoomSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    room_id: uuid.UUID
    room_name: Optional[str] = None
    status: str
    total_players: int
    human_players: int
    ai_players: int
    is_private: bool

class RoomInfo(RoomBase):
    model_config = ConfigDict(from_attributes=True)
    room_id: uuid.UUID
    status: str
    day_number: int
    turn_order: Optional[List[str]] = None
    current_turn_index: Optional[int] = None
    players: List[PlayerInfo] = []

class SpeakInput(BaseModel):
    statement: str = Field(..., min_length=1, max_length=500)

class SeerInvestigateInput(BaseModel):
    target_player_id: uuid.UUID

class SeerInvestigateResult(BaseModel):
    investigator: str
    target: str
    result: str  # "人狼" または "村人"
    message: str

class BodyguardProtectInput(BaseModel):
    target_player_id: uuid.UUID

class BodyguardProtectResult(BaseModel):
    protector: str
    target: str
    message: str
    success: bool

class GameResultPlayer(BaseModel):
    player_id: str
    character_name: str
    role: str
    is_alive: bool
    is_human: bool
    is_winner: bool

class GameResult(BaseModel):
    game_over: bool
    winner: Optional[str] = None  # "villagers", "werewolves", or None
    message: str
    players: List[GameResultPlayer]
    game_summary: Dict[str, Any]
    final_day: int
    game_duration: Optional[str] = None

class GameStateSnapshot(BaseModel):
    """ゲーム状態のスナップショット"""
    room_id: str
    timestamp: datetime
    day_number: int
    phase: str
    turn_order: Optional[List[str]] = None
    current_turn_index: Optional[int] = None
    players_data: List[Dict[str, Any]]
    game_logs_count: int
    checksum: str

class ActorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    player_id: uuid.UUID
    character_name: str

class GameLogInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    log_id: uuid.UUID
    event_type: str
    content: Optional[str] = None
    created_at: datetime
    actor: Optional[ActorInfo] = None

class SpectatorBase(BaseModel):
    spectator_name: str

class SpectatorJoinRequest(SpectatorBase):
    pass

class SpectatorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    spectator_id: uuid.UUID
    spectator_name: str
    joined_at: datetime
    is_active: bool

class SpectatorJoinResponse(BaseModel):
    spectator_id: uuid.UUID
    message: str
    room_info: "SpectatorRoomView"

class SpectatorRoomView(BaseModel):
    """観戦者用の制限されたゲーム情報"""
    room_id: uuid.UUID
    room_name: str
    status: str
    day_number: int
    total_players: int
    living_players: int
    players: List["SpectatorPlayerInfo"]
    public_logs: List[GameLogInfo]

class SpectatorPlayerInfo(BaseModel):
    """観戦者には役職情報を隠したプレイヤー情報"""
    model_config = ConfigDict(from_attributes=True)
    player_id: uuid.UUID
    character_name: str
    is_alive: bool
    is_human: bool
    # 役職情報は意図的に除外

class SpectatorChatMessage(BaseModel):
    spectator_name: str
    message: str

class SpectatorChatResponse(BaseModel):
    message_id: uuid.UUID
    spectator_name: str
    message: str
    timestamp: datetime

# --- Dependency Injection (`deps.py` に相当) ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="AI Werewolf Game Logic Service",
    description="AI人狼ゲームのバックエンドAPI",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- グローバル例外ハンドラー ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTPエラーのカスタムハンドリング"""
    logger.error(f"HTTP {exc.status_code} error at {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """リクエスト検証エラーのハンドリング"""
    logger.error(f"Validation error at {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": 422,
            "message": "リクエストの形式が正しくありません",
            "details": exc.errors(),
            "path": str(request.url),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """データベースエラーのハンドリング"""
    logger.error(f"Database error at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": True,
            "status_code": 503,
            "message": "データベース接続エラーが発生しました",
            "path": str(request.url),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般的な例外のハンドリング"""
    logger.error(f"Unexpected error at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": 500,
            "message": "内部サーバーエラーが発生しました",
            "path": str(request.url),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# --- ヘルスチェックエンドポイント ---
@app.get("/health", summary="アプリケーションの稼働状態を確認")
def health_check():
    """サービスの稼働状態を確認"""
    return {
        "status": "healthy",
        "service": "AI Werewolf Game Logic Service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

# --- Game Logic & CRUD Operations ---
def get_role_config(player_count: int) -> List[str]:
    configs: Dict[int, List[str]] = {
        5: ['werewolf', 'seer', 'villager', 'villager', 'villager'],
        6: ['werewolf', 'werewolf', 'seer', 'villager', 'villager', 'villager'],
        7: ['werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager'],
        8: ['werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager'],
        9: ['werewolf', 'werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager'],
        10: ['werewolf', 'werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager', 'villager'],
        11: ['werewolf', 'werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager', 'villager', 'villager'],
        12: ['werewolf', 'werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager', 'villager', 'villager', 'villager']
    }
    return configs.get(player_count, ['villager'] * player_count)

def create_room(db: Session, room: RoomCreate, host_name: str) -> Room:
    if room.total_players != room.human_players + room.ai_players:
        raise HTTPException(status_code=400, detail="Total players must equal human + AI players.")

    db_room = Room(
        room_name=room.room_name,
        total_players=room.total_players,
        human_players=room.human_players,
        ai_players=room.ai_players,
        is_private=room.is_private
    )
    db.add(db_room)
    db.flush()

    # ホストプレイヤーのみを作成（他の人間プレイヤーは後から参加）
    host_player = Player(room_id=db_room.room_id, character_name=host_name, is_human=True)
    db.add(host_player)
    
    # AIプレイヤーを作成
    for i in range(room.ai_players):
        ai_player = Player(
            room_id=db_room.room_id, character_name=f"AIプレイヤー{i+1}", is_human=False
        )
        db.add(ai_player)
        
    db.commit()
    db.refresh(db_room)
    return db_room

def start_game_logic(db: Session, room_id: uuid.UUID) -> Room:
    db_room: Optional[Room] = get_room(db, room_id)
    if not db_room: raise HTTPException(status_code=404, detail="Room not found")
    if db_room.status != 'waiting': raise HTTPException(status_code=400, detail="Game has already started or finished.")
    
    players = db_room.players
    player_count = len(players)
    if player_count != db_room.total_players:
        raise HTTPException(status_code=400, detail=f"Player count mismatch. Expected {db_room.total_players}, but have {player_count}.")
    
    roles = get_role_config(player_count)
    random.shuffle(roles)
    
    player_ids = [p.player_id for p in players]
    random.shuffle(player_ids)
    
    for player, role in zip(players, roles):
        player.role = role
    
    db_room.status = 'day_discussion'
    db_room.day_number = 1
    db_room.turn_order = [str(pid) for pid in player_ids]
    db_room.current_turn_index = 0
    
    create_game_log(db, room_id, "day_discussion", "game_start", content="ゲームが開始されました。")
    
    db.commit()
    db.refresh(db_room)
    logger.info(f"Game started in room {room_id}. Turn order: {db_room.turn_order}")
    
    return db_room

def speak_logic(db: Session, room_id: uuid.UUID, player_id: uuid.UUID, statement: str) -> Room:
    db_room = get_room(db, room_id)
    if not db_room: raise HTTPException(status_code=404, detail="Room not found")
    if db_room.status != 'day_discussion': raise HTTPException(status_code=400, detail="Not in discussion phase.")

    if not db_room.turn_order or db_room.current_turn_index is None:
        raise HTTPException(status_code=500, detail="Game turn order not initialized.")

    turn_order = db_room.turn_order
    current_index = db_room.current_turn_index
    
    if turn_order[current_index] != str(player_id):
        raise HTTPException(status_code=403, detail="It's not your turn.")

    create_game_log(db, room_id, "day_discussion", "speech", actor_player_id=player_id, content=statement)

    next_index = (current_index + 1)
    if next_index >= len(turn_order):
        db_room.status = 'day_vote'
        logger.info(f"All players have spoken in room {room_id}. Moving to vote phase.")
    else:
        db_room.current_turn_index = next_index
        current_player_id = turn_order[db_room.current_turn_index]
        logger.info(f"Turn advanced in room {room_id} to player {current_player_id}.")

    db.commit()
    db.refresh(db_room)
    return db_room

def create_game_log(db: Session, room_id: uuid.UUID, phase: str, event_type: str, actor_player_id: Optional[uuid.UUID] = None, content: Optional[str] = None):
    db_room = get_room(db, room_id)
    if not db_room: return None
    log_entry = GameLog(
        room_id=room_id,
        day_number=db_room.day_number,
        phase=phase,
        event_type=event_type,
        actor_player_id=actor_player_id,
        content=content
    )
    db.add(log_entry)
    return log_entry

def get_player(db: Session, player_id: uuid.UUID) -> Optional[Player]:
    return db.query(Player).filter(Player.player_id == player_id).first()

def update_player_persona(db: Session, player_id: uuid.UUID, persona: dict) -> Optional[Player]:
    db_player = get_player(db, player_id)
    if db_player:
        db_player.character_persona = persona
        db.commit()
        db.refresh(db_player)
    return db_player

# 【修正】公開部屋のみを取得するようにフィルタを追加
def get_rooms(db: Session, skip: int = 0, limit: int = 100) -> List[Room]:
    return db.query(Room).filter(Room.is_private == False).order_by(Room.created_at.desc()).offset(skip).limit(limit).all()

def get_room(db: Session, room_id: uuid.UUID) -> Optional[Room]:
    return db.query(Room).options(joinedload(Room.players)).filter(Room.room_id == room_id).first()

def get_game_logs(db: Session, room_id: uuid.UUID) -> List[GameLog]:
    return db.query(GameLog).filter(GameLog.room_id == room_id).options(joinedload(GameLog.actor)).order_by(GameLog.created_at.asc()).all()

# --- Spectator CRUD Functions ---
def create_spectator(db: Session, room_id: uuid.UUID, spectator_name: str) -> Spectator:
    """観戦者を作成"""
    db_spectator = Spectator(
        room_id=room_id,
        spectator_name=spectator_name
    )
    db.add(db_spectator)
    db.commit()
    db.refresh(db_spectator)
    return db_spectator

def get_spectator(db: Session, spectator_id: uuid.UUID) -> Optional[Spectator]:
    """観戦者を取得"""
    return db.query(Spectator).filter(Spectator.spectator_id == spectator_id).first()

def get_spectators_by_room(db: Session, room_id: uuid.UUID) -> List[Spectator]:
    """部屋の観戦者一覧を取得"""
    return db.query(Spectator).filter(
        Spectator.room_id == room_id,
        Spectator.is_active == True
    ).order_by(Spectator.joined_at.asc()).all()

def deactivate_spectator(db: Session, spectator_id: uuid.UUID) -> bool:
    """観戦者を非アクティブにする"""
    spectator = get_spectator(db, spectator_id)
    if spectator:
        spectator.is_active = False
        db.commit()
        return True
    return False

def create_spectator_message(db: Session, room_id: uuid.UUID, spectator_id: uuid.UUID, message: str) -> SpectatorMessage:
    """観戦者チャットメッセージを作成"""
    db_message = SpectatorMessage(
        room_id=room_id,
        spectator_id=spectator_id,
        message=message
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_spectator_messages(db: Session, room_id: uuid.UUID, limit: int = 50) -> List[SpectatorMessage]:
    """観戦者チャットメッセージを取得"""
    return db.query(SpectatorMessage).filter(
        SpectatorMessage.room_id == room_id
    ).options(
        joinedload(SpectatorMessage.spectator)
    ).order_by(
        SpectatorMessage.timestamp.desc()
    ).limit(limit).all()

def get_spectator_room_view(db: Session, room_id: uuid.UUID) -> Optional[SpectatorRoomView]:
    """観戦者用の制限されたゲーム情報を取得"""
    room = get_room(db, room_id)
    if not room:
        return None
    
    # 公開されているログのみ（役職に関する情報を除外）
    public_logs = db.query(GameLog).filter(
        GameLog.room_id == room_id,
        GameLog.event_type.in_(['speak', 'vote', 'game_start', 'game_end', 'phase_change'])
    ).options(joinedload(GameLog.actor)).order_by(GameLog.created_at.asc()).all()
    
    # プレイヤー情報（役職を隠す）
    spectator_players = [
        SpectatorPlayerInfo(
            player_id=p.player_id,
            character_name=p.character_name,
            is_alive=p.is_alive,
            is_human=p.is_human
        ) for p in room.players
    ]
    
    living_players = len([p for p in room.players if p.is_alive])
    
    return SpectatorRoomView(
        room_id=room.room_id,
        room_name=room.room_name,
        status=room.status,
        day_number=room.day_number or 0,
        total_players=room.total_players,
        living_players=living_players,
        players=spectator_players,
        public_logs=[GameLogInfo.model_validate(log) for log in public_logs]
    )

def process_vote(db: Session, room_id: uuid.UUID, voter_id: uuid.UUID, target_id: uuid.UUID) -> VoteResult:
    """投票を処理し、結果を返す"""
    db_room = get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    if db_room.status != 'day_vote':
        raise HTTPException(status_code=400, detail="Not in voting phase")

    # 投票を記録
    create_game_log(db, room_id, "day_vote", "vote", actor_player_id=voter_id, content=f"voted for {target_id}")
    
    # 現在の投票を集計（ログから）
    vote_logs = db.query(GameLog).filter(
        GameLog.room_id == room_id,
        GameLog.event_type == "vote",
        GameLog.phase == "day_vote"
    ).all()
    
    vote_counts = {}
    voters = set()
    
    for log in vote_logs:
        if log.actor_player_id:
            # 最新の投票のみをカウント（一人一票）
            voters.add(str(log.actor_player_id))
            target = log.content.replace("voted for ", "")
            vote_counts[target] = vote_counts.get(target, 0) + 1
    
    # 生存中の人間プレイヤー数を確認
    living_human_players = [p for p in db_room.players if p.is_alive and p.is_human]
    
    # 全員が投票したかチェック
    if len(voters) >= len(living_human_players):
        # 最多票を獲得したプレイヤーを特定
        if vote_counts:
            max_votes = max(vote_counts.values())
            most_voted = [pid for pid, votes in vote_counts.items() if votes == max_votes]
            
            if len(most_voted) == 1:
                # 単独最多票
                voted_out_id = most_voted[0]
                voted_out_player = db.query(Player).filter(Player.player_id == voted_out_id).first()
                if voted_out_player:
                    voted_out_player.is_alive = False
                
                create_game_log(db, room_id, "day_vote", "execution", content=f"{voted_out_player.character_name} was voted out")
                
                # 夜フェーズに移行
                db_room.status = 'night'
                db.commit()
                
                return VoteResult(
                    vote_counts=vote_counts,
                    voted_out_player_id=voted_out_id,
                    tied_vote=False,
                    message=f"{voted_out_player.character_name}が投票により追放されました。"
                )
            else:
                # 同票
                return VoteResult(
                    vote_counts=vote_counts,
                    voted_out_player_id=None,
                    tied_vote=True,
                    message="同票のため、誰も追放されませんでした。"
                )
        else:
            return VoteResult(
                vote_counts={},
                voted_out_player_id=None,
                tied_vote=False,
                message="投票がありませんでした。"
            )
    
    db.commit()
    return VoteResult(
        vote_counts=vote_counts,
        voted_out_player_id=None,
        tied_vote=False,
        message=f"投票受付中... ({len(voters)}/{len(living_human_players)})"
    )

def process_night_actions(db: Session, room_id: uuid.UUID) -> Dict[str, Any]:
    """夜のアクションを自動処理"""
    db_room = get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if db_room.status != 'night':
        raise HTTPException(status_code=400, detail="Not in night phase")
    
    results = {}
    
    # 人狼の襲撃
    werewolves = [p for p in db_room.players if p.role == 'werewolf' and p.is_alive]
    villagers = [p for p in db_room.players if p.role in ['villager', 'seer', 'bodyguard'] and p.is_alive]
    
    if werewolves and villagers:
        # ランダムに村人を襲撃
        target = random.choice(villagers)
        
        # ボディガードの守りをチェック
        protection_log = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == db_room.day_number,
            GameLog.phase == "night",
            GameLog.event_type == "protect",
            GameLog.content.like(f"%protected {target.character_name}%")
        ).first()
        
        if protection_log:
            # 守られているため、攻撃は無効
            create_game_log(db, room_id, "night", "attack", 
                          content=f"{target.character_name} was attacked by werewolves but was protected")
            results['attack_result'] = f"{target.character_name}が人狼に襲われましたが、ボディガードに守られました"
            results['protected'] = True
            results['target'] = target.character_name
        else:
            # 守られていないため、攻撃成功
            target.is_alive = False
            create_game_log(db, room_id, "night", "attack", content=f"{target.character_name} was attacked and killed by werewolves")
            results['victim'] = target.character_name
            results['victim_id'] = str(target.player_id)
            results['protected'] = False
    
    # 占い師の占い（自動）
    seers = [p for p in db_room.players if p.role == 'seer' and p.is_alive]
    if seers:
        seer = seers[0]
        alive_players = [p for p in db_room.players if p.is_alive and p.player_id != seer.player_id]
        if alive_players:
            investigated = random.choice(alive_players)
            result = "人狼" if investigated.role == 'werewolf' else "村人"
            
            create_game_log(db, room_id, "night", "investigate", 
                          actor_player_id=seer.player_id,
                          content=f"investigated {investigated.character_name}: {result}")
            results['investigation'] = f"{seer.character_name}が{investigated.character_name}を占いました: {result}"
    
    # ゲーム終了条件をチェック
    game_end_result = check_game_end_condition(db, room_id)
    if game_end_result['game_over']:
        db_room.status = 'finished'
        results.update(game_end_result)
    else:
        # 次の日に進む
        db_room.day_number += 1
        db_room.status = 'day_discussion'
        db_room.current_turn_index = 0
        
        # 生存者でターン順序を再構築
        living_players = [p for p in db_room.players if p.is_alive]
        random.shuffle(living_players)
        db_room.turn_order = [str(p.player_id) for p in living_players]
    
    db.commit()
    return results

def check_game_end_condition(db: Session, room_id: uuid.UUID) -> Dict[str, Any]:
    """ゲーム終了条件をチェック"""
    db_room = get_room(db, room_id)
    if not db_room:
        return {'game_over': False}
    
    living_players = [p for p in db_room.players if p.is_alive]
    living_werewolves = [p for p in living_players if p.role == 'werewolf']
    living_villagers = [p for p in living_players if p.role in ['villager', 'seer', 'bodyguard']]
    
    if len(living_werewolves) == 0:
        # 村人陣営の勝利
        create_game_log(db, room_id, db_room.status, "game_end", content="村人陣営の勝利！全ての人狼が排除されました。")
        return {
            'game_over': True,
            'winner': 'villagers',
            'message': '村人陣営の勝利！全ての人狼が排除されました。'
        }
    elif len(living_werewolves) >= len(living_villagers):
        # 人狼陣営の勝利
        create_game_log(db, room_id, db_room.status, "game_end", content="人狼陣営の勝利！人狼の数が村人と同数以上になりました。")
        return {
            'game_over': True,
            'winner': 'werewolves',
            'message': '人狼陣営の勝利！人狼の数が村人と同数以上になりました。'
        }
    
    return {'game_over': False}

def get_detailed_game_result(db: Session, room_id: uuid.UUID) -> GameResult:
    """詳細なゲーム結果を取得"""
    room = get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # 基本のゲーム終了チェック
    basic_result = check_game_end_condition(db, room_id)
    
    # プレイヤー情報を取得
    players = []
    living_werewolves = []
    living_villagers = []
    
    for player in room.players:
        is_winner = False
        if basic_result['game_over']:
            if basic_result['winner'] == 'werewolves' and player.role == 'werewolf':
                is_winner = True
            elif basic_result['winner'] == 'villagers' and player.role in ['villager', 'seer']:
                is_winner = True
        
        players.append(GameResultPlayer(
            player_id=str(player.player_id),
            character_name=player.character_name,
            role=player.role or "unknown",
            is_alive=player.is_alive,
            is_human=player.is_human,
            is_winner=is_winner
        ))
        
        if player.is_alive:
            if player.role == 'werewolf':
                living_werewolves.append(player)
            elif player.role in ['villager', 'seer']:
                living_villagers.append(player)
    
    # ゲーム統計を計算
    total_players = len(room.players)
    total_werewolves = len([p for p in room.players if p.role == 'werewolf'])
    total_villagers = len([p for p in room.players if p.role in ['villager', 'seer']])
    
    game_summary = {
        "total_players": total_players,
        "total_werewolves": total_werewolves,
        "total_villagers": total_villagers,
        "living_werewolves": len(living_werewolves),
        "living_villagers": len(living_villagers),
        "elimination_count": total_players - len([p for p in room.players if p.is_alive]),
    }
    
    # ゲーム時間を計算（簡易版）
    game_duration = None
    if room.created_at:
        duration_seconds = (datetime.now(timezone.utc) - room.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        if hours > 0:
            game_duration = f"{hours}時間{minutes}分"
        else:
            game_duration = f"{minutes}分"
    
    return GameResult(
        game_over=basic_result['game_over'],
        winner=basic_result.get('winner'),
        message=basic_result.get('message', 'ゲーム進行中'),
        players=players,
        game_summary=game_summary,
        final_day=room.day_number,
        game_duration=game_duration
    )

def generate_ai_speech(db: Session, room_id: uuid.UUID, ai_player_id: uuid.UUID) -> str:
    """AIプレイヤーの発言を生成（AIエージェント使用）"""
    try:
        # プレイヤーとルーム情報を取得
        ai_player = get_player(db, ai_player_id)
        if not ai_player or ai_player.is_human:
            raise HTTPException(status_code=400, detail="Not an AI player")
        
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # AIエージェントが利用可能な場合
        if root_agent and GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
            # プレイヤー情報を準備
            player_info = {
                'name': ai_player.character_name,
                'role': ai_player.role,
                'is_alive': ai_player.is_alive,
                'persona': ai_player.character_persona
            }
            
            # ゲーム情報を準備
            game_context = {
                'day_number': room.day_number,
                'phase': room.status,
                'alive_count': len([p for p in room.players if p.is_alive]),
                'total_players': len(room.players)
            }
            
            # 最近のメッセージを取得
            recent_logs = db.query(GameLog).filter(
                GameLog.room_id == room_id,
                GameLog.day_number == room.day_number,
                GameLog.event_type == "speech"
            ).order_by(GameLog.created_at.desc()).limit(5).all()
            
            recent_messages = []
            for log in recent_logs:
                if log.actor:
                    recent_messages.append({
                        'speaker': log.actor.character_name,
                        'content': log.content or '',
                        'timestamp': log.created_at
                    })
            
            # AIエージェントで発言を生成
            speech = root_agent.generate_speech(player_info, game_context, recent_messages)
            
            logger.info(f"AI agent generated speech for {ai_player.character_name}: {speech}")
            return speech
            
        else:
            # フォールバック: シンプルなVertex AI生成
            logger.info("Using fallback AI speech generation")
            return generate_fallback_ai_speech(ai_player, room, db)
            
    except Exception as e:
        logger.error(f"Error generating AI speech: {e}", exc_info=True)
        # エラー時のフォールバック
        return "..."

def generate_fallback_ai_speech(ai_player, room, db) -> str:
    """フォールバック用のAI発言生成"""
    try:
        if GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
            # 最近のゲームログを取得
            recent_logs = db.query(GameLog).filter(
                GameLog.room_id == room.room_id,
                GameLog.day_number == room.day_number
            ).order_by(GameLog.created_at.desc()).limit(10).all()
            
            # プロンプトを構築
            prompt = build_ai_speech_prompt(ai_player, room, recent_logs)
            
            model = GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
            speech = response.text.strip()
            if len(speech) > 200:
                speech = speech[:197] + "..."
            
            return speech
        else:
            # 完全なフォールバック
            fallback_speeches = [
                "今日も一日頑張りましょう！",
                "皆さんの意見を聞かせてください。",
                "何か気になることはありませんか？",
                "慎重に考えて行動しましょう。",
                "みんなで協力して真実を見つけましょう！"
            ]
            return random.choice(fallback_speeches)
    except Exception:
        return "今の状況をよく考えてみましょう。"

def build_ai_speech_prompt(ai_player: Player, room: Room, recent_logs: List[GameLog]) -> str:
    """AI発言生成用のプロンプトを構築"""
    
    # 基本設定
    role_description = {
        'villager': '村人として、人狼を見つけ出すことが目標です。',
        'werewolf': '人狼として、正体がばれないように振る舞い、村人を惑わせることが目標です。',
        'seer': '占い師として、調査結果を元に人狼を見つけることが目標です。'
    }
    
    # ペルソナ情報
    persona_info = ""
    if ai_player.character_persona:
        persona_info = f"キャラクター設定: {ai_player.character_persona}"
    
    # 最近の会話履歴
    conversation_history = ""
    if recent_logs:
        conversation_history = "最近の会話:\n"
        for log in reversed(recent_logs[-5:]):  # 最新5件
            if log.event_type == "speech" and log.actor:
                conversation_history += f"- {log.actor.character_name}: {log.content}\n"
    
    prompt = f"""
あなたは人狼ゲームの参加者「{ai_player.character_name}」です。

# 役職と目標
{role_description.get(ai_player.role, '村人として行動してください。')}

# ゲーム状況
- 現在は{room.day_number}日目の{('昼の議論' if room.status == 'day_discussion' else '投票' if room.status == 'day_vote' else '夜')}フェーズです
- 生存プレイヤー数: {len([p for p in room.players if p.is_alive])}人

{persona_info}

{conversation_history}

# 指示
上記の状況を踏まえて、あなたの役職と性格に合った発言を1つ生成してください。
- 50文字以内で簡潔に
- 自然で人間らしい発言
- 役職の目標に沿った内容
- 必要に応じて他のプレイヤーに質問や提案

発言:
"""
    
    return prompt

def save_game_state(db: Session, room_id: uuid.UUID) -> str:
    """ゲーム状態をデータベースに保存"""
    try:
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # プレイヤーデータを収集
        players_data = []
        for player in room.players:
            players_data.append({
                'player_id': str(player.player_id),
                'character_name': player.character_name,
                'role': player.role,
                'is_alive': player.is_alive,
                'is_human': player.is_human,
                'character_persona': player.character_persona
            })
        
        # ゲームログ数を取得
        logs_count = db.query(GameLog).filter(GameLog.room_id == room_id).count()
        
        # チェックサムを生成（データ整合性確認用）
        import hashlib
        data_string = f"{room.day_number}_{room.status}_{len(players_data)}_{logs_count}"
        checksum = hashlib.md5(data_string.encode()).hexdigest()
        
        # スナップショットデータを作成
        snapshot_data = {
            'room_id': str(room_id),
            'timestamp': datetime.now(timezone.utc),
            'day_number': room.day_number,
            'phase': room.status,
            'turn_order': room.turn_order,
            'current_turn_index': room.current_turn_index,
            'players_data': players_data,
            'game_logs_count': logs_count,
            'checksum': checksum
        }
        
        # JSONとして保存（GameLogとして記録）
        create_game_log(
            db, room_id, room.status, "state_save", 
            content=f"Game state saved with checksum: {checksum}"
        )
        
        db.commit()
        logger.info(f"Game state saved for room {room_id} with checksum {checksum}")
        
        return checksum
        
    except Exception as e:
        logger.error(f"Error saving game state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save game state")

def restore_game_state(db: Session, room_id: uuid.UUID) -> bool:
    """ゲーム状態をデータベースから復旧"""
    try:
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # 最新の状態保存ログを取得
        state_log = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.event_type == "state_save"
        ).order_by(GameLog.created_at.desc()).first()
        
        if not state_log:
            logger.warning(f"No saved state found for room {room_id}")
            return False
        
        # データ整合性を確認
        current_logs_count = db.query(GameLog).filter(GameLog.room_id == room_id).count()
        current_players_count = len(room.players)
        
        # 基本的な復旧処理
        if room.status == 'waiting' and current_players_count > 0:
            logger.info(f"Room {room_id} appears to be in a restorable state")
            
            # ゲームが途中で中断された場合の復旧ロジック
            if room.turn_order and len(room.turn_order) > 0:
                # ターン順序が存在する場合、進行中のゲーム
                if room.current_turn_index is None:
                    room.current_turn_index = 0
                
                # 不正な状態をクリーンアップ
                if room.current_turn_index >= len(room.turn_order):
                    room.current_turn_index = 0
                
                db.commit()
                logger.info(f"Restored game state for room {room_id}")
                return True
        
        return True
        
    except Exception as e:
        logger.error(f"Error restoring game state: {e}", exc_info=True)
        return False

def verify_game_integrity(db: Session, room_id: uuid.UUID) -> Dict[str, Any]:
    """ゲームデータの整合性を検証"""
    try:
        room = get_room(db, room_id)
        if not room:
            return {'valid': False, 'error': 'Room not found'}
        
        issues = []
        warnings = []
        
        # プレイヤー数の検証
        if len(room.players) != room.total_players:
            issues.append(f"Player count mismatch: expected {room.total_players}, found {len(room.players)}")
        
        # 役職配分の検証
        if room.status != 'waiting':
            roles = [p.role for p in room.players if p.role]
            werewolf_count = roles.count('werewolf')
            seer_count = roles.count('seer')
            villager_count = roles.count('villager')
            
            if werewolf_count == 0:
                issues.append("No werewolves found")
            if seer_count == 0:
                warnings.append("No seer found")
            if villager_count == 0:
                warnings.append("No villagers found")
        
        # ターン順序の検証
        if room.turn_order:
            if room.current_turn_index is not None:
                if room.current_turn_index >= len(room.turn_order):
                    issues.append(f"Invalid turn index: {room.current_turn_index} >= {len(room.turn_order)}")
        
        # 生存者数の検証
        alive_count = len([p for p in room.players if p.is_alive])
        if alive_count == 0 and room.status not in ['finished', 'waiting']:
            issues.append("No living players but game not finished")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'room_status': room.status,
            'player_count': len(room.players),
            'alive_count': alive_count
        }
        
    except Exception as e:
        logger.error(f"Error verifying game integrity: {e}", exc_info=True)
        return {'valid': False, 'error': str(e)}

def create_player_session(db: Session, player_id: uuid.UUID) -> str:
    """プレイヤーセッションを作成"""
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24時間有効
    
    session = PlayerSession(
        player_id=player_id,
        session_token=session_token,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    
    return session_token

def verify_player_session(db: Session, session_token: str) -> Optional[Player]:
    """セッショントークンを検証してプレイヤーを取得"""
    session = db.query(PlayerSession).filter(
        PlayerSession.session_token == session_token,
        PlayerSession.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if session:
        return session.player
    return None

def seer_investigate_player(db: Session, room_id: uuid.UUID, investigator_id: uuid.UUID, target_id: uuid.UUID) -> SeerInvestigateResult:
    """占い師が指定したプレイヤーを占う"""
    
    # 占い師の存在確認
    investigator = get_player(db, investigator_id)
    if not investigator:
        raise HTTPException(status_code=404, detail="Investigator not found")
    
    if investigator.role != 'seer':
        raise HTTPException(status_code=403, detail="Only seers can investigate")
    
    if not investigator.is_alive:
        raise HTTPException(status_code=403, detail="Dead players cannot investigate")
    
    # 対象プレイヤーの存在確認
    target = get_player(db, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target player not found")
    
    if not target.is_alive:
        raise HTTPException(status_code=400, detail="Cannot investigate dead players")
    
    if target.player_id == investigator_id:
        raise HTTPException(status_code=400, detail="Cannot investigate yourself")
    
    # 部屋状態の確認
    room = get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status != 'night':
        raise HTTPException(status_code=400, detail="Investigations can only be performed at night")
    
    # 今夜既に占いを行ったかチェック
    existing_investigation = db.query(GameLog).filter(
        GameLog.room_id == room_id,
        GameLog.day_number == room.day_number,
        GameLog.phase == "night",
        GameLog.event_type == "investigate",
        GameLog.actor_player_id == investigator_id
    ).first()
    
    if existing_investigation:
        raise HTTPException(status_code=400, detail="You have already investigated someone tonight")
    
    # 占い結果を決定
    result = "人狼" if target.role == 'werewolf' else "村人"
    
    # ログに記録
    create_game_log(
        db, room_id, "night", "investigate", 
        actor_player_id=investigator_id,
        content=f"investigated {target.character_name}: {result}"
    )
    
    db.commit()
    
    message = f"{investigator.character_name}が{target.character_name}を占いました: {result}"
    
    return SeerInvestigateResult(
        investigator=investigator.character_name,
        target=target.character_name,
        result=result,
        message=message
    )

def bodyguard_protect_player(db: Session, room_id: uuid.UUID, protector_id: uuid.UUID, target_id: uuid.UUID) -> BodyguardProtectResult:
    """ボディガードが指定したプレイヤーを守る"""
    
    # ボディガードの存在確認
    protector = get_player(db, protector_id)
    if not protector:
        raise HTTPException(status_code=404, detail="Protector not found")
    
    if protector.role != 'bodyguard':
        raise HTTPException(status_code=403, detail="Only bodyguards can protect")
    
    if not protector.is_alive:
        raise HTTPException(status_code=403, detail="Dead players cannot protect")
    
    # 対象プレイヤーの存在確認
    target = get_player(db, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target player not found")
    
    if not target.is_alive:
        raise HTTPException(status_code=400, detail="Cannot protect dead players")
    
    if target.player_id == protector_id:
        raise HTTPException(status_code=400, detail="Cannot protect yourself")
    
    # 部屋状態の確認
    room = get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status != 'night':
        raise HTTPException(status_code=400, detail="Protection can only be performed at night")
    
    # 今夜既に守りを行ったかチェック
    existing_protection = db.query(GameLog).filter(
        GameLog.room_id == room_id,
        GameLog.day_number == room.day_number,
        GameLog.phase == "night",
        GameLog.event_type == "protect",
        GameLog.actor_player_id == protector_id
    ).first()
    
    if existing_protection:
        raise HTTPException(status_code=400, detail="You have already protected someone tonight")
    
    # 同じプレイヤーを連続で守ることはできない制限チェック
    if room.day_number > 1:
        previous_protection = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == room.day_number - 1,
            GameLog.phase == "night",
            GameLog.event_type == "protect",
            GameLog.actor_player_id == protector_id,
            GameLog.content.like(f"%protected {target.character_name}%")
        ).first()
        
        if previous_protection:
            raise HTTPException(status_code=400, detail="Cannot protect the same player two nights in a row")
    
    # ログに記録
    create_game_log(
        db, room_id, "night", "protect", 
        actor_player_id=protector_id,
        content=f"protected {target.character_name}"
    )
    
    db.commit()
    
    message = f"{protector.character_name}が{target.character_name}を守りました"
    
    return BodyguardProtectResult(
        protector=protector.character_name,
        target=target.character_name,
        message=message,
        success=True
    )

def join_room_as_player(db: Session, room_id: uuid.UUID, player_name: str) -> JoinRoomResponse:
    """プレイヤーとして部屋に参加"""
    db_room = get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # 既に同じ名前のプレイヤーがいるかチェック（満員チェックより先に実行）
    existing_player = next((p for p in db_room.players if p.character_name == player_name), None)
    if existing_player:
        # 既存プレイヤーとして再接続
        session_token = create_player_session(db, existing_player.player_id)
        return JoinRoomResponse(
            player_id=str(existing_player.player_id),
            player_name=existing_player.character_name,
            room_id=str(room_id),
            session_token=session_token
        )
    
    # 新規プレイヤーの場合のみ部屋に空きがあるかチェック
    current_human_players = len([p for p in db_room.players if p.is_human])
    if current_human_players >= db_room.human_players:
        raise HTTPException(status_code=400, detail="Room is full")
    
    # 新しいプレイヤーを作成
    new_player = Player(
        room_id=room_id,
        character_name=player_name,
        is_human=True
    )
    db.add(new_player)
    db.flush()
    
    session_token = create_player_session(db, new_player.player_id)
    db.commit()
    
    return JoinRoomResponse(
        player_id=str(new_player.player_id),
        player_name=new_player.character_name,
        room_id=str(room_id),
        session_token=session_token
    )

# --- API Endpoints ---
@app.post("/api/rooms", response_model=RoomInfo)
def handle_create_room(room: RoomCreate, host_name: str = "ホスト", db: Session = Depends(get_db)):
    return create_room(db=db, room=room, host_name=host_name)

@app.get("/api/rooms", response_model=List[RoomSummary])
def handle_get_rooms(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    rooms_from_db = get_rooms(db, skip=skip, limit=limit)
    return [RoomSummary.model_validate(room) for room in rooms_from_db]

@app.get("/api/rooms/{room_id}", response_model=RoomInfo)
def handle_get_room(room_id: uuid.UUID, db: Session = Depends(get_db)):
    db_room = get_room(db, room_id=room_id)
    if not db_room: raise HTTPException(status_code=404, detail="Room not found")
    return db_room

@app.post("/api/rooms/{room_id}/start", response_model=RoomInfo)
async def handle_start_game(room_id: uuid.UUID, db: Session = Depends(get_db)):
    updated_room = start_game_logic(db, room_id)
    await sio.emit("game_started", {"room_id": str(room_id), "message": "ゲームが開始されました！"}, room=str(room_id))
    return updated_room
    
@app.post("/api/rooms/{room_id}/speak", response_model=RoomInfo, summary="プレイヤーが発言する")
async def handle_speak(room_id: uuid.UUID, speak_input: SpeakInput, player_id: uuid.UUID, db: Session = Depends(get_db)):
    updated_room = speak_logic(db, room_id, player_id, speak_input.statement)
    
    await sio.emit("new_speech", {
        "room_id": str(room_id),
        "speaker_id": str(player_id),
        "statement": speak_input.statement
    }, room=str(room_id))
    
    return updated_room

@app.get("/api/rooms/{room_id}/logs", response_model=List[GameLogInfo], summary="ゲームログ（会話履歴）を取得する")
def handle_get_game_logs(room_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_game_logs(db, room_id=room_id)

@app.get("/api/players/{player_id}", response_model=PlayerInfo, summary="特定のプレイヤー情報を取得する")
def handle_get_player_info(player_id: uuid.UUID, db: Session = Depends(get_db)):
    player = get_player(db, player_id=player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@app.post("/api/players/{player_id}/generate_persona", response_model=PlayerInfo)
def handle_generate_persona(player_id: uuid.UUID, persona_input: PersonaInput, db: Session = Depends(get_db)):
    if not GOOGLE_PROJECT_ID or not GOOGLE_LOCATION: raise HTTPException(status_code=503, detail="AI Service is not configured")
    db_player = get_player(db, player_id)
    if not db_player: raise HTTPException(status_code=404, detail="Player not found")
    
    prompt = f"""
    あなたは、人狼ゲームの熟練ゲームマスターです。
    以下のキーワードを基に、人狼ゲームに登場するキャラクター設定を考えてください。
    生成するデータは、必ず下記のJSON形式に従ってください。
    # キーワード
    {persona_input.keywords}
    # JSON形式の定義
    {{
      "gender": "性別 (例: 男性, 女性, 不明)",
      "age": "年齢 (整数)",
      "personality": "性格や特徴 (例: 冷静沈着で論理的、疑い深い、感情的な発言が多い)",
      "speech_style": "口調 (例: 丁寧語、タメ口、古風な話し方、無口)",
      "background": "キャラクターの背景設定 (例: 村の医者、旅の詩人、元騎士団長)"
    }}
    """
    try:
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        persona_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        return update_player_persona(db, player_id, persona_data)
    except Exception as e:
        logger.error(f"Error in persona generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI service error.")

@app.post("/api/game/discuss", response_model=DiscussionResponse)
def handle_ai_discussion(request: DiscussionRequest):
    """AI NPCが議論に参加するためのエンドポイント"""
    try:
        persona_info = request.speaker_persona
        
        if root_agent is None:
            # フォールバック: シンプルなAI応答
            if not GOOGLE_PROJECT_ID or not GOOGLE_LOCATION:
                raise HTTPException(status_code=503, detail="AI Service is not configured")
                
            model = GenerativeModel("gemini-1.5-flash")
            
            history_text = "\n".join([f"{h.get('speaker', 'Unknown')}: {h.get('text', '')}" for h in request.discussion_history[-5:]])
            
            prompt = f"""
            あなたは人狼ゲームに参加している{persona_info.get('character_name', 'プレイヤー')}です。
            ペルソナ情報: {json.dumps(persona_info.get('character_persona', {}), ensure_ascii=False)}
            役職: {persona_info.get('role', '不明')}
            
            現在は{request.current_day}日目の{request.current_phase}フェーズです。
            
            これまでの議論:
            {history_text}
            
            生存プレイヤー: {', '.join(request.living_player_names)}
            
            あなたのキャラクターらしい発言を200文字以内で生成してください。
            自然な会話として、疑問を投げかけたり、推理を述べたり、他の人の意見に反応してください。
            """
            
            response = model.generate_content(prompt)
            discussion_text = response.text.strip()
            
        else:
            # 高度なAI NPCエージェントを使用
            agent_input = {
                "persona": persona_info,
                "day": request.current_day,
                "phase": request.current_phase,
                "discussion_history": request.discussion_history,
                "living_players": request.living_player_names
            }
            
            discussion_text = root_agent.run(json.dumps(agent_input, ensure_ascii=False))
        
        return DiscussionResponse(
            speaker=request.speaker_persona.get('character_name', 'AI Player'),
            text=discussion_text
        )
        
    except Exception as e:
        logger.error(f"Error in AI discussion generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI discussion generation failed")

@app.post("/api/rooms/{room_id}/vote", response_model=VoteResult)
async def handle_vote(room_id: uuid.UUID, vote_request: VoteRequest, db: Session = Depends(get_db)):
    """投票を処理する"""
    try:
        result = process_vote(db, room_id, uuid.UUID(vote_request.voter_id), uuid.UUID(vote_request.target_id))
        
        # WebSocketで投票結果を通知
        await sio.emit("vote_cast", {
            "room_id": str(room_id),
            "voter_id": vote_request.voter_id,
            "target_id": vote_request.target_id,
            "vote_counts": result.vote_counts,
            "message": result.message
        }, room=str(room_id))
        
        return result
        
    except Exception as e:
        logger.error(f"Error in vote processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Vote processing failed")

@app.post("/api/rooms/{room_id}/night_action")
async def handle_night_action(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """夜のアクションを処理する"""
    try:
        results = process_night_actions(db, room_id)
        
        # WebSocketで夜のアクション結果を通知
        await sio.emit("night_action_complete", {
            "room_id": str(room_id),
            "results": results
        }, room=str(room_id))
        
        return results
        
    except Exception as e:
        logger.error(f"Error in night action processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Night action processing failed")

@app.post("/api/rooms/{room_id}/transition_to_vote", response_model=RoomInfo)
async def handle_transition_to_vote(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """議論フェーズから投票フェーズに移行"""
    db_room = get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if db_room.status != 'day_discussion':
        raise HTTPException(status_code=400, detail="Not in discussion phase")
    
    db_room.status = 'day_vote'
    db.commit()
    
    # WebSocketで状態変更を通知
    await sio.emit("phase_transition", {
        "room_id": str(room_id),
        "new_phase": "day_vote",
        "message": "投票フェーズに移行しました"
    }, room=str(room_id))
    
    return db_room

@app.post("/api/rooms/{room_id}/join", response_model=JoinRoomResponse)
async def handle_join_room(room_id: uuid.UUID, player_name: str, db: Session = Depends(get_db)):
    """プレイヤーが部屋に参加"""
    try:
        result = join_room_as_player(db, room_id, player_name)
        
        # WebSocketで新しいプレイヤーの参加を通知
        await sio.emit("player_joined_game", {
            "room_id": str(room_id),
            "player_id": result.player_id,
            "player_name": result.player_name
        }, room=str(room_id))
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in join room: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to join room: {str(e)}")

@app.get("/api/auth/verify")
def handle_verify_session(session_token: str, db: Session = Depends(get_db)):
    """セッショントークンを検証"""
    player = verify_player_session(db, session_token)
    if not player:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return {
        "player_id": str(player.player_id),
        "player_name": player.character_name,
        "room_id": str(player.room_id)
    }

@app.post("/api/rooms/{room_id}/seer_investigate", response_model=SeerInvestigateResult)
async def handle_seer_investigate(
    room_id: uuid.UUID, 
    investigator_id: uuid.UUID,
    investigate_data: SeerInvestigateInput, 
    db: Session = Depends(get_db)
):
    """占い師が指定したプレイヤーを占う"""
    try:
        result = seer_investigate_player(db, room_id, investigator_id, investigate_data.target_player_id)
        
        # WebSocketで占い結果を通知（占い師のみに送信）
        await sio.emit("seer_investigation_result", {
            "room_id": str(room_id),
            "investigator_id": str(investigator_id),
            "result": result.model_dump()
        }, room=str(investigator_id))  # 占い師だけに結果を送信
        
        return result
        
    except Exception as e:
        logger.error(f"Error in seer investigation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to perform investigation")

@app.post("/api/rooms/{room_id}/bodyguard_protect", response_model=BodyguardProtectResult)
async def handle_bodyguard_protect(
    room_id: uuid.UUID,
    protector_id: uuid.UUID,
    protect_data: BodyguardProtectInput,
    db: Session = Depends(get_db)
):
    """ボディガードが指定したプレイヤーを守る"""
    try:
        result = bodyguard_protect_player(db, room_id, protector_id, protect_data.target_player_id)
        
        # WebSocketで守り結果を通知（ボディガードのみに送信）
        await sio.emit("bodyguard_protection_result", {
            "room_id": str(room_id),
            "protector_id": str(protector_id),
            "result": result.model_dump()
        }, room=str(protector_id))  # ボディガードだけに結果を送信
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bodyguard protection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to perform protection")

@app.get("/api/players/{player_id}/available_targets")
def get_available_investigate_targets(player_id: uuid.UUID, db: Session = Depends(get_db)):
    """占い師が占うことができる対象プレイヤーのリストを取得"""
    try:
        player = get_player(db, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        if player.role != 'seer':
            raise HTTPException(status_code=403, detail="Only seers can investigate")
        
        room = get_room(db, player.room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        if room.status != 'night':
            raise HTTPException(status_code=400, detail="Investigations can only be performed at night")
        
        # 占い可能な対象（自分以外の生存者）
        available_targets = [
            {
                "player_id": str(p.player_id),
                "character_name": p.character_name,
                "is_human": p.is_human
            }
            for p in room.players 
            if p.is_alive and p.player_id != player_id
        ]
        
        return {
            "available_targets": available_targets,
            "can_investigate": len(available_targets) > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting investigate targets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get available targets")

@app.get("/api/rooms/{room_id}/game_result", response_model=GameResult)
def get_game_result(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """ゲーム終了時の詳細な結果を取得"""
    try:
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # ゲーム終了条件をチェック
        result = get_detailed_game_result(db, room_id)
        return result
        
    except Exception as e:
        logger.error(f"Error getting game result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get game result")

@app.post("/api/rooms/{room_id}/ai_speak/{ai_player_id}")
async def handle_ai_speak(room_id: uuid.UUID, ai_player_id: uuid.UUID, db: Session = Depends(get_db)):
    """AIプレイヤーに発言を生成させる"""
    try:
        # AI発言を生成
        speech = generate_ai_speech(db, room_id, ai_player_id)
        
        # 発言を実行
        updated_room = speak_logic(db, room_id, ai_player_id, speech)
        
        # WebSocketで発言を通知
        await sio.emit("new_speech", {
            "room_id": str(room_id),
            "speaker_id": str(ai_player_id),
            "statement": speech,
            "is_ai": True
        }, room=str(room_id))
        
        return {
            "speech": speech,
            "room_status": updated_room.status,
            "current_turn_index": updated_room.current_turn_index
        }
        
    except Exception as e:
        logger.error(f"Error in AI speak: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate AI speech")

@app.post("/api/rooms/{room_id}/auto_progress")
async def handle_auto_progress(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """ゲームの自動進行（AIプレイヤーのターン処理）"""
    try:
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        if room.status != 'day_discussion':
            return {"message": "Auto progress only available during discussion phase"}
        
        # 現在のターンプレイヤーを確認
        if not room.turn_order or room.current_turn_index is None:
            return {"message": "Turn order not initialized"}
        
        current_player_id = room.turn_order[room.current_turn_index]
        current_player = get_player(db, uuid.UUID(current_player_id))
        
        if not current_player:
            return {"message": "Current player not found"}
        
        # AIプレイヤーの場合、自動発言
        if not current_player.is_human:
            speech = generate_ai_speech(db, room_id, current_player.player_id)
            updated_room = speak_logic(db, room_id, current_player.player_id, speech)
            
            # WebSocketで発言を通知
            await sio.emit("new_speech", {
                "room_id": str(room_id),
                "speaker_id": str(current_player.player_id),
                "statement": speech,
                "is_ai": True
            }, room=str(room_id))
            
            return {
                "auto_progressed": True,
                "speaker": current_player.character_name,
                "speech": speech,
                "room_status": updated_room.status,
                "current_turn_index": updated_room.current_turn_index
            }
        else:
            return {
                "auto_progressed": False,
                "message": "Current player is human, waiting for manual input"
            }
            
    except Exception as e:
        logger.error(f"Error in auto progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to auto progress game")

# --- Spectator API Endpoints ---
@app.post("/api/rooms/{room_id}/spectators/join", response_model=SpectatorJoinResponse)
async def join_as_spectator(
    room_id: uuid.UUID,
    spectator_data: SpectatorJoinRequest,
    db: Session = Depends(get_db)
):
    """観戦者として部屋に参加"""
    try:
        # 部屋の存在確認
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # 観戦者作成
        spectator = create_spectator(db, room_id, spectator_data.spectator_name)
        
        # 観戦者用のゲーム情報取得
        room_view = get_spectator_room_view(db, room_id)
        if not room_view:
            raise HTTPException(status_code=500, detail="Failed to get room view")
        
        # WebSocketで観戦者参加を通知
        await sio.emit("spectator_joined", {
            "room_id": str(room_id),
            "spectator_name": spectator.spectator_name,
            "spectator_count": len(get_spectators_by_room(db, room_id))
        }, room=str(room_id))
        
        return SpectatorJoinResponse(
            spectator_id=spectator.spectator_id,
            message=f"{spectator.spectator_name}が観戦を開始しました",
            room_info=room_view
        )
        
    except Exception as e:
        logger.error(f"Error joining as spectator: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to join as spectator")

@app.get("/api/rooms/{room_id}/spectators/view", response_model=SpectatorRoomView)
async def get_spectator_view(
    room_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """観戦者用のゲーム情報を取得"""
    try:
        room_view = get_spectator_room_view(db, room_id)
        if not room_view:
            raise HTTPException(status_code=404, detail="Room not found")
        
        return room_view
        
    except Exception as e:
        logger.error(f"Error getting spectator view: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get spectator view")

@app.get("/api/rooms/{room_id}/spectators", response_model=List[SpectatorInfo])
async def get_room_spectators(
    room_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """部屋の観戦者一覧を取得"""
    try:
        # 部屋の存在確認
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        spectators = get_spectators_by_room(db, room_id)
        return [SpectatorInfo.model_validate(spec) for spec in spectators]
        
    except Exception as e:
        logger.error(f"Error getting spectators: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get spectators")

@app.post("/api/rooms/{room_id}/spectators/{spectator_id}/chat", response_model=SpectatorChatResponse)
async def send_spectator_chat(
    room_id: uuid.UUID,
    spectator_id: uuid.UUID,
    chat_data: SpectatorChatMessage,
    db: Session = Depends(get_db)
):
    """観戦者チャットメッセージを送信"""
    try:
        # 観戦者の存在確認
        spectator = get_spectator(db, spectator_id)
        if not spectator or not spectator.is_active:
            raise HTTPException(status_code=404, detail="Active spectator not found")
        
        if spectator.room_id != room_id:
            raise HTTPException(status_code=403, detail="Spectator not in this room")
        
        # メッセージ作成
        message = create_spectator_message(db, room_id, spectator_id, chat_data.message)
        
        # WebSocketで観戦者チャットを配信（観戦者のみに送信）
        spectators = get_spectators_by_room(db, room_id)
        chat_response = SpectatorChatResponse(
            message_id=message.message_id,
            spectator_name=spectator.spectator_name,
            message=message.message,
            timestamp=message.timestamp
        )
        
        for spec in spectators:
            await sio.emit("spectator_chat", chat_response.model_dump(), room=str(spec.spectator_id))
        
        return chat_response
        
    except Exception as e:
        logger.error(f"Error sending spectator chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send chat message")

@app.get("/api/rooms/{room_id}/spectators/chat", response_model=List[SpectatorChatResponse])
async def get_spectator_chat_history(
    room_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """観戦者チャット履歴を取得"""
    try:
        # 部屋の存在確認
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        messages = get_spectator_messages(db, room_id, limit)
        
        return [
            SpectatorChatResponse(
                message_id=msg.message_id,
                spectator_name=msg.spectator.spectator_name,
                message=msg.message,
                timestamp=msg.timestamp
            ) for msg in reversed(messages)  # 新しいメッセージが下に来るように
        ]
        
    except Exception as e:
        logger.error(f"Error getting spectator chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@app.delete("/api/spectators/{spectator_id}")
async def leave_spectator_mode(
    spectator_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """観戦モードを退出"""
    try:
        spectator = get_spectator(db, spectator_id)
        if not spectator:
            raise HTTPException(status_code=404, detail="Spectator not found")
        
        room_id = spectator.room_id
        spectator_name = spectator.spectator_name
        
        # 観戦者を非アクティブにする
        if deactivate_spectator(db, spectator_id):
            # WebSocketで観戦者退出を通知
            await sio.emit("spectator_left", {
                "room_id": str(room_id),
                "spectator_name": spectator_name,
                "spectator_count": len(get_spectators_by_room(db, room_id))
            }, room=str(room_id))
            
            return {"message": f"{spectator_name}が観戦を終了しました"}
        else:
            raise HTTPException(status_code=500, detail="Failed to leave spectator mode")
        
    except Exception as e:
        logger.error(f"Error leaving spectator mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to leave spectator mode")

@app.get("/api/ai_agent/status")
def get_ai_agent_status():
    """AIエージェントの状態を確認"""
    return {
        "ai_agent_enabled": root_agent is not None,
        "vertex_ai_configured": bool(GOOGLE_PROJECT_ID and GOOGLE_LOCATION),
        "agent_type": "Vertex AI Multi-Agent System" if root_agent else "Simple Vertex AI",
        "available_agents": ["question_agent", "accuse_agent", "support_agent", "root_agent"] if root_agent else ["simple_ai"]
    }

@app.post("/api/ai_agent/test_speech")
def test_ai_agent_speech(test_data: Dict[str, Any]):
    """AIエージェントの発言生成をテスト"""
    try:
        if not root_agent:
            return {"error": "AI agent not available", "fallback_used": True}
        
        # テストデータから情報を抽出
        player_info = test_data.get('player_info', {
            'name': 'テストプレイヤー',
            'role': 'villager',
            'is_alive': True,
            'persona': None
        })
        
        game_context = test_data.get('game_context', {
            'day_number': 1,
            'phase': 'day_discussion',
            'alive_count': 5,
            'total_players': 5
        })
        
        recent_messages = test_data.get('recent_messages', [])
        
        # AIエージェントでテスト発言を生成
        speech = root_agent.generate_speech(player_info, game_context, recent_messages)
        
        return {
            "success": True,
            "generated_speech": speech,
            "agent_used": "Vertex AI Multi-Agent System",
            "test_data_received": test_data
        }
        
    except Exception as e:
        logger.error(f"Error testing AI agent: {e}", exc_info=True)
        return {
            "error": str(e),
            "success": False
        }

@app.post("/api/rooms/{room_id}/save_state")
def handle_save_game_state(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """ゲーム状態を保存"""
    try:
        checksum = save_game_state(db, room_id)
        return {
            "success": True,
            "checksum": checksum,
            "message": "Game state saved successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error saving game state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save game state")

@app.post("/api/rooms/{room_id}/restore_state")
def handle_restore_game_state(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """ゲーム状態を復旧"""
    try:
        success = restore_game_state(db, room_id)
        return {
            "success": success,
            "message": "Game state restored successfully" if success else "No saved state to restore",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error restoring game state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to restore game state")

@app.get("/api/rooms/{room_id}/integrity_check")
def handle_verify_game_integrity(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """ゲームデータの整合性を検証"""
    try:
        integrity_result = verify_game_integrity(db, room_id)
        return integrity_result
    except Exception as e:
        logger.error(f"Error checking game integrity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check game integrity")

@app.get("/api/debug/info")
def get_debug_info():
    """デバッグ情報を取得"""
    return debug_info.get_summary()

@app.get("/api/debug/logs")
def get_debug_logs(limit: int = 50):
    """詳細なデバッグログを取得"""
    return {
        "api_calls": debug_info.api_calls[-limit:],
        "errors": debug_info.errors[-limit:],
        "game_events": debug_info.game_events[-limit:],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/debug/room/{room_id}")
def get_room_debug_info(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """特定の部屋のデバッグ情報を取得"""
    try:
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # ゲームログを取得
        logs = get_game_logs(db, room_id)
        
        # プレイヤー詳細情報
        players_debug = []
        for player in room.players:
            players_debug.append({
                'player_id': str(player.player_id),
                'character_name': player.character_name,
                'role': player.role,
                'is_alive': player.is_alive,
                'is_human': player.is_human,
                'has_persona': bool(player.character_persona)
            })
        
        # WebSocket接続情報（シミュレート）
        websocket_info = {
            'estimated_connections': len([p for p in room.players if p.is_human]),
            'room_id': str(room_id)
        }
        
        return {
            'room_info': {
                'room_id': str(room.room_id),
                'status': room.status,
                'day_number': room.day_number,
                'current_turn_index': room.current_turn_index,
                'turn_order': room.turn_order,
                'player_count': len(room.players),
                'created_at': room.created_at.isoformat() if room.created_at else None
            },
            'players': players_debug,
            'logs_count': len(logs),
            'recent_logs': [
                {
                    'event_type': log.event_type,
                    'content': log.content,
                    'actor': log.actor.character_name if log.actor else None,
                    'created_at': log.created_at.isoformat()
                } for log in logs[-10:]
            ],
            'websocket_info': websocket_info,
            'integrity_check': verify_game_integrity(db, room_id)
        }
        
    except Exception as e:
        logger.error(f"Error getting room debug info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get room debug info")

@app.post("/api/debug/clear")
def clear_debug_logs():
    """デバッグログをクリア"""
    global debug_info
    debug_info = GameDebugInfo()
    return {"message": "Debug logs cleared", "timestamp": datetime.now(timezone.utc).isoformat()}

# デバッグ用のミドルウェア
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    """APIコールをログに記録"""
    start_time = datetime.now(timezone.utc)
    
    # リクエスト情報をデバッグログに記録
    debug_info.log_api_call(
        endpoint=str(request.url.path),
        method=request.method,
        params=dict(request.query_params)
    )
    
    try:
        response = await call_next(request)
        
        # レスポンス時間を計算
        process_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # レスポンス情報をログ
        logger.debug(f"{request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
        
        return response
        
    except Exception as e:
        # エラーをデバッグログに記録
        debug_info.log_error(str(e), f"{request.method} {request.url.path}")
        raise

# --- WebSocket Setup ---
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app_sio = socketio.ASGIApp(sio, app)
@sio.event
async def connect(sid, environ): 
    logger.info(f"Socket.IO client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO client disconnected: {sid}")

@sio.on("ping")
async def handle_ping(sid):
    """ハートビートpingに対するpong応答"""
    try:
        await sio.emit("pong", room=sid)
        logger.debug(f"Heartbeat ping received from {sid}, pong sent")
    except Exception as e:
        logger.error(f"Error handling ping from {sid}: {e}")

@sio.on("join_room")
async def handle_join(sid, data):
    try:
        if not data:
            return
        room_id = data.get("room_id")
        if not room_id: 
            return
        await sio.enter_room(sid, room_id)
        logger.info(f"Client {sid} joined room {room_id}")
        await sio.emit("player_joined", {"player_name": "新しい参加者", "sid": sid}, room=str(room_id))
    except Exception as e:
        logger.error(f"Error handling join_room from {sid}: {e}")

@sio.on("chat_message")
async def handle_chat(sid, data):
    try:
        if not data:
            return
        room_id = data.get("room_id")
        message = data.get("message")
        if not room_id or not message: 
            return
        logger.info(f"Message from {sid} in room {room_id}: {message}")
        await sio.emit("new_message", {"sender_sid": sid, "message": message}, room=str(room_id))
    except Exception as e:
        logger.error(f"Error handling chat_message from {sid}: {e}")

# Duplicate disconnect function removed

# --- データベース管理エンドポイント ---
@app.get("/api/db/init", summary="【開発用】データベースのテーブルを初期化する")
def init_database():
    """データベースのテーブルを初期化（全データ削除）"""
    try:
        logger.info("Starting database initialization...")
        
        # 既存のテーブルを削除
        Base.metadata.drop_all(bind=engine)
        logger.info("Existing tables dropped successfully")
        
        # 新しいテーブルを作成
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        return {
            "message": "Database tables recreated successfully.",
            "tables_created": [table.name for table in Base.metadata.sorted_tables],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except OperationalError as e:
        logger.error(f"Database operational error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")
    except Exception as e:
        logger.error(f"DB initialization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {e}")

@app.get("/api/db/status", summary="データベース接続状態を確認")
def check_database_status():
    """データベースの接続状態とテーブル情報を確認"""
    try:
        # データベース接続テスト
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            row = result.fetchone()
            connection_ok = row is not None and row[0] == 1
        
        # テーブル存在確認
        existing_tables = []
        for table in Base.metadata.sorted_tables:
            try:
                with engine.connect() as connection:
                    connection.execute(text(f"SELECT 1 FROM {table.name} LIMIT 1"))
                existing_tables.append(table.name)
            except Exception:
                pass
        
        # データベースURL表示（機密情報を隠す）
        display_url = DATABASE_URL or "Not configured"
        if '@' in display_url:
            display_url = display_url.split('@')[1]
        
        return {
            "database_connected": connection_ok,
            "database_url": display_url,
            "existing_tables": existing_tables,
            "expected_tables": [table.name for table in Base.metadata.sorted_tables],
            "all_tables_exist": len(existing_tables) == len(Base.metadata.sorted_tables),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Database status check failed: {e}", exc_info=True)
        return {
            "database_connected": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/api/db/migrate", summary="【開発用】データベースマイグレーションを実行")
def migrate_database():
    """データベースのマイグレーション（データ保持しながらスキーマ更新）"""
    try:
        logger.info("Starting database migration...")
        
        # 既存テーブルを確認
        with engine.connect() as connection:
            # SQLAlchemyのテーブル作成（IF NOT EXISTSは自動で処理される）
            Base.metadata.create_all(bind=engine)
        
        logger.info("Database migration completed successfully")
        
        return {
            "message": "Database migration completed successfully.",
            "tables": [table.name for table in Base.metadata.sorted_tables],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Database migration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database migration failed: {e}")

# 後方互換性のため既存のエンドポイントも保持
@app.get("/initdb", summary="【廃止予定】データベースのテーブルを初期化する")
def init_db_legacy():
    """レガシーエンドポイント - /api/db/init を使用してください"""
    logger.warning("Legacy /initdb endpoint used. Please use /api/db/init instead.")
    return init_database()
