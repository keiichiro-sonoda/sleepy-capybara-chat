import logging
import json
import asyncio
from typing import Any, AsyncGenerator
import httpx

from app.services.chat.base import ModelProvider

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class OllamaProvider(ModelProvider):
    """Ollamaモデルプロバイダの実装"""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def chat_completion(
        self, messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool, dict], None]:
        """Ollamaのチャットエンドポイントを呼び出す"""
        request_data = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }

        logger.info(f"Sending request to Ollama API: {request_data}")

        if stream:
            return self._stream_chat_response(request_data)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=request_data,
            )
            if response.status_code != 200:
                logger.error(
                    f"Ollama API error: {response.status_code} {response.text}"
                )
                raise Exception(
                    f"Failed to get response from Ollama: {response.status_code} {response.text}"
                )

            response_data = response.json()

            # トークン使用量を詳細にログ出力
            prompt_eval_count = response_data.get("prompt_eval_count", 0)
            eval_count = response_data.get("eval_count", 0)
            total_tokens = prompt_eval_count + eval_count

            logger.info(
                f"Ollama API token counts - prompt_eval_count: {prompt_eval_count}, "
                f"eval_count: {eval_count}, total: {total_tokens}"
            )
            logger.debug(f"Complete Ollama API response: {response_data}")

            token_usage = {
                "prompt_tokens": prompt_eval_count,
                "completion_tokens": eval_count,
                "total_tokens": total_tokens,
            }

            return {
                "content": response_data.get("message", {}).get("content", ""),
                "token_usage": token_usage,
            }

    async def _stream_chat_response(
        self, request_data: dict
    ) -> AsyncGenerator[tuple[str, bool, dict], None]:
        """Ollamaストリーミングレスポンスをジェネレータとして処理"""
        complete_response = ""
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=request_data, timeout=300.0
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(
                        f"Ollama API error: {response.status_code} {error_text!r}"
                    )
                    raise Exception(f"Error from Ollama API: {response.status_code}")

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        is_done = data.get("done", False)

                        if is_done:
                            # 最終チャンクからトークン数を取得
                            prompt_eval_count = data.get("prompt_eval_count", 0)
                            eval_count = data.get("eval_count", 0)
                            total_tokens = prompt_eval_count + eval_count

                            token_usage = {
                                "prompt_tokens": prompt_eval_count,
                                "completion_tokens": eval_count,
                                "total_tokens": total_tokens,
                            }

                            logger.info(
                                f"Ollama streaming final token counts - prompt_eval_count: {prompt_eval_count}, "
                                f"eval_count: {eval_count}, total: {total_tokens}"
                            )
                            logger.debug(f"Final streaming chunk data: {data}")

                        # チャンク、完了フラグ、トークン使用量を返す
                        if chunk:
                            complete_response += chunk
                            yield (chunk, is_done, token_usage if is_done else {})

                        if is_done:
                            break

                        await asyncio.sleep(0.01)

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e} for line: {line}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing stream: {e}")
                        raise

                # ストリームが終了したが、is_doneが送られてこなかった場合のフォールバック
                if not is_done:
                    logger.warning(
                        "Stream ended without explicit done flag, sending empty token usage"
                    )
                    yield ("", True, token_usage)

    async def text_generation(self, prompt: str, model_name: str) -> str:
        """Ollamaのテキスト生成エンドポイントを呼び出す"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                    },
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to generate text: {response.status_code} {response.text}"
                    )
                    return ""

                response_data = response.json()
                return response_data.get("response", "").strip()

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""
