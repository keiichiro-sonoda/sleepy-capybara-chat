# オンプレサーバーデプロイガイド

## 概要

Cloudflare Tunnelを使用したオンプレサーバーへのデプロイ手順です。

## 前提条件

- Docker及びDocker Composeがインストールされたサーバー
- Cloudflareアカウントとドメイン設定済み
- 十分なディスク容量（最低20GB推奨）

## デプロイ手順

### 1. サーバー準備

```bash
# システムアップデート
sudo apt update && sudo apt upgrade -y

# 必要なパッケージのインストール
sudo apt install build-essential -y

# Dockerインストール（Ubuntu/Debian）
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Composeインストール
sudo apt install docker-compose-plugin -y

# 再ログインしてDockerグループ権限を適用
logout
```

### 2. プロジェクトのデプロイ

```bash
# リポジトリクローン
git clone <your-repo-url>
cd sleepy-capybara-chat

# 環境変数設定（本番環境用）
cp .env.example .env.prod
nano .env.prod  # 本番環境設定を編集

# サービス起動（Makefileを活用）
make prod-up

# または従来のコマンド
# docker-compose -f docker-compose.prod.yml up -d

# ログ確認
make prod-logs
```

### 3. 環境変数設定例（.env.prod）

```bash
# .env.prod ファイル
POSTGRES_USER=sleepy_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=sleepy_capybara_chat
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here

# API設定
CORS_ORIGINS='["https://chat.sleepycapybara.org"]'
FRONTEND_URL=https://chat.sleepycapybara.org
NEXT_PUBLIC_API_URL=https://api.sleepycapybara.org/api
NEXT_PUBLIC_APP_NAME=Sleepy Capybara Chat

# JWT設定
JWT_SECRET_KEY=your_jwt_secret_key

# メール設定（Gmail SMTP）
EMAIL_SERVICE=gmail
GMAIL_USERNAME=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
GMAIL_SMTP_SERVER=smtp.gmail.com
GMAIL_SMTP_PORT=587
```

### 4. Ollamaモデルのセットアップ

```bash
# 利用可能なモデルの確認
make prod-models

# モデルのダウンロード（例：llama3）
make prod-pull-model MODEL=llama3

# または従来のコマンド
# docker compose -f docker-compose.prod.yml exec ollama ollama pull llama3
```

### 5. GPU設定の確認（オプション）

GPU使用を検討する場合は以下でハードウェアを確認：

```bash
# GPU情報確認
nvidia-smi
lspci | grep -i vga

# OpenCL情報確認
clinfo

# CPU情報確認
lscpu
```

注意：現在の本番環境設定ではGPU設定は無効化されています。必要に応じて`docker-compose.prod.yml`を編集してください。

### 6. 動作確認

```bash
# サービス状態確認
docker compose -f docker-compose.prod.yml ps

# アプリケーションアクセス
curl https://chat.sleepycapybara.org
curl https://api.sleepycapybara.org/health
```

### 7. トラブルシューティング

```bash
# サービス別ログ確認
make prod-logs-backend
make prod-logs-frontend

# サービス別再起動
make prod-restart-backend
make prod-restart-frontend

# 全体再ビルド
make prod-build
```

## 便利なMakefileコマンド

プロジェクトにはMakefileが用意されており、以下のコマンドが利用できます：

```bash
# ヘルプ表示
make help

# 本番環境操作
make prod-up          # 起動
make prod-down        # 停止
make prod-build       # 再ビルド
make prod-logs        # ログ表示
make prod-restart     # 再起動

# サービス別操作
make prod-build-backend    # バックエンドのみ再ビルド
make prod-build-frontend   # フロントエンドのみ再ビルド
make prod-restart-backend  # バックエンドのみ再起動
make prod-restart-frontend # フロントエンドのみ再起動

# Ollamaモデル管理
make prod-models              # モデル一覧
make prod-pull-model MODEL=llama3  # モデルダウンロード

# メンテナンス
make backup           # データベースバックアップ
make clean           # 未使用リソース削除
```

## メンテナンス

### 定期的なアップデート

```bash
# コードアップデート
git pull origin develop  # または適切なブランチ

# イメージ再ビルド
make prod-build

# または従来のコマンド
# docker compose -f docker-compose.prod.yml build --no-cache
# docker compose -f docker-compose.prod.yml up -d
```

### バックアップ

```bash
# Makefileを使用したバックアップ
make backup

# または手動バックアップ
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U sleepy_user sleepy_capybara_chat > backup.sql

# 環境設定バックアップ
cp .env.prod .env.prod.backup
```

## セキュリティ推奨事項

1. `.env.prod`ファイルの権限設定: `chmod 600 .env.prod`
2. 定期的なシステムアップデート
3. Cloudflareセキュリティ設定の確認
4. データベースパスワードの強化

## パフォーマンス最適化

### Docker限定事項

```yaml
# docker-compose.prod.yml に追加可能な最適化
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
```

### ディスク容量管理

```bash
# 未使用イメージの削除（Makefileコマンド推奨）
make clean

# または手動削除
docker system prune -a

# ログローテーション設定
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```
