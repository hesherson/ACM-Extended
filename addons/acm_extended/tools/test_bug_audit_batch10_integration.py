from historical_source import read_source
from collections import Counter
from pathlib import Path
import re

import tagcheck

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent
F = ROOT / "functions"


def read(path: Path) -> str:
    return read_source(path, encoding="utf-8-sig")


def source(name: str) -> str:
    return read(F / f"fn_{name}.sqf")


def test_removed_acre_babel_runtime_does_not_reappear():
    needles = (
        "acreBabble",
        "AcreBabble",
        "ACME_acre_",
        "ACME_Common",
        "acre_api_fnc_babel",
        "acre_sys_core_languages",
    )
    runtime = [ROOT / "config.cpp", *F.glob("*.sqf")]
    for path in runtime:
        text = read(path)
        for needle in needles:
            assert needle not in text, f"{needle} survived in {path.relative_to(ROOT)}"


def test_debug_circulation_reads_authoritative_state_hashmap():
    clinical = source("debugMenuClinical")
    assert 'call ACME_fnc_debugMenuClinical;' in source("debugMenuCore")
    assert 'getOrDefault ["pressorSupport", 0]' in clinical
    assert 'getOrDefault ["shockSeverity", 0]' in clinical
    assert 'getVariable ["ACME_circ_pressorSupport"' not in clinical
    assert 'getVariable ["ACME_circ_shockSeverity"' not in clinical


def test_debug_aed_visual_matches_real_monitor_precedence():
    gen = read(ADDONS / "circulation/functions/fnc_displayAEDMonitor_generateEKG.sqf")
    clinical = source("debugMenuClinical")
    assert '_effective >= 100 && {!(_rhythm in [-1,1,2])}' in gen
    assert 'ACM_circulation_AED_EKGRhythm' in clinical
    assert '_activeRh >= 100 && {!(_aedRh in [-1,1,2])}' in clinical
    assert 'ACME_AED_VisualRhythm' not in clinical


def test_all_acme_function_references_resolve_to_cfgfunctions_registration():
    rows = tagcheck.parse_config(ROOT / "config.cpp")
    registered = {row["resolved"].lower() for row in rows}
    refs = {}
    for addon in ADDONS.iterdir():
        if not addon.is_dir():
            continue
        for name, evidence in tagcheck.collect_references(addon).items():
            refs.setdefault(name, []).extend(evidence)
    unresolved = sorted(name for name in refs if name.startswith("acme_fnc_") and name not in registered)
    assert unresolved == []


def test_cfgfunctions_has_no_duplicate_resolved_names_or_missing_local_files():
    rows = tagcheck.parse_config(ROOT / "config.cpp")
    names = [row["resolved"].lower() for row in rows]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    missing = []
    for row in rows:
        rel = (row.get("file") or "").replace("\\", "/").lstrip("/")
        if rel.lower().startswith("acm_extended/"):
            target = ROOT / rel.split("/", 1)[1]
            if not target.is_file():
                missing.append((row["resolved"], rel))
    assert duplicates == []
    assert missing == []


def test_owner_dispatch_transaction_names_are_unique():
    cases = re.findall(r'case\s+"([^"]+)"', source("ownerDispatch"))
    duplicates = sorted(name for name, count in Counter(cases).items() if count > 1)
    assert len(cases) >= 100
    assert duplicates == []


def test_approx_network_helper_is_registered_and_scanner_treats_it_as_write():
    cfg = read(ROOT / "config.cpp")
    varcheck = read(ROOT / "tools/varcheck.py")
    assert cfg.count("class setVarNetApprox {};") == 1
    assert "acme_fnc_setvarnetapprox" in varcheck.lower()
