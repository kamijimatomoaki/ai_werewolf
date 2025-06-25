#!/usr/bin/env python3
"""
Database migration script to add last_activity column to rooms table
This fixes the critical error causing AI speech generation failures
"""

import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, Column, DateTime
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get the appropriate database URL for the current environment"""
    # Try Cloud Run environment variables first
    if os.getenv('GOOGLE_CLOUD_PROJECT'):
        return "postgresql://postgres:fall0408@/ai_werewolf?host=/cloudsql/fourth-dynamo-423103-q2:asia-northeast1:tg-app-db-dev"
    
    # Fallback to direct connection for testing
    return "postgresql://postgres:fall0408@34.146.187.79:5432/ai_werewolf"

def add_last_activity_column():
    """Add last_activity column to rooms table if it doesn't exist"""
    
    database_url = get_database_url()
    print(f"Connecting to database...")
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'rooms' AND column_name = 'last_activity'
            """)
            
            result = conn.execute(check_query)
            if result.fetchone():
                print("✅ last_activity column already exists")
                return True
            
            # Add the column
            print("Adding last_activity column to rooms table...")
            add_column_query = text("""
                ALTER TABLE rooms 
                ADD COLUMN last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            """)
            
            conn.execute(add_column_query)
            
            # Update existing rows with current timestamp
            update_query = text("""
                UPDATE rooms 
                SET last_activity = COALESCE(updated_at, created_at, NOW())
                WHERE last_activity IS NULL
            """)
            
            conn.execute(update_query)
            conn.commit()
            
            print("✅ Successfully added last_activity column and updated existing rows")
            return True
            
    except OperationalError as e:
        print(f"❌ Database connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    database_url = get_database_url()
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check column exists and has data
            verify_query = text("""
                SELECT 
                    COUNT(*) as total_rooms,
                    COUNT(last_activity) as rooms_with_activity,
                    MIN(last_activity) as earliest_activity,
                    MAX(last_activity) as latest_activity
                FROM rooms
            """)
            
            result = conn.execute(verify_query)
            row = result.fetchone()
            
            print(f"\n📊 Migration Verification:")
            print(f"   Total rooms: {row.total_rooms}")
            print(f"   Rooms with last_activity: {row.rooms_with_activity}")
            print(f"   Earliest activity: {row.earliest_activity}")
            print(f"   Latest activity: {row.latest_activity}")
            
            if row.total_rooms == row.rooms_with_activity:
                print("✅ All rooms have last_activity values")
                return True
            else:
                print("⚠️  Some rooms missing last_activity values")
                return False
                
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration for last_activity column...")
    
    # Add the column
    if add_last_activity_column():
        # Verify the migration
        if verify_migration():
            print("\n🎉 Migration completed successfully!")
            print("   The game loop monitor errors should now be resolved.")
            print("   AI speech generation should resume normal operation.")
        else:
            print("\n⚠️  Migration completed but verification failed")
            sys.exit(1)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)