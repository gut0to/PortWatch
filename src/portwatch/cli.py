from typing import Annotated

import typer

app = typer.Typer(
    name="portwatch",
    help="Find out what's using your ports.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", help="Show the version.")] = False,
) -> None:
    if version:
        from portwatch import __version__

        typer.echo(f"PortWatch {__version__}")
    elif ctx.invoked_subcommand is None:
        typer.echo("PortWatch\n\nNo commands are available yet.")
