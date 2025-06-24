# データベースマイグレーション管理

このドキュメントは、Sleepy Capybara ChatアプリケーションにおけるSQLAlchemyとAlembicを使用したデータベースマイグレーション管理についてまとめています。

## 目次

1. [現状と課題](#現状と課題)
2. [マイグレーション履歴](#マイグレーション履歴)
3. [問題解決事例](#問題解決事例)
4. [ベストプラクティス](#ベストプラクティス)
5. [マイグレーションチートシート](#マイグレーションチートシート)

## 現状と課題

現在、プロジェクトにはデータベース管理に関する以下の課題があります：

1. **SQLAlchemyとAlembicの連携問題**:
   - アプリケーション起動時にSQLAlchemyが自動的にテーブルを作成している
   - Alembicのマイグレーションスクリプトも同様のテーブル作成を試みるため、競合が発生する
   - 結果として、`alembic upgrade head`コマンドがエラーになることがある

2. **マイグレーション履歴の不整合**:
   - データベースが存在しても、`alembic_version`テーブルが存在しない場合がある
   - Alembicがどのマイグレーションまで適用済みか把握できないため、新しいマイグレーションの適用に失敗する

3. **初期データベース設定の明確な手順の欠如**:
   - 新しい開発環境をセットアップする際の正確な手順が文書化されていない

## 短期的対応（現在の対処法）

現在は以下の方法で問題を回避しています：

1. **既存のテーブルとAlembicの同期**:

   ```bash
   # 既にテーブルが存在する場合、現在のスキーマを最新として登録
   docker compose exec backend poetry run alembic stamp head
   ```

2. **データベースの再作成**:

   ```bash
   # 問題が複雑な場合、データベースを完全にリセット
   docker compose down -v
   docker compose up -d
   docker compose exec backend poetry run alembic stamp head
   ```

これらの対応は一時的なもので、根本的な解決策ではありません。

## 長期的対応（推奨される実装）

今後の開発のために、以下の対応を実施することを推奨します：

1. **アプリケーション起動時の自動テーブル作成を無効化**:
   - `app/db/session.py`を修正し、`Base.metadata.create_all(bind=engine)`の呼び出しを削除またはコメントアウト
   - これにより、テーブル作成はAlembicのマイグレーションのみに委ねられる

2. **初期マイグレーションの適切な作成**:
   - 既存のモデルを対象とした包括的な初期マイグレーションファイルを作成
   - 新しい空のデータベースから始めて、すべてのテーブルを作成するマイグレーションを生成

   ```bash
   # 初期マイグレーションを生成（既存データベースがリセットされた状態で）
   docker compose exec backend poetry run alembic revision --autogenerate -m "Initial database setup"
   ```

3. **明確なデータベース初期化手順の文書化**:

   ```text
   # 新しい開発環境のセットアップ手順
   1. make dev-up
   2. make dev-migrate
   3. make dev-restart-backend
   ```

4. **CI/CDパイプラインでのマイグレーション自動化**:
   - デプロイ前に自動的にマイグレーションを適用するCI/CDパイプラインを整備
   - テスト環境でのマイグレーションテストを自動化

## マイグレーション開発のベストプラクティス

1. **モデル変更時の手順**:

   ```text
   1. SQLAlchemyモデル（app/models/*.py）を変更する
   2. マイグレーションファイルを自動生成する:
      docker compose exec backend poetry run alembic revision --autogenerate -m "変更内容の説明"
   3. 生成されたマイグレーションファイルを確認・編集する
   4. マイグレーションを適用する:
      make dev-migrate
   5. アプリケーションが正常に動作することを確認する
   6. 変更をコミットする（モデル変更とマイグレーションファイルを同じコミットに含める）
   ```

2. **マイグレーションファイルの注意点**:
   - 自動生成されたマイグレーションファイルは必ず内容を確認する
   - 必要に応じて手動で修正を行う（特に複雑なデータ変換が必要な場合）
   - 日本語でのコメントを追加し、変更の目的と影響を明確にする

3. **ダウングレード関数の実装**:
   - `downgrade()`関数は必ず実装し、テストする
   - これにより、必要に応じて安全にマイグレーションを元に戻すことができる

4. **既存データの取り扱い**:
   - NOT NULL制約を追加する場合は、既存レコードのデフォルト値を設定する
   - カラム名を変更する場合は、データを移行するロジックを実装する

## トラブルシューティング

よくある問題と解決方法:

1. **「テーブルがすでに存在する」エラー**:

   ```bash
   alembic stamp head  # 現在のスキーマを最新として登録
   ```

   **重要**: この対応だけでは不十分な場合があります。`alembic stamp`はマイグレーション履歴のみを更新し、実際のマイグレーション処理（CASCADE制約の追加など）は実行されません。

   **完全な対応手順**:

   ```bash
   # 1. 現在のスキーマを最新として登録
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic stamp head
   
   # 2. 重要なマイグレーションの処理が実行されていない場合、段階的に実行
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic stamp 43b943c73c86
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic upgrade ddb6fc93d72b
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic upgrade cc12785e15bb
   
   # 3. CASCADE制約が正しく適用されたか確認
   # （上記の制約確認SQLを実行）
   ```

2. **「リビジョンが見つからない」エラー**:

   ```bash
   # alembic_versionテーブルを初期化
   docker compose exec db psql -U postgres -d capybara_chat -c "DELETE FROM alembic_version;"
   docker compose exec backend poetry run alembic stamp head
   ```

3. **マイグレーションの競合**:

   ```bash
   # マイグレーション履歴を確認
   make dev-migration-history
   
   # 特定のリビジョンまでダウングレード
   docker compose exec backend poetry run alembic downgrade <revision_id>
   ```

4. **コンテナ内とホスト側のマイグレーションファイルの不一致**:

   ```bash
   # 1. docker-compose.ymlのボリュームマウント設定を確認
   #    migrationsディレクトリが正しくマウントされているか確認
   #    例: ./backend/migrations:/src/migrations

   # 2. マウント設定を追加した場合、コンテナを再起動
   make dev-down
   make dev-up
   
   # 3. マイグレーションを再実行
   make dev-migrate
   ```

## カスケード削除問題の解決

### 問題の概要

2025年6月22日に発生した問題：ユーザー削除時にデータベース整合性制約エラーが発生。

**エラーの症状**:

```bash
sqlalchemy.exc.IntegrityError: (psycopg2.errors.NotNullViolation) 
null value in column "user_id" of relation "chat_sessions" violates not-null constraint
```

さらに続けて：

```bash
null value in column "session_id" of relation "messages" violates not-null constraint
```

**原因**:

1. SQLAlchemyがユーザー削除時に関連レコードの外部キーを `null` に設定しようとした
2. データベースの外部キー制約に `ON DELETE CASCADE` が設定されていたが、SQLAlchemyがそれを認識していなかった
3. SQLAlchemyがデータベースのCASCADE制約よりも先に関連レコードを更新しようとしてエラーが発生

### 解決方法

#### 1. SQLAlchemyモデルの修正

**修正前**:

```python
# app/models/user.py
chat_sessions = relationship("ChatSession", back_populates="user")
token_limits = relationship("TokenLimit", back_populates="user")
```

**修正後**:

```python
# app/models/user.py
chat_sessions = relationship(
    "ChatSession", back_populates="user", 
    cascade="all, delete-orphan", passive_deletes=True
)
token_limits = relationship(
    "TokenLimit", back_populates="user", 
    cascade="all, delete-orphan", passive_deletes=True
)
token_usage = relationship(
    "TokenUsage", back_populates="user", 
    cascade="all, delete-orphan", passive_deletes=True
)
```

**`passive_deletes=True`の重要性**:

- SQLAlchemyに「削除処理はデータベースのCASCADE制約に任せる」ことを指示
- SQLAlchemyが関連レコードを手動で削除しようとすることを防ぐ

#### 2. 外部キー制約の修正

一部のテーブルで `ON DELETE CASCADE` が設定されていなかったため、マイグレーションで修正：

```python
# マイグレーションファイル例
def upgrade() -> None:
    # token_usage テーブルの session_id 外部キー制約を追加
    op.drop_constraint('token_usage_session_id_fkey', 'token_usage', type_='foreignkey')
    op.create_foreign_key(
        'token_usage_session_id_fkey', 'token_usage', 'chat_sessions', 
        ['session_id'], ['id'], ondelete='CASCADE'
    )
```

#### 3. エラーハンドリングの改善

```python
# app/api/v1/auth/auth.py
try:
    # ユーザーを削除（cascade設定により関連データも自動削除される）
    db.delete(user)
    db.commit()
    logger.info(f"User {user_id} and all related data deleted successfully")
except Exception as e:
    db.rollback()
    logger.error(f"Failed to delete user {user_id}: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to delete user"
    )
```

### 実装手順のまとめ

1. **SQLAlchemyモデルを修正**:
   - `cascade="all, delete-orphan"` を追加
   - `passive_deletes=True` を追加

2. **データベース制約を確認・修正**:

   ```bash
   # 外部キー制約を確認
   make dev-db-constraints  # 開発環境
   make prod-db-constraints # 本番環境
   
   # 必要に応じてマイグレーションを作成
   docker compose exec backend poetry run alembic revision --autogenerate -m "説明"
   ```

3. **マイグレーションファイルを手動で調整**:
   - 自動生成されたファイルは必ず内容を確認
   - `ondelete='CASCADE'` パラメータが正しく設定されているか確認

4. **マイグレーションを適用**:

   ```bash
   make dev-migrate   # 開発環境
   make prod-migrate  # 本番環境（確認プロンプト付き）
   ```

5. **アプリケーションを再起動**:

   ```bash
   make dev-restart-backend   # 開発環境
   make prod-restart-backend  # 本番環境
   ```

### 本番環境でのマイグレーション適用手順

**注意**: 本開発で作成された以下のマイグレーションは本番環境でも適用が必要です：

- `ddb6fc93d72b` - カスケード削除制約の追加
- `cc12785e15bb` - token_usage session_id制約の修正

#### 1. 事前準備

```bash
# 1. データベースのバックアップを取得
make prod-backup-db

# 2. 現在のマイグレーション状態を確認
make prod-migration-status

# 3. 適用予定のマイグレーション履歴を確認
make prod-migration-history
```

#### 2. メンテナンスモード（推奨）

```bash
# フロントエンドとCloudflare Tunnelを停止してユーザーアクセスを制限
make prod-maintenance-start
```

#### 3. マイグレーション適用

```bash
# マイグレーションを適用（確認プロンプト付き）
make prod-migrate

# 手動で段階的に適用したい場合
docker compose -f docker-compose.prod.yml exec backend poetry run alembic upgrade ddb6fc93d72b
docker compose -f docker-compose.prod.yml exec backend poetry run alembic upgrade cc12785e15bb
```

#### 3-1. 既存テーブルとマイグレーション履歴の不整合が発生した場合

**問題**: 本番環境で既にテーブルが存在するため、初期マイグレーション実行時に以下のエラーが発生：

```text
sqlalchemy.exc.ProgrammingError: (psycongregate2.errors.DuplicateTable) relation "users" already exists
```

**原因**: SQLAlchemyによる自動テーブル作成と、Alembicのマイグレーションが競合している

**対処法**:

1. **現在のスキーマを最新として登録**:

   ```bash
   # 既存のテーブル構造を最新のマイグレーション状態として認識させる
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic stamp head
   ```

2. **マイグレーション状態を確認**:

   ```bash
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic current
   ```

3. **重要**: `alembic stamp head`は**マイグレーション履歴のみを更新**し、実際のマイグレーション処理は実行しない

   これは重要な問題で、マイグレーション履歴は最新になるが、実際のデータベース制約の変更（CASCADE制約の追加など）は実行されない。

4. **実際のマイグレーション処理を段階的に実行**:

   `alembic stamp head`後、以下の手順で実際のマイグレーション処理を実行する：

   ```bash
   # まず一つ前のマイグレーションに戻る（履歴上のみ）
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic stamp 43b943c73c86
   
   # 段階的にマイグレーションを実行（実際の処理を実行）
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic upgrade ddb6fc93d72b
   docker compose -f docker-compose.prod.yml exec backend poetry run alembic upgrade cc12785e15bb
   ```

   **注意**: `downgrade`コマンドではなく、`stamp`コマンドで履歴を調整してから`upgrade`で実際の処理を実行する

5. **制約の適用確認**:

   ```bash
   # CASCADE制約が正しく設定されているか確認
   docker compose -f docker-compose.prod.yml exec db psql -U sleepy_user -d sleepy_capybara_chat -c "
   SELECT 
       tc.constraint_name, 
       tc.table_name, 
       kcu.column_name, 
       ccu.table_name AS foreign_table_name,
       rc.delete_rule
   FROM 
       information_schema.table_constraints AS tc 
       JOIN information_schema.key_column_usage AS kcu
         ON tc.constraint_name = kcu.constraint_name
       JOIN information_schema.constraint_column_usage AS ccu
         ON ccu.constraint_name = tc.constraint_name
       JOIN information_schema.referential_constraints AS rc
         ON tc.constraint_name = rc.constraint_name
   WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name IN ('chat_sessions', 'messages', 'token_limits', 'token_usage');
   "
   ```

   期待される結果: `delete_rule`列に`CASCADE`が表示されること

**教訓**:

- `alembic stamp`はマイグレーション履歴の管理のみを行い、実際のデータベース変更は実行しない
- 本番環境では必ず実際のマイグレーション処理も段階的に実行し、制約の適用を確認すること

#### 4. 動作確認

```bash
# 1. バックエンドサービスを再起動
make prod-restart-backend

# 2. データベース制約の確認
make prod-db-constraints

# 3. ログでエラーがないことを確認
make prod-logs-backend
```

#### 5. サービス復旧

```bash
# フロントエンドとCloudflare Tunnelを再開
make prod-maintenance-end

# 全サービスの状態確認
docker compose -f docker-compose.prod.yml ps
```

#### 6. 機能テスト

```bash
# ユーザー削除機能のテスト（管理者権限で）
# 1. 管理者でログイン
# 2. テストユーザーを作成
# 3. そのユーザーの削除を実行
# 4. エラーが発生しないことを確認
# 5. 関連データが正しく削除されていることを確認
```

#### ロールバック手順（問題発生時）

```bash
# 1. 問題のあるマイグレーションを特定
make prod-migration-status

# 2. 前のマイグレーションまでダウングレード
docker compose -f docker-compose.prod.yml exec backend poetry run alembic downgrade 43b943c73c86

# 3. バックアップからデータベースを復元（重大な問題の場合）
make prod-restore-db BACKUP_FILE=backups/prod_backup_20250622_123456.sql

# 4. サービスを再起動
make prod-restart-backend
```

#### 本番環境マイグレーションのベストプラクティス

1. **バックアップの必須性**:
   - マイグレーション前には必ずデータベースの完全バックアップを取得
   - 復元テストも事前に実施しておく

2. **段階的適用**:
   - 複数のマイグレーションがある場合は一つずつ適用
   - 各段階で動作確認を実施

3. **メンテナンス時間の確保**:
   - ユーザーへの事前通知
   - 十分な作業時間を確保（ロールバック時間も含む）

4. **監視とログ確認**:
   - マイグレーション中は継続的にログを監視
   - エラーが発生した場合は即座に停止してロールバック

5. **事前テスト**:
   - 本番相当の環境でマイグレーションをテスト実行
   - データ量が多い場合は実行時間を事前測定

### 学んだ教訓

1. **SQLAlchemyとデータベース制約の連携**:
   - SQLAlchemyのリレーションシップ設定とデータベースの制約は別々に管理される
   - `passive_deletes=True` の設定が重要

2. **マイグレーション作成の注意点**:
   - 自動生成されたマイグレーションファイルは必ず内容を確認する
   - 外部キー制約の名前は実際のデータベースの状態と一致させる必要がある

3. **段階的な問題解決**:
   - 一つのエラーを修正すると、次のエラーが見えてくることがある
   - 全体的な関連性を理解して包括的に修正することが重要

4. **`alembic stamp`の重要な落とし穴**:
   - `alembic stamp head`はマイグレーション履歴の更新のみを行い、実際のマイグレーション処理は実行しない
   - 既存テーブルとマイグレーション履歴を同期させた後、重要なマイグレーション（CASCADE制約追加など）は個別に実行が必要
   - 本番環境では特に、マイグレーション履歴の同期と実際の処理実行を明確に分けて考える必要がある

5. **本番環境でのマイグレーション検証の重要性**:
   - マイグレーション適用後は必ず制約やデータベース構造の確認を実施する
   - アプリケーションレベルでの機能テスト（ユーザー削除など）も必須

## マイグレーションチートシート

よく使用するマイグレーション操作のクイックリファレンス：

### 基本コマンド

```bash
# 新しいマイグレーションを自動生成
docker compose exec backend poetry run alembic revision --autogenerate -m "説明"

# マイグレーション履歴を確認
docker compose exec backend poetry run alembic history --verbose

# 現在のマイグレーション状態を確認
docker compose exec backend poetry run alembic current

# 最新までマイグレーションを適用
docker compose exec backend poetry run alembic upgrade head

# 特定のリビジョンまでマイグレーション
docker compose exec backend poetry run alembic upgrade <revision_id>

# マイグレーションを1つ戻す
docker compose exec backend poetry run alembic downgrade -1

# 実行されるSQLを確認（実際には実行しない）
docker compose exec backend poetry run alembic upgrade head --sql
```

### 型変換マイグレーション

PostgreSQLで型変換を行う場合の`USING`句の使用例：

```python
# VARCHAR → TIMESTAMP WITH TIME ZONE
op.execute("""
    ALTER TABLE users 
    ALTER COLUMN reset_token_expires_at 
    TYPE TIMESTAMP WITH TIME ZONE 
    USING CASE 
        WHEN reset_token_expires_at IS NULL OR reset_token_expires_at = '' THEN NULL
        ELSE reset_token_expires_at::timestamp with time zone
    END
""")

# TIMESTAMP → VARCHAR
op.execute("""
    ALTER TABLE users 
    ALTER COLUMN reset_token_expires_at 
    TYPE VARCHAR 
    USING reset_token_expires_at::text
""")

# INTEGER → ENUM
op.execute("""
    ALTER TABLE table_name 
    ALTER COLUMN column_name 
    TYPE enum_type 
    USING column_name::text::enum_type
""")
```

### 外部キー制約の操作

```python
# CASCADE制約付きの外部キーを追加
op.create_foreign_key(
    'fk_name', 'source_table', 'target_table',
    ['source_column'], ['target_column'],
    ondelete='CASCADE'
)

# 外部キー制約を削除
op.drop_constraint('fk_name', 'table_name', type_='foreignkey')
```

### インデックス操作

```python
# インデックスを作成
op.create_index('ix_table_column', 'table_name', ['column_name'])

# ユニークインデックスを作成
op.create_index('ix_table_column', 'table_name', ['column_name'], unique=True)

# インデックスを削除
op.drop_index('ix_table_column', table_name='table_name')
```

### マイグレーションのベストプラクティス

1. **自動生成後の確認**: `--autogenerate`で生成されたファイルは必ず手動確認
2. **バックアップ**: 本番環境では事前にデータベースバックアップを取得
3. **段階的適用**: 複数の変更がある場合は1つずつ適用して確認
4. **downgrade関数**: 必ず実装してロールバック可能にする
5. **USING句**: PostgreSQLで型変換時は明示的な変換ロジックを指定

### トラブルシューティング

```bash
# マイグレーション履歴の不整合を修正
docker compose exec backend poetry run alembic stamp head

# 特定のリビジョンまで履歴を戻す
docker compose exec backend poetry run alembic stamp <revision_id>

# データベース制約を確認
docker compose exec db psql -U postgres -d capybara_chat -c "
SELECT constraint_name, table_name, column_name, 
       foreign_table_name, delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu USING (constraint_name)
JOIN information_schema.constraint_column_usage ccu USING (constraint_name)
JOIN information_schema.referential_constraints rc USING (constraint_name)
WHERE tc.constraint_type = 'FOREIGN KEY';"

# カラムの型を確認
docker compose exec db psql -U postgres -d capybara_chat -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'table_name';"
```

## 参考リソース

- [Alembic公式ドキュメント](https://alembic.sqlalchemy.org/)
- [SQLAlchemy公式ドキュメント](https://www.sqlalchemy.org/)
- [SQLAlchemy Relationship Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html)
