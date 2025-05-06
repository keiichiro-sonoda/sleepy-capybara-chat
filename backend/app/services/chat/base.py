import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

# ロガーの設定
logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """AI言語モデルプロバイダの基底クラス"""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model_name: str,
        stream: bool = False,
        thinking_mode: bool = False,
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None]:
        """
        チャット形式での補完を行う

        :param messages: 会話履歴
        :param model_name: 使用するモデル名
        :param stream: ストリーミングレスポンスを使用するかどうか
        :param thinking_mode: 思考モードを有効にするかどうか
        :return: レスポンスデータまたはストリーミングジェネレータ
        """
        pass

    @abstractmethod
    async def text_generation(self, prompt: str, model_name: str) -> str:
        """テキスト生成を行う"""
        pass
