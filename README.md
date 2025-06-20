# AI人狼オンライン (AI Werewolf Online)

リアルタイムマルチプレイヤー対応のAI人狼ゲームアプリケーションです。人間とAIが一緒にプレイできる革新的な人狼ゲーム体験を提供します。

## 特徴

- 🤖 **AI vs 人間**: 高度なAIプレイヤーと人間が同じゲームで対戦
- 🌐 **リアルタイム**: WebSocketによるリアルタイム通信
- 👁️ **観戦機能**: ゲームを観戦してチャットで交流
- 🎭 **複数の役職**: 占い師、ボディガード、人狼、村人
- 🎨 **美しいUI**: 現代的で直感的なユーザーインターフェース
- 📱 **レスポンシブ**: デスクトップ・モバイル対応

## 技術スタック

### バックエンド
- **FastAPI**: 高性能WebAPIフレームワーク
- **Socket.IO**: リアルタイム双方向通信
- **SQLAlchemy**: ORM
- **PostgreSQL**: データベース
- **Google Vertex AI**: AI エージェント
- **Pydantic**: データバリデーション

### フロントエンド
- **React**: UIライブラリ
- **TypeScript**: 型安全な開発
- **Vite**: 高速開発サーバー
- **Tailwind CSS**: ユーティリティファーストCSS
- **HeroUI**: UIコンポーネントライブラリ

## セットアップ

### 前提条件
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Google Cloud Project (Vertex AI用)

### バックエンドセットアップ

```bash
# リポジトリをクローン
git clone git@github.com:kamijimatomoaki/tg_app.git
cd tg_app

# Python仮想環境を作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係をインストール
cd backend/game_logic
pip install -r requirements.txt

# 環境変数を設定
export DATABASE_URL="postgresql://username:password@localhost/werewolf_db"
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_REGION="asia-northeast1"

# データベースを初期化
python -c "from main import Base, engine; Base.metadata.create_all(bind=engine)"

# サーバーを起動
python main.py
```

### フロントエンドセットアップ

```bash
# フロントエンドディレクトリに移動
cd frontend

# 依存関係をインストール
npm install

# 開発サーバーを起動
npm run dev
```

## 使用方法

1. **ゲーム作成**: プレイヤー数とAI/人間の比率を設定してルームを作成
2. **ゲーム参加**: ルーム一覧から参加したいゲームを選択
3. **観戦モード**: 進行中のゲームを観戦してチャットで交流
4. **ゲームプレイ**: 各フェーズで議論、投票、特殊能力を使用

## API エンドポイント

主要なAPIエンドポイント:

- `POST /api/rooms` - ゲームルーム作成
- `GET /api/rooms` - ルーム一覧取得
- `POST /api/rooms/{room_id}/join` - ゲーム参加
- `POST /api/rooms/{room_id}/spectators/join` - 観戦参加
- `POST /api/rooms/{room_id}/start` - ゲーム開始
- `POST /api/rooms/{room_id}/speak` - 発言
- `POST /api/rooms/{room_id}/vote` - 投票

## 開発

### バックエンド開発

```bash
# 開発モードでサーバー起動
cd backend/game_logic
python main.py
```

### フロントエンド開発

```bash
# 開発サーバー起動
cd frontend
npm run dev

# ビルド
npm run build

# リント
npm run lint
```

## 貢献

プロジェクトへの貢献を歓迎します！

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下で提供されています。

## 作者

[@kamijimatomoaki](https://github.com/kamijimatomoaki)