from portwatch.domain.models import PortInfo
from portwatch.services.port_filters import filter_ports


def test_search_matches_metadata_without_matching_missing_values():
    items = [PortInfo(3000, "tcp", "LISTENING", process_name="Python", command="server")]
    assert filter_ports(items, " PYTHON ") == items
    assert filter_ports(items, "server") == items
    assert filter_ports(items, "none") == []
    assert filter_ports(items) == items
