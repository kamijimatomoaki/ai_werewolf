# AI人狼オンライン - Docker管理用Makefile

.PHONY: help build up down logs clean dev test

# デフォルトタスク
help:
	@echo "AI人狼オンライン - Docker管理コマンド"
	@echo ""
	@echo "本番環境:"
	@echo "  build     - Dockerイメージをビルド"
	@echo "  up        - サービスを起動"
	@echo "  down      - サービスを停止"
	@echo "  restart   - サービスを再起動"
	@echo "  logs      - ログを表示"
	@echo ""
	@echo "開発環境:"
	@echo "  dev       - 開発環境を起動"
	@echo "  dev-down  - 開発環境を停止"
	@echo "  dev-logs  - 開発環境のログを表示"
	@echo ""
	@echo "メンテナンス:"
	@echo "  clean     - 未使用のDockerリソースを削除"
	@echo "  reset     - 全データを削除して再構築"
	@echo "  test      - テストを実行"
	@echo "  shell-backend  - バックエンドコンテナにシェル接続"
	@echo "  shell-db       - データベースに接続"

# 本番環境コマンド
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart: down up

logs:
	docker-compose logs -f

# 開発環境コマンド
dev:
	docker-compose -f docker-compose.dev.yml up -d

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# メンテナンスコマンド
clean:
	docker system prune -f
	docker volume prune -f
	docker image prune -f

reset:
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d

# テスト
test:
	docker-compose exec backend pytest

# デバッグ用シェル
shell-backend:
	docker-compose exec backend /bin/bash

shell-db:
	docker-compose exec database psql -U werewolf_user -d werewolf_game

# ヘルスチェック
health:
	@echo "=== サービス状態確認 ==="
	docker-compose ps
	@echo ""
	@echo "=== ヘルスチェック ==="
	@curl -f http://localhost:8000/health 2>/dev/null && echo "✅ Backend: OK" || echo "❌ Backend: NG"
	@curl -f http://localhost/ 2>/dev/null && echo "✅ Frontend: OK" || echo "❌ Frontend: NG"

# ログの個別表示
logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-db:
	docker-compose logs -f database

# データベース操作
db-migrate:
	docker-compose exec backend python -c "from game_logic.main import Base, engine; Base.metadata.create_all(bind=engine)"

db-seed:
	docker-compose exec backend python scripts/seed_data.py

# 本番デプロイ用
deploy-prod: build
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d