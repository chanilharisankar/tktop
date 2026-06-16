from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tktop import __version__
from tktop.adapter.factory import create_adapter
from tktop.config import SETTINGS_FILE, Config, load_config

DiagnosticStatus = Literal["ok", "warn", "error"]


@dataclass(frozen=True)
class Info:
    version: str
    python: str
    platform: str
    config_path: str
    session_adapter: str
    claude_dir: str
    codex_dir: str
    llm_provider: str


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: DiagnosticStatus
    message: str


@dataclass(frozen=True)
class DoctorReport:
    checks: list[DiagnosticCheck]

    @property
    def has_errors(self) -> bool:
        return any(check.status == "error" for check in self.checks)


def build_info(cfg: Config, settings_path: Path | None = None) -> Info:
    return Info(
        version=__version__,
        python=sys.version.split()[0],
        platform=platform.platform(),
        config_path=str(settings_path or SETTINGS_FILE),
        session_adapter=cfg.session_adapter,
        claude_dir=cfg.claude_dir,
        codex_dir=cfg.codex_dir,
        llm_provider=cfg.llm_provider,
    )


async def run_doctor(settings_path: Path | None = None) -> DoctorReport:
    checks: list[DiagnosticCheck] = []

    try:
        cfg = load_config(settings_path=settings_path)
    except Exception as exc:  # noqa: BLE001 - diagnostics should report any config failure.
        return DoctorReport(
            [
                DiagnosticCheck(
                    "Config",
                    "error",
                    f"could not load configuration: {exc}",
                )
            ]
        )

    resolved_settings_path = settings_path or SETTINGS_FILE
    if resolved_settings_path.exists():
        _add_check(checks, "Config", "ok", f"settings file: {resolved_settings_path}")
    else:
        _add_check(
            checks,
            "Config",
            "error",
            f"settings file was not created: {resolved_settings_path}",
        )

    _check_agent_dir(checks, "Claude data", Path(cfg.claude_dir))
    _check_agent_dir(checks, "Codex data", Path(cfg.codex_dir))
    await _check_adapter(checks, cfg)
    _check_provider(checks, cfg)

    return DoctorReport(checks)


def _add_check(
    checks: list[DiagnosticCheck],
    name: str,
    status: DiagnosticStatus,
    message: str,
) -> None:
    checks.append(DiagnosticCheck(name, status, message))


def _check_agent_dir(checks: list[DiagnosticCheck], name: str, path: Path) -> None:
    if path.exists():
        status = "ok" if path.is_dir() else "error"
        message = f"{path}" if path.is_dir() else f"not a directory: {path}"
    else:
        status = "warn"
        message = f"not found: {path}"
    _add_check(checks, name, status, message)


async def _check_adapter(checks: list[DiagnosticCheck], cfg: Config) -> None:
    choice = (cfg.session_adapter or "auto").strip().lower()
    try:
        adapter = create_adapter(cfg)
    except ValueError as exc:
        _add_check(checks, "Adapter", "error", str(exc))
        return

    if choice == "claude" and not Path(cfg.claude_dir).is_dir():
        _add_check(
            checks,
            "Adapter",
            "error",
            f"claude adapter data dir missing: {cfg.claude_dir}",
        )
        return
    if choice == "codex" and not Path(cfg.codex_dir).is_dir():
        _add_check(
            checks,
            "Adapter",
            "error",
            f"codex adapter data dir missing: {cfg.codex_dir}",
        )
        return

    try:
        sessions = await adapter.discover()
    except Exception as exc:  # noqa: BLE001 - diagnostics should report adapter failures.
        _add_check(checks, "Adapter", "error", f"discovery failed: {exc}")
        return

    _add_check(
        checks,
        "Adapter",
        "ok",
        f"{adapter.name} selected; {len(sessions)} session(s) discovered",
    )


def _check_provider(checks: list[DiagnosticCheck], cfg: Config) -> None:
    provider = (cfg.llm_provider or "").strip().lower()

    if provider == "ollama":
        if cfg.ollama_host:
            _add_check(checks, "LLM provider", "ok", f"ollama host: {cfg.ollama_host}")
        else:
            _add_check(checks, "LLM provider", "warn", "ollama host is not configured")
        return

    if provider == "anthropic":
        status = "ok" if cfg.anthropic_api_key else "warn"
        message = (
            "anthropic API key configured"
            if cfg.anthropic_api_key
            else "anthropic API key missing"
        )
        _add_check(checks, "LLM provider", status, message)
        return

    if provider == "vertex":
        if cfg.vertex_project and cfg.vertex_region:
            _add_check(
                checks,
                "LLM provider",
                "ok",
                f"vertex project/region: {cfg.vertex_project}/{cfg.vertex_region}",
            )
        else:
            _add_check(checks, "LLM provider", "warn", "vertex project or region missing")
        return

    if provider == "openai":
        if cfg.openai_base_url and cfg.openai_api_key:
            _add_check(
                checks,
                "LLM provider",
                "ok",
                f"openai base URL: {cfg.openai_base_url}",
            )
        elif cfg.openai_base_url:
            _add_check(checks, "LLM provider", "warn", "openai API key missing")
        else:
            _add_check(checks, "LLM provider", "warn", "openai base URL missing")
        return

    _add_check(checks, "LLM provider", "error", f"unknown provider: {cfg.llm_provider}")
