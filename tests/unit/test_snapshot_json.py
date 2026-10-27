import pytest

from portwatch.services.snapshots import parse_snapshot_json


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "1e9999"])
def test_snapshot_json_rejects_nonfinite_numbers(value):
    with pytest.raises(ValueError):
        parse_snapshot_json(value)


def test_snapshot_json_bounds_nesting_and_preserves_finite_numbers():
    with pytest.raises(ValueError, match="nested too deeply"):
        parse_snapshot_json("[" * 2000 + "]" * 2000)
    assert parse_snapshot_json("1.25") == 1.25


def test_snapshot_parser_normalizes_runtime_recursion_errors(monkeypatch):
    from unittest.mock import Mock

    monkeypatch.setattr("portwatch.services.snapshots.json.loads", Mock(side_effect=RecursionError))
    with pytest.raises(ValueError, match="nested too deeply"):
        parse_snapshot_json("[]")
