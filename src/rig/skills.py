"""Run the active checkout's skills engine, as the chezmoi after-hook does."""

import json
import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from rig import chezmoi

errors = Console(stderr=True, highlight=False, soft_wrap=True)

app = typer.Typer(
    help="Sync and update skills from the active Rig checkout.",
    no_args_is_help=True,
)

# Same values the hook template reads, so both resolve the same engine and home.
PATHS = (
    '{{ dict "workingTree" .chezmoi.workingTree "destDir" .chezmoi.destDir | toJson }}'
)


def run(command: str, *flags: str) -> int:
    """Run `skills.py <command>` from chezmoi's working tree against its destination."""
    name = f"skills {command}"
    executable = chezmoi.find(name, "chezmoi")
    uv = chezmoi.find(name, "uv")
    try:
        resolved = subprocess.run(
            [executable, "execute-template", PATHS],
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as error:
        raise chezmoi.DependencyError(
            f"rig {name} could not start chezmoi at {executable}: {error}. "
            "Reinstall it from https://www.chezmoi.io/install/ and try again."
        ) from error
    paths = json.loads(resolved.stdout) if resolved.returncode == 0 else {}
    engine = Path(paths.get("workingTree", ""), "agents", "skills.py")
    if not paths or not engine.is_file():
        found = (
            f"no skills engine at {engine}"
            if paths
            else resolved.stderr.strip() or f"chezmoi exited {resolved.returncode}"
        )
        raise chezmoi.DependencyError(
            f"rig {name} could not find the active Rig checkout ({found}). "
            "Set up Rig with `chezmoi init` and try again."
        )
    # The engine prints emoji; keep them intact when output is redirected on Windows.
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        return subprocess.run(
            [
                uv,
                "run",
                "--script",
                str(engine),
                command,
                "--home",
                paths["destDir"],
                *flags,
            ],
            env=environment,
            check=False,
        ).returncode
    except OSError as error:
        raise chezmoi.DependencyError(
            f"rig {name} could not start uv at {uv}: {error}. Reinstall it from "
            "https://docs.astral.sh/uv/getting-started/installation/ and try again."
        ) from error
    except KeyboardInterrupt:
        return 130


def engine(command: str, *flags: str) -> None:
    try:
        code = run(command, *flags)
    except chezmoi.DependencyError as error:
        errors.print(Text.assemble(("Error: ", "bold red"), str(error)))
        raise typer.Exit(1) from None
    raise typer.Exit(code)


DryRun = Annotated[
    bool, typer.Option("--dry-run", help="Plan changes without downloads or writes.")
]


@app.command()
def sync(
    dry_run: DryRun = False,
    adopt_existing: Annotated[
        bool,
        typer.Option(
            "--adopt-existing",
            help="Adopt matching existing installs, or transfer ownership to an "
            "identical custom skill.",
        ),
    ] = False,
) -> None:
    """Install missing selections and refresh custom skills; keep downloaded versions."""
    flags = ["--dry-run"] * dry_run + ["--adopt-existing"] * adopt_existing
    engine("sync", *flags)


@app.command()
def update(dry_run: DryRun = False) -> None:
    """Refresh selected downloaded skills from upstream."""
    engine("update", *["--dry-run"] * dry_run)
