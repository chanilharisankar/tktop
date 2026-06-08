import typer

app = typer.Typer(help="tktop — token monitor for coding agents")


@app.command()
def run() -> None:
    """Launch the interactive token monitor."""
    typer.echo("tktop — token monitor for coding agents")


def main() -> None:
    app()
