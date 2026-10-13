import pytest

from portwatch.web.request_data import single_port_parameter


@pytest.mark.parametrize("value", ["١", "1" * 5000, "000001"])
def test_port_parameter_rejects_unbounded_and_unicode_numbers(value):
    with pytest.raises(ValueError):
        single_port_parameter({"start": [value]}, "start", "1")


def test_action_json_rejects_duplicate_pid():
    import json

    from portwatch.web.request_data import unique_json_object

    with pytest.raises(ValueError, match="Duplicate JSON field"):
        json.loads('{"pid":42,"pid":99}', object_pairs_hook=unique_json_object)
    assert unique_json_object([("pid", 42)]) == {"pid": 42}
