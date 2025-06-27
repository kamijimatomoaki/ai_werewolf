# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

日本語で必ず回答してください。
本番はCloudrunの環境にデプロイします。
デプロイしたい場合は、Githubにプッシュすることで自動でデプロイが始まり、5分後にデプロイが完了します。
テストにはPlaywrightのMCPサーバーを使うことができます。

ClaudeRunのサービス
https://werewolf-backend-483231515533.asia-northeast1.run.app
https://werewolf-frontend-483231515533.asia-northeast1.run.app

github
https://github.com/kamijimatomoaki/tg_app

データベース
postgresql://postgres:fall0408@/ai_werewolf

## Project Overview

This is an AI-powered multiplayer Werewolf (Mafia) game application with real-time gameplay where humans and AI players compete together. The application consists of a FastAPI backend with WebSocket support and a React/TypeScript frontend.

## Architecture

### Backend (`/backend/game_logic/`)
- **FastAPI** server with Socket.IO for real-time communication
- **SQLAlchemy** ORM with PostgreSQL database
- **Google Vertex AI** integration for AI players (`/backend/npc_agent/`)
- Game logic handles room management, player actions, and game phases
- Main entry point: `main.py`

### Frontend (`/frontend/`)
- **React + TypeScript** with Vite build system
- **HeroUI** component library with Tailwind CSS
- Real-time WebSocket connections via Socket.IO client
- Game components in `/src/components/game/`
- WebSocket hooks and API services in `/src/hooks/` and `/src/services/`

## Development Commands

### Frontend Development
```bash
cd frontend
npm run dev          # Start development server
npm run build        # Production build
npm run build-with-check  # Build with TypeScript checking
npm run lint         # Run ESLint with auto-fix
npm run preview      # Preview production build
```

### Backend Development
```bash
cd backend/game_logic
python main.py       # Start development server
```

### Docker Development (Recommended)
```bash
make dev            # Start development environment
make dev-down       # Stop development environment
make dev-logs       # View development logs
make health         # Check service health
```

### Production & Deployment
```bash
make build          # Build Docker images
make up             # Start production services
make down           # Stop services
make deploy-cloudrun # Deploy to Google Cloud Run
make status-cloudrun # Check Cloud Run deployment status
```

### Database Operations
```bash
make db-migrate     # Create database tables
make shell-db       # Connect to PostgreSQL database
```

## Key Components

### Game Flow
- Room creation and management (`/backend/game_logic/main.py`)
- WebSocket event handlers for real-time communication
- Game phases: Day discussion, voting, night actions
- AI player integration with Google Vertex AI

### Frontend Structure
- `GameRoom.tsx` - Main game interface
- Game-specific components in `/src/components/game/`
- WebSocket management in `/src/hooks/useWebSocket.ts`
- API client in `/src/services/api.ts`

### Environment Setup
Backend requires:
- `DATABASE_URL` - PostgreSQL connection string
- `GOOGLE_CLOUD_PROJECT` - GCP project ID for Vertex AI
- `GOOGLE_CLOUD_REGION` - GCP region (default: asia-northeast1)

## Testing
```bash
make test           # Run backend tests via Docker
```

The codebase uses primarily Japanese comments and documentation, with English for technical configurations.