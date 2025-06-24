#!/usr/bin/env python3
"""
Minimal test to identify what's causing the hang in main.py
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("1. Starting minimal test...")

# Test 1: Basic imports
try:
    logger.info("2. Testing basic imports...")
    from fastapi import FastAPI, HTTPException
    from sqlalchemy import create_engine
    logger.info("2. ✓ Basic imports successful")
except Exception as e:
    logger.error(f"2. ✗ Basic imports failed: {e}")
    sys.exit(1)

# Test 2: Environment loading
try:
    logger.info("3. Testing environment loading...")
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./test_werewolf.db"
    logger.info(f"3. ✓ Environment loaded, DATABASE_URL: {DATABASE_URL}")
except Exception as e:
    logger.error(f"3. ✗ Environment loading failed: {e}")
    sys.exit(1)

# Test 3: Database engine creation
try:
    logger.info("4. Testing database engine creation...")
    engine = create_engine(DATABASE_URL)
    logger.info("4. ✓ Database engine created")
except Exception as e:
    logger.error(f"4. ✗ Database engine creation failed: {e}")
    sys.exit(1)

# Test 4: FastAPI app creation
try:
    logger.info("5. Testing FastAPI app creation...")
    app = FastAPI(title="Test App")
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    
    logger.info("5. ✓ FastAPI app created")
except Exception as e:
    logger.error(f"5. ✗ FastAPI app creation failed: {e}")
    sys.exit(1)

# Test 5: AI agent import
try:
    logger.info("6. Testing AI agent import...")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from npc_agent.agent import root_agent
    logger.info(f"6. ✓ AI agent imported: {root_agent is not None}")
except Exception as e:
    logger.info(f"6. ⚠ AI agent import failed (expected): {e}")

# Test 6: Socket.IO
try:
    logger.info("7. Testing Socket.IO import...")
    import socketio
    logger.info("7. ✓ Socket.IO imported")
    
    logger.info("8. Testing Socket.IO AsyncServer creation...")
    sio = socketio.AsyncServer(async_mode="asgi")
    logger.info("8. ✓ Socket.IO AsyncServer created")
except Exception as e:
    logger.error(f"7-8. ✗ Socket.IO failed: {e}")
    sys.exit(1)

logger.info("✅ All tests passed! The hang is likely in the full initialization sequence.")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting test server on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")