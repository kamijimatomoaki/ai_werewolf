# Cloud Run デプロイガイド

このドキュメントでは、AI人狼オンラインをGoogle Cloud Runにデプロイする方法を説明します。

## 前提条件

- Google Cloud Project
- gcloud CLI がインストール済み
- Cloud Build API が有効化済み
- Cloud Run API が有効化済み
- Cloud SQL Admin API が有効化済み
- Secret Manager API が有効化済み

## セットアップ手順

### 1. Google Cloud プロジェクトの準備

```bash
# プロジェクトを設定
export GOOGLE_CLOUD_PROJECT="your-project-id"
gcloud config set project $GOOGLE_CLOUD_PROJECT

# 必要なAPIを有効化
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable vpcaccess.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### 2. 自動デプロイ（推奨）

```bash
# リポジトリをクローン
git clone git@github.com:kamijimatomoaki/tg_app.git
cd tg_app

# デプロイスクリプトを実行
./scripts/deploy-cloudrun.sh
```

### 3. 手動デプロイ

#### Cloud Build Triggerの設定

```bash
# GitHub連携の設定
gcloud builds triggers create github \
    --repo-name=tg_app \
    --repo-owner=kamijimatomoaki \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml
```

#### 手動ビルド・デプロイ

```bash
# 手動でCloud Buildを実行
gcloud builds submit --config=cloudbuild.yaml .
```

## 設定詳細

### Cloud Run Services

#### Backend Service
- **名前**: `werewolf-backend`
- **リージョン**: `asia-northeast1`
- **CPU**: 1 vCPU
- **メモリ**: 1GB
- **最大インスタンス**: 10
- **同時接続数**: 80
- **タイムアウト**: 300秒

#### Frontend Service
- **名前**: `werewolf-frontend`
- **リージョン**: `asia-northeast1`
- **CPU**: 1 vCPU
- **メモリ**: 512MB
- **最大インスタンス**: 5
- **同時接続数**: 100
- **タイムアウト**: 60秒

### 環境変数

#### Backend
```yaml
GOOGLE_CLOUD_PROJECT: プロジェクトID
GOOGLE_CLOUD_REGION: asia-northeast1
ENVIRONMENT: production
LOG_LEVEL: INFO
PORT: 8080
```

#### Secrets
- `DATABASE_URL`: Cloud SQL接続文字列
- `REDIS_URL`: Redis接続文字列（将来使用）
- `SECRET_KEY`: アプリケーション秘密鍵

### データベース設定

```bash
# Cloud SQL インスタンス
gcloud sql instances create werewolf-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=asia-northeast1 \
    --storage-type=SSD \
    --storage-size=20GB

# データベースとユーザー作成
gcloud sql databases create werewolf_game --instance=werewolf-db
gcloud sql users create werewolf_user --instance=werewolf-db --password=werewolf_password
```

## モニタリング

### ログの確認

```bash
# バックエンドログ
gcloud logs read 'resource.type=cloud_run_revision AND resource.labels.service_name=werewolf-backend' --limit=50

# フロントエンドログ  
gcloud logs read 'resource.type=cloud_run_revision AND resource.labels.service_name=werewolf-frontend' --limit=50

# Cloud Buildログ
gcloud builds list --limit=10
```

### メトリクス監視

```bash
# サービス状況確認
gcloud run services list --region=asia-northeast1

# リビジョン確認
gcloud run revisions list --service=werewolf-backend --region=asia-northeast1
```

## カスタムドメイン設定

```bash
# カスタムドメインのマッピング
gcloud run domain-mappings create \
    --service=werewolf-frontend \
    --domain=yourdomain.com \
    --region=asia-northeast1
```

## セキュリティ設定

### IAM権限

```bash
# サービスアカウント作成
gcloud iam service-accounts create werewolf-backend-sa \
    --display-name="Werewolf Backend Service Account"

# 必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:werewolf-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:werewolf-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### Secret Manager

```bash
# 秘密情報の管理
gcloud secrets create DATABASE_URL --data-file=db_url.txt
gcloud secrets create SECRET_KEY --data-file=secret_key.txt

# 権限付与
gcloud secrets add-iam-policy-binding DATABASE_URL \
    --member="serviceAccount:werewolf-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## トラブルシューティング

### よくある問題

1. **Cloud Build失敗**
   ```bash
   # ビルドログ確認
   gcloud builds list --limit=5
   gcloud builds log BUILD_ID
   ```

2. **Database接続エラー**
   ```bash
   # Cloud SQL Proxy接続テスト
   cloud_sql_proxy -instances=$PROJECT_ID:asia-northeast1:werewolf-db=tcp:5432
   ```

3. **メモリ不足**
   ```bash
   # メモリ制限を増加
   gcloud run services update werewolf-backend \
       --memory=2Gi \
       --region=asia-northeast1
   ```

4. **タイムアウトエラー**
   ```bash
   # タイムアウト時間を延長
   gcloud run services update werewolf-backend \
       --timeout=600 \
       --region=asia-northeast1
   ```

### ロールバック

```bash
# 前のリビジョンにロールバック
gcloud run services update-traffic werewolf-backend \
    --to-revisions=werewolf-backend-00001-abc=100 \
    --region=asia-northeast1
```

## コスト最適化

### 最小インスタンス設定

```bash
# 最小インスタンス数を0に設定（コールドスタートを許可）
gcloud run services update werewolf-backend \
    --min-instances=0 \
    --region=asia-northeast1
```

### リソース制限

```bash
# CPUとメモリを最適化
gcloud run services update werewolf-backend \
    --cpu=1 \
    --memory=512Mi \
    --region=asia-northeast1
```

## CI/CDパイプライン

GitHub Actionsとの連携例:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: google-github-actions/setup-gcloud@v0
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ secrets.GCP_PROJECT_ID }}
    - run: gcloud builds submit --config=cloudbuild.yaml .
```