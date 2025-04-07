# Sleepy Capybara Chat

ローカルSLMを活用したチャットアプリケーション

## 開発環境のセットアップ

### 前提条件

- Docker と Docker Compose がインストールされていること
- NVIDIA GPU ドライバーがインストールされていること（GPU利用の場合）
- WSL2 がインストールされていること（Windowsの場合）

### 1. リポジトリのクローン

```bash
git clone https://github.com/[username]/sleepy-capybara-chat.git
cd sleepy-capybara-chat
```

### 2. 環境変数の設定

`.env` ファイルを作成し、以下の内容を設定します：

```bash
# PostgreSQL
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=chatdb

# JWT
JWT_SECRET_KEY=your_jwt_secret_key

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

### 3. Docker コンテナの起動

```bash
# 開発環境用のコンテナを起動
docker compose up --build
```

### 4. Ollamaのセットアップ

チャット機能を使用するには、Ollamaコンテナ内に言語モデルをインストールする必要があります。
以下のコマンドを実行して、必要なモデルをダウンロードしてください：

```bash
# 利用可能なモデルの一覧を表示
docker compose exec ollama ollama list

# モデルのダウンロード（例：llama3）
docker compose exec ollama ollama pull llama3
```

注意：
- モデルのダウンロードには時間がかかる場合があります（モデルサイズによって数分から数十分）
- 初回のチャットリクエスト時は、モデルのロードに時間がかかる場合があります

### 5. 開発サーバーの起動

#### フロントエンド（Next.js）

```bash
cd frontend
npm install
npm run dev
```

#### バックエンド（FastAPI）

```bash
cd backend
poetry install
poetry run uvicorn main:app --reload
```

### 6. アクセス方法

- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:8000
- APIドキュメント: http://localhost:8000/docs

## プロジェクト構造

```
sleepy-capybara-chat/
├── frontend/           # Next.js フロントエンド
├── backend/            # FastAPI バックエンド
├── nginx/              # Nginx 設定
├── docker-compose.yml  # Docker Compose 設定
└── .env                # 環境変数
```

## 開発時の注意点

1. **GPU利用の確認**
   - `nvidia-smi` コマンドでGPU認識を確認
   - 必要に応じて `docker-compose.yml` のGPU設定を調整

2. **デバッグ**
   - コンテナ内のログを確認：`docker-compose logs -f [service_name]`
   - VSCodeのDocker拡張機能を使用すると便利

3. **環境変数**
   - 開発用：`.env.development`
   - 本番用：`.env.production`
   - シークレット情報は`.env`ファイルで管理

## 技術スタック

- フロントエンド: Next.js, React, TypeScript, TailwindCSS
- バックエンド: FastAPI, Python 3.13+
- データベース: PostgreSQL
- AI/LLM: Ollama API
- コンテナ化: Docker, Docker Compose
- リバースプロキシ: Nginx

## ライセンス

MIT License 
