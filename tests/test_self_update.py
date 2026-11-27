"""Upgrade the installed CLI through `rig self update`."""

import json
import os
import shutil
import subprocess
import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest
from test_cli import REPO, fake_tool, rig


@pytest.fixture
def device(tmp_path: Path, latest: Path):
    """Fake uv and chezmoi on PATH, with the latest release served from a file."""
    tools = tmp_path / "bin"
    tools.mkdir()
    fake_tool(tools, "uv")
    fake_tool(tools, "chezmoi")
    return dict(
        os.environ,
        PATH=str(tools),
        RIG_RELEASES_URL=latest.as_uri(),
    )


def publish(latest: Path, tag: str) -> None:
    """Serve `tag` as the latest stable release, shaped like GitHub's API."""
    latest.write_text(json.dumps({"tag_name": tag}))


def test_newer_release_is_installed_by_uv_without_touching_the_checkout(
    device: dict[str, str], latest: Path
):
    publish(latest, "v99.0.0")

    result = rig("self", "update", env=device)

    assert result.returncode == 0, result.stderr
    # Only uv runs; chezmoi, and so the checkout and skills, stay untouched.
    installer, outcome = result.stdout.strip().splitlines()
    assert installer == (
        "uv tool install --force git+https://github.com/RafyTime/rig@v99.0.0"
    )
    assert outcome == f"Upgraded rig {version('rig')} to 99.0.0."


@pytest.mark.parametrize("tag", [f"v{version('rig')}", "v0.0.1"])
def test_current_cli_reports_up_to_date_without_installing(
    device: dict[str, str], latest: Path, tag: str
):
    publish(latest, tag)

    result = rig("self", "update", env=device)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        f"rig {version('rig')} is up to date (latest stable release: {tag[1:]})."
    )


def development_build(tmp_path: Path, env: dict[str, str]) -> dict[str, str]:
    """`env` with rig reporting a version that is not a stable release."""
    # Python finds PYTHONPATH's metadata before the installed rig's.
    metadata = tmp_path / "dev" / "rig-0.3.0.dev1.dist-info"
    metadata.mkdir(parents=True)
    (metadata / "METADATA").write_text("Name: rig\nVersion: 0.3.0.dev1\n")
    return dict(env, PYTHONPATH=str(metadata.parent))


def assert_fails_with(result, *hints: str) -> None:
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "\x1b[" not in result.stderr
    for hint in hints:
        assert hint in result.stderr


def test_unreachable_release_service_stops_with_recovery_step(device: dict[str, str]):
    # Nothing is published, so the release service cannot answer.
    result = rig("self", "update", env=device)

    assert_fails_with(
        result, "rig could not reach the release service", "Check your connection"
    )
    assert result.stdout == ""


@pytest.mark.parametrize("response", ["{}", '{"tag_name": "v1.0.0-rc.1"}', "<html>"])
def test_unreadable_latest_release_stops_with_manual_install_step(
    device: dict[str, str], latest: Path, response: str
):
    latest.write_text(response)

    result = rig("self", "update", env=device)

    assert_fails_with(
        result,
        "rig could not read the latest release",
        "uv tool install git+https://github.com/RafyTime/rig@<tag>",
    )
    assert result.stdout == ""


def test_development_build_stops_with_install_step(
    tmp_path: Path, device: dict[str, str], latest: Path
):
    publish(latest, "v99.0.0")

    result = rig("self", "update", env=development_build(tmp_path, device))

    assert_fails_with(
        result,
        "rig cannot tell which stable release is installed",
        "uv tool install --force git+https://github.com/RafyTime/rig@<tag>",
    )
    assert result.stdout == ""


def test_missing_uv_stops_with_install_step(
    tmp_path: Path, device: dict[str, str], latest: Path
):
    publish(latest, "v99.0.0")
    no_uv = tmp_path / "no-uv"
    no_uv.mkdir()

    result = rig("self", "update", env=dict(device, PATH=str(no_uv)))

    assert_fails_with(
        result, "rig needs uv to install rig 99.0.0", "https://docs.astral.sh/uv/"
    )


def test_failed_install_keeps_uv_output_and_names_the_manual_command(
    device: dict[str, str], latest: Path
):
    publish(latest, "v99.0.0")
    fake_tool(Path(device["PATH"]), "uv", exit_code=2)

    result = rig("self", "update", env=device)

    assert_fails_with(
        result,
        "uv could not install rig 99.0.0 (exit status 2)",
        "uv tool install --force git+https://github.com/RafyTime/rig@v99.0.0",
    )
    assert result.stdout.startswith("uv tool install")
    assert "Upgraded" not in result.stdout


@pytest.mark.skipif(
    not (os.environ.get("CI") or (shutil.which("git") and shutil.which("uv"))),
    reason="git and uv required",
)
def test_installed_tagged_build_upgrades_itself_to_a_newer_tag(tmp_path: Path):
    """A real uv tool install of one tag replaces itself with the next tag's build."""
    old = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
    major, minor, patch = old.split(".")
    new = f"{major}.{minor}.{int(patch) + 1}"
    source, bin_dir = tmp_path / "source", tmp_path / "bin"
    latest = tmp_path / "latest.json"
    environment = dict(
        os.environ,
        UV_TOOL_DIR=str(tmp_path / "tools"),
        UV_TOOL_BIN_DIR=str(bin_dir),
        RIG_RELEASES_URL=latest.as_uri(),
        RIG_RELEASE_SOURCE=source.as_uri(),
    )

    def run(*command: str, cwd: Path = source):
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    shutil.copytree(
        REPO / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy2(REPO / "pyproject.toml", source)
    git = ["git", "-c", "user.name=Rig Test", "-c", "user.email=rig@example.invalid"]
    run(*git, "init", "--quiet")
    for release in (old, new):
        pyproject = source / "pyproject.toml"
        pyproject.write_text(
            pyproject.read_text().replace(
                f'version = "{old}"', f'version = "{release}"'
            )
        )
        run(*git, "add", ".")
        run(*git, "commit", "--quiet", "--allow-empty", "--message", release)
        run(*git, "tag", f"v{release}")
    run("uv", "tool", "install", f"git+{source.as_uri()}@v{old}", cwd=tmp_path)
    installed = shutil.which("rig", path=str(bin_dir))
    assert installed
    publish(latest, f"v{new}")

    # TEMP CI diagnostics: what uv could not remove.
    attempt = subprocess.run(
        [installed, "self", "update"], cwd=tmp_path, env=environment,
        capture_output=True, encoding="utf-8", errors="replace", timeout=300,
    )
    if attempt.returncode != 0:
        left = sorted(str(p.relative_to(tmp_path)) for p in (tmp_path / "tools").rglob("*"))
        pytest.fail(attempt.stdout + attempt.stderr + "\nLEFT:\n" + "\n".join(left[:200]))
    upgraded = attempt

    assert f"Upgraded rig {old} to {new}." in upgraded.stdout
    assert run(installed, "--version", cwd=tmp_path).stdout.strip() == f"rig {new}"
    current = run(installed, "self", "update", cwd=tmp_path)
    assert f"rig {new} is up to date" in current.stdout
