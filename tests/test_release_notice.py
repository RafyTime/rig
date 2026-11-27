"""Tell interactive users about newer stable CLI releases during normal use."""

import os
import socket
import threading
import time
from importlib.metadata import version
from pathlib import Path

import pytest
from test_cli import fake_tool, rig
from test_self_update import development_build, publish

NOTICE = "Run `rig self update` to upgrade."


@pytest.fixture
def device(tmp_path: Path, latest: Path) -> dict[str, str]:
    """An interactive session with fake tools, its own home and a fixture release."""
    tools, home = tmp_path / "bin", tmp_path / "home"
    tools.mkdir()
    home.mkdir()
    fake_tool(tools, "chezmoi", exit_code=7)
    fake_tool(tools, "uv")
    return dict(
        os.environ,
        PATH=str(tools),
        HOME=str(home),
        USERPROFILE=str(home),
        RIG_RELEASES_URL=latest.as_uri(),
        # Rich's override for "a person is at the terminal"; the tests capture output.
        TTY_INTERACTIVE="1",
    )


def test_interactive_run_names_newer_release_and_still_runs_the_command(
    device: dict[str, str], latest: Path
):
    publish(latest, "v99.0.0")

    result = rig("diff", env=device)

    assert result.returncode == 7
    assert result.stdout.strip() == "chezmoi diff"
    assert (
        result.stderr.strip()
        == f"rig 99.0.0 is available (installed: {version('rig')}). {NOTICE}"
    )


def last_check(device: dict[str, str]) -> Path:
    return Path(device["HOME"], ".local", "state", "rig", "release-check")


def test_release_service_is_asked_at_most_once_a_day(
    device: dict[str, str], latest: Path
):
    publish(latest, "v99.0.0")
    assert NOTICE in rig("diff", env=device).stderr
    publish(latest, "v100.0.0")

    same_day = rig("apply", env=device)

    assert same_day.returncode == 7
    assert same_day.stderr == ""
    day_ago = time.time() - 24 * 60 * 60
    os.utime(last_check(device), (day_ago, day_ago))

    next_day = rig("diff", env=device)

    assert "rig 100.0.0 is available" in next_day.stderr


@pytest.mark.parametrize("tag", [f"v{version('rig')}", "v0.0.1", "v99.0.0-rc.1"])
def test_no_notice_unless_a_newer_stable_release_exists(
    device: dict[str, str], latest: Path, tag: str
):
    publish(latest, tag)

    result = rig("diff", env=device)

    assert result.returncode == 7
    assert result.stderr == ""


def test_noninteractive_run_never_checks(device: dict[str, str], latest: Path):
    publish(latest, "v99.0.0")
    # Output is captured, so without the override stderr is not a terminal.
    scripted = {key: value for key, value in device.items() if key != "TTY_INTERACTIVE"}

    result = rig("diff", env=scripted)

    assert result.returncode == 7
    assert result.stderr == ""
    assert not last_check(device).exists()


def test_unreachable_release_service_leaves_the_command_usable(
    device: dict[str, str],
):
    # Nothing is published, so the release service cannot answer.
    result = rig("diff", env=device)

    assert result.returncode == 7
    assert result.stdout.strip() == "chezmoi diff"
    assert result.stderr == ""


def test_development_build_runs_the_command_without_a_notice(
    tmp_path: Path, device: dict[str, str], latest: Path
):
    publish(latest, "v99.0.0")

    result = rig("diff", env=development_build(tmp_path, device))

    assert result.returncode == 7
    assert result.stdout.strip() == "chezmoi diff"
    assert result.stderr == ""


def test_cut_off_release_response_leaves_the_command_usable(device: dict[str, str]):
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]

        def answer_partly() -> None:
            connection, _ = server.accept()
            with connection:
                connection.recv(4096)
                # Promises 100 bytes, sends one, then closes.
                connection.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n{")

        responder = threading.Thread(target=answer_partly)
        responder.start()
        result = rig(
            "diff", env=dict(device, RIG_RELEASES_URL=f"http://127.0.0.1:{port}")
        )
        responder.join(timeout=10)

    assert result.returncode == 7
    assert result.stdout.strip() == "chezmoi diff"
    assert result.stderr == ""


def test_unresponsive_release_service_delays_the_command_by_the_timeout_at_most(
    device: dict[str, str],
):
    # Connections queue in the backlog but never get an answer.
    with socket.create_server(("127.0.0.1", 0)) as silent:
        port = silent.getsockname()[1]
        started = time.monotonic()
        result = rig(
            "diff", env=dict(device, RIG_RELEASES_URL=f"http://127.0.0.1:{port}")
        )
        elapsed = time.monotonic() - started

    assert result.returncode == 7
    assert result.stderr == ""
    assert 2 <= elapsed < 15


@pytest.mark.parametrize(
    "command", [["--version"], ["--help"], ["diff", "--help"], ["self", "update"]]
)
def test_help_version_and_self_update_skip_the_notice(
    device: dict[str, str], latest: Path, command: list[str]
):
    publish(latest, "v99.0.0")

    result = rig(*command, env=device)

    assert result.returncode == 0, result.stderr
    assert NOTICE not in result.stdout + result.stderr
    assert not last_check(device).exists()
