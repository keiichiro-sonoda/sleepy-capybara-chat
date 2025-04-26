import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

# ロガーの設定
logger = logging.getLogger(__name__)

class ModelProvider(ABC):
    """AI言語モデルプロバイダの基底クラス"""

    @abstractmethod
    async def chat_completion(
        self, messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        """チャット形式での補完を行う"""
        pass

    @abstractmethod
    async def text_generation(self, prompt: str, model_name: str) -> str:
        """テキスト生成を行う"""
        pass
