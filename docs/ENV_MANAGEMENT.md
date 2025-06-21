# 環境変数管理方針

## 基本原則

このプロジェクトでは、環境変数を以下の原則に従って管理します：

1. **分離の原則**: フロントエンドとバックエンドの環境変数は分離する
2. **環境別管理**: 開発/テスト/本番環境で設定を分ける
3. **シークレット保護**: 機密情報はGitに保存しない
4. **明確な所在**: 全ての環境変数の所在を明確にドキュメント化する

## ディレクトリ構造

```text
sleepy-capybara-chat/
├── .env                # プロジェクト共通の環境変数（Gitで管理しない）
├── .env.example        # .envのテンプレート（Gitで管理する）
├── backend/
│   ├── .env            # バックエンド固有の環境変数（Gitで管理しない）
│   └── .env.example    # バックエンド環境変数のテンプレート（Gitで管理する）
└── frontend/
    ├── .env.local      # フロントエンド固有の環境変数（Gitで管理しない）
    └── .env.example    # フロントエンド環境変数のテンプレート（Gitで管理する）
```

## 環境変数の分類

### 1. プロジェクト共通の環境変数（ルートの`.env`）

- **対象**: Docker Compose全体に影響する設定
- **例**:
  - データベース接続情報（POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB）
  - サービス間の接続設定（BACKEND_URL, FRONTEND_URL）
  - コンテナのポート設定
  - コンテナの名前設定

### 2. バックエンド固有の環境変数（`backend/.env`）

- **対象**: FastAPIアプリケーションの動作に関わる設定
- **例**:
  - JWT認証設定（SECRET_KEY, ALGORITHM, EXPIRATION）
  - メール送信設定
  - APIキー
  - ログレベル設定

### 3. フロントエンド固有の環境変数（`frontend/.env.local`）

- **対象**: Next.jsアプリケーションの動作に関わる設定
- **例**:
  - API接続URL（NEXT_PUBLIC_API_URL）
  - 分析ツール用設定
  - 機能フラグ

## 環境別管理

環境ごとに異なる設定が必要な場合は、以下のパターンを使用します：

### 開発環境

- デフォルトは`.env`や`.env.local`ファイル

### テスト環境

- CI/CD環境では環境変数を直接設定
- テスト用の`.env.test`ファイルを使用（Gitで管理しない）

### 本番環境

- 本番サーバーでは環境変数を直接設定
- デプロイプロセスで自動的に適用される仕組みを構築

## Docker Composeでの環境変数の取り扱い

### 基本アプローチ

1. **ルートの`.env`ファイルからの自動読み込み**：
   - Docker Composeはルートの`.env`ファイルを自動的に読み込みます
   - サービス間で共有される設定はここに配置します

2. **個別サービスへの環境変数設定**：

   ```yaml
   services:
     backend:
       env_file:
         - ./backend/.env
       # 共通変数の上書きが必要な場合に使用
       environment:
         - DATABASE_URL=${DATABASE_URL}
   ```

3. **ボリュームとしてのマウント**：

   ```yaml
   services:
     frontend:
       volumes:
         - ./frontend/.env.local:/app/.env.local
   ```

## セキュリティ上の注意点

1. `.gitignore`に全ての実際の環境変数ファイルを含める
2. 機密情報を含む環境変数は`.env.example`ファイルに実際の値を入れない
3. プロダクション環境のシークレットは安全なシークレット管理サービスを使用する

## 環境変数詳細リファレンス

### バックエンド環境変数

#### データベース関連

- `DATABASE_URL`: PostgreSQLデータベースの接続URL
  - 形式: `postgresql://user:password@host:port/database`
  - ローカル開発: `postgresql://user:password@localhost:5432/chat_db`

#### 認証・セキュリティ関連

- `SECRET_KEY`: JWT トークン署名用の秘密鍵（本番環境では長くランダムな値を設定）
- `ALGORITHM`: JWT ハッシュアルゴリズム（通常は "HS256"）
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWTアクセストークンの有効期限（分単位、通常は30）

#### メール送信関連

