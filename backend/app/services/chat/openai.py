import logging
import json
from typing import Any, AsyncGenerator
import httpx

from app.services.chat.base import ModelProvider

# ロガーの設定
logger = logging.getLogger(__name__)

class OpenAIProvider(ModelProvider):
    """OpenAIモデルプロバイダの実装"""

    def __init__(self, api_key: str, organization_id: str | None = None):
        self.api_key = api_key
        self.organization_id = organization_id
        self.base_url = "https://api.openai.com/v1"

    async def chat_completion(
        self, messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool], None]:
        """OpenAIのチャットエンドポイントを呼び出す"""
        # モデル名からAPI種別を判定
        api_type = self._get_api_type(model_name)

        if api_type == "responses":
            return await self._responses_completion(messages, model_name, stream)
        else:
            return await self._chat_completion(messages, model_name, stream)

    def _get_api_type(self, model_name: str) -> str:
        """モデル名からAPI種別を判定"""
        # 明示的にResponses APIを指定された場合のみResponses APIを使用
        if "responses:" in model_name.lower():
            # "responses:" プレフィックスを削除して実際のモデル名を返す
            return "responses"

        # それ以外の全モデルはChat Completions APIを使用
        return "chat_completions"

    async def _chat_completion(
        self, messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool], None]:
        """OpenAIのChat Completions APIを呼び出す"""
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

        logger.info(f"Sending request to OpenAI Chat Completions API: {request_data}")

        if stream:
            return self._stream_chat_completion(request_data, headers)

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

    async def _responses_completion(
        self, messages: list[dict[str, str]], model_name: str, stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool], None]:
        """OpenAIのResponses APIを呼び出す"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization_id:
            headers["OpenAI-Organization"] = self.organization_id

        # Responsesフォーマットにメッセージを変換
        input_content = self._format_messages_for_responses(messages)

        request_data = {
            "model": self._normalize_model_name(model_name),
            "input": input_content,
            "stream": stream,
            "store": False,  # サーバーに会話を保存しない
        }

        logger.info(f"Sending request to OpenAI Responses API: {request_data}")

        if stream:
            return self._stream_responses_completion(request_data, headers)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/responses",
                headers=headers,
                json=request_data,
            )
            if response.status_code != 200:
                logger.error(
                    f"OpenAI Responses API error: {response.status_code} {response.text}"
                )
                raise Exception(
                    f"Failed to get response from OpenAI Responses: {response.status_code} {response.text}"
                )

            response_data = response.json()
            logger.info(f"Received response from OpenAI Responses API: {response_data}")

            # Responses API形式からOllama形式に変換
            content = response_data.get("text", "")
            return {"message": {"content": content}}

    def _normalize_model_name(self, model_name: str) -> str:
        """モデル名を正規化"""
        # "responses:" プレフィックスがある場合は削除
        if model_name.lower().startswith("responses:"):
            model_name = model_name[10:]

        model_mapping = {
            "gpt4.1nano": "gpt-4.1-nano",
            "gpt41nano": "gpt-4.1-nano",
            "gpt-41-nano": "gpt-4.1-nano",
        }

        # 特殊な形式の場合は正規化
        normalized = model_name.lower().replace(".", "").replace("-", "")
        if normalized in model_mapping:
            return model_mapping[normalized]

        return model_name

    def _format_messages_for_responses(self, messages: list[dict[str, str]]) -> str:
        """メッセージをResponses APIフォーマットに変換"""
        # システムメッセージを抽出
        system_message = None
        conversation_history = []

        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")

            if role == "system":
                system_message = content
            else:
                # ユーザーとアシスタントの会話履歴を構築
                if role == "user":
                    conversation_history.append(f"ユーザー: {content}")
                elif role == "assistant":
                    conversation_history.append(f"アシスタント: {content}")

        # システムメッセージとこれまでの会話履歴を含む最終的なプロンプトを構築
        final_prompt = ""

        if system_message:
            final_prompt += f"{system_message}\n\n"

        if conversation_history:
            # 最後のユーザーメッセージを除く会話履歴
            conversation_context = "\n".join(conversation_history[:-1])
            if conversation_context:
                final_prompt += f"これまでの会話：\n{conversation_context}\n\n"

            # 最後のユーザーメッセージ（通常は現在の質問）
            last_user_message = (
                conversation_history[-1]
                if conversation_history
                and conversation_history[-1].startswith("ユーザー: ")
                else None
            )
            if last_user_message:
                final_prompt += last_user_message.replace("ユーザー: ", "", 1)

        # 空の場合はエラー回避
        if not final_prompt.strip():
            logger.warning("Empty prompt generated for Responses API")
            # messagesから直接最後のユーザーメッセージを探す
            for msg in reversed(messages):
                if msg["role"] == "user":
                    return msg["content"]
            return "Empty message"

        logger.debug(f"Formatted prompt for Responses API: {final_prompt}")
        return final_prompt

    async def _stream_chat_completion(
        self, request_data: dict, headers: dict[str, str]
    ) -> AsyncGenerator[tuple[str, bool], None]:
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

    async def _stream_responses_completion(
        self, request_data: dict, headers: dict[str, str]
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """OpenAI Responses APIストリーミングレスポンスをジェネレータとして処理"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/responses",
                headers=headers,
                json=request_data,
                timeout=300.0,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(
                        f"OpenAI Responses API error: {response.status_code} {error_text!r}"
                    )
                    raise Exception(
                        f"Error from OpenAI Responses API: {response.status_code}"
                    )

                # SSE形式のレスポンスを処理するための変数
                complete_text = ""  # 完全なテキスト
                is_completed = False
                current_event = None  # 現在処理中のイベント
                json_data = None  # イベントのデータ

                # 最後のチャンクが処理されたかどうかを追跡
                last_chunk_processed = False
                last_delta_sent = False

                try:
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        logger.debug(f"SSE Line: {line}")

                        # イベント行の処理
                        if line.startswith("event:"):
                            current_event = line[6:].strip()
                            logger.debug(f"SSE event: {current_event}")

                            # 完了イベントを検出
                            if current_event in [
                                "response.completed",
                                "response.output_text.done",
                            ]:
                                is_completed = True
                            continue

                        # データ行の処理
                        if line.startswith("data:"):
                            data_content = line[5:].strip()
                            if data_content == "[DONE]":
                                if not last_delta_sent:
                                    logger.info(
                                        "Received [DONE] marker, sending final done signal"
                                    )
                                    yield ("", True)
                                    last_delta_sent = True
                                break

                            # データが空でなければJSON解析を試みる
                            if data_content:
                                try:
                                    json_data = json.loads(data_content)

                                    # データタイプによる処理分岐
                                    if (
                                        current_event == "response.output_text.delta"
                                        and "delta" in json_data
                                    ):
                                        # デルタ（差分）テキストを取得
                                        delta = json_data.get("delta", "")
                                        if delta:
                                            complete_text += delta
                                            logger.debug(
                                                f"Delta text: {delta}, is_completed: {is_completed}"
                                            )
                                            yield (delta, is_completed)

                                            if is_completed and not last_delta_sent:
                                                last_delta_sent = True

                                    # 完全なテキストを含むデータの場合
                                    elif "text" in json_data:
                                        new_text = json_data["text"]
                                        if new_text != complete_text:
                                            # 差分を計算して送信
                                            delta = new_text[len(complete_text) :]
                                            complete_text = new_text

                                            if delta:
                                                logger.debug(
                                                    f"Text delta from full text: {delta}"
                                                )
                                                yield (delta, is_completed)

                                                if is_completed and not last_delta_sent:
                                                    last_delta_sent = True
                                except json.JSONDecodeError:
                                    logger.debug(f"Invalid JSON data: {data_content}")
                                except Exception as e:
                                    logger.error(f"Error processing data: {str(e)}")
                            continue

                    # ストリームが完了した後の最終処理
                    if not last_delta_sent:
                        logger.info("Stream ended, sending final done signal")
                        yield ("", True)

                except Exception as e:
                    logger.error(f"Error in stream processing: {str(e)}", exc_info=True)
                    # エラーでも最後の完了シグナルを送信
                    if not last_delta_sent:
                        yield ("", True)

    async def text_generation(self, prompt: str, model_name: str) -> str:
        """OpenAIのテキスト生成エンドポイントを呼び出す"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization_id:
            headers["OpenAI-Organization"] = self.organization_id

        # API種別の判定
        api_type = self._get_api_type(model_name)

        if api_type == "responses":
            # Responses APIを使用
            request_data = {
                "model": self._normalize_model_name(model_name),
                "input": prompt,
                "store": False,
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{self.base_url}/responses",
                        headers=headers,
                        json=request_data,
                    )

                    if response.status_code != 200:
                        logger.error(
                            f"Failed to generate text: {response.status_code} {response.text}"
                        )
                        return ""

                    response_data = response.json()
                    return response_data.get("text", "").strip()

            except Exception as e:
                logger.error(f"Error generating text: {e}")
                return ""
        else:
            # Chat Completionsを使用
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
