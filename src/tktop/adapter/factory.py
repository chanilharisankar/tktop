from tktop.config import Config

from .claude import ClaudeCodeAdapter
from .codex import CodexAdapter
from .protocol import SessionAdapter


def create_adapter(cfg: Config) -> SessionAdapter:
    choice = (cfg.session_adapter or "auto").strip().lower()

    if choice == "claude":
        return ClaudeCodeAdapter(cfg.claude_dir)
    if choice == "codex":
        return CodexAdapter(cfg.codex_dir)
    if choice != "auto":
        raise ValueError(f"unknown session adapter: {cfg.session_adapter}")

    if ClaudeCodeAdapter.is_available(cfg.claude_dir):
        return ClaudeCodeAdapter(cfg.claude_dir)
    if CodexAdapter.is_available(cfg.codex_dir):
        return CodexAdapter(cfg.codex_dir)

    return ClaudeCodeAdapter(cfg.claude_dir)
