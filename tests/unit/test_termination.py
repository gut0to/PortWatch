from unittest.mock import Mock

import psutil
import pytest

from portwatch.domain.exceptions import PermissionDeniedError, ProcessTerminationError
from portwatch.system.termination import ProcessTerminator


def test_terminator_requests_graceful_exit(monkeypatch) -> None:
    process = Mock()
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))

    ProcessTerminator().terminate(42)

    process.terminate.assert_called_once_with()
    process.wait.assert_called_once()


def test_terminator_treats_disappeared_process_as_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "portwatch.system.termination.psutil.Process",
        Mock(side_effect=psutil.NoSuchProcess(42)),
    )

    ProcessTerminator().terminate(42)


def test_terminator_can_force_after_timeout(monkeypatch) -> None:
    process = Mock()
    process.wait.side_effect = [psutil.TimeoutExpired(0.5), None]
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))

    ProcessTerminator().terminate(42, force=True)

    process.terminate.assert_called_once_with()
    process.kill.assert_called_once_with()


def test_terminator_reports_graceful_timeout_without_force(monkeypatch) -> None:
    process = Mock()
    process.wait.side_effect = psutil.TimeoutExpired(0.5)
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))

    with pytest.raises(ProcessTerminationError):
        ProcessTerminator().terminate(42)


def test_terminator_reports_self_termination(monkeypatch) -> None:
    import os

    process_factory = Mock()
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", process_factory)
    with pytest.raises(ProcessTerminationError, match="itself"):
        ProcessTerminator().terminate(os.getpid())
    process_factory.assert_not_called()


def test_terminator_reports_access_denied(monkeypatch) -> None:
    process = Mock()
    process.terminate.side_effect = psutil.AccessDenied(42)
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))

    with pytest.raises(PermissionDeniedError):
        ProcessTerminator().terminate(42)


def test_terminator_reports_timeout_after_forced_kill(monkeypatch) -> None:
    process = Mock()
    process.wait.side_effect = psutil.TimeoutExpired(0.5)
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))
    with pytest.raises(ProcessTerminationError, match="did not exit"):
        ProcessTerminator().terminate(42, force=True)


def test_terminator_reports_operating_system_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "portwatch.system.termination.psutil.Process", Mock(side_effect=OSError("unavailable"))
    )
    with pytest.raises(ProcessTerminationError, match="unavailable"):
        ProcessTerminator().terminate(42)


@pytest.mark.parametrize("force", [False, True])
def test_terminator_accepts_an_exited_non_child_waiting_for_its_parent(monkeypatch, force):
    process = Mock()
    process.wait.side_effect = psutil.TimeoutExpired(0.5)
    process.status.return_value = psutil.STATUS_ZOMBIE
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))
    ProcessTerminator().terminate(42, force=force)
    process.kill.assert_not_called()


def test_terminator_accepts_zombie_after_forced_kill(monkeypatch):
    process = Mock()
    process.wait.side_effect = psutil.TimeoutExpired(0.5)
    process.status.side_effect = [psutil.STATUS_RUNNING, psutil.STATUS_ZOMBIE]
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))
    ProcessTerminator().terminate(42, force=True)
    process.kill.assert_called_once_with()
