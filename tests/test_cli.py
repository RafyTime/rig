"""Exercise the public rig commands as a separate process."""

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

# Typer and Rich force color when these are set, as on GitHub Actions. Callers
# that opt in get color; the tests check rig's default redirected output.
COLOR_OVERRIDES = {"FORCE_COLOR", "PY_COLORS", "GITHUB_ACTIONS"}


def rig(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None):
    environment = {
        key: value
        for key, value in (os.environ if env is None else env).items()
        if key not in COLOR_OVERRIDES
    }
    return subprocess.run(
        [sys.executable, "-m", "rig", *args],
        cwd=cwd,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


def test_version_names_the_installed_cli():
    result = rig("--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("rig ")


def test_help_lists_dotfile_commands():
    result = rig("--help")
    assert result.returncode == 0, result.stderr
    assert "diff" in result.stdout and "apply" in result.stdout
    assert "\x1b[" not in result.stdout


def fake_tool(directory: Path, name: str, exit_code: int = 0) -> None:
    """Install a stand-in that echoes its arguments and exits with a known code."""
    if os.name == "nt":
        # write_text already turns \n into CRLF on Windows.
        script = f"@echo {name} %*\n@exit /b {exit_code}\n"
        (directory / f"{name}.cmd").write_text(script)
    else:
        path = directory / name
        path.write_text(f'#!/bin/sh\necho {name} "$@"\nexit {exit_code}\n')
        path.chmod(0o755)


@pytest.mark.parametrize(
    ("command", "delegated"),
    [
        (["diff"], "diff"),
        (["apply"], "apply"),
        (["update"], "update"),
        (["update", "--no-apply"], "update --apply=false"),
    ],
)
def test_dotfile_commands_delegate_arguments_output_and_exit_code(
    tmp_path: Path, command: list[str], delegated: str
):
    tools = tmp_path / "bin"
    tools.mkdir()
    fake_tool(tools, "chezmoi", exit_code=7)
    fake_tool(tools, "uv")

    result = rig(
        *command,
        "--exclude",
        "scripts",
        cwd=tmp_path,
        env=dict(os.environ, PATH=str(tools)),
    )

    assert result.returncode == 7
    assert result.stdout.strip() == f"chezmoi {delegated} --exclude scripts"


@pytest.mark.skipif(os.name == "nt", reason="POSIX signals")
def test_chezmoi_killed_by_signal_reports_shell_status(tmp_path: Path):
    chezmoi = tmp_path / "chezmoi"
    chezmoi.write_text("#!/bin/sh\nkill -TERM $$\n")
    chezmoi.chmod(0o755)

    result = rig("diff", env=dict(os.environ, PATH=f"{tmp_path}:/bin:/usr/bin"))

    assert result.returncode == 128 + 15


@pytest.mark.parametrize(
    ("command", "present", "missing", "hint"),
    [
        ("diff", [], "chezmoi", "https://www.chezmoi.io/install/"),
        ("apply", [], "chezmoi", "https://www.chezmoi.io/install/"),
        ("apply", ["chezmoi"], "uv", "https://docs.astral.sh/uv/"),
        ("update", ["chezmoi"], "uv", "https://docs.astral.sh/uv/"),
    ],
)
def test_missing_dependency_stops_with_plain_recovery_step(
    tmp_path: Path, command: str, present: list[str], missing: str, hint: str
):
    for tool in present:
        fake_tool(tmp_path, tool)

    result = rig(command, env=dict(os.environ, PATH=str(tmp_path)))

    assert result.returncode == 1
    assert result.stdout == ""
    assert f"rig {command} needs {missing}" in result.stderr
    assert hint in result.stderr
    assert "\x1b[" not in result.stderr


def test_pull_only_update_does_not_need_the_skill_sync_hook(tmp_path: Path):
    fake_tool(tmp_path, "chezmoi")

    result = rig("update", "--no-apply", env=dict(os.environ, PATH=str(tmp_path)))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "chezmoi update --apply=false"


def test_chezmoi_that_cannot_start_stops_with_plain_recovery_step(tmp_path: Path):
    broken = tmp_path / ("chezmoi.exe" if os.name == "nt" else "chezmoi")
    broken.write_bytes(b"not an executable")
    broken.chmod(0o755)

    result = rig("diff", env=dict(os.environ, PATH=str(tmp_path)))

    assert result.returncode == 1
    assert "rig diff could not start chezmoi" in result.stderr
    assert "https://www.chezmoi.io/install/" in result.stderr
    assert "Traceback" not in result.stderr


REPO = Path(__file__).parents[1]

# CI provisions both tools, so a missing one fails there instead of skipping.
needs_chezmoi_and_uv = pytest.mark.skipif(
    not (os.environ.get("CI") or (shutil.which("chezmoi") and shutil.which("uv"))),
    reason="chezmoi and uv required",
)

RECORDING_SKILLS_ENGINE = """\
import json
import sys
from pathlib import Path

with Path(__file__).with_name("sync-calls.log").open("a") as log:
    print(json.dumps(sys.argv[1:]), file=log)
"""


@needs_chezmoi_and_uv
def test_diff_previews_and_each_apply_syncs_skills_once_from_outside_checkout(
    tmp_path: Path,
):
    checkout, home, elsewhere = tmp_path / "rig", tmp_path / "home", tmp_path / "cwd"
    elsewhere.mkdir()
    (checkout / "agents").mkdir(parents=True)
    (checkout / ".chezmoiroot").write_text("home\n")
    shutil.copytree(REPO / "home/.chezmoiscripts", checkout / "home/.chezmoiscripts")
    (checkout / "agents/skills.py").write_text(RECORDING_SKILLS_ENGINE)
    (checkout / "home/dot_example").write_text("configuration")
    config = home / ".config/chezmoi/chezmoi.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps({"sourceDir": str(checkout), "workingTree": str(checkout)})
    )
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("XDG_")
    }
    environment.update(
        HOME=str(home), USERPROFILE=str(home), UV_CACHE_DIR=str(tmp_path / "uv")
    )
    sync_calls = checkout / "agents/sync-calls.log"

    preview = rig("diff", cwd=elsewhere, env=environment)

    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert "example" in preview.stdout
    assert not (home / ".example").exists()
    assert not sync_calls.exists()

    applied = rig("apply", cwd=elsewhere, env=environment)

    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert (home / ".example").read_text() == "configuration"
    [call] = map(json.loads, sync_calls.read_text().splitlines())
    assert call[:2] == ["sync", "--home"]
    assert Path(call[2]) == home

    (checkout / "home/dot_example").write_text("updated configuration")
    preview = rig("diff", cwd=elsewhere, env=environment)

    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert "updated configuration" in preview.stdout
    assert (home / ".example").read_text() == "configuration"
    assert len(sync_calls.read_text().splitlines()) == 1

    applied = rig("apply", cwd=elsewhere, env=environment)

    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert (home / ".example").read_text() == "updated configuration"
    assert len(sync_calls.read_text().splitlines()) == 2


