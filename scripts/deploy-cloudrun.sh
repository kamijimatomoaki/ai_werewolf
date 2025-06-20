#!/bin/bash
# Cloud Run デプロイスクリプト

set -e

# 設定
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"fourth-dynamo-423103-q2"}
REGION="asia-northeast1"
BACKEND_SERVICE="werewolf-backend"
FRONTEND_SERVICE="werewolf-frontend"

echo "🚀 AI人狼オンライン Cloud Run デプロイ開始"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Google Cloud SDKの設定確認
echo "📋 Google Cloud SDK設定確認..."
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# サービスアカウントの作成
echo "👤 サービスアカウント作成..."
gcloud iam service-accounts create werewolf-backend-sa \
    --display-name="Werewolf Backend Service Account" \
    --description="Service account for werewolf backend on Cloud Run" \
    || echo "Service account already exists"

# IAM権限の設定
echo "🔐 IAM権限設定..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:werewolf-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:werewolf-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:werewolf-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Cloud SQL インスタンスの作成
echo "🗄️ Cloud SQL インスタンス確認..."
gcloud sql instances describe werewolf-db --region=$REGION || {
    echo "Cloud SQL インスタンスを作成中..."
    gcloud sql instances create werewolf-db \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=20GB \
        --backup-start-time=03:00 \
        --enable-bin-log \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=04 \
        --deletion-protection
}

# データベースとユーザーの作成
echo "👤 データベースユーザー作成..."
gcloud sql users create werewolf_user \
    --instance=werewolf-db \
    --password=werewolf_password \
    || echo "User already exists"

gcloud sql databases create werewolf_game \
    --instance=werewolf-db \
    || echo "Database already exists"

# Secretの作成
echo "🔐 Secret Manager設定..."
echo "postgresql://werewolf_user:werewolf_password@localhost/werewolf_game?host=/cloudsql/$PROJECT_ID:$REGION:werewolf-db" | \
    gcloud secrets create DATABASE_URL --data-file=- || echo "DATABASE_URL secret already exists"

echo "redis://localhost:6379" | \
    gcloud secrets create REDIS_URL --data-file=- || echo "REDIS_URL secret already exists"

openssl rand -base64 32 | \
    gcloud secrets create SECRET_KEY --data-file=- || echo "SECRET_KEY secret already exists"

# VPCコネクタの作成
echo "🌐 VPCコネクタ作成..."
gcloud compute networks vpc-access connectors create werewolf-connector \
    --region=$REGION \
    --subnet-project=$PROJECT_ID \
    --subnet=default \
    --min-instances=2 \
    --max-instances=3 \
    --machine-type=f1-micro \
    || echo "VPC connector already exists"

# Cloud Buildを使用してビルド・デプロイ
echo "🔨 Cloud Build実行..."
gcloud builds submit --config=cloudbuild.yaml .

echo "✅ デプロイ完了！"
echo ""
echo "📊 サービス情報:"
echo "Backend:  $(gcloud run services describe $BACKEND_SERVICE --region=$REGION --format='value(status.url)')"
echo "Frontend: $(gcloud run services describe $FRONTEND_SERVICE --region=$REGION --format='value(status.url)')"
echo ""
echo "🔍 ログ確認:"
echo "gcloud logs read 'resource.type=cloud_run_revision AND resource.labels.service_name=$BACKEND_SERVICE' --limit=50"
echo "gcloud logs read 'resource.type=cloud_run_revision AND resource.labels.service_name=$FRONTEND_SERVICE' --limit=50"