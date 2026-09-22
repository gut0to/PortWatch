from unittest.mock import Mock

import psutil

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
