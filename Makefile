# ========================================
# Docker環境管理用Makefile
# ========================================

# デフォルトターゲット
.DEFAULT_GOAL := help

# ヘルプ表示
help:
	@echo "利用可能なコマンド:"
	@echo ""
	@echo "🔧 環境全体の操作:"
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
	@echo "🔨 サービス別操作:"
	@echo "  dev-build-backend    - 開発環境のバックエンドのみ再ビルド"
	@echo "  dev-build-frontend   - 開発環境のフロントエンドのみ再ビルド"
	@echo "  prod-build-backend   - 本番環境のバックエンドのみ再ビルド"
	@echo "  prod-build-frontend  - 本番環境のフロントエンドのみ再ビルド"
	@echo ""
	@echo "🔄 サービス別再起動:"
	@echo "  dev-restart-backend  - 開発環境のバックエンドのみ再起動"
	@echo "  dev-restart-frontend - 開発環境のフロントエンドのみ再起動"
	@echo "  prod-restart-backend - 本番環境のバックエンドのみ再起動"
	@echo "  prod-restart-frontend - 本番環境のフロントエンドのみ再起動"
	@echo ""
	@echo "📋 サービス別ログ:"
	@echo "  dev-logs-backend     - 開発環境のバックエンドログ表示"
	@echo "  dev-logs-frontend    - 開発環境のフロントエンドログ表示"
	@echo "  prod-logs-backend    - 本番環境のバックエンドログ表示"
	@echo "  prod-logs-frontend   - 本番環境のフロントエンドログ表示"
	@echo ""
	@echo "🤖 Ollamaモデル管理:"
	@echo "  dev-models   - 開発環境のモデル一覧表示"
	@echo "  prod-models  - 本番環境のモデル一覧表示"
	@echo ""
	@echo "🛠️ メンテナンス:"
	@echo "  backup       - データベースバックアップ"
	@echo "  clean        - 未使用のDockerリソースを削除"

# ========================================
# 開発環境用コマンド
# ========================================

dev-up:
	@echo "🚀 開発環境を起動しています..."
	docker compose up -d

dev-down:
	@echo "🛑 開発環境を停止しています..."
	docker compose down

dev-build:
	@echo "🔨 開発環境を再ビルドしています..."
	docker compose build --no-cache
	docker compose up -d

dev-logs:
	@echo "📋 開発環境のログを表示しています..."
	docker compose logs -f

dev-restart:
	@echo "🔄 開発環境を再起動しています..."
	docker compose restart

# ========================================
# 開発環境 - サービス別操作
# ========================================

dev-build-backend:
	@echo "🔨 開発環境のバックエンドを再ビルドしています..."
	docker compose build --no-cache backend
	docker compose up -d backend
	@echo "✅ バックエンドの再ビルド完了"

dev-build-frontend:
	@echo "🔨 開発環境のフロントエンドを再ビルドしています..."
	docker compose build --no-cache frontend
	docker compose up -d frontend
	@echo "✅ フロントエンドの再ビルド完了"

dev-restart-backend:
	@echo "🔄 開発環境のバックエンドを再起動しています..."
	docker compose restart backend
	@echo "✅ バックエンドの再起動完了"

dev-restart-frontend:
	@echo "🔄 開発環境のフロントエンドを再起動しています..."
	docker compose restart frontend
	@echo "✅ フロントエンドの再起動完了"

dev-logs-backend:
	@echo "📋 開発環境のバックエンドログを表示しています..."
	docker compose logs -f backend

dev-logs-frontend:
	@echo "📋 開発環境のフロントエンドログを表示しています..."
	docker compose logs -f frontend

# ========================================
# 本番環境用コマンド
# ========================================

prod-up:
	@echo "🚀 本番環境を起動しています..."
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	@echo "🛑 本番環境を停止しています..."
	docker compose -f docker-compose.prod.yml down

prod-build:
	@echo "🔨 本番環境を再ビルドしています..."
	docker compose -f docker-compose.prod.yml build --no-cache
	docker compose -f docker-compose.prod.yml up -d

prod-logs:
	@echo "📋 本番環境のログを表示しています..."
	docker compose -f docker-compose.prod.yml logs -f

prod-restart:
	@echo "🔄 本番環境を再起動しています..."
	docker compose -f docker-compose.prod.yml restart

