"""Resolve stable rig releases and upgrade the installed CLI to them.

The CLI is a uv tool installed from a release tag. It has its own lifecycle, so
upgrading it never touches the active checkout or the installed skills.
"""

import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import NamedTuple

import typer

from rig.report import errors

# Test hooks that point rig at a fixture release service and Git repository; not
# documented user settings. RIG_RELEASES_URL serves a GitHub-shaped latest-release
# response, and RIG_RELEASE_SOURCE is the Git URL its tags are installed from.
RELEASES_URL = os.environ.get(
    "RIG_RELEASES_URL", "https://api.github.com/repos/RafyTime/rig/releases/latest"
)
SOURCE = os.environ.get("RIG_RELEASE_SOURCE", "https://github.com/RafyTime/rig")
UV_INSTALL = "https://docs.astral.sh/uv/getting-started/installation/"
# Short, so an unreachable release service barely delays the requested command.
NOTICE_TIMEOUT = 2
CHECK_INTERVAL = 24 * 60 * 60  # Seconds between release notice checks.


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
    try:
        rig = next(iter(metadata.distributions(name="rig", path=directories)))
        return parse(rig.version)
    except (StopIteration, ValueError) as error:
        raise ReleaseError(
            "rig cannot tell which stable release is installed"
            f"{f' ({error})' if str(error) else ''}. Install a release tag with "
            f"`uv tool install --force git+{SOURCE}@<tag>`."
        ) from error


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
    try:
        request = urllib.request.Request(
            RELEASES_URL, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            tag = json.load(response)["tag_name"]
        return Release(tag, parse(tag))
    except (OSError, http.client.HTTPException) as error:
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


def notify() -> None:
    """Name a newer stable release on stderr, at most once a day, for a person.

    Never stops or fails the command it runs before: an unreachable or unreadable
    release service only delays it by the short timeout, without a message.
    """
    if not interactive() or not claim_daily_check():
        return
    found: list[Release] = []

    def check() -> None:
        try:
            found.append(latest_stable(timeout=NOTICE_TIMEOUT))
        except ReleaseError:
            pass

    # The socket timeout bounds each read, not DNS or a trickling response, so the
    # whole check gets one deadline; a daemon thread still waiting is abandoned.
    worker = threading.Thread(target=check, daemon=True)
    worker.start()
    worker.join(NOTICE_TIMEOUT)
    if not found:
        return
    latest = found[0]
    try:
        current = installed()  # A development build has no stable version to compare.
    except ReleaseError:
        return
    if latest.version > current:
        errors.print(
            f"rig {latest.version} is available (installed: {current}). "
            "Run `rig self update` to upgrade."
        )


def claim_daily_check() -> bool:
    """Record a check now if a day has passed since the last one; say whether.

    The marker's modification time is the last check, counted whether or not the
    service answered, so an offline device waits out the timeout once a day at most.
    A marker rig cannot write skips the check rather than repeating it every run.
    """
    marker = Path.home() / ".local" / "state" / "rig" / "release-check"
    try:
        if time.time() - marker.stat().st_mtime < CHECK_INTERVAL:
            return False
    except FileNotFoundError:
        pass
    except OSError:
        return False
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        return False
    return True


def interactive() -> bool:
    """Whether a person is at the terminal, as opposed to a script, pipe or CI.

    That means stdin and stderr, where the notice goes, are both terminals. Rich's
    TTY_INTERACTIVE variable overrides this either way ("1" or "0"); unlike Rich,
    FORCE_COLOR does not count, so colored CI logs still skip the check.
    """
    override = os.environ.get("TTY_INTERACTIVE")
    if override in ("0", "1"):
        return override == "1"
    return sys.stdin.isatty() and sys.stderr.isatty()


def update_cli() -> None:
    """Install the latest stable release if it is newer than the running CLI."""
    current = installed()
    with errors.status("Checking for the latest rig release..."):
        latest = latest_stable()
    if latest.version <= current:
        typer.echo(
            f"rig {current} is up to date (latest stable release: {latest.version})."
        )
        return
    errors.print(f"Upgrading rig {current} to {latest.version}...")
    upgrade(latest)
    typer.echo(f"Upgraded rig {current} to {latest.version}.")


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
    with running_files_moved_aside(release):
        try:
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


def running_files() -> list[Path]:
    """The tool environment files this rig process has loaded and runs from."""
    launcher = Path(sys.argv[0])
    if not launcher.suffix:
        launcher = launcher.with_suffix(".exe")  # Shells may drop it from argv.
    if launcher.suffix.lower() != ".exe":
        return []  # Not started from a launcher, e.g. `python -m rig`.
    files = [launcher]
    environment = Path(sys.prefix)
    if sys.prefix != sys.base_prefix:  # Only a venv's python.exe, never a base.
        files.append(Path(sys.executable))
    # Native extensions such as pydantic_core's stay loaded, so stay undeletable.
    for module in list(sys.modules.values()):
        path = Path(getattr(module, "__file__", None) or "")
        if path.suffix.lower() == ".pyd" and path.is_relative_to(environment):
            files.append(path)
    return files


@contextmanager
def running_files_moved_aside(release: Release) -> Generator[None]:
    """Let uv replace the tool environment this rig process runs from on Windows.

    Windows refuses to delete a running executable or a loaded extension but lets
    them move. So they move aside, with a copy of python.exe left in place for uv
    to find the environment by. If uv fails, they come back wherever uv left a gap.
    """
    files = running_files() if sys.platform == "win32" else []
    if not files:
        yield
        return
    manual = f"Run `{' '.join(install_command(release))}` yourself."
    moved: list[tuple[Path, Path]] = []

    def restore() -> None:
        for original, aside in moved:
            if not original.exists() and original.parent.is_dir():
                aside.replace(original)

    try:
        # Left behind: the moved files stay in use until this process exits.
        folder = Path(tempfile.mkdtemp(prefix="rig-self-update-"))
        for index, original in enumerate(files):
            aside = folder / f"{index}-{original.name}"
            original.replace(aside)
            moved.append((original, aside))
            if original == Path(sys.executable):
                shutil.copy2(aside, original)
    except OSError as error:
        for original, _ in moved:
            original.unlink(missing_ok=True)  # Including a partial python.exe copy.
        restore()
        raise ReleaseError(
            f"rig could not move its running files aside for uv to replace "
            f"({error}). {manual}"
        ) from error
    try:
        yield
    except ReleaseError:
        try:
            restore()
        except OSError as error:
            raise ReleaseError(
                f"rig could not put back its files after uv failed ({error}). {manual}"
            ) from error
        raise
