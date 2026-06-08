from tktop.config import Config
from tktop.llm.anthropic_provider import AnthropicProvider
from tktop.llm.factory import create_provider
from tktop.llm.ollama import OllamaProvider
from tktop.llm.openai_provider import OpenAIProvider
from tktop.llm.vertex import VertexProvider


def test_create_ollama_provider():
    cfg = Config(
        llm_provider="ollama", ollama_host="http://localhost:11434", ollama_model="llama3"
    )
    provider = create_provider(cfg)
    assert isinstance(provider, OllamaProvider)


def test_create_anthropic_provider():
    cfg = Config(
        llm_provider="anthropic", anthropic_api_key="sk-test",
        anthropic_model="claude-sonnet-4-6",
    )
    provider = create_provider(cfg)
    assert isinstance(provider, AnthropicProvider)


def test_create_vertex_provider():
    cfg = Config(
        llm_provider="vertex", vertex_project="proj",
        vertex_region="us-central1", vertex_model="claude-sonnet-4-6",
    )
    provider = create_provider(cfg)
    assert isinstance(provider, VertexProvider)


def test_create_openai_provider():
    cfg = Config(
        llm_provider="openai", openai_base_url="http://localhost:8000/v1",
        openai_api_key="sk-test", openai_model="gpt-4o",
    )
    provider = create_provider(cfg)
    assert isinstance(provider, OpenAIProvider)


def test_create_unknown_provider():
    cfg = Config(llm_provider="unknown")
    provider = create_provider(cfg)
    assert provider is None
