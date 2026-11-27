from pathlib import Path

import pytest


@pytest.fixture
def latest(tmp_path: Path) -> Path:
    """Where a test serves the release service's latest-release response."""
    return tmp_path / "latest.json"
