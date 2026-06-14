import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

SETTINGS_DIR = Path.home() / ".tktop"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class Config:
    session_adapter: str = "auto"
    claude_dir: str = ""
    codex_dir: str = ""
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


def _default_settings() -> dict:
    return {
        "default_provider": "ollama",
        "session_adapter": "auto",
        "ui": {
            "show_token_flow": False,  # nosec B105 — not a password
        },
        "agents": {
            "claude": {
                "dir": str(Path.home() / ".claude"),
            },
            "codex": {
                "dir": str(Path.home() / ".codex"),
            },
        },
        "providers": {
            "ollama": {
                "host": "http://localhost:11434",
                "model": "llama3",
            },
            "anthropic": {
                "api_key": "",
                "model": "claude-sonnet-4-6",
            },
            "vertex": {
                "project": "",
                "region": "us-east5",
                "model": "claude-sonnet-4-6",
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "model": "gpt-4o",
            },
        },
    }


def _ensure_settings_file(path: Path | None = None) -> Path:
    path = path or SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(_default_settings(), indent=2) + "\n")
        path.chmod(0o600)
    return path


def _load_settings_file(path: Path | None = None) -> dict:
    path = _ensure_settings_file(path)
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _default_settings()


def _apply_settings(cfg: Config, settings: dict) -> None:
    if "default_provider" in settings:
        cfg.llm_provider = settings["default_provider"]
    if "session_adapter" in settings:
        cfg.session_adapter = settings["session_adapter"]
    if "claude_dir" in settings:
        cfg.claude_dir = settings["claude_dir"]
    if "codex_dir" in settings:
        cfg.codex_dir = settings["codex_dir"]

    ui = settings.get("ui", {})
    if "show_token_flow" in ui:
        cfg.show_token_flow = ui["show_token_flow"]

    agents = settings.get("agents", {})
    claude = agents.get("claude", {})
    if "dir" in claude:
        cfg.claude_dir = claude["dir"]
    codex = agents.get("codex", {})
    if "dir" in codex:
        cfg.codex_dir = codex["dir"]

    providers = settings.get("providers", {})

    ollama = providers.get("ollama", {})
    if "host" in ollama:
        cfg.ollama_host = ollama["host"]
    if "model" in ollama:
        cfg.ollama_model = ollama["model"]

    anthropic = providers.get("anthropic", {})
    if "api_key" in anthropic and anthropic["api_key"]:
        cfg.anthropic_api_key = anthropic["api_key"]
    if "model" in anthropic:
        cfg.anthropic_model = anthropic["model"]

    vertex = providers.get("vertex", {})
    if "project" in vertex and vertex["project"]:
        cfg.vertex_project = vertex["project"]
    if "region" in vertex:
        cfg.vertex_region = vertex["region"]
    if "model" in vertex:
        cfg.vertex_model = vertex["model"]

    openai = providers.get("openai", {})
    if "base_url" in openai:
        cfg.openai_base_url = openai["base_url"]
    if "api_key" in openai and openai["api_key"]:
        cfg.openai_api_key = openai["api_key"]
    if "model" in openai:
        cfg.openai_model = openai["model"]


def load_config(settings_path: Path | None = None) -> Config:
    load_dotenv()

    home = Path.home()
    cfg = Config(
        claude_dir=str(home / ".claude"),
        codex_dir=str(home / ".codex"),
    )

    # Layer 1: settings.json
    settings = _load_settings_file(settings_path)
    _apply_settings(cfg, settings)

    # Layer 2: env vars override settings.json
    env_map = {
        "TKTOP_SESSION_ADAPTER": "session_adapter",
        "TKTOP_CLAUDE_DIR": "claude_dir",
        "TKTOP_CODEX_DIR": "codex_dir",
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

    # Layer 3: Auto-detect Vertex AI from Claude Code env vars
    if not cfg.vertex_project and os.getenv("ANTHROPIC_VERTEX_PROJECT_ID"):
        cfg.vertex_project = os.getenv("ANTHROPIC_VERTEX_PROJECT_ID", "")
    if os.getenv("CLOUD_ML_REGION", "") not in ("", "global"):
        cfg.vertex_region = os.getenv("CLOUD_ML_REGION", cfg.vertex_region)
    if os.getenv("CLAUDE_CODE_USE_VERTEX") == "1" and cfg.llm_provider == "ollama":
        cfg.llm_provider = "vertex"

    cfg.claude_dir = str(Path(cfg.claude_dir).expanduser())
    cfg.codex_dir = str(Path(cfg.codex_dir).expanduser())

    return cfg


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return key
    return "*" * (len(key) - 4) + key[-4:]


def get_resolved_config_as_dict(cfg: Config) -> dict:
    return {
        "default_provider": cfg.llm_provider,
        "session_adapter": cfg.session_adapter,
        "claude_dir": cfg.claude_dir,
        "codex_dir": cfg.codex_dir,
        "ui": {
            "show_token_flow": cfg.show_token_flow,
        },
        "agents": {
            "claude": {
                "dir": cfg.claude_dir,
            },
            "codex": {
                "dir": cfg.codex_dir,
            },
        },
        "providers": {
            "ollama": {
                "host": cfg.ollama_host,
                "model": cfg.ollama_model,
            },
            "anthropic": {
                "api_key": _mask_key(cfg.anthropic_api_key),
                "model": cfg.anthropic_model,
            },
            "vertex": {
                "project": cfg.vertex_project,
                "region": cfg.vertex_region,
                "model": cfg.vertex_model,
            },
            "openai": {
                "base_url": cfg.openai_base_url,
                "api_key": _mask_key(cfg.openai_api_key),
                "model": cfg.openai_model,
            },
        },
    }
