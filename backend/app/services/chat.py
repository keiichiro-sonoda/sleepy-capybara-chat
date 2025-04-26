import logging
from abc import ABC, abstractmethod
import json
import asyncio
from typing import Dict, List, Any, AsyncGenerator, Optional, Tuple
import httpx

from app.core.config import get_settings

# ロガーの設定
logger = logging.getLogger(__name__)
settings = get_settings()


class ModelProvider(ABC):
    """AIモデルプロバイダの抽象基底クラス"""

    @abstractmethod
    async def chat_completion(
        self, messages: List[Dict[str, str]], model_name: str, stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator[str, None]:
        """チャット完了APIを呼び出す"""
        pass

    @abstractmethod
    async def text_generation(self, prompt: str, model_name: str) -> str:
        """テキスト生成APIを呼び出す"""
        pass


class OllamaProvider(ModelProvider):
    """Ollamaモデルプロバイダの実装"""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def chat_completion(
        self, messages: List[Dict[str, str]], model_name: str, stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator[str, None]:
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
    ) -> AsyncGenerator[Tuple[str, bool], None]:
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


class OpenAIProvider(ModelProvider):
    """OpenAIモデルプロバイダの実装"""

    def __init__(self, api_key: str, organization_id: Optional[str] = None):
        self.api_key = api_key
        self.organization_id = organization_id
        self.base_url = "https://api.openai.com/v1"

    async def chat_completion(
        self, messages: List[Dict[str, str]], model_name: str, stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator[str, None]:
        """OpenAIのチャットエンドポイントを呼び出す"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization_id:
            headers["OpenAI-Organization"] = self.organization_id

        request_data = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }

        logger.info(f"Sending request to OpenAI API: {request_data}")

        if stream:
            return self._stream_chat_response(request_data, headers)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_data,
            )
            if response.status_code != 200:
                logger.error(
                    f"OpenAI API error: {response.status_code} {response.text}"
                )
                raise Exception(
                    f"Failed to get response from OpenAI: {response.status_code} {response.text}"
                )

            response_data = response.json()
            logger.info(f"Received response from OpenAI API: {response_data}")

            # OpenAI形式からOllama形式に変換
            content = response_data["choices"][0]["message"]["content"]
            return {"message": {"content": content}}

    async def _stream_chat_response(
        self, request_data: dict, headers: Dict[str, str]
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        """OpenAIストリーミングレスポンスをジェネレータとして処理"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_data,
                timeout=300.0,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(
                        f"OpenAI API error: {response.status_code} {error_text!r}"
                    )
                    raise Exception(f"Error from OpenAI API: {response.status_code}")

                # 最後のチャンクが処理されたかどうかを追跡
                last_chunk_processed = False

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # 完了メッセージの場合
                    if line.startswith("data: [DONE]"):
                        if not last_chunk_processed:
                            # 最後の完了シグナルを送信
                            logger.info(
                                f"Received [DONE] signal, sending final done signal"
                            )
                            yield ("", True)
                        break

                    if line.startswith("data: "):
                        line = line[6:]  # "data: " を削除

                    try:
                        data = json.loads(line)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            chunk = delta.get("content", "")
                            is_done = (
                                data["choices"][0].get("finish_reason") is not None
                            )

                            # ログを追加して状態を確認
                            logger.debug(
                                f"OpenAI stream chunk: length={len(chunk) if chunk else 0}, is_done={is_done}"
                            )

                            if chunk:
                                yield (chunk, is_done)

                                # 最後のチャンクがis_done=Trueの場合、処理済みとマーク
                                if is_done:
                                    last_chunk_processed = True

                            # 空のデルタで完了シグナルが来た場合
                            elif is_done and not chunk:
                                logger.info(
                                    f"Empty delta with finish_reason, sending final done signal"
                                )
                                yield ("", True)
                                last_chunk_processed = True

                            if is_done:
                                break

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e} for line: {line}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing stream: {e}")
                        raise Exception(f"Error processing stream: {e}")

                # ストリームが終了したが、is_doneが送られてこなかった場合のフォールバック
                if not last_chunk_processed:
                    logger.info(
                        f"Stream ended without explicit done flag, sending final done signal"
                    )
                    yield ("", True)

    async def text_generation(self, prompt: str, model_name: str) -> str:
        """OpenAIのテキスト生成エンドポイントを呼び出す"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization_id:
            headers["OpenAI-Organization"] = self.organization_id

        request_data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=request_data,
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to generate text: {response.status_code} {response.text}"
                    )
                    return ""

                response_data = response.json()
                return response_data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""


class ProviderFactory:
    """AIプロバイダファクトリークラス"""

    @staticmethod
    def get_provider(provider_name: str) -> ModelProvider:
        """指定されたプロバイダ名に基づいてプロバイダインスタンスを返す"""
        settings = get_settings()

        if provider_name.lower() == "ollama":
            return OllamaProvider(settings.OLLAMA_API_BASE_URL)
        elif provider_name.lower() == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key is not set")
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                organization_id=settings.OPENAI_ORGANIZATION_ID,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")


class ChatService:
    """チャットサービスクラス"""

    @staticmethod
    def get_provider_from_model(model_name: str) -> Tuple[str, str]:
        """モデル名からプロバイダとモデルを判定"""
        # モデル名の規則に基づいてプロバイダを判定
        if model_name.startswith("gpt-") or model_name.startswith("openai:"):
            if model_name.startswith("openai:"):
                model_name = model_name[7:]  # "openai:" プレフィックスを削除
            return "openai", model_name
        else:
            return "ollama", model_name

    @staticmethod
    async def generate_session_name_from_message(message_content: str) -> str:
        """最初のメッセージの内容を基にセッション名を生成する"""
        prompt = f"""あなたはチャットセッションの名前を生成するアシスタントです。
以下のメッセージの内容を基に、20文字以内の簡潔で分かりやすいセッション名を1つだけ返してください。
メッセージ: {message_content}"""

        try:
            # Ollamaプロバイダを使用
            provider = ProviderFactory.get_provider("ollama")
            generated_name = await provider.text_generation(prompt, "llama3")

            # 生成された名前が長すぎる場合はカット
            if len(generated_name) > 20:
                generated_name = generated_name[:17] + "..."

            return generated_name

        except Exception as e:
            logger.error(f"Error generating session name: {e}")
            return "新しいチャット"

    @staticmethod
    async def get_chat_response(
        messages: List[Dict[str, str]], model_name: str, stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator[Tuple[str, bool], None]:
        """適切なプロバイダを使用してチャットレスポンスを取得"""
        provider_name, actual_model = ChatService.get_provider_from_model(model_name)
        provider = ProviderFactory.get_provider(provider_name)
        return await provider.chat_completion(messages, actual_model, stream)
