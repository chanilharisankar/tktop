from typer.testing import CliRunner

from tktop.cli import app
from tktop.config import SETTINGS_FILE

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "token monitor for coding agents" in result.stdout


def test_config_path():
    result = runner.invoke(app, ["config", "path"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(SETTINGS_FILE)
