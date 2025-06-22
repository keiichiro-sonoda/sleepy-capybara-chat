import asyncio
import json
import logging
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
                    "[OllamaProvider] Added /no_think prefix to last user message: "
                    f"'{processed_messages[last_message_index]['content'][:50]}...'"
                )
            else:
                logger.warning(
                    "[OllamaProvider] Last message is not from user, "
                    "cannot add /no_think prefix."
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
                    "Failed to get response from Ollama: "
                    f"{response.status_code} {response.text}"
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

            content_length = len(final_answer_content)
            thinking_length = (
                len(final_thinking_content) if final_thinking_content else 0
            )

            logger.debug(
                f"Returning response (thinking_mode={thinking_mode}): "
                f"content_length={content_length}, thinking_length={thinking_length}"
            )

            return {
                "content": final_answer_content,  # 常に抽出後の回答を返す
                "thinking_content": final_thinking_content,  # thinking_modeに応じて返す
                "token_usage": token_usage,
            }

    def _extract_thinking_and_answer(self, text: str) -> tuple[str | None, str]:
        """思考部分と回答部分を抽出する"""
        logger.debug(f"Extracting thinking and answer from text (length: {len(text)})")

        # 思考部分を検出
        thinking_match = self.thinking_pattern.search(text)
        logger.debug(f"Thinking pattern match found: {thinking_match is not None}")

        thinking_content = thinking_match.group(1).strip() if thinking_match else None

        # 思考部分が見つかった場合は、それを除いた残りを回答とする
        if thinking_match:
            # 思考部分全体（タグ含む）を除去したテキスト
            # <think>から\n</think>までを削除し、その後のテキストを回答とする
            answer_content = text.replace(thinking_match.group(0), "").strip()

            # 先頭の空行を削除
            answer_content = answer_content.lstrip("\n")
            logger.debug(f"Answer content extracted (length: {len(answer_content)})")
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
                            # チャンク処理
                            result = self._process_chunk(
                                chunk,
                                in_thinking_block,
                                is_first_chunk,
                                ignore_next_newline_chunk,
                                complete_response,
                                complete_thinking,
                            )

                            # 結果が None の場合はこのチャンクをスキップ
                            if result[0] is None and result[1] is None:
                                (
                                    _,
                                    _,
                                    in_thinking_block,
                                    is_first_chunk,
                                    ignore_next_newline_chunk,
                                    complete_response,
                                    complete_thinking,
                                ) = result
                                continue

                            # 結果を展開
                            (
                                processed_chunk_for_yield,
                                processed_for_yield_type,
                                in_thinking_block,
                                is_first_chunk,
                                ignore_next_newline_chunk,
                                complete_response,
                                complete_thinking,
                            ) = result

                            # クライアントに yield するチャンクがあれば送信
                            if processed_chunk_for_yield is not None:
                                chunk_type_for_yield = (
                                    processed_for_yield_type or "answer"
                                )
                                yield (
                                    processed_chunk_for_yield,
                                    chunk_type_for_yield,
                                    False,
                                    {},
                                )

                        if is_done:
                            logger.debug("Processing final chunk")
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
                                "Ollama streaming final token counts - "
                                f"prompt_eval_count: {prompt_eval_count}, "
                                f"eval_count: {eval_count}, total: {total_tokens}"
                            )

                            # 最終的に返す内容を決定 (前後の空白・改行を除去)
                            final_thinking_content_to_return = (
                                complete_thinking.strip() if thinking_mode else None
                            )
                            final_answer_content_to_return = complete_response.strip()

                            # ログ用の変数を準備
                            answer_length = len(final_answer_content_to_return)
                            thinking_length = (
                                len(final_thinking_content_to_return)
                                if final_thinking_content_to_return
                                else 0
                            )

                            logger.debug(
                                f"Final response: length={answer_length}, "
                                f"thinking_length={thinking_length}"
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

    def _process_chunk(
        self,
        chunk: str,
        in_thinking_block: bool,
        is_first_chunk: bool,
        ignore_next_newline_chunk: bool,
        complete_response: str,
        complete_thinking: str,
    ) -> tuple[str | None, str | None, bool, bool, bool, str, str]:
        """チャンクを処理し、yield用のデータと更新された状態を返す"""
        logger.debug(
            f"Processing chunk (length: {len(chunk)}, in_thinking: {in_thinking_block})"
        )

        processed_chunk_for_yield = None
        processed_for_yield_type = None

        # 1. タグ直後の改行チャンク無視処理
        if ignore_next_newline_chunk:
            if chunk.strip() == "":
                logger.debug("Ignoring newline-only chunk after tag.")
                return (
                    None,
                    None,
                    in_thinking_block,
                    False,
                    False,
                    complete_response,
                    complete_thinking,
                )
            else:
                logger.warning(
                    "Expected newline-only chunk after tag, but got something else."
                )
                ignore_next_newline_chunk = False

        # 2. 最初のチャンク処理 (思考開始判定)
        if is_first_chunk:
            logger.debug("Processing first chunk")
            if chunk == "<think>":
                in_thinking_block = True
                ignore_next_newline_chunk = True
                logger.debug("Entering thinking block")
            else:
                in_thinking_block = False
                logger.debug("First chunk is regular response")
                complete_response += chunk
                processed_chunk_for_yield = chunk
                processed_for_yield_type = "answer"
            is_first_chunk = False

        # 3. 思考ブロック中の処理 (思考終了判定含む)
        elif in_thinking_block:
            if chunk == "</think>":
                in_thinking_block = False
                ignore_next_newline_chunk = True
                logger.debug("Exiting thinking block")
            else:
                complete_thinking += chunk
                processed_chunk_for_yield = chunk
                processed_for_yield_type = "thinking"

        # 4. 通常の回答処理 (思考ブロック外)
        else:
            complete_response += chunk
            processed_chunk_for_yield = chunk
            processed_for_yield_type = "answer"

        return (
            processed_chunk_for_yield,
            processed_for_yield_type,
            in_thinking_block,
            is_first_chunk,
            ignore_next_newline_chunk,
            complete_response,
            complete_thinking,
        )

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
                        f"Failed to generate text: {response.status_code} "
                        f"{response.text}"
                    )
                    return ""

                response_data = response.json()
                # Cast the result of get().strip() to str before returning
                return cast(str, response_data.get("response", "").strip())

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""
