import pytest

from portwatch.services.snapshots import load_snapshot


def test_load_utf8_bom_snapshot(tmp_path):
    path = tmp_path / "ports.json"
    path.write_bytes(b"\xef\xbb\xbf[]")
    assert load_snapshot(path) == []


def test_snapshot_json_rejects_duplicate_identity_fields(tmp_path):
    path = tmp_path / "ports.json"
    path.write_text('[{"port":1,"port":2,"protocol":"tcp","status":"LISTENING"}]')
    with pytest.raises(ValueError, match="Duplicate snapshot field"):
        load_snapshot(path)
    path.write_text('[{"port":1,"protocol":"tcp","status":"LISTENING"}]')
    assert load_snapshot(path)[0].port == 1
