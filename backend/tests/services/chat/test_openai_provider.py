from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat.openai import OpenAIProvider


class MockAsyncIterator:
    """非同期イテレータのモック"""

    def __init__(self, items: list[Any]) -> None:
        self.items: Iterator[Any] = iter(items)

    def __aiter__(self) -> "MockAsyncIterator":
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration


class TestOpenAIProviderStreaming:
    """OpenAIプロバイダーのストリーミング処理のテスト"""

    @pytest.fixture
    def provider(self) -> OpenAIProvider:
        """OpenAIプロバイダーのインスタンスを作成"""
        return OpenAIProvider()

    @pytest.mark.asyncio
    async def test_empty_stream_handling(self, provider: OpenAIProvider) -> None:
        """空のストリームでもエラーが発生しないことをテスト"""
        # 空のストリームをモック
        mock_stream = MockAsyncIterator([])

        # モックされたclient.responses.createを設定（awaitableにする）
        mock_create = AsyncMock(return_value=mock_stream)

        with patch.object(provider.client.responses, "create", mock_create):
            # ストリーミング処理を実行
            messages = [{"role": "user", "content": "test"}]
            result_generator = provider._stream_responses(messages, "gpt-4")

            # 結果を収集
            results = []
            async for result in result_generator:
                results.append(result)

            # 最後の結果が完了を示していることを確認
            assert len(results) == 1
            assert results[0][1] == "done"  # type
            assert results[0][2] is True  # is_complete
            assert isinstance(results[0][3], dict)  # usage_data

    @pytest.mark.asyncio
    async def test_stream_with_usage_data(self, provider: OpenAIProvider) -> None:
        """usage情報を持つストリームの処理をテスト"""
        # テキストチャンクをモック
        text_chunk = MagicMock()
        text_chunk.__class__.__name__ = "ResponseTextDeltaEvent"
        text_chunk.delta = "Hello"

        # 完了イベントチャンクをモック（usage情報付き）
        done_chunk = MagicMock()
        done_chunk.__class__.__name__ = "ResponseTextDoneEvent"
        done_chunk.usage = MagicMock()
        done_chunk.usage.input_tokens = 10
        done_chunk.usage.output_tokens = 20
        done_chunk.usage.total_tokens = 30

        mock_stream = MockAsyncIterator([text_chunk, done_chunk])

        # モックされたclient.responses.createを設定（awaitableにする）
        mock_create = AsyncMock(return_value=mock_stream)

        with patch.object(provider.client.responses, "create", mock_create):
            messages = [{"role": "user", "content": "test"}]
            result_generator = provider._stream_responses(messages, "gpt-4")

            results = []
            async for result in result_generator:
                results.append(result)

            # テキストチャンクとdoneイベントが返されることを確認
            assert len(results) == 2

            # 最初のチャンクはテキスト
            assert results[0][0] == "Hello"
            assert results[0][1] == "answer"
            assert results[0][2] is False

            # 2番目のチャンクは完了通知（usage情報付き）
            assert results[1][1] == "done"
            assert results[1][2] is True
            usage_data = results[1][3]
            assert usage_data["prompt_tokens"] == 10
            assert usage_data["completion_tokens"] == 20
            assert usage_data["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_stream_without_usage_data(self, provider: OpenAIProvider) -> None:
        """usage情報がないストリームでもエラーが発生しないことをテスト"""
        # usage情報を持たない完了チャンクをモック
        done_chunk = MagicMock()
        done_chunk.__class__.__name__ = "ResponseTextDoneEvent"
        done_chunk.usage = None

        mock_stream = MockAsyncIterator([done_chunk])

        # モックされたclient.responses.createを設定（awaitableにする）
        mock_create = AsyncMock(return_value=mock_stream)

        with patch.object(provider.client.responses, "create", mock_create):
            messages = [{"role": "user", "content": "test"}]
            result_generator = provider._stream_responses(messages, "gpt-4")

            results = []
            async for result in result_generator:
                results.append(result)

            # デフォルトのusage情報が返されることを確認
            assert len(results) == 1
            usage_data = results[0][3]
            assert usage_data["prompt_tokens"] == 0
            assert usage_data["completion_tokens"] == 0
            assert usage_data["total_tokens"] == 0
