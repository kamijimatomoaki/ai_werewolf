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
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
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
    logger.info(f"Root agent status: {root_agent is not None}")
    logger.info(f"Root agent type: {type(root_agent) if root_agent else 'None'}")
    
    # root_agentがNoneの場合は警告
    if root_agent is None:
        logger.error("❌ root_agent is None after import! Check npc_agent/agent.py initialization")
except ImportError as e:
    root_agent = None
    logger.error(f"AI NPC agent could not be imported: {e}")
    logger.error(f"Current working directory: {os.getcwd()}")
    logger.error(f"Script location: {os.path.abspath(__file__)}")
    logger.error(f"Backend directory: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
    logger.error(f"Current sys.path: {sys.path}")
except Exception as e:
    root_agent = None
    logger.error(f"Unexpected error during AI agent import: {e}")
    logger.error(f"Error type: {type(e)}")
    import traceback
    logger.error(f"Full traceback: {traceback.format_exc()}")

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
    vote_round = Column(Integer, default=1)
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
    
    # 手動で vote_round カラムを追加（既存データベース用の一時的な修正）
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS vote_round INTEGER DEFAULT 1"))
            conn.commit()
            logger.info("vote_round column added/verified successfully")
    except Exception as alter_e:
        logger.warning(f"Failed to add vote_round column (may already exist): {alter_e}")
        
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
    is_revote: bool = False
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
room_cleanup_task = None

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

def generate_ai_player_name_sync(player_number: int) -> str:
    """LLMを使ってAIプレイヤーの名前を生成（同期版）"""
    try:
        # Vertex AI の初期化を確認
        if not GOOGLE_PROJECT_ID:
            logger.warning("Google Cloud project not configured, using default AI player name")
            return f"AIプレイヤー{player_number}"
        
        # Vertex AI を使用して名前を生成
        vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
        model = GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""人狼ゲームに参加するキャラクターの名前を1つ生成してください。

要求:
- 日本人らしい名前（姓名両方含む）
- 覚えやすく親しみやすい
- 人狼ゲームに適したキャラクター性を感じさせる
- 他のプレイヤーと区別しやすい
- カタカナや漢字を使用

例: 田中太郎、山田花子、佐藤勇気、高橋美咲

**名前のみを返答してください（説明や追加情報は不要）**"""
        
        response = model.generate_content(prompt)
        generated_name = response.text.strip()
        
        # 生成された名前をクリーンアップ
        # 改行や余分な文字を除去
        generated_name = generated_name.replace('\n', '').replace('\r', '')
        if len(generated_name) > 20:  # 長すぎる場合は切り詰め
            generated_name = generated_name[:20]
        
        logger.info(f"Generated AI player name: {generated_name}")
        return generated_name
        
    except Exception as e:
        logger.error(f"AI name generation failed: {e}", exc_info=True)
        # フォールバック
        return f"AIプレイヤー{player_number}"

async def generate_ai_player_name(player_number: int) -> str:
    """LLMを使ってAIプレイヤーの名前を生成（非同期版）"""
    # 同期版を内部で呼び出し
    return generate_ai_player_name_sync(player_number)

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

async def room_cleanup_monitor():
    """古い部屋の自動削除・クリーンアップ機能"""
    logger.info("Starting room cleanup monitor...")
    
    while True:
        db = None
        try:
            # 1時間ごとに実行
            await asyncio.sleep(3600)  # 1時間 = 3600秒
            
            # Get database session with timeout protection
            try:
                db = SessionLocal()
                db.execute(text("SET statement_timeout = '30s'"))
                
                # 24時間以上活動がない部屋を検索
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                old_rooms = db.query(Room).filter(
                    Room.last_activity < cutoff_time
                ).all()
                
                if old_rooms:
                    logger.info(f"Found {len(old_rooms)} old rooms to cleanup")
                    
                    for room in old_rooms:
                        try:
                            # 削除対象の部屋情報をログ出力
                            logger.info(f"Cleaning up room {room.room_id}: status={room.status}, "
                                      f"last_activity={room.last_activity}, "
                                      f"player_count={len(room.players)}")
                            
                            # 関連するプレイヤーを削除
                            players_deleted = db.query(Player).filter(Player.room_id == room.room_id).count()
                            db.query(Player).filter(Player.room_id == room.room_id).delete()
                            
                            # 関連するゲームログを削除
                            logs_deleted = db.query(GameLog).filter(GameLog.room_id == room.room_id).count()
                            db.query(GameLog).filter(GameLog.room_id == room.room_id).delete()
                            
                            # 関連する投票記録を削除
                            votes_deleted = db.query(Vote).filter(Vote.room_id == room.room_id).count()
                            db.query(Vote).filter(Vote.room_id == room.room_id).delete()
                            
                            # 部屋を削除
                            db.delete(room)
                            
                            # 変更をコミット
                            db.commit()
                            
                            logger.info(f"Successfully cleaned up room {room.room_id}: "
                                      f"deleted {players_deleted} players, "
                                      f"{logs_deleted} logs, "
                                      f"{votes_deleted} votes")
                            
                        except Exception as room_error:
                            logger.error(f"Error cleaning up room {room.room_id}: {room_error}")
                            # ロールバックして続行
                            db.rollback()
                            continue
                else:
                    logger.info("No old rooms found for cleanup")
                    
            except Exception as db_error:
                logger.error(f"Database error in room cleanup monitor: {db_error}")
                if db:
                    db.rollback()
                continue
                
        except Exception as e:
            logger.error(f"Room cleanup monitor error: {e}")
        finally:
            # Ensure database session is always closed
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Error closing database session in room cleanup: {close_error}")

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

async def delayed_ai_progression_new_day(room_id: uuid.UUID, delay_seconds: float):
    """Schedule AI progression for new day start after a delay"""
    await asyncio.sleep(delay_seconds)
    try:
        db = SessionLocal()
        try:
            logger.info(f"Executing delayed AI progression for new day in room {room_id}")
            await check_and_progress_ai_turns(room_id, db)
            
            # ゲーム状態をブロードキャスト
            room = get_room(db, room_id)
            if room:
                complete_state = get_complete_game_state(db, room_id)
                await sio.emit('complete_game_state', complete_state, room=str(room_id))
                logger.info(f"Broadcasted complete game state for new day in room {room_id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in delayed AI progression for new day in room {room_id}: {e}")

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
            # created_atがnaive datetimeの場合はUTCとして扱う
            created_at_utc = vote_phase_logs.created_at
            if created_at_utc.tzinfo is None:
                created_at_utc = created_at_utc.replace(tzinfo=timezone.utc)
            
            time_since_vote_start = (datetime.now(timezone.utc) - created_at_utc).total_seconds() / 60
            if time_since_vote_start > vote_timeout_minutes:
                logger.warning(f"Vote timeout reached for room {room_id}, forcing progression")
                await force_vote_progression(room_id, room, db)
                return
        
        # 最近の投票活動をチェック（3秒以内の活動は待機）
        if room.last_activity:
            last_activity_utc = room.last_activity
            if last_activity_utc.tzinfo is None:
                last_activity_utc = last_activity_utc.replace(tzinfo=timezone.utc)
            
            if (datetime.now(timezone.utc) - last_activity_utc).total_seconds() < 3:
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
        result = await auto_progress_logic(room_id, db)
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
        
        # 各未投票AIプレイヤーに戦略的投票を実行
        for ai_player in unvoted_ai_players:
            possible_targets = [p for p in alive_players if p.player_id != ai_player.player_id]
            if possible_targets:
                target = strategic_target_selection(ai_player, possible_targets, "vote")
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
            
        # Check if AI player hasn't acted recently (more than 10 seconds ago)
        if room.last_activity and (datetime.now(timezone.utc) - room.last_activity).total_seconds() < 10:
            return  # Recent activity, wait a bit more
            
        logger.info(f"Auto-progressing AI player {current_player.character_name} in room {room_id}")
        
        # Call auto_progress logic (reuse existing function)
        try:
            result = await auto_progress_logic(room_id, db)
            if result.get("auto_progressed"):
                logger.info(f"Successfully auto-progressed room {room_id}: {result.get('message', 'No message')}")
        except Exception as e:
            logger.error(f"Error in auto_progress_logic for room {room_id}: {e}")
            
    except Exception as e:
        logger.error(f"Error checking AI turns for room {room_id}: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on application startup"""
    global game_loop_task, pool_monitor_task, room_cleanup_task
    logger.info("Starting application startup tasks...")
    
    # Start the game loop monitor task
    game_loop_task = asyncio.create_task(game_loop_monitor())
    logger.info("AI game auto-progression monitor started")
    
    # Start the connection pool monitor task
    pool_monitor_task = asyncio.create_task(connection_pool_monitor())
    logger.info("Database connection pool monitor started")
    
    # Start the room cleanup monitor task
    room_cleanup_task = asyncio.create_task(room_cleanup_monitor())
    logger.info("Room cleanup monitor started")

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean up background tasks on application shutdown"""
    global game_loop_task, pool_monitor_task, room_cleanup_task
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
    
    # Cancel room cleanup monitor
    if room_cleanup_task:
        room_cleanup_task.cancel()
        try:
            await room_cleanup_task
        except asyncio.CancelledError:
            logger.info("Room cleanup monitor task cancelled successfully")

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
    # 🔧 バランス調整版役職構成（狂人追加でより戦略的に）
    configs: Dict[int, List[str]] = {
        5: ['werewolf', 'madman', 'seer', 'villager', 'villager'],                # 人狼1+狂人1：村人3（占1+村2）- バランス重視
        6: ['werewolf', 'werewolf', 'madman', 'seer', 'bodyguard', 'villager'],  # 人狼2+狂人1：村人3（占1+護1+村1）
        7: ['werewolf', 'werewolf', 'madman', 'seer', 'bodyguard', 'villager', 'villager'], # 人狼2+狂人1：村人4（占1+護1+村2）
        8: ['werewolf', 'werewolf', 'werewolf', 'madman', 'seer', 'bodyguard', 'villager', 'villager'], # 人狼3+狂人1：村人4（占1+護1+村2）
        9: ['werewolf', 'werewolf', 'werewolf', 'madman', 'seer', 'bodyguard', 'villager', 'villager', 'villager'], # 人狼3+狂人1：村人5（占1+護1+村3）
        10: ['werewolf', 'werewolf', 'werewolf', 'madman', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager'], # 人狼3+狂人1：村人6（占1+護1+村4）
        11: ['werewolf', 'werewolf', 'werewolf', 'werewolf', 'madman', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager'], # 人狼4+狂人1：村人6（占1+護1+村4）
        12: ['werewolf', 'werewolf', 'werewolf', 'werewolf', 'madman', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager', 'villager'] # 人狼4+狂人1：村人7（占1+護1+村5）
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
            # 初期はAIプレイヤー1形式、ペルソナ生成時に名前変更
            ai_character_name = f"AIプレイヤー{i+1}"
            
            ai_player = Player(
                room_id=db_room.room_id,
                character_name=ai_character_name,
                is_human=False,
                character_persona=None,
                is_claimed=False
            )
            db.add(ai_player)
            db.flush()
            
        db.commit()
        db.refresh(db_room)

        # ホストプレイヤーのセッショントークンを生成し、PlayerSessionに保存
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7) # 例: 7日間有効
        player_session = PlayerSession(
            player_id=host_player.player_id,
            session_token=session_token,
            expires_at=expires_at
        )
        db.add(player_session)
        db.commit() # PlayerSessionのコミット

        logger.info(f"Room created successfully: {db_room.room_id} with {room.ai_players} AI players")
        # RoomInfoにsession_tokenを含めるために、RoomInfoを拡張するか、別のレスポンスモデルを定義する必要がある
        # ここでは、RoomInfoの代わりにJoinRoomResponseを返すように変更する
        return JoinRoomResponse(
            player_id=str(host_player.player_id),
            player_name=host_name,
            room_id=str(db_room.room_id),
            session_token=session_token
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating room: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create room: {str(e)}")

def start_game_logic(db: Session, room_id: uuid.UUID) -> Room:
    db_room: Optional[Room] = get_room(db, room_id)
    if not db_room: raise HTTPException(status_code=404, detail="Room not found")
    if db_room.status != 'waiting': raise HTTPException(status_code=400, detail="Game has already started or finished.")
    
    # 🔧 完全なゲームデータリセット処理（ペルソナ保持問題対策）
    logger.info(f"🧹 Starting complete game data reset for room {room_id}")
    
    # 1. 全プレイヤーのゲーム関連データをリセット
    players = db_room.players
    for player in players:
        logger.info(f"🧹 Resetting player data for {player.character_name}")
        player.role = None  # 役職をクリア
        player.is_alive = True  # 生存状態をリセット
        player.is_claimed = False  # カミングアウト状態をリセット
        # 注意: character_persona は保持（プレイヤーが設定したペルソナを維持）
        logger.info(f"🧹 Player {player.character_name} data reset complete")
    
    # 2. 既存のGameLog（発言履歴）を完全削除
    try:
        deleted_logs = db.query(GameLog).filter(GameLog.room_id == room_id).delete()
        logger.info(f"🧹 Deleted {deleted_logs} existing GameLog entries for room {room_id}")
    except Exception as log_error:
        logger.error(f"🧹 Error deleting GameLog entries: {log_error}")
        # 削除に失敗してもゲーム開始は継続
    
    # 3. 部屋状態の完全初期化
    db_room.day_number = 1
    db_room.current_round = 1
    db_room.current_turn_index = 0
    db_room.turn_order = []  # 後で設定される
    db_room.last_activity = datetime.now(timezone.utc)
    
    # 4. リセット処理をデータベースにコミット
    try:
        db.commit()
        logger.info(f"🧹 Game data reset committed to database for room {room_id}")
    except Exception as commit_error:
        logger.error(f"🧹 Error committing game data reset: {commit_error}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reset game data")
    
    logger.info(f"🧹 Complete game data reset finished for room {room_id}")
    
    player_count = len(players)
    if player_count != db_room.total_players:
        raise HTTPException(status_code=400, detail=f"Player count mismatch. Expected {db_room.total_players}, but have {player_count}.")
    
    # ペルソナ設定チェック（推奨）
    players_without_persona = [p for p in players if not p.character_persona]
    if players_without_persona:
        player_names = [p.character_name for p in players_without_persona]
        logger.warning(f"Game starting with players without persona: {player_names}")
        # 警告のみ、ゲーム開始は継続（強制はしない）
    
    roles = get_role_config(player_count)
    random.shuffle(roles)
    
    # ホストを最初のターンにして、他はランダム
    host_player = next((p for p in players if p.is_host), None)
    if host_player:
        other_players = [p for p in players if not p.is_host]
        random.shuffle(other_players)
        player_ids = [host_player.player_id] + [p.player_id for p in other_players]
        logger.info(f"🎯 HOST FIRST TURN: {host_player.character_name} will start the game")
    else:
        player_ids = [p.player_id for p in players]
        random.shuffle(player_ids)
        logger.info("🎯 NO HOST FOUND: Using random turn order")
    
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
            logger.error(f"🚫 発言拒否: ゲームステータス '{db_room.status}' は議論フェーズではありません")
            raise HTTPException(status_code=400, detail=f"Not in discussion phase. Current status: {db_room.status}")

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
            logger.error(f"🚫 ターン違反: プレイヤー {player_id} は現在のターンではありません。現在のターン: {current_name} (index: {current_index})")
            raise HTTPException(status_code=403, detail=f"It's not your turn. Current turn: {current_name} (index: {current_index})")

        # 🚫 強化された重複発言防止システム
        player = get_player(db, player_id)
        if not player:
            logger.error(f"🚫 プレイヤー不存在: プレイヤーID {player_id} が見つかりません")
            raise HTTPException(status_code=404, detail="Player not found")
        
        # デバッグ用：現在のゲーム状態を詳細にログ出力
        logger.info(f"🎯 発言開始: プレイヤー {player.character_name} (ID: {player_id})")
        logger.info(f"🎯 ゲーム状態: status={db_room.status}, day={db_room.day_number}, round={db_room.current_round}")
        logger.info(f"🎯 ターン状態: current_index={current_index}, turn_order={turn_order}")
        logger.info(f"🎯 現在のターン: {turn_order[current_index] if current_index < len(turn_order) else 'INVALID'}")
        
        # 🔧 正しい発言制限チェック - 現在ラウンドで1回まで発言
        # 今日のこのプレイヤーの全発言を取得
        player_day_speeches = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.phase == "day_discussion",
            GameLog.event_type == "speech",
            GameLog.day_number == db_room.day_number,
            GameLog.actor_player_id == player_id
        ).all()
        
        current_round = db_room.current_round or 1
        player_total_speeches = len(player_day_speeches)
        
        # 🔧 修正: 現在のラウンドでの発言制限チェック
        # このプレイヤーの現在ラウンドでの発言回数を計算
        
        # 全プレイヤーの今日の発言を時系列で取得
        all_today_speeches = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.phase == "day_discussion",
            GameLog.event_type == "speech",
            GameLog.day_number == db_room.day_number
        ).order_by(GameLog.created_at).all()
        
        # 生存プレイヤー数を取得
        alive_players = [p for p in db_room.players if p.is_alive]
        alive_count = len(alive_players)
        
        # このプレイヤーの発言一覧を取得
        player_speeches = [s for s in all_today_speeches if s.actor_player_id == player_id]
        
        # 発言制限を大幅緩和: ゲーム進行を優先（制限チェックを無効化）
        # 旧制限: 1日1人一回 → 新制限: 制限なし（ゲーム安定性優先）
        logger.info(f"✅ 発言許可: {player.character_name} (累計発言回数: {len(player_speeches)}回) - 制限緩和により許可")
        
        # 2. AI連続発言防止は削除（LLMの発言生成速度に依存させる）
        
        # 3. ログ詳細記録（デバッグ用）
        logger.info(f"✅ 発言許可: {player.character_name} (ラウンド{current_round}, 累計発言回数: {len(player_speeches)})")

        # 発言を記録
        create_game_log(db, room_id, "day_discussion", "speech", actor_player_id=player_id, content=statement)
        
        # 自動サマリー更新
        try:
            update_game_summary_auto(db, room_id)
            logger.info(f"Auto-summary updated for room {room_id} after speech")
        except Exception as e:
            logger.warning(f"Failed to update auto-summary for room {room_id}: {e}")
            # サマリー更新失敗はゲーム進行を止めない
        
        # 制限緩和：シンプルなターン進行（次の生存プレイヤーに移行）
        next_index = find_next_alive_player_safe(db, room_id, current_index)
        
        # 🔍 ターン進行デバッグログ
        logger.info(f"🎯 TURN PROGRESSION: room_id={room_id}, from_index={current_index} to_index={next_index}")
        if next_index < len(turn_order):
            next_player = get_player(db, uuid.UUID(turn_order[next_index]))
            logger.info(f"🎯 NEXT PLAYER: {next_player.character_name if next_player else 'Unknown'} (is_human={next_player.is_human if next_player else 'Unknown'})")
        
        # ターン進行
        db_room.current_turn_index = next_index
        
        # 🔧 根本的な修正: ラウンド別発言管理システム
        alive_count = sum(1 for pid in turn_order 
                         if get_player(db, uuid.UUID(pid)) and get_player(db, uuid.UUID(pid)).is_alive)
        
        # 生存プレイヤー一覧を取得
        alive_player_ids = set()
        for pid in turn_order:
            player = get_player(db, uuid.UUID(pid))
            if player and player.is_alive:
                alive_player_ids.add(pid)
        
        # 🔧 重複コード削除済み - 上記のシンプルな発言チェックを使用
        
        # 🔧 正確なラウンド完了判定
        # 現在の日の全発言を取得
        all_day_speeches = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.phase == "day_discussion",
            GameLog.event_type == "speech",
            GameLog.day_number == db_room.day_number
        ).all()
        
        # 各プレイヤーの発言回数をカウント
        player_speech_counts = {}
        for speech in all_day_speeches:
            if speech.actor_player_id:
                player_id_str = str(speech.actor_player_id)
                player_speech_counts[player_id_str] = player_speech_counts.get(player_id_str, 0) + 1
        
        # 制限緩和：ラウンド別発言管理に復帰
        current_round_speakers = set()
        for player_id_str in alive_player_ids:
            speech_count = player_speech_counts.get(player_id_str, 0)
            # 現在のラウンドで発言済みのプレイヤーをカウント
            if speech_count >= current_round:
                current_round_speakers.add(player_id_str)
        
        round_completed = len(current_round_speakers) >= len(alive_player_ids)
        
        logger.info(f"🎯 ROUND STATUS: round={db_room.current_round}, current_speakers={len(current_round_speakers)}, "
                   f"alive_players={len(alive_player_ids)}, completed={round_completed}")
        logger.info(f"🎯 SPEECH COUNTS: {[(get_player(db, uuid.UUID(pid)).character_name, player_speech_counts.get(pid, 0)) for pid in alive_player_ids if get_player(db, uuid.UUID(pid))]}")
        logger.info(f"🎯 CURRENT ROUND SPEAKERS: {[get_player(db, uuid.UUID(pid)).character_name for pid in current_round_speakers if get_player(db, uuid.UUID(pid))]}")
        
        # ラウンド完了チェック：全ての生存プレイヤーが発言した場合
        if round_completed:
            logger.info(f"✅ Round {db_room.current_round} completed. All {len(alive_player_ids)} alive players spoke.")
            
            # 3ラウンド完了で投票フェーズへ移行
            if db_room.current_round >= 3:
                db_room.status = "day_vote"
                db_room.current_turn_index = 0
                create_game_log(db, room_id, "day_discussion", "phase_transition", 
                              content=f"議論終了（{db_room.current_round}ラウンド完了）。投票フェーズに移行します。")
                logger.info(f"🗳️ Discussion phase completed after {db_room.current_round} rounds. Moving to voting phase.")
            else:
                # 次のラウンドに進む
                db_room.current_round += 1
                # ターンオーダーを最初の生存プレイヤーにリセット
                first_alive_index = None
                for i, pid in enumerate(turn_order):
                    player = get_player(db, uuid.UUID(pid))
                    if player and player.is_alive:
                        first_alive_index = i
                        break
                
                if first_alive_index is not None:
                    db_room.current_turn_index = first_alive_index
                    first_player = get_player(db, uuid.UUID(turn_order[first_alive_index]))
                    logger.info(f"🔄 Round {db_room.current_round} started - first player: {first_player.character_name} (index={first_alive_index})")
                else:
                    logger.error(f"⚠️ No alive players found for round {db_room.current_round}")
                    db_room.current_turn_index = 0
                
                # 重複防止：同じラウンドのround_startメッセージが既に存在するかチェック
                existing_round_start = db.query(GameLog).filter(
                    GameLog.room_id == room_id,
                    GameLog.day_number == db_room.day_number,
                    GameLog.event_type == "round_start",
                    GameLog.content.like(f"%ラウンド{db_room.current_round}が開始%")
                ).first()
                
                if not existing_round_start:
                    create_game_log(db, room_id, "day_discussion", "round_start", 
                                  content=f"ラウンド{db_room.current_round}が開始されました。")
                    logger.info(f"✅ Round {db_room.current_round} start message created")
                else:
                    logger.info(f"⚠️ Round {db_room.current_round} start message already exists, skipping duplicate")
        
        # 最終活動時間を更新（自動クローズ用）
        db_room.last_activity = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(db_room)
        
        logger.info(f"🎯 TURN PROGRESSION: {current_index} -> {next_index}, status: {db_room.status}, round: {db_room.current_round}")
        
        # 🔧 ターン進行の安全性チェックとログ出力の改善
        if db_room.status == 'day_discussion' and next_index < len(turn_order):
            next_player_id = turn_order[next_index]
            next_player = get_player(db, uuid.UUID(next_player_id))
            if next_player and next_player.is_alive:
                logger.info(f"🎯 TURN ADVANCED TO: {next_player.character_name} (index={next_index}, is_human={next_player.is_human})")
                if not next_player.is_human:
                    logger.info(f"Next player is AI ({next_player.character_name}), auto-progression monitor will handle")
            else:
                logger.warning(f"⚠️ Invalid next player at index {next_index}: player_id={next_player_id}")
        
        return db_room
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in speak_logic: {e}")
        raise


def find_next_alive_player_safe(db: Session, room_id: uuid.UUID, current_index: int) -> int:
    """安全な次のプレイヤー検索（無限ループ対策・改善版）"""
    room = get_room(db, room_id)
    if not room or not room.turn_order:
        logger.warning(f"Room or turn_order not found for room {room_id}")
        return current_index
        
    turn_order = room.turn_order
    max_attempts = len(turn_order)
    
    # 🔧 改善: より安全なインデックス検索
    for attempt in range(1, max_attempts + 1):
        next_index = (current_index + attempt) % len(turn_order)
        
        if next_index >= len(turn_order):
            logger.warning(f"Index out of bounds: {next_index} >= {len(turn_order)}")
            continue
            
        player_id = turn_order[next_index]
        try:
            player = get_player(db, uuid.UUID(player_id))
            if player and player.is_alive:
                logger.info(f"🎯 Next alive player found: {player.character_name} at index {next_index}")
                return next_index
        except Exception as e:
            logger.error(f"Error getting player {player_id}: {e}")
            continue
    
    # 全員死亡の場合は現在のインデックスを返す
    logger.warning(f"No alive players found in room {room_id}, staying at current index {current_index}")
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
    """アクティブな部屋のみを取得（古い部屋の非表示対応）"""
    # 1時間以内に活動があった部屋、または待機中の部屋のみ表示
    active_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
    
    return db.query(Room).filter(
        Room.is_private == False,
        # 待機中の部屋は常に表示、それ以外は1時間以内の活動があるもののみ表示
        (Room.status == 'waiting') | (Room.last_activity >= active_threshold)
    ).order_by(Room.created_at.desc()).offset(skip).limit(limit).all()

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
    """【修正版】レースコンディション対応投票処理ロジック"""
    try:
        # 🔒 データベースロックでレースコンディション防止
        db_room = db.query(Room).filter(Room.room_id == room_id).with_for_update().first()
        if not db_room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        if db_room.status != 'day_vote':
            # 議論フェーズの場合は自動的に投票フェーズに移行
            if db_room.status == 'day_discussion':
                logger.info(f"Auto-transitioning room {room_id} from day_discussion to day_vote")
                db_room.status = 'day_vote'
                create_game_log(db, room_id, "phase_transition", "day_vote", content="投票フェーズに移行します。")
                db.commit()
            else:
                raise HTTPException(status_code=400, detail=f"Not in voting phase (current: {db_room.status})")

        target_player = get_player(db, target_id)
        if not target_player:
            raise HTTPException(status_code=404, detail="Target player not found")
        
        # 投票者と対象者が生存していることを確認
        voter_player = get_player(db, voter_id)
        if not voter_player or not voter_player.is_alive:
            raise HTTPException(status_code=400, detail="Voter is not alive")
        if not target_player.is_alive:
            raise HTTPException(status_code=400, detail="Target player is not alive")

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
                    # 同票の場合：再投票処理
                    tied_vote = True
                    
                    # 現在の投票ラウンド数を確認（初期値は1）
                    current_vote_round = getattr(db_room, 'vote_round', 1)
                    
                    if current_vote_round < 2:  # 最大2ラウンドまで再投票
                        # 再投票実施
                        db_room.vote_round = current_vote_round + 1
                        
                        # 既存の投票ログを削除して再投票を可能にする
                        db.query(GameLog).filter(
                            GameLog.room_id == room_id,
                            GameLog.day_number == db_room.day_number,
                            GameLog.phase == "day_vote",
                            GameLog.event_type == "vote"
                        ).delete()
                        
                        message = f"同票のため再投票を行います（{current_vote_round + 1}回目の投票）。"
                        create_game_log(db, room_id, "day_vote", "revote_start", 
                                      content=f"同票により{current_vote_round + 1}回目の投票を開始します。最多票者：{', '.join(most_voted_names)}")
                        
                        db.commit()
                        
                        # 再投票のためVoteResultを返す（投票継続）
                        return VoteResult(
                            message=message,
                            vote_counts={name: count for name, count in vote_counts.items()},
                            voted_out_player_id=None,
                            tied_vote=True,
                            is_revote=True  # 再投票フラグ
                        )
                    else:
                        # 2回目でも同票の場合は処刑なし
                        message = "2回目の投票でも同票のため、誰も追放されませんでした。"
                        create_game_log(db, room_id, "day_vote", "execution", content="Final tied vote. No one was voted out.")
            else:
                # 投票なし
                message = "投票がありませんでした。"

            # 夜フェーズへ移行（再投票でない場合のみ）
            db_room.status = 'night'
            db_room.vote_round = 1  # 投票ラウンドをリセット
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

async def check_night_actions_completion(db: Session, room_id: uuid.UUID) -> bool:
    """夜のアクションが完了したかチェックし、必要に応じて朝フェーズに移行"""
    try:
        db_room = db.query(Room).filter(Room.room_id == room_id).first()
        if not db_room or db_room.status != 'night':
            return False
        
        # 生きている特殊役職プレイヤーを取得
        alive_seers = db.query(Player).filter(
            Player.room_id == room_id,
            Player.role == 'seer',
            Player.is_alive == True
        ).all()
        
        alive_bodyguards = db.query(Player).filter(
            Player.room_id == room_id,
            Player.role == 'bodyguard',
            Player.is_alive == True
        ).all()
        
        alive_werewolves = db.query(Player).filter(
            Player.room_id == room_id,
            Player.role == 'werewolf',
            Player.is_alive == True
        ).all()
        
        # 今夜の占い・護衛・攻撃アクションが実行済みかチェック
        night_logs = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == db_room.day_number,
            GameLog.phase == "night"
        ).all()
        
        # 占い師のアクション完了チェック
        seer_completed = True
        if alive_seers:
            seer_actions = [log for log in night_logs if log.event_type == "investigate"]
            seer_completed = len(seer_actions) >= len(alive_seers)
        
        # ボディガードのアクション完了チェック
        bodyguard_completed = True
        if alive_bodyguards:
            bodyguard_actions = [log for log in night_logs if log.event_type == "protect"]
            bodyguard_completed = len(bodyguard_actions) >= len(alive_bodyguards)
        
        # 人狼の攻撃対象選択完了チェック
        werewolf_completed = True
        if alive_werewolves:
            # 人狼は全体で1つの攻撃対象を選択すればよい
            werewolf_actions = [log for log in night_logs if log.event_type == "attack_target"]
            werewolf_completed = len(werewolf_actions) >= 1
        
        logger.info(f"Night actions check for room {room_id}: seers={len(alive_seers)}, seer_completed={seer_completed}, bodyguards={len(alive_bodyguards)}, bodyguard_completed={bodyguard_completed}, werewolves={len(alive_werewolves)}, werewolf_completed={werewolf_completed}")
        
        # すべてのアクションが完了している場合、朝フェーズに移行
        if seer_completed and bodyguard_completed and werewolf_completed:
            logger.info(f"All night actions completed for room {room_id}, transitioning to day")
            # 夜のアクションを処理して朝フェーズに移行
            results = process_night_actions(db, room_id)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking night actions completion: {e}")
        return False

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
        # 手動で選択された攻撃対象をチェック
        attack_target_log = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == db_room.day_number,
            GameLog.phase == "night",
            GameLog.event_type == "attack_target"
        ).first()
        
        target = None
        if attack_target_log:
            # 手動選択された対象を取得
            target_name = attack_target_log.content.split("targeted ")[1].split(" for attack")[0]
            target = next((p for p in villagers if p.character_name == target_name), None)
        
        if not target:
            # 手動選択がない場合は自動選択（AIプレイヤー用）
            # 優先順位: 1) 占い師 2) ボディガード 3) 村人
            seers = [p for p in villagers if p.role == 'seer']
            bodyguards = [p for p in villagers if p.role == 'bodyguard']
            normal_villagers = [p for p in villagers if p.role == 'villager']
            
            if seers:
                target = seers[0]  # 占い師を最優先狙い
            elif bodyguards:
                target = bodyguards[0]  # ボディガードを次点狙い
            else:
                # 戦略的な村人選択（ランダムの代わりに戦略的フォールバック）
                target = strategic_target_selection(werewolves[0], normal_villagers, "attack")
        
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
    
    # ボディガードの守り（知性的判断）
    bodyguards = [p for p in db_room.players if p.role == 'bodyguard' and p.is_alive]
    if bodyguards:
        bodyguard = bodyguards[0]
        alive_players = [p for p in db_room.players if p.is_alive and p.player_id != bodyguard.player_id]
        if alive_players:
            # 知性的な護衛対象選択
            # 優先順位: 1) 占い師 2) 村人 3) 自分以外のボディガード
            protection_candidates = []
            seers_to_protect = [p for p in alive_players if p.role == 'seer']
            villagers_to_protect = [p for p in alive_players if p.role == 'villager']
            other_bodyguards = [p for p in alive_players if p.role == 'bodyguard']
            
            if seers_to_protect:
                protected = seers_to_protect[0]  # 占い師を最優先護衛
            elif villagers_to_protect:
                protected = strategic_target_selection(bodyguard, villagers_to_protect, "protect")  # 村人を戦略的護衛
            elif other_bodyguards:
                protected = other_bodyguards[0]  # 他のボディガードを護衛
            else:
                protected = strategic_target_selection(bodyguard, alive_players, "protect")  # 戦略的最終選択
            # 🔒 秘匿情報: ボディガードの護衛は一般ログに表示されない
            create_game_log(db, room_id, "night", "protection_secret", 
                          actor_player_id=bodyguard.player_id,
                          content=f"PRIVATE: {bodyguard.character_name} protected {protected.character_name}")
            # 結果には含めない（秘匿情報）
            logger.info(f"🔒 秘匿護衛実行: {bodyguard.character_name} -> {protected.character_name}")
    
    # 占い師の占い（手動システムに移行済み）
    # 占い師は専用エンドポイント /api/rooms/{room_id}/seer_investigate を使用
    seers = [p for p in db_room.players if p.role == 'seer' and p.is_alive]
    if seers:
        results['seer_status'] = f"{seers[0].character_name}による占いを待機中（手動実行）"
    
    # 🔧 確実にデータベースに保存
    db.commit()
    
    # ゲーム終了条件をチェック
    game_end_result = check_game_end_condition(db, room_id)
    if game_end_result['game_over']:
        db_room.status = 'finished'
        results.update(game_end_result)
        logger.info(f"Game ended: {game_end_result}")
    else:
        # 次の日に進む
        db_room.day_number += 1
        db_room.status = 'day_discussion'
        db_room.current_round = 1
        
        # 生存者でターン順序を再構築（相対順序を保持）
        living_players = [p for p in db_room.players if p.is_alive]
        
        logger.info(f"Night actions completed. Moving to Day {db_room.day_number}, {len(living_players)} players alive")
        
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
        
        # 生存プレイヤーが存在する場合のみ、正しいターンインデックスを設定
        if living_players:
            db_room.current_turn_index = 0  # 生存プレイヤーの最初
            logger.info(f"New day started: Day {db_room.day_number}, first player: {living_players[0].character_name}")
            
            # Day開始後のAI発言をスケジュール（3秒後）
            import asyncio
            first_player = living_players[0]
            if not first_player.is_human:
                logger.info(f"Scheduling AI progression for Day {db_room.day_number} start")
                # 非同期でAI発言をスケジュール
                asyncio.create_task(delayed_ai_progression_new_day(room_id, 3.0))
        else:
            db_room.current_turn_index = None
            logger.error(f"No living players found when starting Day {db_room.day_number}")
    
    db.commit()
    return results

def check_game_end_condition(db: Session, room_id: uuid.UUID) -> Dict[str, Any]:
    """ゲーム終了条件をチェック（狂人含む）"""
    db_room = get_room(db, room_id)
    if not db_room:
        return {'game_over': False}
    
    living_players = [p for p in db_room.players if p.is_alive]
    living_werewolves = [p for p in living_players if p.role == 'werewolf']
    living_madmen = [p for p in living_players if p.role == 'madman']
    living_villagers = [p for p in living_players if p.role in ['villager', 'seer', 'bodyguard']]
    
    # 人狼陣営：人狼 + 狂人
    living_werewolf_team = living_werewolves + living_madmen
    
    if len(living_werewolves) == 0:
        # 村人陣営の勝利（人狼が全滅）
        create_game_log(db, room_id, db_room.status, "game_end", content="村人陣営の勝利！全ての人狼が排除されました。")
        return {
            'game_over': True,
            'winner': 'villagers',
            'winner_faction': '村人陣営',
            'victory_message': '村人陣営の勝利！全ての人狼が排除されました。'
        }
    elif len(living_werewolf_team) >= len(living_villagers):
        # 人狼陣営の勝利（人狼+狂人の数が村人と同数以上）
        create_game_log(db, room_id, db_room.status, "game_end", content="人狼陣営の勝利！人狼陣営の数が村人陣営と同数以上になりました。")
        return {
            'game_over': True,
            'winner': 'werewolves',
            'winner_faction': '人狼陣営',
            'victory_message': '人狼陣営の勝利！人狼陣営の数が村人陣営と同数以上になりました。'
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
            if basic_result['winner'] == 'werewolves' and player.role in ['werewolf', 'madman']:
                is_winner = True
            elif basic_result['winner'] == 'villagers' and player.role in ['villager', 'seer', 'bodyguard']:
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

async def get_ai_speech_context(room_id: uuid.UUID, ai_player_id: uuid.UUID, day_number: int, db: Session) -> list:
    """　AI発言コンテキストを安全に取得　"""
    try:
        # 🔍 詳細なデバッグログ
        logger.info(f"🔍 get_ai_speech_context called:")
        logger.info(f"🔍 - room_id: {room_id}")
        logger.info(f"🔍 - ai_player_id: {ai_player_id}")
        logger.info(f"🔍 - day_number: {day_number}")
        
        # このAIプレイヤーの今日の発言回数をチェック
        ai_speech_count = db.query(GameLog).filter(
            GameLog.room_id == room_id,
            GameLog.day_number == day_number,
            GameLog.event_type == "speech",
            GameLog.actor_player_id == ai_player_id
        ).count()
        
        logger.info(f"🔍 AI speech count check: player={ai_player_id}, day={day_number}, count={ai_speech_count}")
        
        # 初回発言の場合は空のコンテキストを返す（1日目のみ）
        if ai_speech_count == 0 and day_number == 1:
            logger.info(f"🔍 First speech of Day 1 detected for AI {ai_player_id} - returning empty context")
            return []
        
        # 🔧 修正: 2日目以降の初回発言でも現在の日の情報のみを提供
        # 存在しない前日情報を参照させないため、現在の状況に集中させる
        if ai_speech_count == 0:
            logger.info(f"🔍 First speech of Day {day_number} detected for AI {ai_player_id} - providing current day context only")
            
            # 現在の日の状況のみを提供（混乱を避けるため）
            current_day_info = []
            if day_number > 1:
                # 2日目以降は一般的な朝の挨拶コンテキストのみ
                current_day_info.append({
                    'speaker': 'システム',
                    'content': f"{day_number}日目の議論が始まりました。",
                    'timestamp': datetime.now(timezone.utc)
                })
                logger.info(f"🔍 Added system message for day {day_number}")
            
            return current_day_info
        
        # 既に発言済みの場合は既存の発言履歴を取得
        logger.info(f"🔍 Fetching speech logs for room {room_id}, day {day_number}")
        try:
            recent_logs = db.query(GameLog).filter(
                GameLog.room_id == room_id,
                GameLog.day_number == day_number,
                GameLog.event_type == "speech"
            ).order_by(GameLog.created_at.asc()).all()
        except Exception as db_error:
            logger.error(f"❌ Database error in get_ai_speech_context: {db_error}")
            # データベースエラーの場合は最小限のコンテキストを返す
            return [{
                'speaker': 'システム',
                'content': f"{day_number}日目の議論が続いています。",
                'timestamp': datetime.now(timezone.utc)
            }]
        
        logger.info(f"🔍 Found {len(recent_logs)} speech logs")
        
        recent_messages = []
        for i, log in enumerate(recent_logs):
            logger.info(f"🔍 Processing log {i+1}: actor_id={log.actor_player_id}, content_preview={log.content[:50] if log.content else 'None'}...")
            try:
                if log.actor:
                    recent_messages.append({
                        'speaker': log.actor.character_name,
                        'content': log.content or '',
                        'timestamp': log.created_at
                    })
                    logger.info(f"🔍 Added message from {log.actor.character_name}")
                elif log.actor_player_id:
                    # actorがNullだが、actor_player_idが存在する場合は直接データベースから取得を試みる
                    try:
                        player = get_player(db, log.actor_player_id)
                        if player:
                            recent_messages.append({
                                'speaker': player.character_name,
                                'content': log.content or '',
                                'timestamp': log.created_at
                            })
                            logger.info(f"🔍 Added message from {player.character_name} (recovered from actor_player_id)")
                        else:
                            logger.warning(f"🔍 Could not find player for actor_player_id: {log.actor_player_id}")
                    except Exception as player_error:
                        logger.error(f"🔍 Error recovering player from actor_player_id {log.actor_player_id}: {player_error}")
                else:
                    logger.warning(f"🔍 Log {i+1} has no actor or actor_player_id: log_id={log.log_id}")
            except Exception as log_error:
                logger.error(f"🔍 Error processing log {i+1}: {log_error}")
                continue
        
        logger.info(f"🔍 Speech context prepared: {len(recent_messages)} messages for AI {ai_player_id}")
        return recent_messages
        
    except Exception as e:
        logger.error(f"🔍 Error getting AI speech context: {e}")
        import traceback
        logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
        # エラー時は安全に空のコンテキストを返す
        return []

async def broadcast_complete_game_state(room_id: uuid.UUID, db: Session):
    """　完全なゲーム状態を全プレイヤーに通知　"""
    try:
        room = get_room(db, room_id)
        if not room:
            logger.error(f"Room not found for broadcast: {room_id}")
            return
            
        # 完全なゲーム状態を構築
        complete_state = {
            'event_type': 'complete_game_state',
            'room_id': str(room_id),
            'current_turn_index': room.current_turn_index,
            'turn_order': room.turn_order or [],
            'status': room.status,
            'day_number': room.day_number,
            'players': [{
                'player_id': str(p.player_id),
                'character_name': p.character_name,
                'is_alive': p.is_alive,
                'is_human': p.is_human
            } for p in room.players],
            'timestamp': datetime.now().isoformat()
        }
        
        # ターン情報の検証とログ
        if room.turn_order and room.current_turn_index is not None:
            if 0 <= room.current_turn_index < len(room.turn_order):
                current_player_id = room.turn_order[room.current_turn_index]
                logger.info(f"Broadcasting turn state: index={room.current_turn_index}, player={current_player_id}")
            else:
                logger.warning(f"Invalid turn index: {room.current_turn_index} for turn_order length {len(room.turn_order)}")
        
        # 全プレイヤーに状態を通知
        await sio.emit('complete_game_state', complete_state, room=str(room_id))
        logger.debug(f"Complete game state broadcasted for room {room_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting complete game state: {e}", exc_info=True)

def generate_safe_fallback_speech(ai_player, room) -> str:
    """AIプレイヤーのペルソナに基づいた安全なフォールバック発言を生成"""
    try:
        # ペルソナ情報を取得
        persona = ai_player.character_persona
        role = ai_player.role
        
        # ペルソナの口調情報を取得
        speech_style = ""
        if persona and hasattr(persona, 'speech_style'):
            speech_style = persona.speech_style or ""
        
        # 役職と状況に応じたベース発言を生成
        if role == 'werewolf':
            base_speeches = [
                "慎重に状況を見極めたいと思います。",
                "皆さんの意見を聞かせてください。",
                "もう少し情報を整理してから判断しましょう。"
            ]
        elif role == 'seer':
            base_speeches = [
                "現在の情報をもとに判断したいと思います。",
                "しっかりと観察して考察します。",
                "真実を見極めるために慎重に行動します。"
            ]
        elif role == 'bodyguard':
            base_speeches = [
                "みんなを守るために注意深く見ています。",
                "状況をよく観察して判断します。",
                "安全を最優先に考えて行動します。"
            ]
        else:  # villager
            base_speeches = [
                "情報を整理して冷静に判断します。",
                "皆で協力して真実を見つけましょう。",
                "疑わしい点があれば教えてください。"
            ]
        
        # ペルソナ情報をLLMが自動的に反映できるよう、基本発言をそのまま使用
        # 口調変換はLLMに委ねる（より自然で一貫性のある発言が期待できる）
        selected_speech = random.choice(base_speeches)
        
        return selected_speech
        
    except Exception as e:
        # 最終フォールバック
        logger.error(f"Safe fallback speech generation failed: {e}")
        return "状況を確認しています。"

async def generate_ai_speech(db: Session, room_id: uuid.UUID, ai_player_id: uuid.UUID, emergency_skip: bool = False) -> str:
    """AIプレイヤーの発言を生成（AIエージェント使用・緊急スキップ対応）"""
    global root_agent
    
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
        
        # 🔍 詳細デバッグ: AI発言システム状態診断
        logger.info(f"=== AI SPEECH SYSTEM DIAGNOSIS ===")
        logger.info(f"Player: {ai_player.character_name}")
        logger.info(f"Player persona type: {type(ai_player.character_persona)}")
        logger.info(f"Player persona content: {ai_player.character_persona}")
        logger.info(f"Room status: {room.status}, Day: {room.day_number}")
        
        # 🔍 root_agent状態の詳細チェック
        logger.info(f"🤖 root_agent diagnosis:")
        logger.info(f"🤖 - root_agent exists: {root_agent is not None}")
        logger.info(f"🤖 - root_agent type: {type(root_agent) if root_agent else 'None'}")
        if root_agent:
            logger.info(f"🤖 - model available: {getattr(root_agent, 'model', None) is not None}")
            logger.info(f"🤖 - tools_available: {getattr(root_agent, 'tools_available', 'Unknown')}")
            logger.info(f"🤖 - fallback_mode: {getattr(root_agent, 'fallback_mode', 'Unknown')}")
        
        # 🔍 環境変数チェック
        logger.info(f"🌐 Environment variables:")
        logger.info(f"🌐 - GOOGLE_PROJECT_ID: '{GOOGLE_PROJECT_ID}' (length: {len(GOOGLE_PROJECT_ID) if GOOGLE_PROJECT_ID else 0})")
        logger.info(f"🌐 - GOOGLE_LOCATION: '{GOOGLE_LOCATION}' (length: {len(GOOGLE_LOCATION) if GOOGLE_LOCATION else 0})")
        
        # AIエージェントシステムを使用した発言生成
        logger.info(f"🚀 AI agent system selection logic: root_agent={root_agent is not None}, PROJECT_ID_OK={bool(GOOGLE_PROJECT_ID)}, LOCATION_OK={bool(GOOGLE_LOCATION)}")
        
        # 🔧 root_agentの再初期化処理（発言失敗対策）
        if (not root_agent or getattr(root_agent, 'fallback_mode', True)) and GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
            logger.warning("⚠️ root_agent is None or in fallback mode, attempting re-initialization...")
            try:
                from npc_agent.agent import RootAgent
                new_root_agent = RootAgent()
                if new_root_agent and not getattr(new_root_agent, 'fallback_mode', True):
                    root_agent = new_root_agent
                    logger.info("✅ root_agent successfully re-initialized")
                else:
                    logger.warning("⚠️ New root_agent is also in fallback mode")
            except Exception as reinit_error:
                logger.error(f"❌ Failed to re-initialize root_agent: {reinit_error}")
                # root_agent = None  # 既存のエージェントを保持してフォールバックモードで続行
        
        # 高度なAIエージェントシステムが利用可能な場合
        if root_agent and GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
            logger.info("✅ Using advanced AI agent system with Function Calling")
            logger.info(f"✅ Root agent type: {type(root_agent)}")
            logger.info(f"✅ Root agent fallback mode: {getattr(root_agent, 'fallback_mode', 'Unknown')}")
            logger.info(f"✅ Root agent tools available: {getattr(root_agent, 'tools_available', 'Unknown')}")
            # プレイヤー情報を準備（ペルソナ未設定の場合はデフォルト）
            persona = ai_player.character_persona
            
            # 🔍 ペルソナ情報の詳細ログ出力（デバッグ用）
            logger.info(f"🎭 PERSONA DEBUG for {ai_player.character_name}:")
            logger.info(f"🎭 - Raw persona type: {type(persona)}")
            logger.info(f"🎭 - Raw persona content: {persona}")
            logger.info(f"🎭 - Player role: {ai_player.role}")
            logger.info(f"🎭 - Player is_alive: {ai_player.is_alive}")
            
            if not persona:
                persona = f"私は{ai_player.character_name}です。冷静に分析して判断します。"
                logger.info(f"🎭 - Using default persona: {persona}")
            else:
                logger.info(f"🎭 - Using stored persona")
                
            player_info = {
                'name': ai_player.character_name,
                'role': ai_player.role,
                'is_alive': ai_player.is_alive,
                'persona': persona
            }
            
            # 🔍 player_info確認ログ
            logger.info(f"🎭 Final player_info: {player_info}")
            
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
            
            # AI発言コンテキストの完全管理
            recent_messages = await get_ai_speech_context(room_id, ai_player.player_id, room.day_number, db)
            logger.info(f"AI speech context prepared for {ai_player.character_name}: {len(recent_messages)} messages")
            
            # 🔍 コンテキストメッセージの詳細ログ（デバッグ用）
            logger.info(f"🗨️ CONTEXT DEBUG for {ai_player.character_name}:")
            for i, msg in enumerate(recent_messages):
                logger.info(f"🗨️ Message {i+1}: Speaker={msg.get('speaker', 'Unknown')}, Content={msg.get('content', '')[:100]}...")
                logger.info(f"🗨️ Message {i+1} timestamp: {msg.get('timestamp', 'Unknown')}")
            if not recent_messages:
                logger.info(f"🗨️ No recent messages found for context")
            
            # AI発言生成前のデバッグ情報
            logger.info(f"=== AI SPEECH GENERATION START ===")
            logger.info(f"Player: {ai_player.character_name}")
            logger.info(f"Day: {room.day_number}, First speech: {len(recent_messages) == 0}")
            logger.info(f"Player info: {player_info}")
            logger.info(f"Game context: {game_context}")
            logger.info(f"Recent messages count: {len(recent_messages)}")
            
            # 高度なAIエージェントで発言を生成
            
            try:
                logger.info("🚀 Calling advanced AI agent system...")
                logger.info(f"🚀 Player info being passed: {player_info}")
                logger.info(f"🚀 Game context being passed: {game_context}")
                logger.info(f"🚀 Recent messages count: {len(recent_messages)}")
                
                # 🔧 タイムアウト調整とエラーハンドリング強化
                import asyncio
                speech = await asyncio.wait_for(
                    asyncio.create_task(asyncio.to_thread(
                        root_agent.generate_speech, player_info, game_context, recent_messages
                    )), 
                    timeout=15.0  # 15秒に短縮（迅速なフォールバック）
                )
                logger.info(f"✅ AI agent system response: {speech}")
                logger.info(f"📏 Speech length: {len(speech) if speech else 0} characters")
                logger.info(f"✅ AI agent system SUCCESS - using Function Calling tools")
                    
            except Exception as agent_error:
                logger.error(f"❌ Error in AI agent system: {agent_error}", exc_info=True)
                logger.error(f"Error type: {type(agent_error)}")
                logger.error(f"Error args: {agent_error.args}")
                
                # より詳細なエラー情報をログ出力
                logger.error(f"Room ID: {room_id}, Player ID: {ai_player_id}")
                logger.error(f"Player name: {ai_player.character_name if ai_player else 'None'}")
                logger.error(f"Game phase: {room.status if room else 'None'}")
                
                # エラータイプに応じた詳細処理とroot_agentリセット
                if "timeout" in str(agent_error).lower():
                    logger.error("⏰ AI agent system timed out")
                    # タイムアウト時はroot_agentをリセット
                    root_agent = None
                elif "quota" in str(agent_error).lower() or "rate" in str(agent_error).lower():
                    logger.error("🚫 AI service quota/rate limit exceeded")
                    # クォータ制限時は短時間待機後にリセット
                    root_agent = None
                elif "connection" in str(agent_error).lower():
                    logger.error("🌐 AI service connection error")
                    # 接続エラー時はroot_agentをリセット
                    root_agent = None
                else:
                    logger.error("🔧 Other AI agent system error")
                
                # 🔧 確実なフォールバック：即座に安全な発言を返す
                logger.info("🔄 Using immediate safe fallback due to AI agent system failure")
                
                # ペルソナに基づいた適切なフォールバック発言を生成
                logger.info(f"🔄 Generating safe fallback speech for {ai_player.character_name}")
                speech = generate_safe_fallback_speech(ai_player, room)
            
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
            
        elif GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
            # root_agentが無効だが、Vertex AIは利用可能
            logger.warning("⚠️ Advanced AI agent system unavailable, using direct Vertex AI fallback")
            
            persona = ai_player.character_persona
            if not persona:
                persona = f"私は{ai_player.character_name}です。冷静に分析して判断します。"
            
            # 最近の会話を取得
            recent_logs = db.query(GameLog).filter(
                GameLog.room_id == room_id,
                GameLog.day_number == room.day_number,
                GameLog.event_type == "speech"
            ).order_by(GameLog.created_at.desc()).limit(5).all()
            
            conversation_context = ""
            if recent_logs:
                conversation_context = "\n最近の会話:\n"
                for log in reversed(recent_logs):  # 時系列順にソート
                    if log.actor:
                        conversation_context += f"- {log.actor.character_name}: {log.content}\n"
            
            # 他のプレイヤー情報
            alive_players = [p for p in room.players if p.is_alive]
            other_players = [p.character_name for p in alive_players if p.player_id != ai_player.player_id]
            
            prompt = f"""あなたは人狼ゲームのプレイヤーです。

キャラクター情報:
名前: {ai_player.character_name}
役職: {ai_player.role}
ペルソナ: {persona}

ゲーム状況:
- フェーズ: {room.status}
- {room.day_number}日目
- 生存者数: {len(alive_players)}人
- 他の生存プレイヤー: {', '.join(other_players)}

{conversation_context}

あなたのキャラクターの性格と役職に基づいて、自然で一貫性のある発言をしてください。
発言は1-3文程度の適切な長さで、ゲームの状況に応じた内容にしてください。

発言:"""

            try:
                logger.info("🔄 Using direct Vertex AI as primary method...")
                vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
                model = GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                
                if response.text and len(response.text.strip()) > 5:
                    speech = response.text.strip()
                    logger.info(f"✅ Direct Vertex AI speech generation successful: {speech}")
                    # 発言の検証と整形
                    if len(speech) < 5:
                        speech = "少し考えさせてください。"
                    return speech
                else:
                    logger.warning(f"Empty or too short response from Vertex AI: {response.text}")
                    
            except Exception as vertex_error:
                logger.error(f"❌ Direct Vertex AI also failed: {vertex_error}")
                
            # 最終フォールバック
            logger.info("Using ultra-safe fallback due to all AI failures")
            return random.choice(ULTRA_SAFE_FALLBACK_SPEECHES)
            
        else:
            # フォールバック: 環境変数が不足している場合
            logger.info(f"Missing AI credentials - using ultra-safe fallback. root_agent: {root_agent is not None}, PROJECT_ID: {bool(GOOGLE_PROJECT_ID)}, LOCATION: {bool(GOOGLE_LOCATION)}")
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

def build_ai_vote_prompt(ai_player, room, possible_targets, recent_logs) -> str:
    """AI投票決定用のプロンプトを構築"""
    try:
        # ペルソナ情報を取得
        persona = ai_player.character_persona or f"私は{ai_player.character_name}です。"
        
        # 候補者リスト
        target_names = [target.character_name for target in possible_targets]
        
        # 最近の発言を要約
        recent_speeches = []
        for log in recent_logs[:5]:  # 最新5件
            if log.actor and log.content:
                speaker_name = log.actor.character_name if hasattr(log.actor, 'character_name') else 'Unknown'
                content = log.content[:100] + "..." if len(log.content) > 100 else log.content
                recent_speeches.append(f"- {speaker_name}: {content}")
        
        speeches_text = "\n".join(recent_speeches) if recent_speeches else "- まだ発言がありません"
        
        return f"""あなたは人狼ゲームのプレイヤー「{ai_player.character_name}」として投票を行います。

キャラクター設定：
{persona}

あなたの役職：{ai_player.role}
現在：{room.day_number}日目の投票フェーズ

最近の議論：
{speeches_text}

投票候補者：{', '.join(target_names)}

【重要な判断基準】
- 村人陣営なら：疑わしい行動をした人に投票
- 人狼陣営なら：村人（特に占い師など重要役職）に投票
- 発言内容、行動パターン、投票履歴を考慮

上記の候補者の中から、最も投票すべき相手を1人選んで、その名前だけを答えてください。
理由は不要です。候補者の名前のみを正確に回答してください。

投票先："""
        
    except Exception as e:
        logger.error(f"Error building AI vote prompt: {e}")
        # フォールバック：シンプルなプロンプト
        target_names = [target.character_name for target in possible_targets]
        return f"""投票候補者：{', '.join(target_names)}

上記の中から1人を選んで名前を答えてください。
投票先："""

def strategic_target_selection(actor_player, possible_targets: List[Player], context: str = "vote") -> Player:
    """
    戦略的ターゲット選択機能
    
    Args:
        actor_player: 行動するプレイヤー（投票者、襲撃者、護衛者等）
        possible_targets: 可能なターゲットのリスト
        context: 選択の文脈 ("vote", "attack", "protect")
    
    Returns:
        選択されたターゲット
    """
    if not possible_targets:
        return None
    
    # 人狼陣営の場合
    if actor_player.role == 'werewolf':
        if context == "vote":
            # 人狼の投票戦略：村人陣営を優先、特に占い師・ボディガード
            # 1. 占い師を最優先
            seers = [p for p in possible_targets if p.role == 'seer']
            if seers:
                return seers[0]
            
            # 2. ボディガードを次点
            bodyguards = [p for p in possible_targets if p.role == 'bodyguard']
            if bodyguards:
                return bodyguards[0]
            
            # 3. 村人
            villagers = [p for p in possible_targets if p.role == 'villager']
            if villagers:
                return villagers[0]
            
            # 4. AIプレイヤーを優先（人間よりも読みやすい）
            ai_targets = [p for p in possible_targets if not p.is_human]
            if ai_targets:
                return ai_targets[0]
                
        elif context == "attack":
            # 夜の襲撃戦略（既存ロジックを流用）
            # 1. 占い師を最優先
            seers = [p for p in possible_targets if p.role == 'seer']
            if seers:
                return seers[0]
            
            # 2. ボディガードを次点
            bodyguards = [p for p in possible_targets if p.role == 'bodyguard']
            if bodyguards:
                return bodyguards[0]
            
            # 3. 村人をバランス良く選択（完全ランダムではなく、最初の村人）
            villagers = [p for p in possible_targets if p.role == 'villager']
            if villagers:
                return villagers[0]
    
    # 村人陣営（占い師、ボディガード、村人）の場合
    elif actor_player.role in ['seer', 'bodyguard', 'villager']:
        if context == "vote":
            # 村人陣営の投票戦略：疑わしいプレイヤーを優先
            # 1. AIプレイヤーを優先（戦略が読みにくく疑わしい）
            ai_targets = [p for p in possible_targets if not p.is_human]
            if ai_targets:
                return ai_targets[0]
            
            # 2. 人狼の可能性が高いプレイヤー（ここでは人間プレイヤー）
            human_targets = [p for p in possible_targets if p.is_human]
            if human_targets:
                return human_targets[0]
                
        elif context == "protect":
            # ボディガードの護衛戦略
            # 1. 占い師を最優先
            seers = [p for p in possible_targets if p.role == 'seer']
            if seers:
                return seers[0]
            
            # 2. 村人を次点（最初の村人を選択）
            villagers = [p for p in possible_targets if p.role == 'villager']
            if villagers:
                return villagers[0]
            
            # 3. 他のボディガード
            other_bodyguards = [p for p in possible_targets if p.role == 'bodyguard']
            if other_bodyguards:
                return other_bodyguards[0]
    
    # フォールバック：最初のターゲットを選択（完全ランダムの代替）
    return possible_targets[0]

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
                # 非同期でタイムアウト付き実行（短縮：30秒→12秒）
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, prompt),
                    timeout=12.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"AI vote decision timeout for {ai_player.character_name}, using strategic selection")
                return strategic_target_selection(ai_player, possible_targets, "vote")
            
            # レスポンスからプレイヤー名を抽出（改善版）
            decision_text = response.text.strip()
            logger.info(f"AI {ai_player.character_name} vote decision response: {decision_text}")
            
            # より精密なプレイヤー名マッチング
            target_names = [target.character_name for target in possible_targets]
            
            # 完全一致を優先
            for target in possible_targets:
                if target.character_name == decision_text.strip():
                    logger.info(f"AI {ai_player.character_name} decided to vote for {target.character_name} (exact match)")
                    return target
            
            # 部分一致をチェック
            for target in possible_targets:
                if target.character_name in decision_text:
                    logger.info(f"AI {ai_player.character_name} decided to vote for {target.character_name} (partial match)")
                    return target
            
            # レスポンスにプレイヤー名が含まれているかを逆順でチェック
            decision_lower = decision_text.lower()
            for target in possible_targets:
                if target.character_name.lower() in decision_lower:
                    logger.info(f"AI {ai_player.character_name} decided to vote for {target.character_name} (case insensitive match)")
                    return target
            
            # どれもマッチしなかった場合は最初のターゲット
            logger.warning(f"AI {ai_player.character_name} LLM vote decision unclear: '{decision_text}', candidates: {target_names}, using first target")
            return possible_targets[0]
            
    except Exception as e:
        logger.error(f"Error in AI vote decision: {e}")
    
    # フォールバック: 戦略的選択
    logger.warning(f"AI vote decision failed for {ai_player.character_name}, using strategic selection")
    return strategic_target_selection(ai_player, possible_targets, "vote")


# --- WebSocket (Socket.IO) Setup ---
sio = socketio.AsyncServer(
    async_mode="asgi", 
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    allow_upgrades=True,
    transports=['websocket', 'polling']
)

# Socket.IOアプリケーションを作成（デバッグ用設定付き）
app_sio = socketio.ASGIApp(
    sio, 
    app, 
    socketio_path='socket.io'
)

@sio.event
async def connect(sid, environ):
    try:
        logger.info(f"Socket.IO client attempting to connect: {sid}")
        logger.info(f"Environment: {environ.get('REQUEST_METHOD', 'N/A')}")
        logger.info(f"Path: {environ.get('PATH_INFO', 'N/A')}")
        logger.info(f"Query: {environ.get('QUERY_STRING', 'N/A')}")
        
        # 認証を完全にスキップして接続を許可
        logger.info(f"BYPASS: Allowing connection without authentication")
        await sio.save_session(sid, {'player_id': 'anonymous', 'authenticated': True})
        await sio.emit('authenticated', {'player_id': 'anonymous', 'status': 'connected'}, to=sid)
        logger.info(f"Client {sid} connected and authenticated successfully")
        return True
    except Exception as e:
        logger.error(f"Connection error for {sid}: {str(e)}")
        return False

@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO client disconnected: {sid}")
    # TODO: 必要に応じてプレイヤーの切断処理を実装

@sio.event
async def join_room(sid, data):
    room_id = data.get('room_id')
    if room_id:
        await sio.enter_room(sid, room_id)
        logger.info(f"Client {sid} joined room {room_id}")
        await sio.emit('message', {'data': f'Successfully joined room {room_id}'}, to=sid)

@sio.event
async def leave_room(sid, data):
    room_id = data.get('room_id')
    if room_id:
        await sio.leave_room(sid, room_id)
        logger.info(f"Client {sid} left room {room_id}")

# --- API Endpoints ---
@app.post("/api/rooms", response_model=JoinRoomResponse, summary="新しいゲームルームを作成")
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

    # プレイヤーを作成
    new_player = Player(
        room_id=room_id,
        character_name=player_name,
        is_human=True,
        is_claimed=False
    )
    db.add(new_player)
    db.flush()

    # セッショントークンを生成し、PlayerSessionに保存
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    player_session = PlayerSession(
        player_id=new_player.player_id,
        session_token=session_token,
        expires_at=expires_at
    )
    db.add(player_session)
    db.commit()
    db.refresh(new_player) # new_playerをリフレッシュしてplayer_idを取得

    return JoinRoomResponse(
        player_id=str(new_player.player_id),
        player_name=player_name,
        room_id=str(room_id),
        session_token=session_token
    )

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
    
    # 完全なゲーム状態をWebSocketで通知
    await broadcast_complete_game_state(room_id, db)
    
    # 発言イベントも別途通知
    player = get_player(db, player_id)
    await sio.emit('new_speech', {
        'room_id': str(room_id),
        'speaker_id': str(player_id),
        'speaker_name': player.character_name if player else 'Unknown',
        'statement': speak_input.statement,
        'current_turn_index': updated_room.current_turn_index,
        'turn_order': updated_room.turn_order,
        'timestamp': datetime.now().isoformat()
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

@app.get("/api/players/{player_id}/available_targets", summary="夜間アクション可能な対象を取得")
async def get_available_targets(player_id: uuid.UUID, db: Session = Depends(get_db)):
    """占い師・ボディガードが夜間アクション可能な対象プレイヤーのリストを取得"""
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # 占い師、ボディガード、人狼のみ許可
    if player.role not in ['seer', 'bodyguard', 'werewolf']:
        raise HTTPException(status_code=403, detail="Only seers, bodyguards, and werewolves can use this endpoint")
    
    if not player.is_alive:
        raise HTTPException(status_code=403, detail="Dead players cannot perform night actions")
    
    room = db.query(Room).filter(Room.room_id == player.room_id).first()
    if not room or room.status != 'night':
        raise HTTPException(status_code=400, detail="Night actions only available during night phase")
    
    # 生存している他のプレイヤーを取得
    available_targets = db.query(Player).filter(
        Player.room_id == player.room_id,
        Player.is_alive == True,
        Player.player_id != player_id
    ).all()
    
    # 役職に応じたレスポンス
    if player.role == 'seer':
        return {
            'targets': [PlayerInfo.model_validate(p) for p in available_targets],
            'can_investigate': True,
            'action_type': 'investigate'
        }
    elif player.role == 'bodyguard':
        return {
            'targets': [PlayerInfo.model_validate(p) for p in available_targets],
            'can_protect': True,
            'action_type': 'protect'
        }
    elif player.role == 'werewolf':
        # 人狼は村人陣営のみを攻撃対象とする
        villager_targets = [p for p in available_targets if p.role in ['villager', 'seer', 'bodyguard']]
        return {
            'targets': [PlayerInfo.model_validate(p) for p in villager_targets],
            'can_attack': True,
            'action_type': 'attack'
        }

@app.post("/api/rooms/{room_id}/seer_investigate", summary="占い師の調査実行")
async def seer_investigate(
    room_id: uuid.UUID, 
    investigator_id: str = Query(...),
    target_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """占い師が特定の対象を調査する"""
    try:
        investigator_uuid = uuid.UUID(investigator_id)
        target_player_id = uuid.UUID(target_data['target_player_id'])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # 調査者の検証
    investigator = db.query(Player).filter(Player.player_id == investigator_uuid).first()
    if not investigator:
        raise HTTPException(status_code=404, detail="Investigator not found")
    
    if investigator.role != 'seer':
        raise HTTPException(status_code=403, detail="Only seers can investigate")
    
    if not investigator.is_alive:
        raise HTTPException(status_code=403, detail="Dead players cannot investigate")
    
    # 対象の検証
    target = db.query(Player).filter(Player.player_id == target_player_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    if not target.is_alive:
        raise HTTPException(status_code=400, detail="Cannot investigate dead players")
    
    if target.player_id == investigator.player_id:
        raise HTTPException(status_code=400, detail="Cannot investigate yourself")
    
    # 部屋とフェーズの検証
    room = db.query(Room).filter(Room.room_id == room_id).first()
    if not room or room.status != 'night':
        raise HTTPException(status_code=400, detail="Investigation only available during night phase")
    
    # 調査実行
    result = "人狼" if target.role == 'werewolf' else "村人"
    
    # 調査実行ログを記録（結果は秘匿）
    create_game_log(db, room_id, "night", "investigate", 
                  actor_player_id=investigator.player_id,
                  content=f"{investigator.character_name}が占いを実行しました")
    
    db.commit()
    
    # 🔧 占い後の夜フェーズ自動進行チェック
    try:
        if await check_night_actions_completion(db, room_id):
            logger.info(f"All night actions completed, auto-progressing from night phase for room {room_id}")
            # 2秒の遅延を追加してフロントエンドの安定性を向上
            await asyncio.sleep(2)
            await sio.emit('complete_game_state', get_room_dict(db, room_id), room=str(room_id))
    except Exception as e:
        logger.error(f"Error in night actions completion check: {e}")
    
    # 占い師にのみ結果を返す
    return {
        'investigator': investigator.character_name,
        'target': target.character_name,
        'result': result,
        'message': f"{target.character_name}の正体: {result}"
    }

@app.post("/api/rooms/{room_id}/bodyguard_protect", summary="ボディガードの護衛実行")
async def bodyguard_protect(
    room_id: uuid.UUID, 
    protector_id: str = Query(...),
    target_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """ボディガードが特定の対象を護衛する"""
    try:
        protector_uuid = uuid.UUID(protector_id)
        target_player_id = uuid.UUID(target_data['target_player_id'])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # 護衛者の検証
    protector = db.query(Player).filter(Player.player_id == protector_uuid).first()
    if not protector:
        raise HTTPException(status_code=404, detail="Protector not found")
    
    if protector.role != 'bodyguard':
        raise HTTPException(status_code=403, detail="Only bodyguards can protect")
    
    if not protector.is_alive:
        raise HTTPException(status_code=403, detail="Dead players cannot protect")
    
    # 対象の検証
    target = db.query(Player).filter(Player.player_id == target_player_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    if not target.is_alive:
        raise HTTPException(status_code=400, detail="Cannot protect dead players")
    
    if target.player_id == protector.player_id:
        raise HTTPException(status_code=400, detail="Cannot protect yourself")
    
    # 部屋とフェーズの検証
    room = db.query(Room).filter(Room.room_id == room_id).first()
    if not room or room.status != 'night':
        raise HTTPException(status_code=400, detail="Protection only available during night phase")
    
    # 同じ夜に既に護衛を実行していないかチェック
    existing_protection = db.query(GameLog).filter(
        GameLog.room_id == room_id,
        GameLog.day_number == room.day_number,
        GameLog.phase == "night",
        GameLog.event_type == "protect",
        GameLog.actor_player_id == protector.player_id
    ).first()
    
    if existing_protection:
        raise HTTPException(status_code=400, detail="You have already protected someone tonight")
    
    # 護衛実行ログを記録
    create_game_log(db, room_id, "night", "protect", 
                  actor_player_id=protector.player_id,
                  content=f"protected {target.character_name}")
    
    db.commit()
    
    # 🔧 護衛後の夜フェーズ自動進行チェック
    try:
        if await check_night_actions_completion(db, room_id):
            logger.info(f"All night actions completed, auto-progressing from night phase for room {room_id}")
            # 2秒の遅延を追加してフロントエンドの安定性を向上
            await asyncio.sleep(2)
            await sio.emit('complete_game_state', get_room_dict(db, room_id), room=str(room_id))
    except Exception as e:
        logger.error(f"Error in night actions completion check: {e}")
    
    # ボディガードに結果を返す
    return {
        'protector': protector.character_name,
        'target': target.character_name,
        'message': f"{target.character_name}を今夜の攻撃から守ります",
        'success': True
    }

@app.post("/api/rooms/{room_id}/werewolf_attack", summary="人狼の攻撃実行")
async def werewolf_attack(
    room_id: uuid.UUID, 
    attacker_id: str = Query(...),
    target_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """人狼が特定の対象を攻撃する"""
    try:
        attacker_uuid = uuid.UUID(attacker_id)
        target_player_id = uuid.UUID(target_data['target_player_id'])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # 攻撃者の検証
    attacker = db.query(Player).filter(Player.player_id == attacker_uuid).first()
    if not attacker:
        raise HTTPException(status_code=404, detail="Attacker not found")
    
    if attacker.role != 'werewolf':
        raise HTTPException(status_code=403, detail="Only werewolves can attack")
    
    if not attacker.is_alive:
        raise HTTPException(status_code=403, detail="Dead players cannot attack")
    
    # 対象の検証
    target = db.query(Player).filter(Player.player_id == target_player_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    if not target.is_alive:
        raise HTTPException(status_code=400, detail="Cannot attack dead players")
    
    if target.role == 'werewolf':
        raise HTTPException(status_code=400, detail="Cannot attack fellow werewolves")
    
    # 部屋とフェーズの検証
    room = db.query(Room).filter(Room.room_id == room_id).first()
    if not room or room.status != 'night':
        raise HTTPException(status_code=400, detail="Attacks only available during night phase")
    
    # 同じ夜に既に攻撃を実行していないかチェック
    existing_attack = db.query(GameLog).filter(
        GameLog.room_id == room_id,
        GameLog.day_number == room.day_number,
        GameLog.phase == "night",
        GameLog.event_type == "attack_target",
        GameLog.actor_player_id == attacker.player_id
    ).first()
    
    if existing_attack:
        raise HTTPException(status_code=400, detail="You have already attacked someone tonight")
    
    # 攻撃実行ログを記録（ただし実際の結果は夜フェーズ終了時に処理）
    create_game_log(db, room_id, "night", "attack_target", 
                  actor_player_id=attacker.player_id,
                  content=f"targeted {target.character_name} for attack")
    
    db.commit()
    
    # 🔧 攻撃後の夜フェーズ自動進行チェック
    try:
        if await check_night_actions_completion(db, room_id):
            logger.info(f"All night actions completed, auto-progressing from night phase for room {room_id}")
            # 2秒の遅延を追加してフロントエンドの安定性を向上
            await asyncio.sleep(2)
            await sio.emit('complete_game_state', get_room_dict(db, room_id), room=str(room_id))
    except Exception as e:
        logger.error(f"Error in night actions completion check: {e}")
    
    # 人狼に結果を返す
    return {
        'attacker': attacker.character_name,
        'target': target.character_name,
        'message': f"{target.character_name}を今夜の襲撃対象に選択しました",
        'success': True
    }

@app.post("/api/rooms/{room_id}/transition_to_vote", summary="投票フェーズに移行")
async def transition_to_vote(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """議論フェーズから投票フェーズに手動で移行する"""
    try:
        db_room = db.query(Room).filter(Room.room_id == room_id).with_for_update().first()
        if not db_room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        if db_room.status != 'day_discussion':
            raise HTTPException(status_code=400, detail=f"Cannot transition to vote from current phase: {db_room.status}")
        
        # 投票フェーズに移行
        db_room.status = 'day_vote'
        create_game_log(db, room_id, "phase_transition", "day_vote", content="手動で投票フェーズに移行しました。")
        db.commit()
        
        # 部屋の最新状態を取得
        updated_room = get_room(db, room_id)
        
        # WebSocket通知
        await sio.emit('room_updated', {'room_id': str(room_id)}, room=str(room_id))
        
        return {
            "room_id": str(room_id),
            "status": updated_room.status,
            "message": "投票フェーズに移行しました"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in transition_to_vote: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to transition to vote phase")

@app.get("/api/rooms/{room_id}/logs", response_model=List[GameLogInfo], summary="ゲームログを取得")
def read_game_logs(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """特定のゲームルームのログを取得する"""
    return get_game_logs(db, room_id)

@app.post("/api/players/{player_id}/generate_persona", summary="プレイヤーのペルソナを生成")
async def generate_persona(player_id: uuid.UUID, persona_input: PersonaInput, db: Session = Depends(get_db)):
    """プレイヤー（AI・人間問わず）のペルソナをキーワードに基づいて生成する"""
    player = get_player(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    try:
        # Vertex AI の初期化を確認
        if not GOOGLE_PROJECT_ID:
            logger.warning("Google Cloud project not configured, using mock persona")
            # モックペルソナを生成
            persona_data = {
                "name": f"プレイヤー{player.character_name[-1] if player.character_name else '1'}",
                "gender": "不明",
                "age": 25,
                "personality": "ミステリアスで慎重な性格",
                "speech_style": "丁寧語を使い、慎重に発言する",
                "background": "詳細は秘密に包まれている"
            }
        else:
            # Vertex AI を使用してペルソナを生成
            try:
                vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
                model = GenerativeModel("gemini-1.5-flash")
                prompt = f"""以下のキーワードを元に、人狼ゲームのキャラクターのペルソナをJSON形式で生成してください: {persona_input.keywords}

返答は必ず以下のJSON形式のみで回答してください：
{{
  "name": "キャラクターに合った日本人らしい名前（姓名両方）",
  "gender": "男性/女性/その他",
  "age": 数値,
  "personality": "性格の説明",
  "speech_style": "話し方や口調の説明",
  "background": "背景設定の説明"
}}"""
                
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                
                # JSONの抽出（```json から ```までを除去）
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    if json_end != -1:
                        response_text = response_text[json_start:json_end]
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    if json_end != -1:
                        response_text = response_text[json_start:json_end]
                
                persona_data = json.loads(response_text.strip())
                logger.info(f"Generated persona for player {player_id}: {persona_data}")
                
            except Exception as ai_error:
                logger.error(f"Vertex AI persona generation failed: {ai_error}", exc_info=True)
                # フォールバック用のペルソナ
                persona_data = {
                    "name": generate_ai_player_name_sync(1),  # フォールバック名前生成
                    "gender": "不明",
                    "age": 25,
                    "personality": f"キーワード「{persona_input.keywords}」に基づく個性的なキャラクター",
                    "speech_style": "独特な話し方をする",
                    "background": f"「{persona_input.keywords}」という特徴を持つ謎めいた人物"
                }
        
        # データベースを更新
        update_player_persona(db, player_id, persona_data)
        
        # ペルソナに名前が含まれている場合、プレイヤー名も更新
        if "name" in persona_data and persona_data["name"]:
            try:
                player.character_name = persona_data["name"]
                db.commit()
                logger.info(f"Updated player name to: {persona_data['name']}")
            except Exception as name_error:
                logger.error(f"Failed to update player name: {name_error}")
                # 名前更新失敗してもペルソナ生成は成功として扱う
        
        # 更新を通知
        await sio.emit('room_updated', {'room_id': str(player.room_id)}, room=str(player.room_id))
        
        return {"message": "Persona generated successfully", "persona": persona_data}
    except Exception as e:
        logger.error(f"Persona generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate persona: {str(e)}")

@app.get("/api/rooms/{room_id}/summary", summary="ゲーム状況サマリーを取得")
async def get_game_summary(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """現在のゲーム状況のLLM生成サマリーを取得する"""
    try:
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # ゲームログを取得
        logs = get_game_logs(db, room_id)
        
        # プレイヤー状況を分析
        alive_players = [p for p in room.players if p.is_alive]
        dead_players = [p for p in room.players if not p.is_alive]
        
        player_status = {
            "生存者": [
                {
                    "name": p.character_name,
                    "type": "人間" if p.is_human else "AI"
                } for p in alive_players
            ],
            "死亡者": [
                {
                    "name": p.character_name,
                    "type": "人間" if p.is_human else "AI"
                } for p in dead_players
            ]
        }
        
        # 日ごとの活動履歴を集計
        daily_activities = {}
        for log in logs:
            day_key = f"{log.day_number}日目" if hasattr(log, 'day_number') and log.day_number else "1日目"
            if day_key not in daily_activities:
                daily_activities[day_key] = {
                    "発言数": 0,
                    "投票数": 0,
                    "重要イベント": []
                }
            
            if log.event_type == "speak":
                daily_activities[day_key]["発言数"] += 1
            elif log.event_type == "vote":
                daily_activities[day_key]["投票数"] += 1
            elif log.event_type in ["execution", "attack", "protection", "divination"]:
                if log.content:
                    daily_activities[day_key]["重要イベント"].append(log.content)
        
        # LLMを使って状況サマリーを生成
        llm_summary = await generate_game_summary_llm(room, logs, alive_players, dead_players)
        
        return {
            "room_id": str(room_id),
            "day_number": room.day_number,
            "current_phase": room.status,
            "summary": {
                "llm_summary": llm_summary,
                "player_status": player_status,
                "daily_activities": daily_activities,
                "current_phase": {
                    "day": room.day_number,
                    "phase": room.status,
                    "round": getattr(room, 'current_round', None)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate game summary for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate game summary")

@app.get("/api/rooms/{room_id}/game_result", summary="ゲーム結果と役職開示を取得")
async def get_game_result(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """ゲーム終了時の詳細な結果と全プレイヤーの役職を開示する"""
    try:
        room = get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # ゲーム終了チェック
        game_end_result = check_game_end_condition(db, room_id)
        
        if not game_end_result['game_over']:
            raise HTTPException(status_code=400, detail="Game is not finished yet")
        
        # 全プレイヤーの役職情報を開示
        players_with_roles = []
        for player in room.players:
            player_info = {
                "player_id": str(player.player_id),
                "character_name": player.character_name,
                "role": player.role,
                "is_alive": player.is_alive,
                "is_human": player.is_human,
                "faction": "人狼陣営" if player.role == "werewolf" else "村人陣営",
                "is_winner": False
            }
            
            # 勝利判定
            if game_end_result['winner'] == 'werewolves' and player.role == 'werewolf':
                player_info['is_winner'] = True
            elif game_end_result['winner'] == 'villagers' and player.role in ['villager', 'seer', 'bodyguard']:
                player_info['is_winner'] = True
            
            players_with_roles.append(player_info)
        
        # ゲーム統計を生成
        total_players = len(room.players)
        human_players = len([p for p in room.players if p.is_human])
        ai_players = len([p for p in room.players if not p.is_human])
        werewolves = len([p for p in room.players if p.role == 'werewolf'])
        villagers = len([p for p in room.players if p.role in ['villager', 'seer', 'bodyguard']])
        
        # ゲームログから重要なイベントを抽出
        important_events = []
        logs = get_game_logs(db, room_id)
        for log in logs:
            if log.event_type in ['execution', 'attack', 'game_end', 'seer_result']:
                important_events.append({
                    "day": log.day_number,
                    "phase": log.phase,
                    "event_type": log.event_type,
                    "content": log.content,
                    "timestamp": log.created_at.isoformat()
                })
        
        # LLMで詳細なゲームサマリーを生成
        game_summary = await generate_game_end_summary_llm(room, game_end_result, players_with_roles, important_events)
        
        return {
            "room_id": str(room_id),
            "game_result": {
                "game_over": True,
                "winner": game_end_result['winner'],
                "winner_faction": "人狼陣営" if game_end_result['winner'] == 'werewolves' else "村人陣営",
                "victory_message": game_end_result['message'],
                "final_day": room.day_number,
                "total_days": room.day_number
            },
            "players": players_with_roles,
            "game_statistics": {
                "total_players": total_players,
                "human_players": human_players,
                "ai_players": ai_players,
                "werewolves_count": werewolves,
                "villagers_count": villagers
            },
            "important_events": important_events,
            "game_summary": game_summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get game result for room {room_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get game result")

@app.post("/api/rooms/{room_id}/auto_progress", summary="ゲームの自動進行")
async def auto_progress(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """AIプレイヤーのターンを自動で進行させる"""
    try:
        result = await auto_progress_logic(room_id, db)
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
            # 🔍 AI発言デバッグ：開始
            logger.info(f"🤖 AUTO-PROGRESS: AI speech generation started for {current_player.character_name}")
            logger.info(f"🤖 TURN STATE: room_id={room_id}, current_turn_index={room.current_turn_index}, player_id={current_player_id}")
            
            # 発言制限緩和：AI発言前チェックを無効化（ゲーム進行優先）
            player_day_speeches = db.query(GameLog).filter(
                GameLog.room_id == room_id,
                GameLog.phase == "day_discussion",
                GameLog.event_type == "speech",
                GameLog.day_number == room.day_number,
                GameLog.actor_player_id == current_player_id
            ).count()
            
            logger.info(f"🤖 AI SPEECH ALLOWED: {current_player.character_name} has spoken {player_day_speeches} times today - proceeding with speech generation")
            
            # AIの発言を生成
            try:
                statement = await generate_ai_speech(db, room_id, current_player_id)
                logger.info(f"🤖 AI SPEECH GENERATED: {current_player.character_name} said: '{statement[:100]}...'")  # 最初の100文字のみログ
                
                # 発言処理 - これによってターンが自動的に進む
                logger.info(f"🤖 BEFORE SPEAK_LOGIC: current_turn_index={room.current_turn_index}")
                updated_room = speak_logic(db, room_id, current_player_id, statement)
                logger.info(f"🤖 AFTER SPEAK_LOGIC: current_turn_index={updated_room.current_turn_index}")
                logger.info(f"🤖 TURN ADVANCED: from {room.current_turn_index} to {updated_room.current_turn_index}")
                
                # WebSocket通知データ
                websocket_data = {
                    "type": "new_speech",
                    "data": {
                        'room_id': str(room_id),
                        'speaker_id': str(current_player_id),
                        'speaker_name': current_player.character_name,
                        'statement': statement,
                        'current_phase': updated_room.status,
                        'current_turn_index': updated_room.current_turn_index
                    }
                }
                return {"auto_progressed": True, "message": f"{current_player.character_name} spoke.", "websocket_data": websocket_data}
            except Exception as e:
                logger.error(f"❌ CRITICAL: AI speech generation failed for {current_player.character_name}: {e}", exc_info=True)
                logger.error(f"❌ Error type: {type(e).__name__}")
                logger.error(f"❌ Error details: {str(e)}")
                
                # 🔧 改善されたエラー処理：ターンスキップではなく安全なフォールバック発言を使用
                logger.info(f"🔄 Using emergency fallback speech for {current_player.character_name}")
                emergency_statement = generate_safe_fallback_speech(current_player, room)
                logger.info(f"🔄 Emergency fallback speech: {emergency_statement}")
                
                try:
                    # フォールバック発言で発言処理を実行
                    updated_room = speak_logic(db, room_id, current_player_id, emergency_statement)
                    logger.info(f"✅ Emergency fallback speech successful for {current_player.character_name}")
                    
                    # WebSocket通知データ
                    websocket_data = {
                        "type": "new_speech",
                        "data": {
                            'room_id': str(room_id),
                            'speaker_id': str(current_player_id),
                            'speaker_name': current_player.character_name,
                            'statement': emergency_statement,
                            'current_turn_index': updated_room.current_turn_index
                        }
                    }
                    return {"auto_progressed": True, "message": f"{current_player.character_name} spoke (emergency fallback).", "websocket_data": websocket_data}
                    
                except Exception as fallback_error:
                    logger.error(f"🚨 Emergency fallback speech also failed: {fallback_error}")
                    # 最終手段としてターンスキップ
                    next_index = find_next_alive_player_safe(db, room_id, room.current_turn_index)
                    room.current_turn_index = next_index
                    db.commit()
                    return {"auto_progressed": True, "message": f"{current_player.character_name} skipped due to complete AI failure.", "error": str(e)}

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
            try:
                logger.info(f"🗳️ Processing AI vote for {ai_to_vote.character_name}")
                # AIの投票先を決定
                possible_targets = [p for p in alive_players if p.player_id != ai_to_vote.player_id]
                if not possible_targets:
                    logger.error(f"No voting targets available for {ai_to_vote.character_name}")
                    return {"auto_progressed": False, "message": "No one to vote for."}
                
                logger.info(f"Possible vote targets for {ai_to_vote.character_name}: {[p.character_name for p in possible_targets]}")
                target_player = await generate_ai_vote_decision(db, room_id, ai_to_vote, possible_targets)
                logger.info(f"AI {ai_to_vote.character_name} decided to vote for {target_player.character_name}")
                
                # 投票処理
                vote_result = process_vote(db, room_id, ai_to_vote.player_id, target_player.player_id)
                
                # WebSocket通知データ
                websocket_data = {
                    "type": "new_vote",
                    "data": {
                        'room_id': str(room_id),
                        'voter_id': str(ai_to_vote.player_id),
                        'voter_name': ai_to_vote.character_name,
                        'target_id': str(target_player.player_id),
                        'target_name': target_player.character_name,
                        'vote_result': vote_result.message if vote_result else None
                    }
                }
                return {"auto_progressed": True, "message": f"{ai_to_vote.character_name} voted for {target_player.character_name}.", "websocket_data": websocket_data}
            except Exception as e:
                logger.error(f"Error in AI voting for {ai_to_vote.character_name}: {e}", exc_info=True)
                # フォールバック: 戦略的投票
                try:
                    logger.info(f"🔄 Using fallback strategic voting for {ai_to_vote.character_name}")
                    target_player = strategic_target_selection(ai_to_vote, possible_targets, "vote")
                    vote_result = process_vote(db, room_id, ai_to_vote.player_id, target_player.player_id)
                    logger.info(f"✅ Fallback random vote successful: {ai_to_vote.character_name} → {target_player.character_name}")
                    
                    # WebSocket通知データ（フォールバック用）
                    websocket_data = {
                        "type": "new_vote",
                        "data": {
                            'room_id': str(room_id),
                            'voter_id': str(ai_to_vote.player_id),
                            'voter_name': ai_to_vote.character_name,
                            'target_id': str(target_player.player_id),
                            'target_name': target_player.character_name,
                            'vote_result': vote_result.message if vote_result else None,
                            'is_fallback': True
                        }
                    }
                    return {"auto_progressed": True, "message": f"{ai_to_vote.character_name} voted randomly for {target_player.character_name} (fallback).", "websocket_data": websocket_data, "error": str(e)}
                except Exception as fallback_error:
                    logger.error(f"🚨 Fallback voting also failed: {fallback_error}", exc_info=True)
                    return {"auto_progressed": False, "message": f"Failed to process AI vote: {str(e)}"}

    # 🔧 デバッグ情報を追加
    logger.warning(f"No auto-progression available for room {room_id} in status {room.status}")
    logger.warning(f"Room details: day={room.day_number}, turn_index={room.current_turn_index}, turn_order_length={len(room.turn_order) if room.turn_order else 0}")
    
    return {"auto_progressed": False, "message": f"Not in a phase for auto-progression. Current status: {room.status}"}

async def generate_game_summary_llm(room, logs, alive_players, dead_players):
    """LLMを使ってゲーム状況サマリーを生成する"""
    try:
        if not GOOGLE_PROJECT_ID:
            return "現在LLMサマリー機能は利用できません。ゲーム状況を手動で確認してください。"
        
        # 最近のイベントを抽出（最大10件）
        recent_events = []
        for log in logs[-10:]:
            if log.content:
                recent_events.append(f"- {log.content}")
        
        # プレイヤー状況をまとめる
        alive_summary = f"生存者: {len(alive_players)}人 ({len([p for p in alive_players if p.is_human])}人の人間, {len([p for p in alive_players if not p.is_human])}人のAI)"
        dead_summary = f"死亡者: {len(dead_players)}人" if dead_players else "死亡者: なし"
        
        # LLMプロンプト作成
        prompt = f"""
人狼ゲームの現在の状況について、プレイヤーにとって有用な戦略的サマリーを日本語で生成してください。

## ゲーム情報
- 現在: {room.day_number}日目 ({room.status})
- {alive_summary}
- {dead_summary}

## 最近の出来事
{chr(10).join(recent_events) if recent_events else "- まだ重要な出来事はありません"}

## 指示
以下の要素を含む簡潔なサマリーを200文字以内で作成してください：
1. 現在の状況の要約
2. 生存プレイヤーの状況
3. 戦略的な観点やゲームの流れ

サマリーは客観的で、プレイヤーの役職を推測したり暴露したりしないように注意してください。
"""
        
        vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"LLM summary generation failed: {e}")
        # フォールバック用の基本サマリー
        return f"{room.day_number}日目の{room.status}フェーズです。生存者{len(alive_players)}人、死亡者{len(dead_players)}人の状況で、ゲームが進行中です。"

async def generate_game_end_summary_llm(room, game_result, players_with_roles, important_events):
    """ゲーム終了時の詳細なLLMサマリーを生成する"""
    try:
        if not GOOGLE_PROJECT_ID:
            return "ゲーム終了。詳細なサマリー機能は現在利用できません。"
        
        # プレイヤー情報を整理
        winners = [p for p in players_with_roles if p['is_winner']]
        losers = [p for p in players_with_roles if not p['is_winner']]
        werewolves = [p for p in players_with_roles if p['role'] == 'werewolf']
        villagers = [p for p in players_with_roles if p['role'] in ['villager', 'seer', 'bodyguard']]
        
        # 重要なイベントを整理
        key_events = []
        for event in important_events[-5:]:  # 最新5件
            key_events.append(f"- {event['day']}日目: {event['content']}")
        
        # LLMプロンプト作成
        prompt = f"""
人狼ゲームが終了しました。以下の情報を基に、プレイヤーにとって有益で興味深いゲーム総括を日本語で作成してください。

## ゲーム結果
- 勝利陣営: {game_result['winner_faction']}
- 勝利理由: {game_result['message']}
- ゲーム期間: {room.day_number}日間

## プレイヤー構成
### 勝利者 ({len(winners)}人)
{chr(10).join([f"- {p['character_name']} ({p['role']}, {'人間' if p['is_human'] else 'AI'})" for p in winners])}

### 敗北者 ({len(losers)}人)
{chr(10).join([f"- {p['character_name']} ({p['role']}, {'人間' if p['is_human'] else 'AI'})" for p in losers])}

## 陣営構成
- 人狼陣営: {len(werewolves)}人 ({', '.join([p['character_name'] for p in werewolves])})
- 村人陣営: {len(villagers)}人 ({', '.join([p['character_name'] for p in villagers])})

## 重要な出来事
{chr(10).join(key_events) if key_events else "- 特別な出来事は記録されていません"}

## 指示
以下の要素を含む400文字以内の総括を作成してください：
1. ゲームの流れと戦略的なポイント
2. 勝敗の決定的要因
3. 印象的だったプレイヤーの行動
4. 各陣営の戦略の成功・失敗点

プレイヤーのゲーム体験を称賛し、次回への意欲を高める内容にしてください。
"""
        
        vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Game end LLM summary generation failed: {e}")
        # フォールバック用の基本サマリー
        winner_faction = "人狼陣営" if game_result['winner'] == 'werewolves' else "村人陣営"
        return f"{room.day_number}日間の激戦が終了し、{winner_faction}が勝利しました。{game_result['message']} 素晴らしいゲームでした！"

# --- Helper Functions ---
def get_players_in_room(db: Session, room_id: uuid.UUID) -> List[Player]:
    return db.query(Player).filter(Player.room_id == room_id).all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app_sio, host="0.0.0.0", port=8000)