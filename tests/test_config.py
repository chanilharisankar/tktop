from tktop.config import load_config


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_USE_VERTEX", raising=False)
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    cfg = load_config()
    assert cfg.claude_dir.endswith(".claude")
    assert cfg.llm_provider == "ollama"
    assert cfg.ollama_host == "http://localhost:11434"
    assert cfg.ollama_model == "llama3"


def test_load_config_env_override(monkeypatch):
    monkeypatch.setenv("TKTOP_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("TKTOP_ANTHROPIC_API_KEY", "sk-test-123")
    monkeypatch.delenv("CLAUDE_CODE_USE_VERTEX", raising=False)
    cfg = load_config()
    assert cfg.llm_provider == "anthropic"
    assert cfg.anthropic_api_key == "sk-test-123"


def test_load_config_vertex(monkeypatch):
    monkeypatch.setenv("TKTOP_LLM_PROVIDER", "vertex")
    monkeypatch.setenv("TKTOP_VERTEX_PROJECT", "my-gcp-project")
    monkeypatch.setenv("TKTOP_VERTEX_REGION", "us-east5")
    monkeypatch.delenv("CLAUDE_CODE_USE_VERTEX", raising=False)
    cfg = load_config()
    assert cfg.llm_provider == "vertex"
    assert cfg.vertex_project == "my-gcp-project"
    assert cfg.vertex_region == "us-east5"


def test_load_config_auto_detect_vertex(monkeypatch):
    monkeypatch.delenv("TKTOP_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_USE_VERTEX", "1")
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "auto-project")
    monkeypatch.setenv("CLOUD_ML_REGION", "global")
    cfg = load_config()
    assert cfg.llm_provider == "vertex"
    assert cfg.vertex_project == "auto-project"
    assert cfg.vertex_region == "us-east5"  # global should not override default
