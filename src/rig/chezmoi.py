"""Delegate dotfile operations to the active chezmoi setup."""

import shutil
import subprocess
from typing import Literal

type Tool = Literal["chezmoi", "uv"]

PURPOSE: dict[Tool, tuple[str, str]] = {
    "chezmoi": ("to manage dotfiles", "https://www.chezmoi.io/install/"),
    "uv": (
        "to run the skill sync hook",
        "https://docs.astral.sh/uv/getting-started/installation/",
    ),
}


class DependencyError(Exception):
    """A tool rig delegates to is missing or cannot be started."""


def find(command: str, tool: Tool) -> str:
    executable = shutil.which(tool)
    if executable is None:
        purpose, install = PURPOSE[tool]
        raise DependencyError(
            f"rig {command} needs {tool} {purpose}, but it is not on PATH. "
            f"Install it from {install} and try again."
        )
    return executable


def run(command: str, *args: str, needs: tuple[Tool, ...] = ()) -> int:
    """Run `chezmoi <command>` with inherited stdio.

    Chezmoi resolves its own configured source and destination, so this works from
    any directory, and its output, prompts, and exit code reach the caller unchanged.
    """
    executable = find(command, "chezmoi")
    for tool in needs:
        find(command, tool)
    try:
        code = subprocess.run([executable, command, *args], check=False).returncode
    except OSError as error:
        raise DependencyError(
            f"rig {command} could not start chezmoi at {executable}: {error}. "
            "Reinstall it from https://www.chezmoi.io/install/ and try again."
        ) from error
    except KeyboardInterrupt:
        return 130  # Shell convention for an interrupted command.
    # POSIX reports a signal death as -signum; shells report 128 + signum.
    return 128 - code if code < 0 else code
