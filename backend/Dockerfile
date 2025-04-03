FROM python:3.13-slim

WORKDIR /app

# Poetryのインストール
RUN pip install poetry

# 依存関係のコピーとインストール
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# アプリケーションコードのコピー
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 
