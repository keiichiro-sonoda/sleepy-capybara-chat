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

プロジェクトは複数の環境変数ファイルを使用します：

1. **プロジェクトルート**に`.env`ファイルを作成し、Docker Compose全体の設定を行います：

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

2. **フロントエンド**用の環境変数は`frontend/.env.local`に設定します：

```bash
# バックエンドAPI接続設定
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

3. **バックエンド**固有の設定は`backend/.env`に設定します。

> 詳細な環境変数管理の方針については[環境変数管理ドキュメント](docs/ENV_MANAGEMENT.md)を参照してください。

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
├── .env                # プロジェクト共通環境変数
└── docs/               # プロジェクトドキュメント
```

## 開発時の注意点

1. **GPU利用の確認**
   - `nvidia-smi` コマンドでGPU認識を確認
   - 必要に応じて `docker-compose.yml` のGPU設定を調整

2. **デバッグ**
   - コンテナ内のログを確認：`docker-compose logs -f [service_name]`
   - VSCodeのDocker拡張機能を使用すると便利

3. **環境変数管理**
   - 環境変数は用途に応じて適切なファイルに分離して管理
   - 詳細は[環境変数管理ドキュメント](docs/ENV_MANAGEMENT.md)を参照
   - フロントエンド用の環境変数は`frontend/.env.local`で設定
   - バックエンド用の環境変数は`backend/.env`で設定
   - Docker Compose全体の設定はルートの`.env`で設定

4. **Dockerでのフロントエンド開発**
   - ホットリロード対応：`CHOKIDAR_USEPOLLING=true`と`WATCHPACK_POLLING=true`を設定
   - ホスト設定：Next.jsは`-H 0.0.0.0`で実行（詳細は`frontend/DEVELOPMENT.md`を参照）
   - APIエンドポイント：`NEXT_PUBLIC_API_URL`環境変数でバックエンドへの接続を設定

## 技術スタック

- フロントエンド: Next.js, React, TypeScript, TailwindCSS
- バックエンド: FastAPI, Python 3.13+
- データベース: PostgreSQL
- AI/LLM: Ollama API
- コンテナ化: Docker, Docker Compose
- リバースプロキシ: Nginx

## ライセンス

MIT License