@pytest.mark.skipif(
    not (os.environ.get("CI") or (shutil.which("git") and shutil.which("uv"))),
    reason="git and uv required",
)
def test_uv_installs_the_cli_from_a_tagged_git_revision(tmp_path: Path):
    expected = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
    source = tmp_path / "source"
    shutil.copytree(
        REPO / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy2(REPO / "pyproject.toml", source)
    tag = f"v{expected['version']}"

    def run(*command: str, cwd: Path = source):
        result = subprocess.run(
            command,
            cwd=cwd,
            env=dict(
                os.environ,
                UV_TOOL_DIR=str(tmp_path / "tools"),
                UV_TOOL_BIN_DIR=str(tmp_path / "bin"),
            ),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    git = ["git", "-c", "user.name=Rig Test", "-c", "user.email=rig@example.invalid"]
    run(*git, "init", "--quiet")
    run(*git, "add", ".")
    run(*git, "commit", "--quiet", "--message", "Release")
    run(*git, "tag", tag)
    run("uv", "tool", "install", f"rig @ git+{source.as_uri()}@{tag}", cwd=tmp_path)

    executable = shutil.which("rig", path=str(tmp_path / "bin"))
    assert executable
    installed = run(executable, "--version", cwd=tmp_path)
    assert installed.stdout.strip() == f"rig {expected['version']}"
