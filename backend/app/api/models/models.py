from fastapi import APIRouter

from app.schemas.chat import AVAILABLE_MODELS, AIModel, DEFAULT_MODEL

router = APIRouter()


@router.get("/", response_model=list[AIModel])
def get_available_models():
    """
    利用可能なAIモデルのリストを返すエンドポイント
    """
    return AVAILABLE_MODELS


@router.get("/default", response_model=str)
def get_default_model():
    """
    デフォルトのAIモデルIDを返すエンドポイント
    """
    return DEFAULT_MODEL
