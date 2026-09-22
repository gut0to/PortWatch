from typer.testing import CliRunner

from portwatch.cli import app
from portwatch.domain.models import PortInfo


def test_list_json_uses_stdout_for_data(monkeypatch) -> None:
    monkeypatch.setattr(
        "portwatch.cli.service.list_ports",
        lambda port_range=None: [PortInfo(3000, "tcp", "LISTENING", pid=42)],
    )

    result = CliRunner().invoke(app, ["list", "--json"])

    assert result.exit_code == 0
    assert '"port": 3000' in result.stdout
    assert "PORTWATCH" not in result.stdout


def test_invalid_range_is_a_user_error() -> None:
    result = CliRunner().invoke(app, ["list", "--range", "9000-3000"])

    assert result.exit_code == 2
    assert "Range start" in result.stderr
