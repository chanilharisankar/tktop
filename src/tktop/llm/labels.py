from tktop.config import Config


def model_name(cfg: Config) -> str:
    match cfg.llm_provider:
        case "ollama":
            return cfg.ollama_model
        case "anthropic":
            return cfg.anthropic_model
        case "vertex":
            return cfg.vertex_model
        case "openai":
            return cfg.openai_model
        case _:
            return "unknown"


def provider_label(cfg: Config) -> str:
    return f"{cfg.llm_provider}/{model_name(cfg)}"
