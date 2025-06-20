-- PostgreSQL initialization script for Werewolf Game

-- Create database if not exists (handled by POSTGRES_DB env var)
-- CREATE DATABASE IF NOT EXISTS werewolf_game;

-- Set timezone
SET timezone = 'UTC';

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enable UUID generation
CREATE OR REPLACE FUNCTION generate_uuid_v4()
RETURNS UUID AS $$
BEGIN
    RETURN uuid_generate_v4();
END;
$$ LANGUAGE plpgsql;

-- Create indexes for better performance (will be created by SQLAlchemy as well)
-- These are additional performance optimizations

-- Game logs performance index
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_game_logs_room_day_phase 
-- ON game_logs(room_id, day_number, phase, created_at);

-- Player sessions performance index  
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_sessions_expires
-- ON player_sessions(expires_at) WHERE expires_at > NOW();

-- Spectator messages performance index
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_spectator_messages_room_time
-- ON spectator_messages(room_id, timestamp DESC);

-- Insert default configuration data if needed
-- INSERT INTO config (key, value) VALUES 
-- ('max_rooms', '100'),
-- ('max_players_per_room', '12'),
-- ('game_timeout_minutes', '60')
-- ON CONFLICT (key) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE werewolf_game TO werewolf_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO werewolf_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO werewolf_user;

-- Set default permissions for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO werewolf_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO werewolf_user;