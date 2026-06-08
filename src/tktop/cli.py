import typer

from tktop.config import load_config
from tktop.tui.app import TktopApp

app = typer.Typer(help="tktop — token monitor for coding agents")


@app.command()
def run() -> None:
    """Launch the interactive token monitor."""
    config = load_config()
    tktop = TktopApp(config=config)
    tktop.run()


def main() -> None:
    app()
