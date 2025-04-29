import logging
from app.core.config import get_settings
from typing import Any, AsyncGenerator, Tuple

from app.services.chat.base import ModelProvider
from app.services.chat.ollama import OllamaProvider
from app.services.chat.openai import OpenAIProvider

# ロガーの設定
logger = logging.getLogger(__name__)
settings = get_settings()


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
            return OpenAIProvider()
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")


class ChatService:
    """チャットサービスクラス"""

    @staticmethod
    def get_provider_from_model(model_name: str) -> Tuple[str, str]:
        """モデル名からプロバイダとモデルを判定"""
        # OpenAIプロバイダを使用する条件
        if (
            model_name.startswith("gpt-")
            or model_name.startswith("openai:")
            or model_name.startswith("responses:")
            or "gpt4" in model_name.lower().replace("-", "").replace(".", "")
        ):
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
        messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool, dict], None]:
        """適切なプロバイダを使用してチャットレスポンスを取得"""
        provider_name, actual_model = ChatService.get_provider_from_model(model_name)
        logger.debug(
            f"Using provider: {provider_name}, model: {actual_model}, stream: {stream}"
        )

        provider = ProviderFactory.get_provider(provider_name)
        response = await provider.chat_completion(messages, actual_model, stream)

        if not stream:
            logger.debug(
                f"Non-streaming response type: {type(response)}, content: {response}"
            )

        return response
