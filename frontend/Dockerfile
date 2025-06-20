# マルチステージビルド

# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# パッケージファイルをコピー
COPY package*.json ./

# 依存関係をインストール
RUN npm ci --only=production

# ソースコードをコピー
COPY . .

# アプリケーションをビルド
RUN npm run build

# Production stage
FROM nginx:alpine

# カスタムnginx設定をコピー
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ビルドされたアプリケーションをコピー
COPY --from=builder /app/dist /usr/share/nginx/html

# 非rootユーザーで実行
RUN addgroup -g 1001 -S nginx && \
    adduser -S nginx -u 1001

# ポートを公開
EXPOSE 80

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# nginxを起動
CMD ["nginx", "-g", "daemon off;"]