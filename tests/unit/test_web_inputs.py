import pytest

from portwatch.web.request_data import single_port_parameter


@pytest.mark.parametrize("value", ["١", "1" * 5000, "000001"])
def test_port_parameter_rejects_unbounded_and_unicode_numbers(value):
    with pytest.raises(ValueError):
        single_port_parameter({"start": [value]}, "start", "1")
