import logging
import json
import asyncio
import re
from typing import Any, AsyncGenerator, cast
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
    ) -> dict[str, Any] | AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None]:
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

    def _extract_thinking_and_answer(self, text: str) -> tuple[str | None, str]:
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
    ) -> AsyncGenerator[tuple[str, str, bool, dict[Any, Any]], None]:
        """Ollamaストリーミングレスポンスをジェネレータとして処理 (チャンクタイプ付き)"""
        complete_response = ""
        complete_thinking = ""
        in_thinking_block = False
        is_first_chunk = True
        ignore_next_newline_chunk = False
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

                final_chunk_processed = False
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        is_done = data.get("done", False)
                        current_usage = {}  # このチャンクで返すusage

                        if chunk:
                            preview_chunk = chunk.replace("\n", "\\n")[:50] + (
                                "..." if len(chunk) > 50 else ""
                            )
                            logger.debug(
                                f"Received chunk: '{preview_chunk}', In thinking: {in_thinking_block}, IgnoreNextNL: {ignore_next_newline_chunk}"
                            )

                            # --- 統合された改行無視 & 思考ブロック検出 ---
                            processed_chunk_for_yield = None
                            processed_for_yield_type = None

                            # 1. タグ直後の改行チャンク無視処理
                            if ignore_next_newline_chunk:
                                if chunk.strip() == "":
                                    logger.debug(
                                        "Ignoring newline-only chunk after tag."
                                    )
                                    ignore_next_newline_chunk = False
                                    continue
                                else:
                                    logger.warning(
                                        "Expected newline-only chunk after tag, but got something else. Resetting ignore flag."
                                    )
                                    ignore_next_newline_chunk = False
                                    # このチャンクはステップ2以降で通常処理

                            # 2. 最初のチャンク処理 (思考開始判定)
                            if is_first_chunk:
                                logger.debug("Processing first chunk...")
                                if chunk == "<think>":
                                    in_thinking_block = True
                                    ignore_next_newline_chunk = True
                                    logger.debug(
                                        "Detected <think>, entering thinking block."
                                    )
                                    # <think> 自体は保存もyieldもしない
                                else:
                                    in_thinking_block = False
                                    logger.debug(
                                        "First chunk is not <think>, treating as response."
                                    )
                                    complete_response += chunk
                                    processed_chunk_for_yield = chunk
                                    processed_for_yield_type = "answer"
                                is_first_chunk = False

                            # 3. 思考ブロック中の処理 (思考終了判定含む)
                            elif in_thinking_block:
                                logger.debug("Currently in thinking block.")
                                if chunk == "</think>":
                                    in_thinking_block = False
                                    ignore_next_newline_chunk = True
                                    logger.debug(
                                        "Detected </think>, exiting thinking block."
                                    )
                                    # </think> 自体は保存もyieldもしない
                                else:
                                    complete_thinking += chunk
                                    processed_chunk_for_yield = chunk
                                    processed_for_yield_type = "thinking"

                            # 4. 通常の回答処理 (思考ブロック外)
                            else:  # not in_thinking_block and not is_first_chunk and not ignore_next_newline_chunk
                                logger.debug("Processing regular response chunk.")
                                complete_response += chunk
                                processed_chunk_for_yield = chunk
                                processed_for_yield_type = "answer"

                            # 5. クライアントに yield するチャンクがあれば送信
                            if processed_chunk_for_yield is not None:
                                chunk_type_for_yield = (
                                    processed_for_yield_type or "answer"
                                )
                                logger.debug(
                                    f"Yielding chunk: '{processed_chunk_for_yield.replace('\n','\\n')[:50]}' as {chunk_type_for_yield}"
                                )
                                yield (
                                    processed_chunk_for_yield,
                                    chunk_type_for_yield,
                                    False,
                                    {},
                                )
                            # --- 統合された改行無視 & 思考ブロック検出 ここまで ---

                        if is_done:
                            logger.debug("Processing final (is_done=True) chunk.")
                            prompt_eval_count = data.get("prompt_eval_count", 0)
                            eval_count = data.get("eval_count", 0)
                            total_tokens = prompt_eval_count + eval_count

                            token_usage = {
                                "prompt_tokens": prompt_eval_count,
                                "completion_tokens": eval_count,
                                "total_tokens": total_tokens,
                            }
                            current_usage = token_usage

                            logger.info(
                                f"Ollama streaming final token counts - prompt_eval_count: {prompt_eval_count}, "
                                f"eval_count: {eval_count}, total: {total_tokens}"
                            )
                            logger.debug(f"Final streaming chunk data: {data}")

                            # 最終的に返す内容を決定 (前後の空白・改行を除去)
                            final_thinking_content_to_return = (
                                complete_thinking.strip() if thinking_mode else None
                            )
                            final_answer_content_to_return = complete_response.strip()

                            logger.debug(
                                f"Complete response accumulated (stripped): '{final_answer_content_to_return.replace('\n','\\n')[:100]}...'"
                            )
                            logger.debug(
                                f"Complete thinking accumulated (stripped): '{final_thinking_content_to_return.replace('\n','\\n')[:100] if final_thinking_content_to_return else 'None'}...'"
                            )

                            current_usage["thinking_content"] = (
                                final_thinking_content_to_return
                            )
                            final_chunk_to_yield = ""

                            final_chunk_processed = True
                            # yield する型を変更 (chunk='', type='done' とする)
                            yield (final_chunk_to_yield, "done", True, current_usage)
                            break

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
                    yield ("", "done", True, current_usage)

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
                # Cast the result of get().strip() to str before returning
                return cast(str, response_data.get("response", "").strip())

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""
