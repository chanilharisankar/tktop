import json

import typer

from tktop.config import SETTINGS_FILE, get_resolved_config_as_dict, load_config
from tktop.tui.app import TktopApp

app = typer.Typer(help="tktop — token monitor for coding agents", invoke_without_command=True)
config_app = typer.Typer(help="Manage tktop configuration")
app.add_typer(config_app, name="config")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Launch the interactive token monitor."""
    if ctx.invoked_subcommand is None:
        config = load_config()
        tktop = TktopApp(config=config)
        tktop.run()


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
