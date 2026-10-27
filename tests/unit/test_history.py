import json
from datetime import UTC, datetime

import pytest

from portwatch.services.history import decode_history


def record(second, port=3000):
    return json.dumps(
        {
            "scanned_at": f"2026-10-27T12:00:{second:02d}+00:00",
            "ports": []
            if port is None
            else [{"port": port, "protocol": "tcp", "status": "LISTENING", "pid": 42}],
        }
    )


def test_history_decoder_preserves_every_frame():
    frames = decode_history(record(0) + "\n\n" + record(1, None))
    assert len(frames) == 2 and frames[0].ports[0].port == 3000
    assert frames[0].scanned_at == datetime(2026, 10, 27, 12, tzinfo=UTC)
    assert frames[1].ports == ()
    assert decode_history("") == []


@pytest.mark.parametrize(
    "value",
    [
        "{}",
        "[]",
        '{"scanned_at":"2026-01-01","ports":[]}',
        record(0).replace('"pid": 42', '"pid": -1'),
    ],
)
def test_history_reports_the_invalid_record_number(value):
    with pytest.raises(ValueError, match="History line 2"):
        decode_history(record(0) + "\n" + value)
