from unittest.mock import Mock

from portwatch.system.termination import ProcessTerminator


def test_terminator_requests_graceful_exit(monkeypatch) -> None:
    process = Mock()
    monkeypatch.setattr("portwatch.system.termination.psutil.Process", Mock(return_value=process))

    ProcessTerminator().terminate(42)

    process.terminate.assert_called_once_with()
    process.wait.assert_called_once()
