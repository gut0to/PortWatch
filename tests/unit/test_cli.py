from unittest.mock import Mock

from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.cli import app
from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError, ProcessTerminationError
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


def _item(pid: int | None = 42) -> PortInfo:
    return PortInfo(
        3000,
        "tcp",
        "LISTENING",
        pid=pid,
        process_name="python.exe",
        project_name="backend",
    )


def test_root_and_human_list_render_ports(monkeypatch) -> None:
    monkeypatch.setattr(cli.service, "list_ports", lambda port_range=None: [_item()])

    runner = CliRunner()
    listed = runner.invoke(app, ["list"])
    root = runner.invoke(app, [])

    assert listed.exit_code == 0
    assert root.exit_code == 0
    assert "PORTWATCH" in listed.stdout
    assert "1 port listening" in listed.stdout


def test_list_shows_empty_state(monkeypatch) -> None:
    monkeypatch.setattr(cli.service, "list_ports", lambda port_range=None: [])

    result = CliRunner().invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No listening TCP ports found" in result.stdout


def test_inspect_human_json_and_errors(monkeypatch) -> None:
    monkeypatch.setattr(cli.service, "inspect", lambda port: _item())
    runner = CliRunner()

    human = runner.invoke(app, ["inspect", "3000"])
    as_json = runner.invoke(app, ["inspect", "3000", "--json"])
    monkeypatch.setattr(cli.service, "inspect", Mock(side_effect=InvalidPortError("invalid")))
    invalid = runner.invoke(app, ["inspect", "0"])

    assert human.exit_code == 0
    assert "Process" in human.stdout
    assert as_json.exit_code == 0
    assert '"port": 3000' in as_json.stdout
    assert invalid.exit_code == 2

    monkeypatch.setattr(cli.service, "inspect", Mock(side_effect=PortNotFoundError("available")))
    missing = runner.invoke(app, ["inspect", "3000"])
    assert missing.exit_code == 3


def test_next_plain_verbose_and_invalid(monkeypatch) -> None:
    monkeypatch.setattr(cli.service, "next_available", lambda port: 3001)
    runner = CliRunner()

    plain = runner.invoke(app, ["next", "3000"])
    verbose = runner.invoke(app, ["next", "3000", "--verbose"])
    monkeypatch.setattr(
        cli.service, "next_available", Mock(side_effect=InvalidPortError("invalid"))
    )
    invalid = runner.invoke(app, ["next", "0"])

    assert plain.stdout.strip() == "3001"
    assert "Next available port: 3001" in verbose.stdout
    assert invalid.exit_code == 2


def test_kill_success_cancellation_and_still_busy(monkeypatch) -> None:
    runner = CliRunner()
    terminator = Mock()
    monkeypatch.setattr(cli.terminator, "terminate", terminator.terminate)
    inspect = Mock(side_effect=[_item(), PortNotFoundError("available")])
    monkeypatch.setattr(cli.service, "inspect", inspect)

    success = runner.invoke(app, ["kill", "3000", "--yes"])
    inspect.side_effect = [_item(), _item()]
    cancelled = runner.invoke(app, ["kill", "3000"], input="n\n")

    assert success.exit_code == 0
    assert "now available" in success.stdout
    inspect.side_effect = [_item(), _item()]
    assert cancelled.exit_code == 0
    assert "cancelled" in cancelled.stdout

    busy = runner.invoke(app, ["kill", "3000", "--yes"])
    assert busy.exit_code == 0
    assert "still in use" in busy.stderr


def test_free_handles_available_missing_pid_and_termination_error(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(cli.service, "inspect", Mock(side_effect=PortNotFoundError("available")))
    available = runner.invoke(app, ["free", "3000", "--yes"])
    assert available.exit_code == 0
    assert "available" in available.stdout

    monkeypatch.setattr(cli.service, "inspect", Mock(return_value=_item(pid=None)))
    no_pid = runner.invoke(app, ["free", "3000", "--yes"])
    assert no_pid.exit_code == 5

    monkeypatch.setattr(cli.service, "inspect", Mock(return_value=_item()))
    monkeypatch.setattr(
        cli.terminator,
        "terminate",
        Mock(side_effect=ProcessTerminationError("failed")),
    )
    failed = runner.invoke(app, ["free", "3000", "--yes"])
    assert failed.exit_code == 5


def test_kill_rejects_invalid_port(monkeypatch) -> None:
    monkeypatch.setattr(cli.service, "inspect", Mock(side_effect=InvalidPortError("invalid")))

    result = CliRunner().invoke(app, ["kill", "0", "--yes"])

    assert result.exit_code == 2


def test_watch_rejects_invalid_range() -> None:
    result = CliRunner().invoke(app, ["watch", "--range", "9000-3000"])

    assert result.exit_code == 2


def test_watch_stops_cleanly_on_keyboard_interrupt(monkeypatch) -> None:
    class FakeLive:
        def __init__(self, **kwargs) -> None:
            self.updated = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def update(self, renderable) -> None:
            self.updated = True

    monkeypatch.setattr(cli, "Live", FakeLive)
    monkeypatch.setattr(cli.service, "list_ports", lambda port_range=None: [])
    monkeypatch.setattr(cli.time, "sleep", Mock(side_effect=KeyboardInterrupt))

    result = CliRunner().invoke(app, ["watch", "--interval", "0.2"])

    assert result.exit_code == 0
