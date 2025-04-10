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
   ```
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
   ```
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
   ```
   alembic stamp head  # 現在のスキーマを最新として登録
   ```

2. **「リビジョンが見つからない」エラー**:
   ```
   # alembic_versionテーブルを初期化
   docker-compose exec db psql -U postgres -d capybara_chat -c "DELETE FROM alembic_version;"
   docker-compose exec backend poetry run alembic stamp head
   ```

3. **マイグレーションの競合**:
   ```
   # マイグレーション履歴を確認
   docker-compose exec backend poetry run alembic history
   
   # 特定のリビジョンまでダウングレード
   docker-compose exec backend poetry run alembic downgrade <revision_id>
   ```

4. **コンテナ内とホスト側のマイグレーションファイルの不一致**:
   ```
   # 1. docker-compose.ymlのボリュームマウント設定を確認
   #    migrationsディレクトリが正しくマウントされているか確認
   #    例: ./backend/migrations:/src/migrations

   # 2. マウント設定を追加した場合、コンテナを再起動
   docker-compose down
   docker-compose up -d
   
   # 3. マイグレーションを再実行
   docker-compose exec backend poetry run alembic upgrade head
   ```

## 参考リソース

- [Alembic公式ドキュメント](https://alembic.sqlalchemy.org/)
- [SQLAlchemy公式ドキュメント](https://www.sqlalchemy.org/) 
