"""Regression checks for smoke-test failure cleanup."""

import threading
from unittest.mock import Mock

import psutil
import pytest
from scripts.smoke_runtime import listener_identity, stop_child


def test_listener_handshake_has_a_deadline():
    gate = threading.Event()
    process = Mock()
    process.stdout.readline.side_effect = lambda: (gate.wait(), "3000 42")[1]
    try:
        with pytest.raises(AssertionError, match="startup timed out"):
            listener_identity(process, timeout=0.01)
    finally:
        gate.set()


def test_cleanup_tolerates_a_child_exiting_before_kill(monkeypatch):
    child = Mock()
    child.kill.side_effect = psutil.NoSuchProcess(42)
    owner = Mock()
    owner.children.return_value = [child]
    monkeypatch.setattr("scripts.smoke_runtime.psutil.Process", Mock(return_value=owner))
    monkeypatch.setattr("scripts.smoke_runtime.psutil.wait_procs", Mock(return_value=([], [child])))
    process = Mock()
    process.poll.return_value = 0
    stop_child(process)
    child.kill.assert_called_once_with()
