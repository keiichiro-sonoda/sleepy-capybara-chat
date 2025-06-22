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

# 環境変数設定
cp .env.example .env
nano .env  # 必要な設定を編集

# サービス起動（nginxなし構成）
docker-compose up -d backend frontend db ollama cloudflared

# ログ確認
docker-compose logs -f cloudflared
```

### 3. 環境変数設定例

```bash
# .env ファイル
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

# メール設定（Gmail SMTP）
EMAIL_SERVICE=gmail
GMAIL_USERNAME=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
GMAIL_SMTP_SERVER=smtp.gmail.com
GMAIL_SMTP_PORT=587
```

### 4. 動作確認

```bash
# サービス状態確認
docker-compose ps

# アプリケーションアクセス
curl https://chat.sleepycapybara.org
curl https://api.sleepycapybara.org/health
```

### 5. トラブルシューティング

```bash
# ログ確認
docker-compose logs backend
docker-compose logs frontend
docker-compose logs cloudflared

# サービス再起動
docker-compose restart
```

## メンテナンス

### 定期的なアップデート

```bash
# コードアップデート
git pull origin main

# イメージ再ビルド
docker-compose build --no-cache

# サービス再起動
docker-compose up -d
```

### バックアップ

```bash
# データベースバックアップ
docker-compose exec db pg_dump -U sleepy_user sleepy_capybara_chat > backup.sql

# 環境設定バックアップ
cp .env .env.backup
```

## セキュリティ推奨事項

1. `.env`ファイルの権限設定: `chmod 600 .env`
2. 定期的なシステムアップデート
3. Cloudflareセキュリティ設定の確認
4. データベースパスワードの強化

## パフォーマンス最適化

### Docker限定事項

```yaml
# docker-compose.yml に追加可能な最適化
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
```

### ディスク容量管理

```bash
# 未使用イメージの削除
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
