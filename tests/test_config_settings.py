import json
import stat

from tktop.config import (
    _default_settings,
    _ensure_settings_file,
    _mask_key,
)


def test_default_settings_structure():
    settings = _default_settings()
    assert settings["default_provider"] == "ollama"
    assert settings["session_adapter"] == "auto"
    assert "ui" in settings
    assert "agents" in settings
    assert "claude" in settings["agents"]
    assert "codex" in settings["agents"]
    assert "providers" in settings
    assert "ollama" in settings["providers"]
    assert "anthropic" in settings["providers"]
    assert "vertex" in settings["providers"]
    assert "openai" in settings["providers"]


def test_ensure_settings_creates_dir_and_file(tmp_path):
    settings_path = tmp_path / "subdir" / "settings.json"
    result = _ensure_settings_file(settings_path)

    assert result == settings_path
    assert settings_path.exists()
    assert settings_path.parent.exists()

    content = json.loads(settings_path.read_text())
    assert content["default_provider"] == "ollama"


def test_ensure_settings_file_permissions(tmp_path):
    settings_path = tmp_path / "settings.json"
    _ensure_settings_file(settings_path)

    file_stat = settings_path.stat()
    permissions = stat.S_IMODE(file_stat.st_mode)
    assert permissions == 0o600


def test_ensure_settings_does_not_overwrite(tmp_path):
    settings_path = tmp_path / "settings.json"
    custom = {"default_provider": "anthropic", "custom_field": True}
    settings_path.write_text(json.dumps(custom))

    _ensure_settings_file(settings_path)

    content = json.loads(settings_path.read_text())
    assert content["default_provider"] == "anthropic"
    assert content["custom_field"] is True


def test_mask_key_long():
    key = "sk-ant-very-secret-key-12345678"
    masked = _mask_key(key)
    assert masked.endswith("5678")
    assert masked.startswith("*")
    assert len(masked) == len(key)


def test_mask_key_short():
    assert _mask_key("short") == "short"


def test_mask_key_empty():
    assert _mask_key("") == ""
