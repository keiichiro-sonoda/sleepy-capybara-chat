import logging
import json
import asyncio
from typing import Any, AsyncGenerator
import httpx

from app.services.chat.base import ModelProvider

# ロガーの設定
logger = logging.getLogger(__name__)

class OllamaProvider(ModelProvider):
    """Ollamaモデルプロバイダの実装"""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def chat_completion(
        self, messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool], None]:
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
            logger.info(f"Received response from Ollama API: {response_data}")
            return response_data

    async def _stream_chat_response(
        self, request_data: dict
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """Ollamaストリーミングレスポンスをジェネレータとして処理"""
        complete_response = ""

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

                        # 応答テキストを取得
                        chunk = data.get("message", {}).get("content", "")
                        is_done = data.get("done", False)

                        # ログを追加して状態を確認
                        logger.debug(
                            f"Ollama stream chunk: length={len(chunk) if chunk else 0}, is_done={is_done}"
                        )

                        if chunk:
                            complete_response += chunk
                            # is_doneと一緒にチャンクを送信
                            yield (chunk, is_done)

                        # 完了フラグがTrueの場合
                        if is_done:
                            # 最後のチャンクのみで完了する場合はすでに送信されているので、
                            # 追加のチャンクがない場合でも、もう一度完了フラグをTrueで送信する
                            if not chunk:
                                logger.info(
                                    f"Stream done with no final chunk, sending final done signal"
                                )
                                # 空文字を送信し、is_done=Trueを知らせる
                                yield ("", True)
                            break

                        # 少し待機
                        await asyncio.sleep(0.01)

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e} for line: {line}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing stream: {e}")
                        raise Exception(f"Error processing stream: {e}")

                # ストリームが終了したが、is_doneが送られてこなかった場合のフォールバック
                logger.info(
                    f"Stream ended without explicit done flag, sending final done signal"
                )
                yield ("", True)

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
