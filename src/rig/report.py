"""Report command failures on stderr in one consistent shape."""

from typing import NoReturn

import typer
from rich.console import Console
from rich.text import Text

# Rich drops styling when stderr is redirected, keeping scripted output plain.
errors = Console(stderr=True, highlight=False, soft_wrap=True)


def fail(error: Exception) -> NoReturn:
    """Print `error` as a one-line recovery message and exit with status 1."""
    errors.print(Text.assemble(("Error: ", "bold red"), str(error)))
    raise typer.Exit(1) from None
