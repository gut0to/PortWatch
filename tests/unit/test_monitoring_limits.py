from unittest.mock import Mock

import pytest

from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError
from portwatch.domain.models import PortInfo
from portwatch.services.port_service import PortService


def test_available_port_blocks_do_not_bridge_busy_or_reserved_ports():
    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(3001, "tcp", "LISTENING")]
    service = PortService(scanner=scanner)
    assert service.available_port_block(3000, 2, 3005, excluded=frozenset({3003})) == [3004, 3005]
    with pytest.raises(PortNotFoundError):
        service.available_port_block(3000, 3, 3003)
    for count in (0, True):
        with pytest.raises(InvalidPortError):
            service.available_port_block(3000, count)


def test_cli_requests_contiguous_ports_and_keeps_batch_json(monkeypatch):
    import json

    from typer.testing import CliRunner

    import portwatch.cli as cli

    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(3001, "tcp", "LISTENING")]
    monkeypatch.setattr(cli, "service", PortService(scanner=scanner))
    result = CliRunner().invoke(cli.app, ["next", "3000", "--count", "2", "--contiguous", "--json"])
    assert result.exit_code == 0 and json.loads(result.stdout)["ports"] == [3002, 3003]


def test_watch_duration_bounds_sleep_and_scan_attempts():
    from portwatch.services.monitoring import watch_snapshots

    now = [0.0]

    def sleep(value):
        now[0] += value

    scan = Mock(return_value=[])
    assert (
        len(list(watch_snapshots(scan, 0.2, 0, duration=0.5, clock=lambda: now[0], sleep=sleep)))
        == 3
    )
    assert now[0] == 0.5


@pytest.mark.parametrize(
    "options",
    [
        {"interval": float("nan")},
        {"interval": 0.1},
        {"count": -1},
        {"count": True},
        {"duration": 0},
        {"duration": float("inf")},
    ],
)
def test_monitor_rejects_unbounded_or_invalid_timing(options):
    from portwatch.services.monitoring import watch_snapshots

    values = {"interval": 0.2, "count": 1, **options}
    with pytest.raises(ValueError):
        list(watch_snapshots(lambda: [], **values))


def test_cli_watch_duration_is_forwarded_and_validated(monkeypatch):
    from typer.testing import CliRunner

    import portwatch.cli as cli

    watch = Mock(return_value=iter([[]]))
    monkeypatch.setattr(cli, "watch_snapshots", watch)
    result = CliRunner().invoke(cli.app, ["watch", "--duration", "1", "--json"])
    assert result.exit_code == 0 and watch.call_args.kwargs["duration"] == 1.0
    assert CliRunner().invoke(cli.app, ["watch", "--duration", "nan"]).exit_code == 2


def test_watch_event_stream_reports_transitions_without_exposing_redacted_data(monkeypatch):
    import json

    from typer.testing import CliRunner

    import portwatch.cli as cli

    item = PortInfo(3000, "tcp", "LISTENING", command="secret")
    monkeypatch.setattr(cli, "watch_snapshots", lambda *args, **kwargs: iter([[item], []]))
    result = CliRunner().invoke(cli.app, ["watch", "--events", "--redact", "--count", "2"])
    assert result.exit_code == 0
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[0]["changes"]["added"][0]["command"] is None
    assert rows[1]["changes"]["removed"][0]["port"] == 3000
    assert "secret" not in result.stdout


def test_watch_heartbeat_emits_periodic_unchanged_snapshots():
    from portwatch.services.monitoring import watch_snapshots

    assert (
        len(list(watch_snapshots(lambda: [], 0.2, 5, changes_only=True, heartbeat=2, sleep=Mock())))
        == 3
    )
    with pytest.raises(ValueError):
        list(watch_snapshots(lambda: [], 0.2, 1, heartbeat=-1))


def test_cli_watch_heartbeat_reaches_the_monitor(monkeypatch):
    from typer.testing import CliRunner

    import portwatch.cli as cli

    watch = Mock(return_value=iter([[]]))
    monkeypatch.setattr(cli, "watch_snapshots", watch)
    result = CliRunner().invoke(
        cli.app, ["watch", "--heartbeat", "3", "--changes-only", "--count", "1", "--json"]
    )
    assert result.exit_code == 0 and watch.call_args.kwargs["heartbeat"] == 3