- `MAIL_PROVIDER`: メール送信プロバイダ（"gmail", "sendgrid", "mailhog"）
- `GMAIL_USER`: Gmail SMTP用のメールアドレス
- `GMAIL_APP_PASSWORD`: Gmail アプリパスワード（16桁）
- `SENDGRID_API_KEY`: SendGrid API キー
- `MAILHOG_HOST`: MailHog サーバーのホスト（開発環境用）

#### フロントエンド連携

- `FRONTEND_URL`: フロントエンドのベースURL
  - **重要**: メール認証リンクやパスワードリセットリンクの生成に使用
  - ローカル開発: `http://localhost:3000`
  - 本番環境: `https://your-domain.com`
  - Cloudflare Tunnel使用時: `https://your-tunnel-domain.com`

#### その他

- `LOG_LEVEL`: ログレベル（DEBUG, INFO, WARNING, ERROR）
- `ENVIRONMENT`: 実行環境（development, testing, production）

### フロントエンド環境変数

#### API接続

- `NEXT_PUBLIC_API_URL`: バックエンドAPIのベースURL
  - ローカル開発: `http://localhost:8000`
  - 本番環境: `https://api.your-domain.com`

## よくある詰まりポイント

### 1. メールリンクのドメインが間違っている

**症状**: パスワードリセットメールのリンクが `localhost:3000` になってしまう

**原因**: `FRONTEND_URL` 環境変数が適切に設定されていない

**解決方法**:

```bash
# backend/.env ファイルで設定
FRONTEND_URL=https://your-cloudflare-tunnel-domain.com
```

### 2. Gmail SMTP認証エラー

**症状**: `Authentication failed` エラーでメール送信失敗

**原因**:

- Gmailアプリパスワードが設定されていない
- 2段階認証が有効になっていない

**解決方法**:

1. Googleアカウントで2段階認証を有効化
2. アプリパスワードを生成（16桁）
3. `GMAIL_APP_PASSWORD` にアプリパスワードを設定

### 3. 環境変数が読み込まれない

**症状**: 設定した環境変数が認識されない

**よくある原因**:

- `.env` ファイルの配置場所が間違っている
- Docker Compose再起動を忘れている
- 環境変数名のタイポ

**解決方法**:

```bash
# Docker Compose を再起動
docker-compose down && docker-compose up -d

# 環境変数が正しく読み込まれているか確認
docker-compose exec backend env | grep FRONTEND_URL
```

### 4. Cloudflare Tunnel使用時の注意点

**問題**: ローカル開発とトンネル使用時でURLが異なる

**解決方法**:

- 開発時は `FRONTEND_URL=http://localhost:3000`
- Cloudflare Tunnel使用時は `FRONTEND_URL=https://tunnel-domain.com`
- 環境に応じて適切に切り替える

### 5. データベース接続エラー

**症状**: `Connection refused` または `Database does not exist`

**チェックポイント**:

- PostgreSQL コンテナが起動しているか
- データベース名、ユーザー名、パスワードが正しいか
- ポート番号が正しいか（デフォルト: 5432）

## 開発ワークフロー

### 新機能開発時の環境変数チェックリスト

1. **新しい環境変数が必要な場合**:
   - `backend/.env.example` に追加
   - 本ドキュメントに説明を追加
   - チーム内で共有

2. **メール機能テスト時**:
   - `FRONTEND_URL` が適切に設定されているか確認
   - メール送信プロバイダの設定確認
   - テストメール送信で動作確認

3. **デプロイ前**:
   - 本番環境用の環境変数値を準備
   - シークレット情報の安全な保管
   - 環境変数の動作確認

## 現状からの移行計画

1. プロジェクトルートに`.env.example`を作成し、全ての必要な環境変数を記載
2. `backend`と`frontend`ディレクトリにそれぞれ`.env.example`を作成
3. `docker-compose.yml`ファイルから直接の環境変数定義を`.env`ファイルに移動
4. CI/CDパイプラインを更新して新しい環境変数構造を反映
5. 環境変数詳細リファレンスと詰まりポイントを追加（パスワードリセット機能実装時）
