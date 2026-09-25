from historical_source import read_source
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return read_source(ROOT / rel, encoding="utf-8-sig", errors="strict")


def test_release_is_the_cfgpatches_version():
    config = read("config.cpp")
    assert 'version = "1.2.3";' in config
def test_both_debug_pages_render_cfgpatches_version():
    for rel in [
        "functions/fn_debugMenuClinical.sqf",
        "functions/fn_debugMenuNetwork.sqf",
        "functions/fn_debugMenuCore.sqf",
    ]:
        text = read(rel)
        assert 'configFile >> "CfgPatches" >> "ACM_Extended" >> "version"' in text
        assert "ACME DEBUG v%2" in text


def test_stable_123_debug_identity_has_no_rc_suffix():
    startup = read("functions/fn_initForkStartupRuntime.sqf")
    assert 'ACME_buildBatch = "B150";' in startup
    assert 'ACME_debugRevision = "";' in startup
    assert 'ACME_networkAuditRevision = "NA2-1.2.3-stable";' in startup
