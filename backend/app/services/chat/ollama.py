import logging
import json
import asyncio
import re
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
        # 思考プロセスを抽出するための正規表現パターン - 様々な形式に対応
        # 1. <think>\n...\n</think> - 行の先頭から始まり単独行で終わる
        # 2. <think>...</think> - 行の途中に埋め込まれている
        self.thinking_pattern = re.compile(
            r"<think>(?:\n)?(.*?)(?:\n)?</think>", re.DOTALL
        )
        logger.debug(f"Initialized thinking pattern: {self.thinking_pattern.pattern}")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model_name: str,
        stream: bool = False,
        thinking_mode: bool = False,
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, bool, dict], None]:
        """Ollamaのチャットエンドポイントを呼び出す"""
        processed_messages = messages.copy()  # メッセージリストをコピーして変更

        # 思考モードがFalseの場合、最後のユーザーメッセージにプレフィックスを追加
        if not thinking_mode and len(processed_messages) > 0:
            last_message_index = -1
            # 最後のメッセージがユーザーからのものか確認
            if processed_messages[last_message_index].get("role") == "user":
                content = processed_messages[last_message_index].get("content", "")
                processed_messages[last_message_index][
                    "content"
                ] = f" /no_think {content}"
                logger.info(
                    f"[OllamaProvider] Added /no_think prefix to last user message: '{processed_messages[last_message_index]['content'][:50]}...'"
                )
            else:
                logger.warning(
                    "[OllamaProvider] Last message is not from user, cannot add /no_think prefix."
                )

        request_data = {
            "model": model_name,
            "messages": processed_messages,  # 変更されたメッセージリストを使用
            "stream": stream,
        }

        logger.info(f"Sending request to Ollama API: {request_data}")

        if stream:
            return self._stream_chat_response(request_data, thinking_mode)

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

            complete_response = response_data.get("message", {}).get("content", "")

            # レスポンスから思考部分と回答部分を分離
            # _extract_thinking_and_answer は思考モードの有効/無効に関わらず実行
            extracted_thinking, extracted_answer = self._extract_thinking_and_answer(
                complete_response
            )

            # 思考モードが有効な場合のみ思考内容を返し、無効ならNoneを返す
            final_thinking_content = extracted_thinking if thinking_mode else None
            # 回答部分は常に抽出後のものを返す
            final_answer_content = extracted_answer

            logger.debug(
                f"Returning content (thinking_mode={thinking_mode}): {final_answer_content[:100]}..."
            )
            logger.debug(
                f"Returning thinking (thinking_mode={thinking_mode}): {final_thinking_content[:100] if final_thinking_content else 'None'}..."
            )

            return {
                "content": final_answer_content,  # 常に抽出後の回答を返す
                "thinking_content": final_thinking_content,  # thinking_modeに応じて返す
                "token_usage": token_usage,
            }

    def _extract_thinking_and_answer(self, text: str) -> tuple[str, str]:
        """思考部分と回答部分を抽出する"""
        # デバッグ用：入力テキストの先頭部分をログ出力
        preview_text = text[:200] + ("..." if len(text) > 200 else "")
        logger.debug(f"Extracting thinking and answer from text: {preview_text}")

        # 思考部分を検出
        thinking_match = self.thinking_pattern.search(text)
        logger.debug(f"Thinking pattern match found: {thinking_match is not None}")

        # 正規表現のパターンもログ出力
        logger.debug(f"Using thinking pattern: {self.thinking_pattern.pattern}")

        thinking_content = thinking_match.group(1).strip() if thinking_match else None
        if thinking_match:
            logger.debug(
                f"Extracted thinking content preview: {thinking_content[:100] if thinking_content else 'None'}..."
            )

        # 思考部分が見つかった場合は、それを除いた残りを回答とする
        if thinking_match:
            # 思考部分全体（タグ含む）を除去したテキスト
            # <think>から\n</think>までを削除し、その後のテキストを回答とする
            answer_content = text.replace(thinking_match.group(0), "").strip()

            # 先頭の空行を削除
            answer_content = answer_content.lstrip("\n")
            logger.debug(
                f"Answer content after removing thinking: {answer_content[:100]}..."
            )
        else:
            # 思考部分が見つからない場合は、テキスト全体が回答
            answer_content = text.strip()
            logger.debug("No thinking content found, using entire text as answer")

        return thinking_content, answer_content

    async def _stream_chat_response(
        self, request_data: dict, thinking_mode: bool = False
    ) -> AsyncGenerator[tuple[str, bool, dict], None]:
        """Ollamaストリーミングレスポンスをジェネレータとして処理"""
        complete_response = ""
        complete_thinking = ""
        in_thinking_block = False
        # 初期値は空の辞書にしておく
        token_usage = {}

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

                final_chunk_processed = False  # 最終チャンク処理済みフラグ
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        is_done = data.get("done", False)
                        current_usage = {}  # このチャンクで返すusage

                        if chunk:
                            # デバッグ用：チャンクの内容をログ出力
                            preview_chunk = chunk[:50] + (
                                "..." if len(chunk) > 50 else ""
                            )
                            logger.debug(f"Received chunk: '{preview_chunk}'")
                            logger.debug(f"In thinking block: {in_thinking_block}")

                            # 思考モードが有効な場合、チャンクを思考部分と回答部分に分割
                            if thinking_mode:
                                # <think>タグの開始を検出
                                if "<think>" in chunk and not in_thinking_block:
                                    in_thinking_block = True
                                    logger.debug(
                                        "Detected <think> tag, entering thinking block"
                                    )
                                    chunk_parts = chunk.split("<think>", 1)
                                    if chunk_parts[
                                        0
                                    ]:  # <think>の前に通常のテキストがある場合
                                        complete_response += chunk_parts[0]
                                        logger.debug(
                                            f"Added text before <think>: '{chunk_parts[0]}'"
                                        )
                                    if len(chunk_parts) > 1:
                                        complete_thinking += chunk_parts[1]
                                        logger.debug(
                                            f"Added to thinking: '{chunk_parts[1]}'"
                                        )
                                # </think>タグの終了を検出 - 単独行での終了を想定
                                elif "\n</think>" in chunk and in_thinking_block:
                                    in_thinking_block = False
                                    logger.debug(
                                        "Detected \\n</think> tag, exiting thinking block"
                                    )
                                    chunk_parts = chunk.split("\n</think>", 1)
                                    if chunk_parts[0]:  # </think>の前の思考部分
                                        complete_thinking += chunk_parts[0]
                                        logger.debug(
                                            f"Added final thinking content: '{chunk_parts[0]}'"
                                        )
                                    if len(chunk_parts) > 1:
                                        complete_response += chunk_parts[1]
                                        logger.debug(
                                            f"Added response after thinking: '{chunk_parts[1]}'"
                                        )
                                # 行の途中での</think>タグの処理も追加
                                elif "</think>" in chunk and in_thinking_block:
                                    in_thinking_block = False
                                    logger.debug(
                                        "Detected </think> tag (inline), exiting thinking block"
                                    )
                                    chunk_parts = chunk.split("</think>", 1)
                                    if chunk_parts[0]:  # </think>の前の思考部分
                                        complete_thinking += chunk_parts[0]
                                        logger.debug(
                                            f"Added final thinking content (inline): '{chunk_parts[0]}'"
                                        )
                                    if len(chunk_parts) > 1:
                                        complete_response += chunk_parts[1]
                                        logger.debug(
                                            f"Added response after thinking (inline): '{chunk_parts[1]}'"
                                        )
                                # 思考ブロック内の通常テキスト
                                elif in_thinking_block:
                                    complete_thinking += chunk
                                    logger.debug(
                                        f"Added to thinking block: '{preview_chunk}'"
                                    )
                                # 思考ブロック外の通常テキスト
                                else:
                                    complete_response += chunk
                                    logger.debug(
                                        f"Added to response: '{preview_chunk}'"
                                    )
                            else:
                                complete_response += chunk

                            # 中間チャンクではコンテンツのみを返す
                            yield (chunk, False, {})

                        if is_done:
                            # 最終チャンクからトークン数を取得
                            prompt_eval_count = data.get("prompt_eval_count", 0)
                            eval_count = data.get("eval_count", 0)
                            total_tokens = prompt_eval_count + eval_count

                            token_usage = {  # 確定したトークン数を格納
                                "prompt_tokens": prompt_eval_count,
                                "completion_tokens": eval_count,
                                "total_tokens": total_tokens,
                            }
                            current_usage = token_usage  # この最終チャンクで返すusage

                            logger.info(
                                f"Ollama streaming final token counts - prompt_eval_count: {prompt_eval_count}, "
                                f"eval_count: {eval_count}, total: {total_tokens}"
                            )
                            logger.debug(f"Final streaming chunk data: {data}")
                            logger.debug(
                                f"Complete response accumulated: '{complete_response[:100]}...'"
                            )
                            logger.debug(
                                f"Complete thinking accumulated: '{complete_thinking[:100] if complete_thinking else 'None'}...'"
                            )

                            # レスポンス全体から思考部分と回答部分を分離
                            final_thinking, final_answer = (
                                self._extract_thinking_and_answer(complete_response)
                            )

                            # 思考モードが有効の場合のみ思考内容を設定
                            if thinking_mode and final_thinking:
                                complete_thinking = final_thinking
                                logger.debug(
                                    f"Set final thinking content from extraction: '{complete_thinking[:100] if complete_thinking else 'None'}...'"
                                )
                            elif thinking_mode and complete_thinking:
                                logger.debug(
                                    f"Using accumulated thinking content: '{complete_thinking[:100]}...'"
                                )
                            else:
                                complete_thinking = None
                                logger.debug("No thinking content available")

                            # 思考モードが有効でかつ思考内容があれば、それを除いた部分を回答とする
                            if thinking_mode and final_thinking:
                                complete_response = final_answer
                                logger.debug(
                                    f"Set final response content from extraction: '{complete_response[:100]}...'"
                                )

                            # 思考部分と回答部分を辞書に格納
                            current_usage["thinking_content"] = complete_thinking

                            # 最終チャンクを処理したことをマーク
                            final_chunk_processed = True
                            # 空のチャンクと完了フラグ、トークン使用量を返す
                            yield ("", True, current_usage)
                            break  # is_doneが来たらループを抜ける

                        await asyncio.sleep(0.01)

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e} for line: {line}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing stream: {e}")
                        raise

                # ループが正常に終了したが is_done が True にならなかった場合
                # (基本的には起こらないはずだが念のため)
                if not final_chunk_processed:
                    logger.warning(
                        "Stream ended unexpectedly without a final 'done: true' chunk."
                    )
                    # 思考モードが有効な場合、思考部分と回答部分を辞書に格納
                    if thinking_mode:
                        current_usage = {"thinking_content": complete_thinking}

                    # 完了と見なして空のチャンクと空のusageを返す
                    yield ("", True, current_usage)

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
