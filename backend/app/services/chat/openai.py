import logging
from typing import Any, AsyncGenerator

from fastapi import HTTPException
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.chat.base import ModelProvider

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class OpenAIProvider(ModelProvider):
    """OpenAIプロバイダの実装 - 公式SDKを使用"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_completion(
        self, messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool], None]:
        """OpenAIのChat Completions APIを呼び出す"""
        try:
            # すべてのモデルでResponses APIを使用
            if stream:
                return self._stream_responses(messages, model_name)
            else:
                return await self._non_stream_responses(messages, model_name)
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def text_generation(self, prompt: str, model_name: str) -> str:
        """OpenAIのResponses APIでテキスト生成を行う"""
        try:
            response = await self.client.responses.create(
                model=model_name, input=[{"role": "user", "content": prompt}]
            )
            return response.output_text
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _non_stream_responses(
        self, messages: list[dict[str, str]], model_name: str
    ) -> dict[str, Any]:
        """非ストリーミングResponses APIを呼び出す"""
        # 既存のメッセージ形式をResponses API形式に変換
        converted_messages = self._convert_messages_format(messages)

        logger.debug(f"Sending to Responses API: {converted_messages}")

        response = await self.client.responses.create(
            model=model_name, input=converted_messages
        )

        content = response.output_text
        logger.debug(f"Responses API result: {content}")

        # 標準形式に整形して返す
        return {"message": {"content": content}}

    async def _stream_responses(
        self, messages: list[dict[str, str]], model_name: str
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """ストリーミングResponses APIを呼び出す"""
        # 既存のメッセージ形式をResponses API形式に変換
        converted_messages = self._convert_messages_format(messages)

        logger.debug(f"Sending to Responses API (streaming): {converted_messages}")

        stream = await self.client.responses.create(
            model=model_name, input=converted_messages, stream=True
        )

        try:
            async for chunk in stream:
                event_type = type(chunk).__name__
                if event_type == "ResponseTextDeltaEvent":
                    yield (chunk.delta, False)
                elif event_type == "ResponseTextDoneEvent":
                    break
            # ストリーム終了時に完了フラグを送信
            yield ("", True)
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}", exc_info=True)
            yield ("", True)

    def _convert_messages_format(
        self, messages: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        """標準メッセージ形式をResponses API形式に変換"""
        converted = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # システムメッセージはdeveloperロールとして扱う
            if role == "system":
                converted.append({"role": "developer", "content": content})
            elif role == "user":
                converted.append({"role": "user", "content": content})
            elif role == "assistant":
                converted.append({"role": "assistant", "content": content})

        return converted
