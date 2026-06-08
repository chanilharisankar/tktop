from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tktop.llm.ollama import OllamaProvider


async def test_ollama_analyze():
    provider = OllamaProvider(host="http://localhost:11434", model="llama3")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Reduce cache creation by using smaller context windows."
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await provider.analyze("test prompt")

        assert result == "Reduce cache creation by using smaller context windows."
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        body = call_args[1]["json"]
        assert body["model"] == "llama3"
        assert body["prompt"] == "test prompt"
        assert body["stream"] is False


async def test_ollama_analyze_error():
    provider = OllamaProvider(host="http://localhost:11434", model="llama3")

    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("500 Server Error")

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with pytest.raises(Exception):
            await provider.analyze("test prompt")


async def test_ollama_health_check():
    provider = OllamaProvider(host="http://localhost:11434", model="llama3")

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await provider.health_check()
        assert result is True
