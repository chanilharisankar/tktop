import json

from tktop.config import get_resolved_config_as_dict, load_config


def _clear_tktop_env(monkeypatch):
    for var in (
        "TKTOP_SESSION_ADAPTER", "TKTOP_CLAUDE_DIR", "TKTOP_CODEX_DIR",
        "TKTOP_LLM_PROVIDER", "TKTOP_OLLAMA_HOST", "TKTOP_OLLAMA_MODEL",
        "TKTOP_ANTHROPIC_API_KEY", "TKTOP_ANTHROPIC_MODEL",
        "TKTOP_VERTEX_PROJECT", "TKTOP_VERTEX_REGION", "TKTOP_VERTEX_MODEL",
        "TKTOP_OPENAI_BASE_URL", "TKTOP_OPENAI_API_KEY", "TKTOP_OPENAI_MODEL",
        "TKTOP_SHOW_TOKEN_FLOW",
        "CLAUDE_CODE_USE_VERTEX", "ANTHROPIC_VERTEX_PROJECT_ID", "CLOUD_ML_REGION",
    ):
        monkeypatch.delenv(var, raising=False)


def test_load_config_defaults(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    cfg = load_config(settings_path=settings_path)
    assert cfg.session_adapter == "auto"
    assert cfg.claude_dir.endswith(".claude")
    assert cfg.codex_dir.endswith(".codex")
    assert cfg.llm_provider == "ollama"
    assert cfg.ollama_host == "http://localhost:11434"
    assert cfg.ollama_model == "llama3"


def test_load_config_env_override(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    monkeypatch.setenv("TKTOP_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("TKTOP_ANTHROPIC_API_KEY", "sk-test-123")
    cfg = load_config(settings_path=tmp_path / "settings.json")
    assert cfg.llm_provider == "anthropic"
    assert cfg.anthropic_api_key == "sk-test-123"


def test_load_config_vertex(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    monkeypatch.setenv("TKTOP_LLM_PROVIDER", "vertex")
    monkeypatch.setenv("TKTOP_VERTEX_PROJECT", "my-gcp-project")
    monkeypatch.setenv("TKTOP_VERTEX_REGION", "us-east5")
    cfg = load_config(settings_path=tmp_path / "settings.json")
    assert cfg.llm_provider == "vertex"
    assert cfg.vertex_project == "my-gcp-project"
    assert cfg.vertex_region == "us-east5"


def test_load_config_auto_detect_vertex(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_USE_VERTEX", "1")
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "auto-project")
    monkeypatch.setenv("CLOUD_ML_REGION", "global")
    cfg = load_config(settings_path=tmp_path / "settings.json")
    assert cfg.llm_provider == "vertex"
    assert cfg.vertex_project == "auto-project"
    assert cfg.vertex_region == "us-east5"


# --- settings.json tests ---


def test_load_config_from_settings_file(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings = {
        "default_provider": "anthropic",
        "providers": {
            "anthropic": {"api_key": "sk-from-file", "model": "claude-opus-4-6"},
        },
    }
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    cfg = load_config(settings_path=settings_path)
    assert cfg.llm_provider == "anthropic"
    assert cfg.anthropic_api_key == "sk-from-file"
    assert cfg.anthropic_model == "claude-opus-4-6"


def test_env_var_overrides_settings_file(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings = {"default_provider": "ollama"}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    monkeypatch.setenv("TKTOP_LLM_PROVIDER", "anthropic")
    cfg = load_config(settings_path=settings_path)
    assert cfg.llm_provider == "anthropic"


def test_missing_settings_file_creates_defaults(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    assert not settings_path.exists()

    cfg = load_config(settings_path=settings_path)
    assert settings_path.exists()

    created = json.loads(settings_path.read_text())
    assert created["default_provider"] == "ollama"
    assert "providers" in created
    assert cfg.llm_provider == "ollama"


def test_corrupt_settings_file_falls_back(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("not valid json {{{")

    cfg = load_config(settings_path=settings_path)
    assert cfg.llm_provider == "ollama"


def test_partial_settings_file(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings = {"default_provider": "openai"}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    cfg = load_config(settings_path=settings_path)
    assert cfg.llm_provider == "openai"
    assert cfg.ollama_host == "http://localhost:11434"
    assert cfg.openai_model == "gpt-4o"


def test_settings_preserves_vertex_autodetect(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings = {"default_provider": "ollama"}
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(settings))

    monkeypatch.setenv("CLAUDE_CODE_USE_VERTEX", "1")
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "auto-proj")

    cfg = load_config(settings_path=settings_path)
    assert cfg.llm_provider == "vertex"


def test_get_resolved_config_masks_keys():
    from tktop.config import Config

    cfg = Config(
        session_adapter="codex",
        anthropic_api_key="sk-ant-very-secret-key-12345678",
        openai_api_key="sk-openai-secret",
    )
    result = get_resolved_config_as_dict(cfg)
    assert result["session_adapter"] == "codex"
    assert result["providers"]["anthropic"]["api_key"].endswith("5678")
    assert result["providers"]["anthropic"]["api_key"].startswith("*")
    assert result["providers"]["openai"]["api_key"].endswith("cret")
