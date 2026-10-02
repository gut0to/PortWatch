"""Translate system failures at the command boundary."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import typer

from portwatch.domain.exceptions import PermissionDeniedError

P = ParamSpec("P")
T = TypeVar("T")


def report_system_errors(command: Callable[P, T]) -> Callable[P, T]:
    """Keep operational failures on stderr with the documented exit codes."""

    @wraps(command)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return command(*args, **kwargs)
        except PermissionDeniedError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(4) from error
        except OSError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(1) from error

    return wrapped