# ========================================
# 本番環境 - サービス別操作
# ========================================

prod-build-backend:
	@echo "🔨 本番環境のバックエンドを再ビルドしています..."
	docker compose -f docker-compose.prod.yml build --no-cache backend
	docker compose -f docker-compose.prod.yml up -d backend
	@echo "✅ バックエンドの再ビルド完了"

prod-build-frontend:
	@echo "🔨 本番環境のフロントエンドを再ビルドしています..."
	docker compose -f docker-compose.prod.yml build --no-cache frontend
	docker compose -f docker-compose.prod.yml up -d frontend
	@echo "✅ フロントエンドの再ビルド完了"

prod-restart-backend:
	@echo "🔄 本番環境のバックエンドを再起動しています..."
	docker compose -f docker-compose.prod.yml restart backend
	@echo "✅ バックエンドの再起動完了"

prod-restart-frontend:
	@echo "🔄 本番環境のフロントエンドを再起動しています..."
	docker compose -f docker-compose.prod.yml restart frontend
	@echo "✅ フロントエンドの再起動完了"

prod-logs-backend:
	@echo "📋 本番環境のバックエンドログを表示しています..."
	docker compose -f docker-compose.prod.yml logs -f backend

prod-logs-frontend:
	@echo "📋 本番環境のフロントエンドログを表示しています..."
	docker compose -f docker-compose.prod.yml logs -f frontend

# ========================================
# Ollamaモデル管理用コマンド
# ========================================

dev-models:
	@echo "🤖 開発環境のOllamaモデル一覧を表示しています..."
	docker compose exec ollama ollama list

prod-models:
	@echo "🤖 本番環境のOllamaモデル一覧を表示しています..."
	docker compose -f docker-compose.prod.yml exec ollama ollama list

dev-pull-model:
	@echo "📥 開発環境にモデルをダウンロードしています..."
	@if [ -z "$(MODEL)" ]; then \
		echo "❌ エラー: MODEL変数が設定されていません"; \
		echo "使用例: make dev-pull-model MODEL=llama3"; \
		exit 1; \
	fi
	docker compose exec ollama ollama pull $(MODEL)
	@echo "✅ $(MODEL)のダウンロード完了（開発環境）"

prod-pull-model:
	@echo "📥 本番環境にモデルをダウンロードしています..."
	@if [ -z "$(MODEL)" ]; then \
		echo "❌ エラー: MODEL変数が設定されていません"; \
		echo "使用例: make prod-pull-model MODEL=llama3"; \
		exit 1; \
	fi
	docker compose -f docker-compose.prod.yml exec ollama ollama pull $(MODEL)
	@echo "✅ $(MODEL)のダウンロード完了（本番環境）"

# ========================================
# メンテナンス用コマンド
# ========================================

backup:
	@echo "💾 データベースをバックアップしています..."
	@mkdir -p backups
	@DATE=$$(date +%Y%m%d_%H%M%S); \
	docker compose exec -T db pg_dump -U $${POSTGRES_USER} $${POSTGRES_DB} > backups/backup_$${DATE}.sql && \
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
	docker compose exec backend bash

dev-shell-frontend:
	@echo "🐚 フロントエンドコンテナに接続しています..."
	docker compose exec frontend sh

dev-shell-db:
	@echo "🗄️ データベースに接続しています..."
	docker compose exec db psql -U $${POSTGRES_USER} $${POSTGRES_DB}

# ========================================
# 環境変数チェック用
# ========================================

check-env:
	@echo "🔍 環境変数をチェックしています..."
	@echo "POSTGRES_USER: $${POSTGRES_USER}"
	@echo "POSTGRES_DB: $${POSTGRES_DB}"
	@echo "FRONTEND_URL: $${FRONTEND_URL}"
	@echo "JWT_SECRET_KEY: [設定済み]" # セキュリティのため値は表示しない

.PHONY: help dev-up dev-down dev-build dev-logs dev-restart dev-build-backend dev-build-frontend dev-restart-backend dev-restart-frontend dev-logs-backend dev-logs-frontend prod-up prod-down prod-build prod-logs prod-restart prod-build-backend prod-build-frontend prod-restart-backend prod-restart-frontend prod-logs-backend prod-logs-frontend dev-models prod-models dev-pull-model prod-pull-model backup clean dev-shell-backend dev-shell-frontend dev-shell-db check-env
