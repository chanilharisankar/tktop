from tktop.config import Config
from tktop.llm.anthropic_provider import AnthropicProvider
from tktop.llm.ollama import OllamaProvider
from tktop.llm.openai_provider import OpenAIProvider
from tktop.llm.protocol import LLMProvider
from tktop.llm.vertex import VertexProvider


def create_provider(cfg: Config) -> LLMProvider | None:
    match cfg.llm_provider:
        case "ollama":
            return OllamaProvider(host=cfg.ollama_host, model=cfg.ollama_model)
        case "anthropic":
            return AnthropicProvider(api_key=cfg.anthropic_api_key, model=cfg.anthropic_model)
        case "vertex":
            return VertexProvider(
                project=cfg.vertex_project, region=cfg.vertex_region, model=cfg.vertex_model
            )
        case "openai":
            return OpenAIProvider(
                base_url=cfg.openai_base_url, api_key=cfg.openai_api_key, model=cfg.openai_model
            )
        case _:
            return None
