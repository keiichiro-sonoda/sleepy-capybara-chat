# ========================================
# Docker環境管理用Makefile
# ========================================

# デフォルトターゲット
.DEFAULT_GOAL := help

# ヘルプ表示
help:
	@echo "利用可能なコマンド:"
	@echo "  dev-up       - 開発環境を起動"
	@echo "  dev-down     - 開発環境を停止"
	@echo "  dev-build    - 開発環境の再ビルド"
	@echo "  dev-logs     - 開発環境のログ表示"
	@echo ""
	@echo "  prod-up      - 本番環境を起動"
	@echo "  prod-down    - 本番環境を停止"
	@echo "  prod-build   - 本番環境の再ビルド"
	@echo "  prod-logs    - 本番環境のログ表示"
	@echo ""
	@echo "  backup       - データベースバックアップ"
	@echo "  clean        - 未使用のDockerリソースを削除"

# ========================================
# 開発環境用コマンド
# ========================================

dev-up:
	@echo "🚀 開発環境を起動しています..."
	docker-compose up -d

dev-down:
	@echo "🛑 開発環境を停止しています..."
	docker-compose down

dev-build:
	@echo "🔨 開発環境を再ビルドしています..."
	docker-compose build --no-cache
	docker-compose up -d

dev-logs:
	@echo "📋 開発環境のログを表示しています..."
	docker-compose logs -f

dev-restart:
	@echo "🔄 開発環境を再起動しています..."
	docker-compose restart

# ========================================
# 本番環境用コマンド
# ========================================

prod-up:
	@echo "🚀 本番環境を起動しています..."
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	@echo "🛑 本番環境を停止しています..."
	docker-compose -f docker-compose.prod.yml down

prod-build:
	@echo "🔨 本番環境を再ビルドしています..."
	docker-compose -f docker-compose.prod.yml build --no-cache
	docker-compose -f docker-compose.prod.yml up -d

prod-logs:
	@echo "📋 本番環境のログを表示しています..."
	docker-compose -f docker-compose.prod.yml logs -f

prod-restart:
	@echo "🔄 本番環境を再起動しています..."
	docker-compose -f docker-compose.prod.yml restart

# ========================================
# メンテナンス用コマンド
# ========================================

backup:
	@echo "💾 データベースをバックアップしています..."
	@mkdir -p backups
	@DATE=$$(date +%Y%m%d_%H%M%S); \
	docker-compose exec -T db pg_dump -U $${POSTGRES_USER} $${POSTGRES_DB} > backups/backup_$${DATE}.sql && \
	echo "✅ バックアップ完了: backups/backup_$${DATE}.sql"

clean:
	@echo "🧹 未使用のDockerリソースを削除しています..."
	docker system prune -a --volumes -f
	@echo "✅ クリーンアップ完了"

# ========================================
# デバッグ用コマンド
# ========================================

dev-shell-backend:
	@echo "🐚 バックエンドコンテナに接続しています..."
	docker-compose exec backend bash

dev-shell-frontend:
	@echo "🐚 フロントエンドコンテナに接続しています..."
	docker-compose exec frontend sh

dev-shell-db:
	@echo "🗄️ データベースに接続しています..."
	docker-compose exec db psql -U $${POSTGRES_USER} $${POSTGRES_DB}

# ========================================
# 環境変数チェック用
# ========================================

check-env:
	@echo "🔍 環境変数をチェックしています..."
	@echo "POSTGRES_USER: $${POSTGRES_USER}"
	@echo "POSTGRES_DB: $${POSTGRES_DB}"
	@echo "FRONTEND_URL: $${FRONTEND_URL}"
	@echo "JWT_SECRET_KEY: [設定済み]" # セキュリティのため値は表示しない

.PHONY: help dev-up dev-down dev-build dev-logs dev-restart prod-up prod-down prod-build prod-logs prod-restart backup clean dev-shell-backend dev-shell-frontend dev-shell-db check-env
