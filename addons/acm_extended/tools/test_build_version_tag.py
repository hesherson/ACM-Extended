from historical_source import assert_release_identity as _assert_current_build
from historical_source import read_source
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return read_source(ROOT / rel, encoding="utf-8-sig", errors="strict")


def test_release_is_the_cfgpatches_version():
    config = read("config.cpp")
    _assert_current_build()


def test_single_debug_renderer_uses_cfgpatches_version():
    text = read("functions/fn_debugMenuClinical.sqf")
    assert 'configFile >> "CfgPatches" >> "ACM_Extended" >> "version"' in text
    assert "ACME DEBUG v%2" in text
    for name in ["debugMenuCore", "debugMenuNetwork"]:
        assert "call ACME_fnc_debugMenuClinical;" in read(f"functions/fn_{name}.sqf")


def test_stable_1241_debug_identity_has_no_rc_suffix():
    startup = read("functions/fn_initForkStartupRuntime.sqf")
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup
    _assert_current_build()
