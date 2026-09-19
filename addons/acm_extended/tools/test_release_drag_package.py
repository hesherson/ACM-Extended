"""Inspect real HEMTT output: release must not expose the experimental drag handle.

Run `hemtt release` before these checks. A dev package is optional and verifies
that development testing remains available. The checks also accept --no-bin output.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
ACTION_CLASSES = ("ACME_AttachDragHandle", "ACME_ReleaseDragHandle", "ACME_ReleaseDragHandleSelf")


def run(hemtt, *args):
    result = subprocess.run([hemtt, *map(str, args)], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


def package(mode, destination):
    hemtt = os.environ.get("HEMTT") or shutil.which("hemtt")
    output = ROOT / ".hemttout" / mode / "addons"
    extended = output / "ACM_acm_extended.pbo"
    gui = output / "ACM_gui.pbo"
    if not hemtt or not extended.exists() or not gui.exists():
        pytest.skip(f"Build the {mode} package and make HEMTT available first")
    destination.mkdir()
    binary = destination / "config.bin"
    config = destination / "config.json"
    menu = destination / "updateActions.sqf"
    post = destination / "postInit.sqf"
    run(hemtt, "utils", "pbo", "extract", extended, "config.bin", binary)
    run(hemtt, "utils", "config", "derapify", binary, config, "--format", "json")
    run(hemtt, "utils", "pbo", "extract", gui, r"overrides\fnc_updateActions.sqf", menu)
    run(hemtt, "utils", "pbo", "extract", extended, r"functions\fn_postInit.sqf", post)
    return json.loads(config.read_text()), menu.read_text(), post.read_text()


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    return package("release", tmp_path_factory.mktemp("drag-release") / "extracted")


def test_release_config_has_no_attach_release_or_self_release_actions(release):
    config, _, _ = release
    assert config["CfgPatches"]["ACM_Extended"]["acme_developmentBuild"] == 0
    man = config["CfgVehicles"]["CAManBase"]
    patient = man["ACE_Actions"]["ACE_MainActions"]
    self_actions = man["ACE_SelfActions"]
    for name in ACTION_CLASSES:
        assert name not in patient and name not in self_actions
    assert "ACM_LyingState_GetUp" in patient
    assert "ACME_LyingState_GetUp_Player" in patient


def test_release_medical_menu_has_no_drag_handle_rows(release):
    _, menu, _ = release
    for text in ("Attach Drag Handle", "Release Drag Handle", "ACME_DragHandleAttach", "ACME_DragHandleRelease"):
        assert text not in menu
    assert "ACME_fnc_headElevateCanStart" in menu


def test_release_does_not_install_drag_runtime_and_keeps_normal_transport(release):
    _, _, post = release
    assert "call ACME_fnc_initDragHandleRuntime" not in post
    assert "call ACME_fnc_registerHeadElevationTransportRuntime" in post


def test_development_package_keeps_actions_only_when_feature_source_exists(tmp_path):
    feature = ROOT / "addons/acm_extended/functions/fn_initDragHandleRuntime.sqf"
    if not feature.exists():
        pytest.skip("This branch deliberately excludes the experimental implementation")
    config, menu, post = package("dev", tmp_path / "development")
    assert config["CfgPatches"]["ACM_Extended"]["acme_developmentBuild"] == 1
    man = config["CfgVehicles"]["CAManBase"]
    assert ACTION_CLASSES[0] in man["ACE_Actions"]["ACE_MainActions"]
    assert ACTION_CLASSES[1] in man["ACE_Actions"]["ACE_MainActions"]
    assert ACTION_CLASSES[2] in man["ACE_SelfActions"]
    assert "Attach Drag Handle" in menu and "Release Drag Handle" in menu
    assert "call ACME_fnc_initDragHandleRuntime" in post


def test_source_defaults_off_and_hook_only_enables_development_modes():
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    hook = (ROOT / ".hemtt/hooks/pre_build/development_actions.rhai").read_text()
    assert "acme_developmentBuild = 0;" in config
    assert "acme_developmentBuild = 1;" not in config
    assert "HEMTT.is_dev() || HEMTT.is_launch()" in hook
    assert "HEMTT_VFS.join(name)" in hook
    assert "HEMTT_RFS" not in hook
    assert "Development drag handle entry escaped release filtering" in hook


def test_retained_development_entrypoints_reject_release_before_any_side_effects():
    functions = ROOT / "addons/acm_extended/functions"
    for name in ("initDragHandleRuntime", "dragHandleCanStart", "dragHandleStart", "dragHandleStartOwner", "dragHandleStartMedic"):
        path = functions / f"fn_{name}.sqf"
        if not path.exists():
            continue
        lines = [line for line in path.read_text().splitlines() if line and not line.startswith("//")]
        assert '"acme_developmentBuild") != 1' in lines[0], name
        assert "exitWith" in lines[0], name
