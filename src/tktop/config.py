import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    claude_dir: str = ""
    llm_provider: str = "ollama"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    vertex_project: str = ""
    vertex_region: str = "us-east5"
    vertex_model: str = "claude-sonnet-4-6"

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    show_token_flow: bool = False


def load_config() -> Config:
    load_dotenv()

    home = Path.home()
    cfg = Config(claude_dir=str(home / ".claude"))

    env_map = {
        "TKTOP_CLAUDE_DIR": "claude_dir",
        "TKTOP_LLM_PROVIDER": "llm_provider",
        "TKTOP_OLLAMA_HOST": "ollama_host",
        "TKTOP_OLLAMA_MODEL": "ollama_model",
        "TKTOP_ANTHROPIC_API_KEY": "anthropic_api_key",
        "TKTOP_ANTHROPIC_MODEL": "anthropic_model",
        "TKTOP_VERTEX_PROJECT": "vertex_project",
        "TKTOP_VERTEX_REGION": "vertex_region",
        "TKTOP_VERTEX_MODEL": "vertex_model",
        "TKTOP_OPENAI_BASE_URL": "openai_base_url",
        "TKTOP_OPENAI_API_KEY": "openai_api_key",
        "TKTOP_OPENAI_MODEL": "openai_model",
    }

    for env_var, attr in env_map.items():
        value = os.getenv(env_var)
        if value:
            setattr(cfg, attr, value)

    if os.getenv("TKTOP_SHOW_TOKEN_FLOW", "").lower() in ("1", "true", "yes"):
        cfg.show_token_flow = True

    # Auto-detect Vertex AI from Claude Code env vars
    if not cfg.vertex_project and os.getenv("ANTHROPIC_VERTEX_PROJECT_ID"):
        cfg.vertex_project = os.getenv("ANTHROPIC_VERTEX_PROJECT_ID", "")
    if os.getenv("CLOUD_ML_REGION", "") not in ("", "global"):
        cfg.vertex_region = os.getenv("CLOUD_ML_REGION", cfg.vertex_region)
    if os.getenv("CLAUDE_CODE_USE_VERTEX") == "1" and cfg.llm_provider == "ollama":
        cfg.llm_provider = "vertex"

    return cfg
