import json
from typing import Annotated

import typer
from rich.console import Console

from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError
from portwatch.presentation.console import print_inspection
from portwatch.presentation.serializers import port_to_dict, ports_to_json
from portwatch.presentation.tables import ports_table
from portwatch.services.port_service import PortService
from portwatch.utils.ports import parse_port_range

app = typer.Typer(
    name="portwatch",
    help="Find out what's using your ports.",
    no_args_is_help=False,
)
console = Console()
service = PortService()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", help="Show the version.")] = False,
) -> None:
    if version:
        from portwatch import __version__

        typer.echo(f"PortWatch {__version__}")
    elif ctx.invoked_subcommand is None:
        list_ports()


@app.command("list")
def list_ports(
    port_range: Annotated[str | None, typer.Option("--range", help="Filter ports, e.g. 3000-9000.")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    try:
        parsed_range = parse_port_range(port_range) if port_range else None
        ports = service.list_ports((parsed_range.start, parsed_range.end) if parsed_range else None)
    except InvalidPortError as error:
        _fail(str(error), 2)
        return
    if as_json:
        typer.echo(ports_to_json(ports))
    else:
        console.print(ports_table(ports))
        console.print(f"\n{len(ports)} ports listening")


@app.command()
def inspect(
    port: Annotated[int, typer.Argument(help="Port to inspect.")],
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    try:
        item = service.inspect(port)
    except (InvalidPortError, PortNotFoundError) as error:
        if isinstance(error, PortNotFoundError):
            typer.echo(str(error))
            raise typer.Exit(code=3) from error
        _fail(str(error), 2)
        return
    if as_json:
        typer.echo(json.dumps(port_to_dict(item), indent=2))
    else:
        print_inspection(console, item)


@app.command()
def next(
    port: Annotated[int, typer.Argument(help="Starting port.")],
    verbose: Annotated[bool, typer.Option("--verbose", help="Explain the result.")] = False,
) -> None:
    try:
        available = service.next_available(port)
    except InvalidPortError as error:
        _fail(str(error), 2)
        return
    if verbose:
        console.print(f"Port {port} is {'available' if available == port else 'busy'}.")
        console.print(f"Next available port: {available}")
    else:
        typer.echo(str(available))


def _fail(message: str, code: int) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=code)
