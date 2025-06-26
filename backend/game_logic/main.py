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
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Set

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
                        ForeignKey, Integer, String, Text, text, JSON, func)
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
    import sys
    import os
    # 親ディレクトリをパスに追加（より確実なパス設定）
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    # 現在のディレクトリも追加
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from npc_agent.agent import root_agent
    logger.info("AI NPC agent enabled successfully")
    logger.info(f"Agent import path: {backend_dir}")
except ImportError as e:
    root_agent = None
    logger.error(f"AI NPC agent could not be imported: {e}")
    logger.error(f"Current working directory: {os.getcwd()}")
    logger.error(f"Script location: {os.path.abspath(__file__)}")
    logger.error(f"Backend directory: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
    logger.error(f"Current sys.path: {sys.path}")

# --- Configuration ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION")

if not DATABASE_URL:
    logger.warning("DATABASE_URL not set, using SQLite database")
    DATABASE_URL = "sqlite:///./werewolf_game.db"
else:
    # Test PostgreSQL connection and fallback to SQLite if it fails
    try:
        import psycopg2
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:],  # Remove leading slash
            connect_timeout=5 # 接続タイムアウトを短縮
        )
        conn.close()
        logger.info("PostgreSQL connection test successful")
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}. Falling back to SQLite.", exc_info=True)
        DATABASE_URL = "sqlite:///./werewolf_game.db"
if not GOOGLE_PROJECT_ID or not GOOGLE_LOCATION:
    logger.warning("WARNING: GOOGLE_PROJECT_ID or GOOGLE_LOCATION environment variable not set. AI persona generation will not work.")
else:
    vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
    logger.info(f"Vertex AI configured successfully for project {GOOGLE_PROJECT_ID} in {GOOGLE_LOCATION}.")


# --- Database Setup (SQLAlchemy) ---
try:
    # Use SQLite with timeout to avoid hangs
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"timeout": 20})
        logger.info("Using SQLite engine.")
    else:
        # PostgreSQL CloudSQL用の最適化された接続設定
        engine = create_engine(
            DATABASE_URL, 
            pool_timeout=15,           # 接続取得タイムアウト
            pool_recycle=1800,         # 30分でリサイクル
            pool_pre_ping=True,        # 接続前にテストpingを送信
            pool_size=20,              # 基本接続プールサイズ
            max_overflow=30,           # 最大追加接続数
            echo_pool=False,           # プール状況ログ
            connect_args={
                "connect_timeout": 15,      # 接続タイムアウト
                "application_name": "werewolf_game",
                "keepalives_idle": 300,     # TCP keepalive 5分
                "keepalives_interval": 10,  # keepalive間隔 10秒
                "keepalives_count": 3       # keepalive試行回数
            }
        )
        logger.info("Using PostgreSQL engine.")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Database engine created successfully.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to create database engine: {e}. Application cannot start without a working database.", exc_info=True)
    raise # データベース接続が必須のため、起動を停止

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
    current_round = Column(Integer, default=1)
    # 【追加】公開・非公開設定
    is_private = Column(Boolean, default=False, nullable=False)
    # 【修正】created_at を再追加
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # 【追加】最終活動時間（自動クローズ用）
    last_activity = Column(DateTime(timezone=True), nullable=True, default=lambda: datetime.now(timezone.utc))
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
    is_claimed = Column(Boolean, default=False) # 新しいフィールド
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

class GameSummary(Base):
    __tablename__ = "game_summaries"
    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.room_id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    phase = Column(String, nullable=False)  # day_discussion, day_vote, night
    summary_content = Column(Text, nullable=False)  # LLM生成のサマリー
    important_events = Column(JSON, nullable=True)  # 重要イベントのリスト
    player_suspicions = Column(JSON, nullable=True)  # プレイヤー疑惑度情報
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    room = relationship("Room")

class DistributedLock(Base):
    __tablename__ = "distributed_locks"
    lock_id = Column(String, primary_key=True)  # ロック名（例: "auto_progress:room_uuid"）
    owner_id = Column(String, nullable=False)  # ロック所有者ID（プロセス識別子）
    owner_info = Column(JSON, nullable=True)  # 所有者情報（IP、プロセスID等）
    acquired_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)  # ロック有効期限
    lock_value = Column(String, nullable=False)  # ロック値（一意な識別子）
    metadata_info = Column(JSON, nullable=True)  # 追加メタデータ（room_id等）
    
    def is_expired(self) -> bool:
        """ロックが期限切れかどうかを確認"""
        current_time = datetime.now(timezone.utc)
        # expires_atがnaiveな場合はUTCタイムゾーンを付与
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return current_time >= expires_at
    
    def is_owned_by(self, owner_id: str, lock_value: str) -> bool:
        """指定された所有者とロック値でロックが所有されているかを確認"""
        return self.owner_id == owner_id and self.lock_value == lock_value

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
    ai_players: int # デフォルト値を削除
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

# --- Background Task for Auto Game Progression ---
game_loop_task = None
pool_monitor_task = None

async def connection_pool_monitor():
    """データベース接続プール使用率の継続監視"""
    logger.info("Starting database connection pool monitor...")
    
    while True:
        try:
            pool = engine.pool
            usage_rate = (pool.checkedout() + pool.overflow()) / (pool.size() + getattr(pool, '_max_overflow', 35))
            
            # 80%超過でワーニング、90%超過でクリティカル
            if usage_rate > 0.9:
                logger.critical(f"🚨 CRITICAL: Database pool usage at {usage_rate:.1%} "
                               f"(checked_out: {pool.checkedout()}, overflow: {pool.overflow()})")
            elif usage_rate > 0.8:
                logger.warning(f"⚠️ WARNING: Database pool usage at {usage_rate:.1%} "
                              f"(checked_out: {pool.checkedout()}, overflow: {pool.overflow()})")
            elif usage_rate > 0.7:
                logger.info(f"📊 INFO: Database pool usage at {usage_rate:.1%}")
            
        except Exception as e:
            logger.error(f"Pool monitoring error: {e}")
        
        # 30秒間隔で監視
        await asyncio.sleep(30)

async def game_loop_monitor():
    """Continuous monitoring and auto-progression for AI player turns"""
    logger.info("Starting AI game auto-progression monitor...")
    
    while True:
        db = None
        try:
            # Get database session with timeout protection
            try:
                db = SessionLocal()
                # Set session timeout to prevent long-running queries
                db.execute(text("SET statement_timeout = '30s'"))
                
                # Check all active game rooms
                active_rooms = db.query(Room).filter(
                    Room.status.in_(['day_discussion', 'day_vote']),
                    Room.last_activity >= datetime.now(timezone.utc) - timedelta(hours=2)
                ).all()
                
                # Process rooms sequentially to avoid connection starvation
                for room in active_rooms:
                    try:
                        await check_and_progress_ai_turns(room.room_id, db)
                    except Exception as room_error:
                        logger.error(f"Error processing room {room.room_id}: {room_error}")
                        # Continue with other rooms
                        continue
                        
            except Exception as db_error:
                logger.error(f"Database error in game loop monitor: {db_error}")
                # If DB connection fails, wait longer before retry
                await asyncio.sleep(10)
                continue
                
        except Exception as e:
            logger.error(f"Game loop monitor error: {e}")
        finally:
            # Ensure database session is always closed
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Error closing database session: {close_error}")
        
        # Wait 2 seconds before next check (faster for vote processing)
        await asyncio.sleep(1)  # 2秒から1秒に短縮

