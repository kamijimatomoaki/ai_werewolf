# Docker セットアップガイド

このドキュメントでは、AI人狼オンラインをDockerを使用して実行する方法を説明します。

## 前提条件

- Docker Engine 20.0+
- Docker Compose 2.0+
- 8GB以上のRAM
- Google Cloud Project (Vertex AI用)

## クイックスタート

### 1. リポジトリのクローン

```bash
git clone git@github.com:kamijimatomoaki/tg_app.git
cd tg_app
```

### 2. 環境変数の設定

```bash
# 環境変数ファイルをコピー
cp .env.docker.example .env

# 必要な環境変数を編集
nano .env
```

必須の環境変数：
- `GOOGLE_CLOUD_PROJECT`: Google CloudプロジェクトID
- `GOOGLE_CLOUD_REGION`: リージョン（デフォルト: asia-northeast1）

### 3. Google Cloud認証の設定

```bash
# Google Cloud CLIでログイン
gcloud auth login
gcloud auth application-default login

# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID
```

### 4. アプリケーションの起動

```bash
# 本番環境での起動
make up

# または直接docker-composeを使用
docker-compose up -d
```

### 5. アクセス確認

- フロントエンド: http://localhost
- バックエンドAPI: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

## 開発環境

開発時はホットリロード対応の環境を使用できます：

```bash
# 開発環境の起動
make dev

# ログの確認
make dev-logs

# 停止
make dev-down
```

## 利用可能なコマンド

```bash
# ヘルプを表示
make help

# サービスの状態確認
make health

# ログの確認
make logs
make logs-backend
make logs-frontend
make logs-db

# データベース操作
make db-migrate    # テーブル作成
make shell-db      # データベースに接続

# デバッグ
make shell-backend # バックエンドコンテナにシェル接続

# メンテナンス
make clean         # 未使用リソースの削除
make reset         # 完全リセット
```

## サービス構成

### backend
- **ポート**: 8000
- **説明**: FastAPI + Socket.IO サーバー
- **ヘルスチェック**: `/health`

### frontend  
- **ポート**: 80
- **説明**: React アプリケーション (Nginx)
- **ヘルスチェック**: `/`

### database
- **ポート**: 5432
- **説明**: PostgreSQL 15
- **認証**: werewolf_user / werewolf_password

### redis
- **ポート**: 6379  
- **説明**: Redis (セッション・キャッシュ)

## トラブルシューティング

### よくある問題

1. **Google Cloud認証エラー**
   ```bash
   # 認証を再実行
   gcloud auth application-default login
   ```

2. **ポート競合**
   ```bash
   # 使用中のポートを確認
   sudo lsof -i :80
   sudo lsof -i :8000
   ```

3. **データベース接続エラー**
   ```bash
   # データベースの状態確認
   docker-compose logs database
   
   # テーブルの再作成
   make db-migrate
   ```

4. **メモリ不足**
   ```bash
   # リソース使用量確認
   docker stats
   
   # 未使用リソースの削除
   make clean
   ```

### ログの確認

```bash
# 全サービスのログ
make logs

# 特定サービスのログ
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f database
```

### データの永続化

データは以下のDockerボリュームに永続化されます：

- `postgres_data`: データベースデータ
- `redis_data`: Redisデータ

データを完全に削除する場合：

```bash
docker-compose down -v
```

## 本番環境での注意事項

1. **環境変数の設定**
   - `SECRET_KEY`を本番用に変更
   - `DATABASE_URL`を外部データベースに変更
   - `CORS_ORIGINS`を本番ドメインに設定

2. **セキュリティ**
   - データベースのパスワードを変更
   - HTTPSを有効化
   - ファイアウォール設定

3. **モニタリング**
   - ログ収集の設定
   - メトリクス監視
   - アラート設定

## パフォーマンス最適化

### リソース制限の設定

```yaml
# docker-compose.yml に追加
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

### スケーリング

```bash
# バックエンドを3つのインスタンスで実行
docker-compose up -d --scale backend=3
```