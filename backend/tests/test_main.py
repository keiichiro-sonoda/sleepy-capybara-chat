from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, drop_database

from app.main import app
from app.core.config import get_settings
from app.db.session import Base

settings = get_settings()

# テスト用のデータベースURL
TEST_DATABASE_URL = (
    "postgresql://postgres:postgrespassword@db:5432/test_capybara_chat"
)


def setup_module(module):
    """テストモジュールのセットアップ"""
    # テスト用データベースの作成
    create_database(TEST_DATABASE_URL)

    # テスト用のエンジンとセッションの作成
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # テーブルの作成
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    """テストモジュールの後片付け"""
    # テスト用データベースの削除
    drop_database(TEST_DATABASE_URL)


def test_read_root():
    """ルートエンドポイントのテスト"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Sleepy Capybara Chat API"}


def test_cors_headers():
    """CORSヘッダーのテスト"""
    client = TestClient(app)
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_api_v1_prefix():
    """APIバージョンプレフィックスのテスト"""
    client = TestClient(app)
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()
