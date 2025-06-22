# データベースマイグレーション管理

このドキュメントは、Sleepy Capybara ChatアプリケーションにおけるSQLAlchemyとAlembicを使用したデータベースマイグレーション管理についてまとめています。

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
   docker-compose exec backend poetry run alembic stamp head
   ```

2. **データベースの再作成**:

   ```bash
   # 問題が複雑な場合、データベースを完全にリセット
   docker-compose down -v
   docker-compose up -d
   docker-compose exec backend poetry run alembic stamp head
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
   docker-compose exec backend poetry run alembic revision --autogenerate -m "Initial database setup"
   ```

3. **明確なデータベース初期化手順の文書化**:

   ```text
   # 新しい開発環境のセットアップ手順
   1. docker-compose up -d
   2. docker-compose exec backend poetry run alembic upgrade head
   3. docker-compose restart backend
   ```

4. **CI/CDパイプラインでのマイグレーション自動化**:
   - デプロイ前に自動的にマイグレーションを適用するCI/CDパイプラインを整備
   - テスト環境でのマイグレーションテストを自動化

## マイグレーション開発のベストプラクティス

1. **モデル変更時の手順**:

   ```text
   1. SQLAlchemyモデル（app/models/*.py）を変更する
   2. マイグレーションファイルを自動生成する:
      docker-compose exec backend poetry run alembic revision --autogenerate -m "変更内容の説明"
   3. 生成されたマイグレーションファイルを確認・編集する
   4. マイグレーションを適用する:
      docker-compose exec backend poetry run alembic upgrade head
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

2. **「リビジョンが見つからない」エラー**:

   ```bash
   # alembic_versionテーブルを初期化
   docker-compose exec db psql -U postgres -d capybara_chat -c "DELETE FROM alembic_version;"
   docker-compose exec backend poetry run alembic stamp head
   ```

3. **マイグレーションの競合**:

   ```bash
   # マイグレーション履歴を確認
   docker-compose exec backend poetry run alembic history
   
   # 特定のリビジョンまでダウングレード
   docker-compose exec backend poetry run alembic downgrade <revision_id>
   ```

4. **コンテナ内とホスト側のマイグレーションファイルの不一致**:

   ```bash
   # 1. docker-compose.ymlのボリュームマウント設定を確認
   #    migrationsディレクトリが正しくマウントされているか確認
   #    例: ./backend/migrations:/src/migrations

   # 2. マウント設定を追加した場合、コンテナを再起動
   docker-compose down
   docker-compose up -d
   
   # 3. マイグレーションを再実行
   docker-compose exec backend poetry run alembic upgrade head
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
   docker-compose exec db psql -U postgres -d capybara_chat -c "\d+ テーブル名"
   
   # 必要に応じてマイグレーションを作成
   docker-compose exec backend poetry run alembic revision --autogenerate -m "説明"
   ```

3. **マイグレーションファイルを手動で調整**:
   - 自動生成されたファイルは必ず内容を確認
   - `ondelete='CASCADE'` パラメータが正しく設定されているか確認

4. **マイグレーションを適用**:

   ```bash
   docker-compose exec backend poetry run alembic upgrade head
   ```

5. **アプリケーションを再起動**:

   ```bash
   docker-compose restart backend
   ```

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

## 参考リソース

- [Alembic公式ドキュメント](https://alembic.sqlalchemy.org/)
- [SQLAlchemy公式ドキュメント](https://www.sqlalchemy.org/)
- [SQLAlchemy Relationship Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html)
