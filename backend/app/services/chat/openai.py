import logging
from typing import Any, AsyncGenerator, cast

from fastapi import HTTPException
from openai import AsyncOpenAI
from openai.types.responses import ResponseInputItemParam

from app.core.config import get_settings
from app.services.chat.base import ModelProvider

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class OpenAIProvider(ModelProvider):
    """OpenAIプロバイダの実装 - 公式SDKを使用"""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model_name: str,
        stream: bool = False,
        thinking_mode: bool = False,
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None]:
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

    def _convert_messages_format(
        self, messages: list[dict[str, str]]
    ) -> list[ResponseInputItemParam]:
        """標準メッセージ形式をResponses API形式に変換"""
        converted: list[ResponseInputItemParam] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Create the dictionary first
            message_dict = {}
            # システムメッセージはdeveloperロールとして扱う
            if role == "system":
                message_dict = {"role": "developer", "content": content}
            elif role == "user":
                message_dict = {"role": "user", "content": content}
            elif role == "assistant":
                message_dict = {"role": "assistant", "content": content}

            # Append the casted dictionary if it's not empty
            if message_dict:
                converted.append(cast(ResponseInputItemParam, message_dict))

        return converted

    def _extract_token_usage(self, usage_obj: Any) -> dict[str, int]:
        """使用されたトークン数を抽出する共通関数"""
        if not usage_obj:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        prompt_tokens = getattr(usage_obj, "input_tokens", 0)
        completion_tokens = getattr(usage_obj, "output_tokens", 0)
        total_tokens = getattr(
            usage_obj, "total_tokens", prompt_tokens + completion_tokens
        )

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    def _log_token_usage(
        self, usage_data: dict[str, int], model_name: str, source: str = ""
    ) -> None:
        """トークン使用量をログに記録する共通関数"""
        if source:
            source = f" from {source}"

        logger.info(
            f"OpenAI Responses token usage{source} - model: {model_name}, "
            f"prompt: {usage_data['prompt_tokens']}, "
            f"completion: {usage_data['completion_tokens']}, "
            f"total: {usage_data['total_tokens']}"
        )

    async def _non_stream_responses(
        self, messages: list[dict[str, str]], model_name: str
    ) -> dict[str, Any]:
        """非ストリーミングResponses APIを呼び出す"""
        # 既存のメッセージ形式をResponses API形式に変換
        converted_messages = self._convert_messages_format(messages)
        logger.debug(f"Sending to Responses API: {converted_messages}")

        try:
            # レスポンスを作成
            response = await self.client.responses.create(
                model=model_name, input=converted_messages
            )

            # レスポンスからコンテンツを取得
            content = response.output_text

            # トークン使用量を抽出
            usage_data = self._extract_token_usage(getattr(response, "usage", None))

            # 使用量をログに記録
            if usage_data["total_tokens"] > 0:
                self._log_token_usage(usage_data, model_name, "create response")
            else:
                logger.warning(
                    f"No usage data in create response for model: {model_name}"
                )

            # 標準形式に整形して返す
            return {"content": content, "token_usage": usage_data}

        except Exception as e:
            logger.error(f"Error in non-streaming response: {e}", exc_info=True)
            # エラー時はコンテンツなしと0トークンを返す
            return {
                "content": "Error getting response from OpenAI",
                "token_usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }

    async def _stream_responses(
        self, messages: list[dict[str, str]], model_name: str
    ) -> AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None]:
        """ストリーミングResponses APIを呼び出す"""
        converted_messages = self._convert_messages_format(messages)
        logger.debug(f"Sending to Responses API (streaming): {converted_messages}")

        try:
            # ストリーミングモードでレスポンスを作成
            stream = await self.client.responses.create(
                model=model_name, input=converted_messages, stream=True
            )

            # 完全なレスポンスを構築
            full_response = ""
            response_id = None  # レスポンスID (resp_XXX) を格納
            last_chunk = None

            # ストリーミングイベントを処理
            async for chunk in stream:
                last_chunk = chunk
                event_type = type(chunk).__name__

                # レスポンスIDを収集（様々なイベントソースから）
                if not response_id:
                    # レスポンスオブジェクトからID取得
                    if hasattr(chunk, "response") and hasattr(chunk.response, "id"):
                        response_id = chunk.response.id
                        logger.debug(
                            f"Captured response_id from response: {response_id}"
                        )
                    # イベント自体からID取得
                    elif event_type == "ResponseCreatedEvent" and hasattr(chunk, "id"):
                        response_id = chunk.id
                        logger.debug(
                            "Captured response_id from ResponseCreatedEvent: "
                            f"{response_id}"
                        )
                    # ResponseInProgressEventからID取得
                    elif event_type == "ResponseInProgressEvent" and hasattr(
                        chunk, "id"
                    ):
                        response_id = chunk.id
                        logger.debug(
                            "Captured response_id from ResponseInProgressEvent: "
                            f"{response_id}"
                        )
                    # その他の属性からID取得
                    elif hasattr(chunk, "response_id"):
                        response_id = chunk.response_id
                        logger.debug(f"Captured response_id from event: {response_id}")

                # テキストチャンクの処理
                if event_type == "ResponseTextDeltaEvent" and hasattr(chunk, "delta"):
                    delta_text = getattr(chunk, "delta", "")
                    full_response += delta_text
                    yield (delta_text, "answer", False, {})

                # ストリーミング完了イベントの処理
                elif event_type in ["ResponseTextDoneEvent", "ResponseCompletedEvent"]:
                    if event_type == "ResponseTextDoneEvent":
                        logger.debug("Received ResponseTextDoneEvent")
                    else:
                        logger.debug("Received ResponseCompletedEvent")
                    break

            # トークン使用量データの取得
            usage_data: dict[str, int] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

            # 1. 直接的な方法：イベントから直接usage情報を取得
            if (
                last_chunk is not None
                and hasattr(last_chunk, "usage")
                and last_chunk.usage
            ):
                usage_data = self._extract_token_usage(last_chunk.usage)
                self._log_token_usage(usage_data, model_name, "event")

            # 2. フォールバック：レスポンスIDを使って取得
            elif response_id and response_id.startswith("resp_"):
                try:
                    logger.debug(f"Getting response details with ID: {response_id}")
                    response_detail = await self.client.responses.retrieve(response_id)

                    if hasattr(response_detail, "usage") and response_detail.usage:
                        usage_data = self._extract_token_usage(response_detail.usage)
                        self._log_token_usage(usage_data, model_name, "retrieve")
                except Exception as e:
                    logger.error(f"Error retrieving response details: {str(e)}")
            else:
                logger.warning(
                    "No usage information available for streaming response. "
                    f"Response ID: {response_id}"
                )

            # ストリーム終了時にトークン使用量情報と共に完了を通知
            yield ("", "done", True, usage_data)

        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}", exc_info=True)
            yield ("", "done", True, {})
