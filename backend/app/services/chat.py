import logging
from app.core.config import get_settings
import httpx

# ロガーの設定
logger = logging.getLogger(__name__)
settings = get_settings()


class ChatService:
    @staticmethod
    async def generate_session_name_from_message(message_content: str) -> str:
        """最初のメッセージの内容を基にセッション名を生成する"""
        prompt = f"""あなたはチャットセッションの名前を生成するアシスタントです。
以下のメッセージの内容を基に、20文字以内の簡潔で分かりやすいセッション名を1つだけ返してください。
メッセージ: {message_content}"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_API_BASE_URL}/api/generate",
                    json={
                        "model": "llama3",
                        "prompt": prompt,
                        "stream": False,
                    },
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to generate session name: {response.status_code} {response.text}"
                    )
                    return "新しいチャット"

                response_data = response.json()
                generated_name = response_data.get("response", "").strip()

                # 生成された名前が長すぎる場合はカット
                if len(generated_name) > 20:
                    generated_name = generated_name[:17] + "..."

                return generated_name

        except Exception as e:
            logger.error(f"Error generating session name: {e}")
            return "新しいチャット"
