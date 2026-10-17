import csv
import io
import json
from dataclasses import asdict

from portwatch.domain.models import PortInfo


def port_to_dict(port: PortInfo) -> dict[str, object]:
    data = asdict(port)
    if port.started_at is not None:
        data["started_at"] = port.started_at.isoformat()
    return data


def ports_to_json(ports: list[PortInfo]) -> str:
    return json.dumps([port_to_dict(port) for port in ports], indent=2)


def ports_to_csv(ports: list[PortInfo]) -> str:
    output = io.StringIO(newline="")
    fields = list(PortInfo.__dataclass_fields__)
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(
        {key: _csv_value(value) for key, value in port_to_dict(item).items()} for item in ports
    )
    return output.getvalue().rstrip("\n")


def ports_to_json_lines(ports: list[PortInfo]) -> str:
    """Emit one complete listener object per line, with no array wrapper."""
    return "\n".join(json.dumps(port_to_dict(item), separators=(",", ":")) for item in ports)


def _csv_value(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def changes_to_csv(changes: dict[str, list[dict[str, object]]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=["change", "side", *PortInfo.__dataclass_fields__], lineterminator="\n"
    )
    writer.writeheader()
    for kind, rows in changes.items():
        for row in rows:
            sides = ("before", "after") if kind == "changed" else ("listener",)
            for side in sides:
                data = row[side] if kind == "changed" else row
                assert isinstance(data, dict)
                writer.writerow(
                    {
                        "change": kind,
                        "side": side,
                        **{key: _csv_value(value) for key, value in data.items()},
                    }
                )
    return output.getvalue().rstrip("\n")
