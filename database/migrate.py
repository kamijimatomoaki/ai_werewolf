#!/usr/bin/env python3
"""
データベースマイグレーション用スクリプト
Cloud Build時にCloud SQL Proxyを使用してテーブルを作成
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """データベースマイグレーションを実行"""
    try:
        # 環境変数からデータベースURLを取得
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable is not set")
            sys.exit(1)

        logger.info("Connecting to database...")
        engine = create_engine(database_url)
        
        # 接続テスト
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")

        # SQLAlchemyモデルをインポートしてテーブル作成
        # パスを追加してmain.pyをインポート可能にする
        sys.path.append('/workspace/backend')
        
        try:
            from game_logic.main import Base
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except ImportError as e:
            logger.error(f"Failed to import main module: {e}")
            # フォールバック: SQLファイルから直接実行
            logger.info("Fallback: Running init.sql...")
            with open('/workspace/database/init.sql', 'r') as f:
                sql_content = f.read()
            
            with engine.connect() as conn:
                conn.execute(text(sql_content))
                conn.commit()
            logger.info("Database initialized from SQL file")

        # 基本的なデータ挿入（必要に応じて）
        with engine.connect() as conn:
            # 設定データの挿入例
            conn.execute(text("""
                INSERT INTO config (key, value) VALUES 
                ('max_rooms', '100'),
                ('max_players_per_room', '12'),
                ('game_timeout_minutes', '60')
                ON CONFLICT (key) DO NOTHING;
            """))
            conn.commit()
            logger.info("Default configuration inserted")

        logger.info("Database migration completed successfully")

    except SQLAlchemyError as e:
        logger.error(f"Database migration failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()