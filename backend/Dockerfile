# Python 3.11 slim image
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をコピーしてインストール
COPY game_logic/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 非rootユーザーを作成
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# ポートを公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# アプリケーションを起動
CMD ["python", "game_logic/main.py"]