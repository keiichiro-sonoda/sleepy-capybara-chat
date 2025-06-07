import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.chat.openai import OpenAIProvider


class TestOpenAIProviderStreaming:
    """OpenAIプロバイダーのストリーミング処理のテスト"""

    @pytest.fixture
    def provider(self):
        """OpenAIプロバイダーのインスタンスを作成"""
        return OpenAIProvider()

    @pytest.mark.asyncio
    async def test_empty_stream_handling(self, provider):
        """空のストリームでもエラーが発生しないことをテスト"""
        # 空のストリームをモック
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = iter([])  # 空のイテレータ

        # モックされたclientを設定
        provider.client.responses.create = AsyncMock(return_value=mock_stream)

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
    async def test_stream_with_usage_data(self, provider):
        """usage情報を持つストリームの処理をテスト"""
        # usage情報を持つチャンクをモック
        mock_chunk = MagicMock()
        mock_chunk.usage = MagicMock()
        mock_chunk.usage.input_tokens = 10
        mock_chunk.usage.output_tokens = 20
        mock_chunk.usage.total_tokens = 30

        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = iter([mock_chunk])

        provider.client.responses.create = AsyncMock(return_value=mock_stream)

        messages = [{"role": "user", "content": "test"}]
        result_generator = provider._stream_responses(messages, "gpt-4")

        results = []
        async for result in result_generator:
            results.append(result)

        # usage情報が正しく抽出されることを確認
        assert len(results) == 1
        usage_data = results[0][3]
        assert usage_data["prompt_tokens"] == 10
        assert usage_data["completion_tokens"] == 20
        assert usage_data["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_stream_without_usage_data(self, provider):
        """usage情報がないストリームでもエラーが発生しないことをテスト"""
        # usage情報を持たないチャンクをモック
        mock_chunk = MagicMock()
        mock_chunk.usage = None

        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = iter([mock_chunk])

        provider.client.responses.create = AsyncMock(return_value=mock_stream)

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