async def delayed_ai_progression(room_id: uuid.UUID, delay_seconds: float):
    """Schedule AI progression after a delay"""
    await asyncio.sleep(delay_seconds)
    try:
        db = SessionLocal()
        try:
            await check_and_progress_ai_turns(room_id, db)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in delayed AI progression for room {room_id}: {e}")

async def handle_voting_phase_auto_progress(room_id: uuid.UUID, room, db: Session):
    """投票フェーズでのAI自動投票処理"""
    try:
        logger.info(f"Checking voting phase auto-progress for room {room_id}")
        
        # 投票フェーズの開始時刻をチェック（タイムアウト処理用）
        vote_phase_logs = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == room.day_number,
            GameLog.event_type == "phase_transition",
            GameLog.content.contains("投票フェーズ")
        ).order_by(GameLog.created_at.desc()).first()
        
        # 投票フェーズ開始から10分経過した場合、強制進行
        vote_timeout_minutes = 10
        if vote_phase_logs:
            time_since_vote_start = (datetime.now(timezone.utc) - vote_phase_logs.created_at).total_seconds() / 60
            if time_since_vote_start > vote_timeout_minutes:
                logger.warning(f"Vote timeout reached for room {room_id}, forcing progression")
                await force_vote_progression(room_id, room, db)
                return
        
        # 最近の投票活動をチェック（3秒以内の活動は待機）
        if room.last_activity and (datetime.now(timezone.utc) - room.last_activity).total_seconds() < 3:
            return
        
        # 未投票のAIプレイヤーをチェック
        players = get_players_in_room(db, room_id)
        alive_players = [p for p in players if p.is_alive]
        
        # 投票済みプレイヤーを取得
        vote_logs = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == room.day_number,
            GameLog.event_type == "vote"
        ).all()
        
        voted_player_ids = set()
        for vote_log in vote_logs:
            if vote_log.actor_player_id:
                voted_player_ids.add(vote_log.actor_player_id)
        
        # 未投票のAIプレイヤーを特定
        unvoted_ai_players = [
            p for p in alive_players 
            if not p.is_human and p.player_id not in voted_player_ids
        ]
        
        if not unvoted_ai_players:
            logger.info(f"All AI players have voted in room {room_id}")
            return
        
        # 1人ずつAI投票を実行（同時実行を避ける）
        ai_player = unvoted_ai_players[0]
        logger.info(f"Auto-voting for AI player: {ai_player.character_name} in room {room_id}")
        
        # AI投票処理を実行
        result = auto_progress_logic(room_id, db)
        if result.get("auto_progressed"):
            logger.info(f"AI vote successful: {result.get('message', 'No message')}")
            
            # WebSocket通知の送信
            if "websocket_data" in result:
                try:
                    ws_data = result["websocket_data"]
                    if ws_data["type"] == "new_vote":
                        await sio.emit("new_vote", ws_data["data"], room=str(room_id))
                        logger.info(f"WebSocket vote notification sent for {ai_player.character_name}")
                except Exception as ws_error:
                    logger.error(f"WebSocket vote notification failed: {ws_error}")
            
            # 投票状況更新を送信
            await send_vote_status_update(room_id, db)
        else:
            logger.warning(f"AI vote failed for {ai_player.character_name}: {result.get('message', 'Unknown error')}")
            
            # 失敗の場合もステータス更新を送信（デバッグ用）
            await send_vote_status_update(room_id, db)
            
    except Exception as e:
        logger.error(f"Error in voting phase auto-progress for room {room_id}: {e}", exc_info=True)

async def force_vote_progression(room_id: uuid.UUID, room, db: Session):
    """投票タイムアウト時の強制進行処理"""
    try:
        logger.warning(f"Forcing vote progression for room {room_id} due to timeout")
        
        # 未投票のAIプレイヤーに対してランダム投票を実行
        players = get_players_in_room(db, room_id)
        alive_players = [p for p in players if p.is_alive]
        
        # 投票済みプレイヤーを取得
        vote_logs = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == room.day_number,
            GameLog.event_type == "vote"
        ).all()
        
        voted_player_ids = set()
        for vote_log in vote_logs:
            if vote_log.actor_player_id:
                voted_player_ids.add(vote_log.actor_player_id)
        
        # 未投票のAIプレイヤーを特定
        unvoted_ai_players = [
            p for p in alive_players 
            if not p.is_human and p.player_id not in voted_player_ids
        ]
        
        # 各未投票AIプレイヤーにランダム投票を実行
        for ai_player in unvoted_ai_players:
            possible_targets = [p for p in alive_players if p.player_id != ai_player.player_id]
            if possible_targets:
                target = random.choice(possible_targets)
                logger.info(f"Emergency vote: {ai_player.character_name} -> {target.character_name}")
                
                try:
                    # 緊急投票を実行
                    vote_result = process_vote(
                        db=db,
                        room_id=room_id,
                        voter_id=ai_player.player_id,
                        target_id=target.player_id
                    )
                    
                    # WebSocket通知
                    await sio.emit("vote_cast", {
                        "room_id": str(room_id),
                        "voter_id": str(ai_player.player_id),
                        "target_id": str(target.player_id),
                        "vote_counts": vote_result.vote_counts,
                        "message": f"タイムアウトによる緊急投票: {ai_player.character_name} -> {target.character_name}",
                        "is_emergency": True
                    }, room=str(room_id))
                    
                except Exception as vote_error:
                    logger.error(f"Emergency vote failed for {ai_player.character_name}: {vote_error}")
        
        # 強制進行のログ記録
        create_game_log(db, room_id, "day_vote", "timeout", 
                       content="投票タイムアウトにより強制的に投票フェーズを終了しました。")
        
    except Exception as e:
        logger.error(f"Error in force vote progression for room {room_id}: {e}", exc_info=True)

