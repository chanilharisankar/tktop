import asyncio
import json
from typing import Annotated

import typer

from tktop import __version__
from tktop.config import SETTINGS_FILE, get_resolved_config_as_dict, load_config
from tktop.diagnostics import build_info, run_doctor
from tktop.tui.app import TktopApp

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

app = typer.Typer(
    help="tktop — token monitor for coding agents",
    invoke_without_command=True,
    context_settings=CONTEXT_SETTINGS,
)
config_app = typer.Typer(help="Manage tktop configuration", context_settings=CONTEXT_SETTINGS)
app.add_typer(config_app, name="config")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tktop {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            "-v",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    """Launch the interactive token monitor."""
    _ = version
    if ctx.invoked_subcommand is None:
        config = load_config()
        tktop = TktopApp(config=config)
        tktop.run()


@app.command("info")
def info() -> None:
    """Print environment and configuration summary."""
    cfg = load_config()
    result = build_info(cfg)
    typer.echo(f"tktop {result.version}")
    typer.echo(f"Python: {result.python}")
    typer.echo(f"Platform: {result.platform}")
    typer.echo(f"Config: {result.config_path}")
    typer.echo(f"Adapter: {result.session_adapter}")
    typer.echo(f"Claude dir: {result.claude_dir}")
    typer.echo(f"Codex dir: {result.codex_dir}")
    typer.echo(f"LLM provider: {result.llm_provider}")


@app.command("doctor")
def doctor() -> None:
    """Diagnose local tktop setup."""
    report = asyncio.run(run_doctor())
    typer.echo("tktop doctor")
    for check in report.checks:
        typer.echo(f"[{check.status}] {check.name}: {check.message}")
    if report.has_errors:
        raise typer.Exit(1)


@config_app.command("show")
def config_show() -> None:
    """Print resolved configuration as JSON."""
    cfg = load_config()
    result = get_resolved_config_as_dict(cfg)
    typer.echo(json.dumps(result, indent=2))


@config_app.command("path")
def config_path() -> None:
    """Print the settings file path."""
    typer.echo(str(SETTINGS_FILE))


if __name__ == "__main__":
    app()
