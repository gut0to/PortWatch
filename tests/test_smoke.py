from typer.testing import CliRunner

from portwatch import __version__
from portwatch.cli import app


def test_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"PortWatch {__version__}" in result.stdout
