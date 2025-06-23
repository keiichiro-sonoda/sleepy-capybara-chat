FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1

# システムユーザーの作成
RUN useradd -m -u 1000 appuser

WORKDIR /src

# pipを使ってpoetryをインストール
RUN pip install poetry

# poetryの定義ファイルをコピー (存在する場合)
COPY pyproject.toml* poetry.lock* ./

# 設定ファイルをコピー
COPY .flake8 ./
COPY mypy.ini ./

# poetryでライブラリをインストール (pyproject.tomlが既にある場合)
RUN poetry config virtualenvs.in-project true
RUN if [ -f pyproject.toml ]; then poetry install --no-root; fi

# アプリケーションコードをコピー
COPY app app/
COPY tests tests/

# ★ ここでマイグレーション関連ファイルもコピー
COPY migrations migrations/
COPY alembic.ini .

# コードフォーマットとリンティングのチェック（testsフォルダも含める）
RUN poetry run black --check --diff app/ tests/
RUN poetry run isort --check-only --diff app/ tests/
RUN poetry run flake8 app/ tests/
RUN poetry run mypy app/ tests/

# 権限の設定
RUN chown -R appuser:appuser /src

# ユーザーの切り替え
USER appuser

# uvicornのサーバーを立ち上げる
ENTRYPOINT ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--reload"]
