"""Compile configs with the real project include mappings and semantic lints."""
import os
from pathlib import Path
import re
import shutil
import subprocess

CONFIG = Path(__file__).resolve().parents[1] / "config.cpp"


def test_full_addon_config_passes_hemtt(tmp_path):
    hemtt = os.environ.get("HEMTT") or shutil.which("hemtt")
    if not hemtt:
        import pytest
        pytest.skip("HEMTT is required for config compilation")

    result = subprocess.run(
        [hemtt, "--no-color", "check"],
        cwd=CONFIG.parents[2],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    diagnostics = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + result.stderr)
    assert result.returncode == 0, diagnostics
    # Also inspect diagnostics: a successful exit alone is insufficient.
    assert not re.search(r"\berror(?:\[[^\]]+\])?:", diagnostics, re.IGNORECASE), diagnostics
    match = re.search(r"Rapified ([0-9]+) addon configs", diagnostics)
    assert match and int(match[1]) >= 14, diagnostics
