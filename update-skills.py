# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Update selected skills: uv run update-skills.py [--dry-run]."""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv.insert(1, "update")
    runpy.run_path(
        str(Path(__file__).resolve().parent / "agents" / "skills.py"),
        run_name="__main__",
    )
