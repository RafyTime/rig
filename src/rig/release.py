"""Resolve stable rig releases and upgrade the installed CLI to them.

The CLI is a uv tool installed from a release tag. It has its own lifecycle, so
upgrading it never touches the active checkout or the installed skills.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import NamedTuple

# Test hooks that point rig at a fixture release service and Git repository; not
# documented user settings. RIG_RELEASES_URL serves a GitHub-shaped latest-release
# response, and RIG_RELEASE_SOURCE is the Git URL its tags are installed from.
RELEASES_URL = os.environ.get(
    "RIG_RELEASES_URL", "https://api.github.com/repos/RafyTime/rig/releases/latest"
)
SOURCE = os.environ.get("RIG_RELEASE_SOURCE", "https://github.com/RafyTime/rig")
UV_INSTALL = "https://docs.astral.sh/uv/getting-started/installation/"


class Version(NamedTuple):
    """A stable release version; tuples compare in release order."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class ReleaseError(Exception):
    """The latest release cannot be resolved or installed."""


@dataclass(frozen=True)
class Release:
    tag: str
    version: Version


def installed() -> Version:
    """The version of the running rig CLI."""
    # Search only directories: on Windows, sys.path includes the running rig.exe
    # launcher, and importlib.metadata keeps a zip it searched open, which would
    # stop uv from replacing that launcher.
    directories = [path for path in sys.path if os.path.isdir(path)]
    rig = next(iter(metadata.distributions(name="rig", path=directories)))
    return parse(rig.version)


def parse(text: str) -> Version:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", text)
    if match is None:
        raise ValueError(f"{text!r} is not a stable rig version")
    return Version(*map(int, match.groups()))


def latest_stable(timeout: float = 10) -> Release:
    """Ask the release service for the latest stable release.

    Raises ReleaseError if the service is unreachable or its answer is not a
    stable tag, so callers decide whether that stops them.
    """
    request = urllib.request.Request(
        RELEASES_URL, headers={"Accept": "application/vnd.github+json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            tag = json.load(response)["tag_name"]
        return Release(tag, parse(tag))
    except OSError as error:
        raise ReleaseError(
            f"rig could not reach the release service at {RELEASES_URL} ({error}). "
            "Check your connection and try again."
        ) from error
    except (ValueError, KeyError, TypeError) as error:
        raise ReleaseError(
            f"rig could not read the latest release from {RELEASES_URL} ({error!r}). "
            f"Try again later, or install a tag from {SOURCE}/releases with "
            f"`uv tool install git+{SOURCE}@<tag>`."
        ) from error


def install_command(release: Release, uv: str = "uv") -> list[str]:
    return [uv, "tool", "install", "--force", f"git+{SOURCE}@{release.tag}"]


def upgrade(release: Release) -> None:
    """Have uv replace the installed CLI with `release`, streaming uv's output."""
    uv = shutil.which("uv")
    if uv is None:
        raise ReleaseError(
            f"rig needs uv to install rig {release.version}, but it is not on PATH. "
            f"Install it from {UV_INSTALL} and try again."
        )
    command = install_command(release, uv)
    try:
        with launchers_released(release):
            code = subprocess.run(command, check=False).returncode
    except OSError as error:
        raise ReleaseError(
            f"rig could not start uv at {uv}: {error}. "
            f"Reinstall it from {UV_INSTALL} and try again."
        ) from error
    if code != 0:
        raise ReleaseError(
            f"uv could not install rig {release.version} (exit status {code}). "
            f"Fix the problem uv reported, then run `rig self update` again, or "
            f"run `{' '.join(install_command(release))}` yourself."
        )


@contextmanager
def launchers_released(release: Release) -> Generator[None]:
    """Let uv replace the executables this rig process runs from on Windows.

    Windows refuses to delete or overwrite a running executable but lets it move.
    So the tool environment's python.exe moves aside, with a copy left in its place
    for uv to find the environment by, and the rig.exe launcher moves aside too. The
    launcher comes back afterwards unless uv installed a new one.
    """
    launcher = Path(sys.argv[0])
    if not launcher.suffix:
        launcher = launcher.with_suffix(".exe")  # Shells may drop it from argv.
    if sys.platform != "win32" or launcher.suffix.lower() != ".exe":
        yield  # Not started from a launcher, e.g. `python -m rig`.
        return
    aside = Path(tempfile.mkdtemp(prefix="rig-self-update-"))
    moved: list[Path] = []

    def restore() -> None:
        """Put back whatever uv did not replace."""
        for original in moved:
            if not original.exists():
                (aside / original.name).replace(original)

    try:
        if sys.prefix != sys.base_prefix:  # Only a venv's python.exe, never a base.
            python = Path(sys.executable)
            python.replace(aside / python.name)
            moved.append(python)
            shutil.copy2(aside / python.name, python)
        launcher.replace(aside / launcher.name)
        moved.append(launcher)
    except OSError as error:
        restore()
        raise ReleaseError(
            f"rig could not move its running files aside for uv to replace "
            f"({error}). Run `{' '.join(install_command(release))}` yourself."
        ) from error
    try:
        yield
    finally:
        restore()
