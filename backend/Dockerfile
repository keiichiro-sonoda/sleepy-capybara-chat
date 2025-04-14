FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1

# システムユーザーの作成
RUN useradd -m -u 1000 appuser

WORKDIR /src

# pipを使ってpoetryをインストール
RUN pip install poetry

# poetryの定義ファイルをコピー (存在する場合)
COPY pyproject.toml* poetry.lock* ./

# poetryでライブラリをインストール (pyproject.tomlが既にある場合)
RUN poetry config virtualenvs.in-project true
RUN if [ -f pyproject.toml ]; then poetry install --no-root; fi

# アプリケーションコードをコピー
COPY app app/

# ★ ここでマイグレーション関連ファイルもコピー
COPY migrations migrations/
COPY alembic.ini .

# mypyで型チェックを実行
# RUN poetry run mypy app/

# 権限の設定
RUN chown -R appuser:appuser /src

# ユーザーの切り替え
USER appuser

# uvicornのサーバーを立ち上げる
ENTRYPOINT ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--reload"]