async def send_vote_status_update(room_id: uuid.UUID, db: Session):
    """投票状況のWebSocket通知を送信"""
    try:
        room = get_room(db, room_id)
        if not room or room.status != 'day_vote':
            return
        
        # 現在の投票状況を取得
        players = get_players_in_room(db, room_id)
        alive_players = [p for p in players if p.is_alive]
        
        # 投票済みプレイヤーを取得
        vote_logs = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == room.day_number,
            GameLog.event_type == "vote"
        ).all()
        
        voted_player_ids = set()
        vote_counts = {}
        latest_votes = {}
        
        # 最新の投票のみを取得（一人一票）
        for log in reversed(vote_logs):  # 最新から順に
            if log.actor_player_id:
                player_id_str = str(log.actor_player_id)
                if player_id_str not in latest_votes:
                    target_name = log.content.replace("voted for ", "")
                    latest_votes[player_id_str] = target_name
                    voted_player_ids.add(log.actor_player_id)
        
        # 投票カウント
        for target_name in latest_votes.values():
            vote_counts[target_name] = vote_counts.get(target_name, 0) + 1
        
        total_votes = len(voted_player_ids)
        total_players = len(alive_players)
        
        # WebSocket通知データを作成
        vote_status = {
            "room_id": str(room_id),
            "total_votes": total_votes,
            "total_players": total_players,
            "vote_counts": vote_counts,
            "progress": f"{total_votes}/{total_players}",
            "is_complete": total_votes >= total_players,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await sio.emit("vote_status_update", vote_status, room=str(room_id))
        logger.debug(f"Vote status update sent for room {room_id}: {total_votes}/{total_players}")
        
    except Exception as e:
        logger.error(f"Error sending vote status update for room {room_id}: {e}")

async def check_and_progress_ai_turns(room_id: uuid.UUID, db: Session):
    """Check if current player is AI and progress if needed"""
    try:
        room = get_room(db, room_id)
        if not room or room.status not in ['day_discussion', 'day_vote']:
            return
            
        # 投票フェーズでは特別な処理を行う
        if room.status == 'day_vote':
            await handle_voting_phase_auto_progress(room_id, room, db)
            return
            
        # 議論フェーズでのターンベース処理
        # Get current player
        current_player = None
        if room.turn_order and room.current_turn_index is not None and room.current_turn_index < len(room.turn_order):
            current_player_id = room.turn_order[room.current_turn_index]
            current_player = get_player(db, uuid.UUID(current_player_id))
        
        if not current_player or current_player.is_human:
            return  # Human player or no current player, skip
            
        # Check if AI player hasn't acted recently (more than 5 seconds ago)
        if room.last_activity and (datetime.now(timezone.utc) - room.last_activity).total_seconds() < 5:
            return  # Recent activity, wait a bit more
            
        logger.info(f"Auto-progressing AI player {current_player.character_name} in room {room_id}")
        
        # Call auto_progress logic (reuse existing function)
        try:
            result = auto_progress_logic(room_id, db)
            if result.get("auto_progressed"):
                logger.info(f"Successfully auto-progressed room {room_id}: {result.get('message', 'No message')}")
        except Exception as e:
            logger.error(f"Error in auto_progress_logic for room {room_id}: {e}")
            
    except Exception as e:
        logger.error(f"Error checking AI turns for room {room_id}: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on application startup"""
    global game_loop_task, pool_monitor_task
    logger.info("Starting application startup tasks...")
    
    # Start the game loop monitor task
    game_loop_task = asyncio.create_task(game_loop_monitor())
    logger.info("AI game auto-progression monitor started")
    
    # Start the connection pool monitor task
    pool_monitor_task = asyncio.create_task(connection_pool_monitor())
    logger.info("Database connection pool monitor started")

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean up background tasks on application shutdown"""
    global game_loop_task, pool_monitor_task
    logger.info("Shutting down application...")
    
    # Cancel game loop monitor
    if game_loop_task:
        game_loop_task.cancel()
        try:
            await game_loop_task
        except asyncio.CancelledError:
            logger.info("Game loop monitor task cancelled successfully")
    
    # Cancel pool monitor
    if pool_monitor_task:
        pool_monitor_task.cancel()
        try:
            await pool_monitor_task
        except asyncio.CancelledError:
            logger.info("Connection pool monitor task cancelled successfully")

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
        "version": "1.0.0",
        "database": "SQLite" if DATABASE_URL.startswith("sqlite") else "PostgreSQL"
    }

@app.get("/api/health", summary="API経由でのアプリケーション稼働状態確認")
def api_health_check():
    """API経由でのサービス稼働状態を確認"""
    return {
        "status": "healthy",
        "service": "AI Werewolf Game Logic Service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "database": "SQLite" if DATABASE_URL.startswith("sqlite") else "PostgreSQL"
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
    try:
        # ai_playersの値を無視し、total_playersとhuman_playersから計算し直す
        # フロントエンドから誤った値が送られてきても、ここで上書きする
        room.ai_players = room.total_players - room.human_players
        if room.ai_players < 0:
            raise HTTPException(status_code=400, detail="AI players count cannot be negative.")
        logger.info(f"Adjusted ai_players for room {room.room_name}. Calculated AI players: {room.ai_players}")

        if room.total_players != room.human_players + room.ai_players:
            # このチェックは、ai_playersを計算し直した後も整合性が取れているかを確認するために残す
            raise HTTPException(status_code=400, detail="Total players must equal human + AI players after adjustment.")

        db_room = Room(
            room_name=room.room_name,
            total_players=room.total_players,
            human_players=room.human_players,
            ai_players=room.ai_players,
            is_private=room.is_private
        )
        db.add(db_room)
        db.flush()

        # ホストプレイヤーを最初に追加
        host_player = Player(
            room_id=db_room.room_id, 
            character_name=host_name, 
            is_human=True,
            is_claimed=True # ホストはclaimed
        )
        db.add(host_player)
        db.flush()

        # 残りの人間プレイヤーを作成 (ホストを除く)
        for i in range(1, room.human_players): # 1から開始
            human_player = Player(
                room_id=db_room.room_id, 
                character_name=f"人間プレイヤー{i+1}", # 名前を調整
                is_human=True,
                is_claimed=False
            )
            db.add(human_player)
            db.flush()
            
        # AIプレイヤーを作成
        # total_players から既にいる人間プレイヤーの数を引いた残りをAIプレイヤーとして追加
        num_ai_to_add = room.total_players - room.human_players
        for i in range(num_ai_to_add):
            ai_player = Player(
                room_id=db_room.room_id,
                character_name=f"AIプレイヤー{i+1}",
                is_human=False,
                character_persona=None,
                is_claimed=False
            )
            db.add(ai_player)
            db.flush()
            
        db.commit()
        db.refresh(db_room)
        logger.info(f"Room created successfully: {db_room.room_id} with {room.ai_players} AI players")
        return db_room
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating room: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create room: {str(e)}")

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
    db_room.current_round = 1
    
    create_game_log(db, room_id, "day_discussion", "game_start", content="ゲームが開始されました。")
    
    db.commit()
    db.refresh(db_room)
    logger.info(f"Game started in room {room_id}. Turn order: {db_room.turn_order}")
    
    # Check if first player is AI and trigger progression
    try:
        if db_room.turn_order and db_room.current_turn_index is not None:
            first_player_id = db_room.turn_order[db_room.current_turn_index]
            first_player = get_player(db, uuid.UUID(first_player_id))
            if first_player and not first_player.is_human and first_player.is_alive:
                logger.info(f"Scheduling AI progression for first player {first_player.character_name}")
                # Schedule AI progression with a small delay to allow game start to complete (only if event loop is running)
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(delayed_ai_progression(room_id, 3.0))
                except RuntimeError:
                    # No event loop running, skip scheduling (auto-progression will handle it)
                    logger.info("No event loop running, relying on auto-progression monitor")
    except Exception as e:
        logger.error(f"Error scheduling initial AI progression: {e}")
    
    return db_room

def speak_logic(db: Session, room_id: uuid.UUID, player_id: uuid.UUID, statement: str) -> Room:
    """発言処理（排他制御付き）"""
    try:
        # DB-level 排他制御（FOR UPDATE）
        db_room = db.query(Room).filter(Room.room_id == room_id).with_for_update().first()
        if not db_room:
            raise HTTPException(status_code=404, detail="Room not found")
        if db_room.status != 'day_discussion':
            raise HTTPException(status_code=400, detail="Not in discussion phase.")

        if not db_room.turn_order or db_room.current_turn_index is None:
            raise HTTPException(status_code=500, detail="Game turn order not initialized.")

        turn_order = db_room.turn_order
        current_index = db_room.current_turn_index
        
        # ターン検証の簡素化
        if current_index >= len(turn_order):
            logger.error(f"Invalid turn index {current_index} >= {len(turn_order)}")
            raise HTTPException(status_code=500, detail="Invalid turn state")
            
        if turn_order[current_index] != str(player_id):
            current_player = get_player(db, uuid.UUID(turn_order[current_index]))
            current_name = current_player.character_name if current_player else "不明"
            raise HTTPException(status_code=403, detail=f"It's not your turn. Current turn: {current_name}")

        # 発言を記録
        create_game_log(db, room_id, "day_discussion", "speech", actor_player_id=player_id, content=statement)
        
        # 自動サマリー更新
        try:
            update_game_summary_auto(db, room_id)
            logger.info(f"Auto-summary updated for room {room_id} after speech")
        except Exception as e:
            logger.warning(f"Failed to update auto-summary for room {room_id}: {e}")
            # サマリー更新失敗はゲーム進行を止めない
        
        # 次のプレイヤーを探す（簡素化）
        next_index = find_next_alive_player_safe(db, room_id, current_index)
        
        # ターン進行
        db_room.current_turn_index = next_index
        
        # 発言回数チェック
        alive_count = sum(1 for pid in turn_order 
                         if get_player(db, uuid.UUID(pid)) and get_player(db, uuid.UUID(pid)).is_alive)
        
        total_speeches = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.phase == "day_discussion",
            GameLog.event_type == "speech",
            GameLog.day_number == db_room.day_number
        ).count()
        
        # 生存プレイヤー数の3倍の発言で投票フェーズへ
        if total_speeches >= alive_count * 3:
            db_room.status = "day_vote"
            db_room.current_turn_index = 0
            create_game_log(db, room_id, "day_discussion", "phase_transition", 
                          content="議論終了。投票フェーズに移行します。")
        
        # 最終活動時間を更新（自動クローズ用）
        db_room.last_activity = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(db_room)
        
        logger.info(f"Turn advanced: {current_index} -> {next_index}, status: {db_room.status}")
        
        # Trigger AI progression if next player is AI
        try:
            if db_room.status == 'day_discussion' and next_index < len(turn_order):
                next_player_id = turn_order[next_index]
                next_player = get_player(db, uuid.UUID(next_player_id))
                if next_player and not next_player.is_human and next_player.is_alive:
                    logger.info(f"Scheduling AI progression for player {next_player.character_name}")
                    # Schedule AI progression with a small delay (only if event loop is running)
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(delayed_ai_progression(room_id, 5.0))
                    except RuntimeError:
                        # No event loop running, skip scheduling (auto-progression will handle it)
                        logger.info("No event loop running, relying on auto-progression monitor")
        except Exception as e:
            logger.error(f"Error scheduling AI progression: {e}")
        
        return db_room
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in speak_logic: {e}")
        raise


def find_next_alive_player_safe(db: Session, room_id: uuid.UUID, current_index: int) -> int:
    """安全な次のプレイヤー検索（無限ループ対策）"""
    room = get_room(db, room_id)
    if not room or not room.turn_order:
        return current_index
        
    turn_order = room.turn_order
    max_attempts = len(turn_order)
    
    for attempt in range(1, max_attempts + 1):
        next_index = (current_index + attempt) % len(turn_order)
        player_id = turn_order[next_index]
        player = get_player(db, uuid.UUID(player_id))
        
        if player and player.is_alive:
            return next_index
    
    # 全員死亡の場合は現在のインデックスを返す
    logger.warning(f"No alive players found in room {room_id}")
    return current_index

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

def get_player_speech_history(db: Session, room_id: uuid.UUID, player_id: Optional[uuid.UUID] = None, 
                            day_number: Optional[int] = None, limit: int = 50) -> List[Dict]:
    """特定プレイヤーまたは全プレイヤーの発言履歴を取得（専門エージェント・Function Calling用）"""
    try:
        query = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.event_type == "speech"
        )
        
        # プレイヤー指定がある場合
        if player_id:
            query = query.filter(GameLog.actor_player_id == player_id)
        
        # 日数指定がある場合
        if day_number:
            query = query.filter(GameLog.day_number == day_number)
        
        # 時系列順（新しい順）で取得
        logs = query.order_by(GameLog.created_at.desc()).limit(limit).all()
        
        # 結果を辞書形式で返す
        result = []
        for log in reversed(logs):  # 古い順に並び替え
            player = get_player(db, log.actor_player_id) if log.actor_player_id else None
            result.append({
                "log_id": str(log.log_id),
                "day_number": log.day_number,
                "phase": log.phase,
                "player_id": str(log.actor_player_id) if log.actor_player_id else None,
                "player_name": player.character_name if player else "不明",
                "content": log.content,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        logger.info(f"Retrieved {len(result)} speech logs for room {room_id}, player {player_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving speech history: {e}")
        return []

def get_player_own_speeches(db: Session, room_id: uuid.UUID, player_id: uuid.UUID, limit: int = 20) -> List[Dict]:
    """特定プレイヤー自身の発言履歴のみを取得（デフォルトインプット用）"""
    return get_player_speech_history(db, room_id, player_id, limit=limit)

def get_latest_game_summary(db: Session, room_id: uuid.UUID, day_number: Optional[int] = None, phase: Optional[str] = None) -> Optional[Dict]:
    """最新のゲームサマリーを取得（Phase 4: デフォルトインプット用）"""
    try:
        query = db.query(GameSummary).filter(GameSummary.room_id == room_id)
        
        # 日数指定がある場合
        if day_number:
            query = query.filter(GameSummary.day_number == day_number)
        
        # フェーズ指定がある場合
        if phase:
            query = query.filter(GameSummary.phase == phase)
        
        # 最新のサマリーを取得
        summary = query.order_by(GameSummary.updated_at.desc()).first()
        
        if summary:
            return {
                "summary_id": str(summary.summary_id),
                "room_id": str(summary.room_id),
                "day_number": summary.day_number,
                "phase": summary.phase,
                "summary_content": summary.summary_content,
                "important_events": summary.important_events,
                "player_suspicions": summary.player_suspicions,
                "updated_at": summary.updated_at.isoformat() if summary.updated_at else None
            }
        else:
            logger.info(f"No game summary found for room {room_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving latest game summary: {e}")
        return None

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
        GameLog.event_type.in_(['speech', 'vote', 'game_start', 'game_end', 'phase_change'])
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
    """【修正版】シンプルで堅牢な投票処理ロジック"""
    try:
        # 1. 投票を記録
        db_room = get_room(db, room_id)
        if not db_room or db_room.status != 'day_vote':
            raise HTTPException(status_code=400, detail="Not in voting phase")

        target_player = get_player(db, target_id)
        if not target_player:
            raise HTTPException(status_code=404, detail="Target player not found")

        # 既に投票済みかチェック（重複投票防止）
        existing_vote = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == db_room.day_number,
            GameLog.phase == "day_vote",
            GameLog.event_type == "vote",
            GameLog.actor_player_id == voter_id
        ).first()

        if existing_vote:
            # 既に投票している場合は、ログを更新する（投票先の変更を許可）
            existing_vote.content = f"voted for {target_player.character_name}"
            existing_vote.created_at = datetime.now(timezone.utc)
            message = "投票先を変更しました。"
        else:
            # 新規投票
            create_game_log(db, room_id, "day_vote", "vote", actor_player_id=voter_id, content=f"voted for {target_player.character_name}")
            message = "投票を受け付けました。"

        db.commit()

        # 2. 全員の投票が完了したかチェック
        living_players = [p for p in db_room.players if p.is_alive]
        vote_logs = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == db_room.day_number,
            GameLog.phase == "day_vote",
            GameLog.event_type == "vote"
        ).all()

        # 各プレイヤーの最新の投票のみをカウント
        latest_votes = {}
        for log in sorted(vote_logs, key=lambda x: x.created_at):
            if log.actor_player_id:
                latest_votes[log.actor_player_id] = log.content.replace("voted for ", "")

        vote_counts = {}
        for target_name in latest_votes.values():
            vote_counts[target_name] = vote_counts.get(target_name, 0) + 1
        
        # 3. 投票完了時の処理
        if len(latest_votes) >= len(living_players):
            voted_out_player_id = None
            tied_vote = False
            
            if vote_counts:
                max_votes = max(vote_counts.values())
                most_voted_names = [name for name, count in vote_counts.items() if count == max_votes]

                if len(most_voted_names) == 1:
                    # 単独最多票
                    voted_out_name = most_voted_names[0]
                    voted_out_player = db.query(Player).filter(
                        Player.character_name == voted_out_name,
                        Player.room_id == room_id
                    ).first()
                    
                    if voted_out_player:
                        voted_out_player.is_alive = False
                        voted_out_player_id = voted_out_player.player_id
                        create_game_log(db, room_id, "day_vote", "execution", content=f"{voted_out_name} was voted out.")
                        message = f"{voted_out_name}が投票により追放されました。"
                    else:
                        message = "追放対象のプレイヤーが見つかりませんでした。"
                else:
                    # 同票
                    tied_vote = True
                    message = "同票のため、誰も追放されませんでした。"
                    create_game_log(db, room_id, "day_vote", "execution", content="Tied vote. No one was voted out.")
            else:
                # 投票なし
                message = "投票がありませんでした。"

            # 夜フェーズへ移行
            db_room.status = 'night'
            create_game_log(db, room_id, "phase_transition", "night", content="夜フェーズに移行します。")
            db.commit()
            
            return VoteResult(
                vote_counts=vote_counts,
                voted_out_player_id=str(voted_out_player_id) if voted_out_player_id else None,
                tied_vote=tied_vote,
                message=message
            )

        # 4. 投票受付中の場合
        db.commit()
        return VoteResult(
            vote_counts=vote_counts,
            voted_out_player_id=None,
            tied_vote=False,
            message=f"投票受付中... ({len(latest_votes)}/{len(living_players)})")
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing vote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during voting.")

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
    
    # ボディガードの守り（自動）
    bodyguards = [p for p in db_room.players if p.role == 'bodyguard' and p.is_alive]
    if bodyguards:
        bodyguard = bodyguards[0]
        alive_players = [p for p in db_room.players if p.is_alive and p.player_id != bodyguard.player_id]
        if alive_players:
            protected = random.choice(alive_players)
            create_game_log(db, room_id, "night", "protect", 
                          actor_player_id=bodyguard.player_id,
                          content=f"protected {protected.character_name}")
            results['protection'] = f"{bodyguard.character_name}が{protected.character_name}を守りました"
    
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
        db_room.current_round = 1
        
        # 生存者でターン順序を再構築（相対順序を保持）
        living_players = [p for p in db_room.players if p.is_alive]
        
        # 前日のターン順序を参照して相対順序を保持
        if db_room.turn_order:
            # 前日のターン順序から生存者のみを抽出して順序を保持
            prev_order_alive = []
            for player_id_str in db_room.turn_order:
                player = next((p for p in living_players if str(p.player_id) == player_id_str), None)
                if player:
                    prev_order_alive.append(player)
            
            # 新しく追加された生存者があれば末尾に追加
            for player in living_players:
                if player not in prev_order_alive:
                    prev_order_alive.append(player)
                    
            living_players = prev_order_alive
        else:
            # 初回の場合のみランダムシャッフル
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

def generate_ai_speech(db: Session, room_id: uuid.UUID, ai_player_id: uuid.UUID, emergency_skip: bool = False) -> str:
    """AIプレイヤーの発言を生成（AIエージェント使用・緊急スキップ対応）"""
    # 超堅牢なフォールバック用の発言リスト
    ULTRA_SAFE_FALLBACK_SPEECHES = [
        "状況を確認しています。",
        "少し考えさせてください。",
        "慎重に判断します。",
        "様子を見てみましょう。",
        "情報を整理中です。",
        "よく考えてみます。"
    ]
    
    # 緊急スキップモード：即座にフォールバック発言を返す
    if emergency_skip:
        logger.warning(f"Emergency skip activated for AI player {ai_player_id}")
        return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
    
    try:
        # 最初にフォールバック用の基本情報を取得
        try:
            ai_player = get_player(db, ai_player_id)
            room = get_room(db, room_id)
        except Exception as db_error:
            logger.error(f"Database access error in generate_ai_speech: {db_error}", exc_info=True)
            return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
        
        # 基本的な検証
        if not ai_player or not room:
            logger.error(f"Player or room not found: player={ai_player}, room={room}")
            return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
        
        if ai_player.is_human:
            logger.error(f"Player {ai_player.character_name} is not an AI player")
            return "少し考えさせてください。"
        
        # デバッグ: ペルソナ情報をログ出力
        logger.info(f"Generating speech for {ai_player.character_name}")
        logger.info(f"Player persona type: {type(ai_player.character_persona)}")
        logger.info(f"Player persona content: {ai_player.character_persona}")
        logger.info(f"Using root_agent: {root_agent is not None}")
        logger.info(f"GOOGLE_PROJECT_ID: {GOOGLE_PROJECT_ID} (actual value)")
        logger.info(f"GOOGLE_LOCATION: {GOOGLE_LOCATION} (actual value)")
        logger.info(f"Room status: {room.status}, Day: {room.day_number}")
        
        # AIエージェントが利用可能な場合
        logger.info(f"Checking AI agent availability: root_agent={root_agent is not None}, GOOGLE_PROJECT_ID='{GOOGLE_PROJECT_ID}', GOOGLE_LOCATION='{GOOGLE_LOCATION}'")
        
        # Debug: root_agent の詳細をログ出力
        if root_agent is None:
            logger.error("❌ CRITICAL: root_agent is None - AI agent not properly initialized")
            logger.error("This indicates a problem with the npc_agent import or initialization")
            logger.info("Using ultra-safe fallback due to missing root_agent")
            return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
        
        # root_agentの型とメソッドを確認
        logger.info(f"✅ root_agent type: {type(root_agent)}")
        logger.info(f"✅ root_agent methods: {dir(root_agent)}")
        logger.info(f"✅ Has generate_speech method: {hasattr(root_agent, 'generate_speech')}")
        
        # Google AI設定の確認
        if root_agent and GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
            logger.info("Using root_agent with Google AI credentials")
            # プレイヤー情報を準備（ペルソナ未設定の場合はデフォルト）
            persona = ai_player.character_persona
            if not persona:
                persona = f"私は{ai_player.character_name}です。冷静に分析して判断します。"
                
            player_info = {
                'name': ai_player.character_name,
                'role': ai_player.role,
                'is_alive': ai_player.is_alive,
                'persona': persona
            }
            
            # ゲーム情報を準備
            game_context = {
                'day_number': room.day_number,
                'phase': room.status,
                'alive_count': len([p for p in room.players if p.is_alive]),
                'total_players': len(room.players),
                'all_players': [{
                    'name': p.character_name,
                    'is_alive': p.is_alive,
                    'is_human': p.is_human,
                    'role': p.role if p.player_id == ai_player.player_id else 'unknown'  # 自分の役職のみ公開
                } for p in room.players]
            }
            
            # 全てのチャットログを取得（現在の日）
            recent_logs = db.query(GameLog).filter(
                GameLog.room_id == room_id,
                GameLog.day_number == room.day_number,
                GameLog.event_type == "speech"
            ).order_by(GameLog.created_at.asc()).all()  # 時系列順で全取得
            
            recent_messages = []
            for log in recent_logs:
                if log.actor:
                    recent_messages.append({
                        'speaker': log.actor.character_name,
                        'content': log.content or '',
                        'timestamp': log.created_at
                    })
            
            # AIエージェントで発言を生成
            logger.info(f"About to call root_agent.generate_speech() for {ai_player.character_name}")
            logger.info(f"Player info: {player_info}")
            logger.info(f"Game context: {game_context}")
            logger.info(f"Recent messages count: {len(recent_messages)}")
            
            try:
                logger.info("🚀 Calling root_agent.generate_speech()...")
                speech = root_agent.generate_speech(player_info, game_context, recent_messages)
                logger.info(f"✅ Successfully called root_agent.generate_speech()")
                logger.info(f"📝 Generated speech: {speech}")
                logger.info(f"📏 Speech length: {len(speech) if speech else 0} characters")
            except Exception as agent_error:
                logger.error(f"❌ CRITICAL ERROR in root_agent.generate_speech(): {agent_error}", exc_info=True)
                logger.error(f"Error type: {type(agent_error)}")
                logger.error(f"Error args: {agent_error.args}")
                
                # より詳細なエラー情報をログ出力
                logger.error(f"Room ID: {room_id}, Player ID: {ai_player_id}")
                logger.error(f"Player name: {ai_player.character_name if ai_player else 'None'}")
                logger.error(f"Game phase: {room.status if room else 'None'}")
                
                # エラータイプに応じた詳細処理
                if "timeout" in str(agent_error).lower():
                    logger.error("⏰ AI speech generation timed out")
                elif "quota" in str(agent_error).lower() or "rate" in str(agent_error).lower():
                    logger.error("🚫 AI service quota/rate limit exceeded")
                elif "connection" in str(agent_error).lower():
                    logger.error("🌐 AI service connection error")
                else:
                    logger.error("🔧 Other AI service error")
                
                # フォールバック前に最後の試行：Function Calling無しでの基本発言生成
                try:
                    logger.info("🔄 Attempting fallback speech generation without function calling...")
                    basic_prompt = f"""あなたは{ai_player.character_name}です。
ペルソナ: {ai_player.character_persona}
現在の状況: {room.status}、{room.day_number}日目
簡潔に1-2文で発言してください。"""
                    
                    # 基本的なVertex AI呼び出し（Function Calling無し）
                    import vertexai
                    from vertexai.generative_models import GenerativeModel
                    
                    if GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
                        vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
                        model = GenerativeModel("gemini-1.5-flash")
                        response = model.generate_content(basic_prompt)
                        if response.text and len(response.text.strip()) > 10:
                            logger.info(f"✅ Fallback speech generation successful: {response.text.strip()}")
                            return response.text.strip()
                except Exception as fallback_error:
                    logger.error(f"🚨 Fallback speech generation also failed: {fallback_error}")
                
                logger.info("Using ultra-safe fallback due to all AI generation failures")
                return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
            
            # レスポンスの検証と整形
            if speech and isinstance(speech, str) and speech.strip():
                speech = speech.strip()
                # 極端に短い発言の場合はフォールバック
                if len(speech) < 5:
                    speech = "少し考えさせてください。"
                logger.info(f"AI agent generated speech for {ai_player.character_name}: {speech}")
                return speech
            else:
                logger.warning(f"AI agent returned invalid speech: {speech}")
                logger.info("Using ultra-safe fallback due to invalid AI response")
                return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
            
        else:
            # フォールバック: 環境変数が不足している場合
            logger.info(f"Missing AI credentials - using ultra-safe fallback. Root agent: {root_agent is not None}, PROJECT_ID: {bool(GOOGLE_PROJECT_ID)}, LOCATION: {bool(GOOGLE_LOCATION)}")
            return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
            
    except Exception as e:
        # ai_playerがNoneの場合の安全な処理
        player_name = "Unknown Player"
        player_id_str = str(ai_player_id)
        
        try:
            ai_player = get_player(db, ai_player_id) if 'ai_player' not in locals() or ai_player is None else ai_player
            if ai_player:
                player_name = getattr(ai_player, 'character_name', 'Unknown Player')
                player_id_str = str(ai_player.player_id)
        except:
            pass  # フォールバック情報取得でエラーが出ても無視
        
        logger.error(f"Error generating AI speech for {player_name}: {e}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        logger.error(f"Player ID: {player_id_str}, Character: {player_name}")
        
        # 緊急フォールバック - どんな状況でも確実に発言を返す
        fallback_speech = random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
        logger.info(f"Using emergency ultra-safe fallback speech for {player_name}: '{fallback_speech}'")
        return fallback_speech

async def generate_ai_vote_decision(db: Session, room_id: uuid.UUID, ai_player, possible_targets) -> Player:
    """
    LLMベースのAI投票先決定
    """
    try:
        if GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
            # ゲーム状況を収集
            room = get_room(db, room_id)
            recent_logs = db.query(GameLog).filter(
                GameLog.room_id == room_id,
                GameLog.day_number == room.day_number,
                GameLog.event_type == "speech"
            ).order_by(GameLog.created_at.desc()).limit(10).all()
            
            # 投票用プロンプトを構築
            prompt = build_ai_vote_prompt(ai_player, room, possible_targets, recent_logs)
            
            model = GenerativeModel("gemini-1.5-flash")
            
            try:
                # 非同期でタイムアウト付き実行
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, prompt),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"AI vote decision timeout for {ai_player.character_name}, using random selection")
                return random.choice(possible_targets)
            
            # レスポンスからプレイヤー名を抽出
            decision_text = response.text.strip()
            
            # プレイヤー名でマッチング
            for target in possible_targets:
                if target.character_name in decision_text:
                    logger.info(f"AI {ai_player.character_name} decided to vote for {target.character_name} via LLM")
                    return target
            
            # マッチしなかった場合は最初のターゲット
            logger.warning(f"AI {ai_player.character_name} LLM vote decision unclear: {decision_text}, using first target")
            return possible_targets[0]
            
    except Exception as e:
        logger.error(f"Error in AI vote decision: {e}")
    
    # フォールバック: ランダム選択
    logger.warning(f"AI vote decision failed for {ai_player.character_name}, using random selection")
    return random.choice(possible_targets)


# --- WebSocket (Socket.IO) Setup ---
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
# Gunicornが起動できるように、FastAPIアプリとSocket.IOを結合
app_sio = socketio.ASGIApp(sio, app)

@sio.event
async def connect(sid, environ):
    logger.info(f"Socket.IO client connected: {sid}")
    # クライアントからセッション情報を取得
    query_string = environ.get('QUERY_STRING', '')
    query_params = dict(qc.split('=') for qc in query_string.split('&') if qc)
    session_token = query_params.get('session_token')

    if session_token:
        db = SessionLocal()
        try:
            player_session = db.query(PlayerSession).filter(
                PlayerSession.session_token == session_token,
                PlayerSession.expires_at > datetime.now(timezone.utc)
            ).first()
            if player_session:
                sio.save_session(sid, {'player_id': str(player_session.player_id)})
                logger.info(f"Client {sid} authenticated as player {player_session.player_id}")
                await sio.emit('authenticated', {'player_id': str(player_session.player_id)}, to=sid)
            else:
                logger.warning(f"Client {sid} provided invalid or expired session token.")
                await sio.emit('authentication_failed', {'message': 'Invalid or expired session token.'}, to=sid)
                await sio.disconnect(sid)
        finally:
            db.close()
    else:
        logger.warning(f"Client {sid} connected without session token.")
        await sio.emit('authentication_required', {'message': 'Session token required.'}, to=sid)
        await sio.disconnect(sid)

@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO client disconnected: {sid}")
    # TODO: 必要に応じてプレイヤーの切断処理を実装

@sio.event
async def join_room(sid, data):
    room_id = data.get('room_id')
    if room_id:
        sio.enter_room(sid, room_id)
        logger.info(f"Client {sid} joined room {room_id}")
        await sio.emit('message', {'data': f'Successfully joined room {room_id}'}, to=sid)

@sio.event
async def leave_room(sid, data):
    room_id = data.get('room_id')
    if room_id:
        sio.leave_room(sid, room_id)
        logger.info(f"Client {sid} left room {room_id}")

# --- API Endpoints ---
@app.post("/api/rooms", response_model=RoomInfo, summary="新しいゲームルームを作成")
def create_new_room(room: RoomCreate, host_name: str, db: Session = Depends(get_db)):
    """新しいゲームルームを作成し、ホストプレイヤーを追加する"""
    return create_room(db=db, room=room, host_name=host_name)

@app.get("/api/rooms", response_model=List[RoomSummary], summary="公開ゲームルームの一覧を取得")
def read_rooms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """現在参加可能な公開ゲームルームの一覧を取得する"""
    return get_rooms(db, skip=skip, limit=limit)

@app.get("/api/rooms/{room_id}", response_model=RoomInfo, summary="特定のゲームルーム情報を取得")
def read_room(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """特定のゲームルームの詳細情報を取得する"""
    db_room = get_room(db, room_id)
    if db_room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return db_room

@app.post("/api/rooms/{room_id}/join", response_model=JoinRoomResponse, summary="ゲームルームに参加")
async def join_room_api(room_id: uuid.UUID, player_name: str, db: Session = Depends(get_db)):
    """既存のゲームルームに新しいプレイヤーとして参加する"""
    db_room = get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    if len(db_room.players) >= db_room.total_players:
        raise HTTPException(status_code=400, detail="Room is full")
    
    new_player = Player(room_id=room_id, character_name=player_name, is_human=True)
    db.add(new_player)
    db.flush() # player_idを確定させるため

    # プレイヤーセッションを作成
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=1) # 24時間有効
    player_session = PlayerSession(
        player_id=new_player.player_id,
        session_token=session_token,
        expires_at=expires_at
    )
    db.add(player_session)
    db.commit()
    db.refresh(new_player)
    
    # 他のプレイヤーに通知
    await sio.emit('player_joined', {'room_id': str(room_id), 'player_name': player_name}, room=str(room_id))
    
    return JoinRoomResponse(player_id=new_player.player_id, player_name=new_player.character_name, room_id=room_id, session_token=session_token)

@app.post("/api/rooms/{room_id}/start", response_model=RoomInfo, summary="ゲームを開始")
async def start_game(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """ゲームを開始し、役職を割り当てる"""
    updated_room = start_game_logic(db, room_id)
    await sio.emit('game_started', {'room_id': str(room_id), 'message': 'Game has started!'}, room=str(room_id))
    return updated_room

@app.post("/api/rooms/{room_id}/speak", summary="プレイヤーが発言")
async def speak(room_id: uuid.UUID, player_id: uuid.UUID, speak_input: SpeakInput, db: Session = Depends(get_db)):
    """プレイヤーが議論中に発言する"""
    updated_room = speak_logic(db, room_id, player_id, speak_input.statement)
    
    # WebSocketで発言をブロードキャスト
    player = get_player(db, player_id)
    await sio.emit('new_speech', {
        'room_id': str(room_id),
        'speaker_id': str(player_id),
        'speaker_name': player.character_name if player else 'Unknown',
        'statement': speak_input.statement
    }, room=str(room_id))
    
    return updated_room

@app.post("/api/rooms/{room_id}/vote")
async def vote(room_id: uuid.UUID, vote_request: VoteRequest, db: Session = Depends(get_db)) -> VoteResult:
    """プレイヤーが特定のターゲットに投票する"""
    try:
        voter_id = uuid.UUID(vote_request.voter_id)
        target_id = uuid.UUID(vote_request.target_id)
        
        # 投票処理
        vote_result = process_vote(db, room_id, voter_id, target_id)
        
        # 投票状況を全部屋に通知
        await send_vote_status_update(room_id, db)
        
        # 投票完了後、ゲーム状態が変化した場合の通知
        if vote_result.voted_out_player_id or vote_result.tied_vote:
            await sio.emit('room_updated', {'room_id': str(room_id)}, room=str(room_id))

        return vote_result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing vote for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during voting.")

@app.post("/api/rooms/{room_id}/night_action", summary="夜のアクションを実行")
async def night_action(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """夜のフェーズのアクション（人狼の襲撃など）を自動で実行する"""
    results = process_night_actions(db, room_id)
    await sio.emit('night_action_result', {'room_id': str(room_id), 'results': results}, room=str(room_id))
    return results

@app.get("/api/rooms/{room_id}/logs", response_model=List[GameLogInfo], summary="ゲームログを取得")
def read_game_logs(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """特定のゲームルームのログを取得する"""
    return get_game_logs(db, room_id)

@app.post("/api/players/{player_id}/generate_persona", summary="AIプレイヤーのペルソナを生成")
async def generate_persona(player_id: uuid.UUID, persona_input: PersonaInput, db: Session = Depends(get_db)):
    """AIプレイヤーのペルソナをキーワードに基づいて生成する"""
    player = get_player(db, player_id)
    if not player or player.is_human:
        raise HTTPException(status_code=400, detail="Invalid player for persona generation")

    if not root_agent:
        raise HTTPException(status_code=503, detail="AI agent is not available")

    try:
        # Vertex AI を使用してペルソナを生成
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"以下のキーワードを元に、人狼ゲームのキャラクターのペルソナをJSON形式で生成してください: {persona_input.keywords}" +
            "\n\n{\n  \"gender\": \"(性別)\",\n  \"age\": (年齢),\n  \"personality\": \"(性格)\",\n  \"speech_style\": \"(話し方、口調)\",\n  \"background\": \"(背景設定)\"\n}"
        )
        persona_data = json.loads(response.text)
        
        # データベースを更新
        update_player_persona(db, player_id, persona_data)
        
        # 更新を通知
        await sio.emit('room_updated', {'room_id': str(player.room_id)}, room=str(player.room_id))
        
        return {"message": "Persona generated successfully", "persona": persona_data}
    except Exception as e:
        logger.error(f"Persona generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate persona")

@app.post("/api/rooms/{room_id}/auto_progress", summary="ゲームの自動進行")
async def auto_progress(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """AIプレイヤーのターンを自動で進行させる"""
    try:
        result = auto_progress_logic(room_id, db)
        if result.get("auto_progressed"):
            # WebSocket通知
            if "websocket_data" in result:
                ws_data = result["websocket_data"]
                await sio.emit(ws_data["type"], ws_data["data"], room=str(room_id))
            return {"message": result.get("message", "Auto-progression successful.")}
        else:
            return {"message": result.get("message", "No action taken.")}
    except Exception as e:
        logger.error(f"Auto-progress failed for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Auto-progress failed: {str(e)}")

async def auto_progress_logic(room_id: uuid.UUID, db: Session) -> dict:
    """自動進行のコアロジック"""
    room = get_room(db, room_id)
    if not room:
        return {"auto_progressed": False, "message": "Room not found."}

    if room.status == 'day_discussion':
        if not room.turn_order or room.current_turn_index is None:
            return {"auto_progressed": False, "message": "Turn order not set."}
        
        current_player_id = uuid.UUID(room.turn_order[room.current_turn_index])
        current_player = get_player(db, current_player_id)

        if current_player and not current_player.is_human and current_player.is_alive:
            # AIの発言を生成
            statement = generate_ai_speech(db, room_id, current_player_id)
            
            # 発言処理
            updated_room = speak_logic(db, room_id, current_player_id, statement)
            
            # WebSocket通知データ
            websocket_data = {
                "type": "new_speech",
                "data": {
                    'room_id': str(room_id),
                    'speaker_id': str(current_player_id),
                    'speaker_name': current_player.character_name,
                    'statement': statement
                }
            }
            return {"auto_progressed": True, "message": f"{current_player.character_name} spoke.", "websocket_data": websocket_data}

    elif room.status == 'day_vote':
        # 未投票のAIプレイヤーを探す
        players = get_players_in_room(db, room_id)
        alive_players = [p for p in players if p.is_alive]
        voted_player_ids = {log.actor_player_id for log in db.query(GameLog).filter(
            GameLog.room_id == room_id, 
            GameLog.day_number == room.day_number, 
            GameLog.event_type == 'vote'
        ).all()}

        ai_to_vote = next((p for p in alive_players if not p.is_human and p.player_id not in voted_player_ids), None)

        if ai_to_vote:
            # AIの投票先を決定
            possible_targets = [p for p in alive_players if p.player_id != ai_to_vote.player_id]
            if not possible_targets:
                return {"auto_progressed": False, "message": "No one to vote for."}
            
            target_player = await generate_ai_vote_decision(db, room_id, ai_to_vote, possible_targets)
            
            # 投票処理
            process_vote(db, room_id, ai_to_vote.player_id, target_player.player_id)
            
            # WebSocket通知データ
            websocket_data = {
                "type": "new_vote",
                "data": {
                    'room_id': str(room_id),
                    'voter_id': str(ai_to_vote.player_id),
                    'voter_name': ai_to_vote.character_name,
                    'target_id': str(target_player.player_id),
                    'target_name': target_player.character_name
                }
            }
            return {"auto_progressed": True, "message": f"{ai_to_vote.character_name} voted for {target_player.character_name}.", "websocket_data": websocket_data}

    return {"auto_progressed": False, "message": "Not in a phase for auto-progression."}


# --- Helper Functions ---
def get_players_in_room(db: Session, room_id: uuid.UUID) -> List[Player]:
    return db.query(Player).filter(Player.room_id == room_id).all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)