from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")

def test_wake_gate_and_request_are_registered():
    prep = read(ADDONS / "core/XEH_PREP.hpp")
    assert "PREP(canWake);" in prep
    assert "PREP(requestWake);" in prep

def test_request_wake_repairs_only_after_gate_recheck():
    s = read(ADDONS / "core/functions/fnc_reconcileWake.sqf")
    assert "FUNC(canWake)" in s
    assert "ACE_isUnconscious" in s
    assert "setUnconsciousState" in s
    assert "ACME CONSCIOUSNESS REPAIR" in s

def test_cba_wake_boundaries_accept_direct_patient_object():
    gate = read(ADDONS / "core/functions/fnc_canWake.sqf")
    sm = read(ADDONS / "core/ACM_Statemachine.hpp")
    post = read(ADDONS / "core/XEH_postInit.sqf")
    fracture = read(ROOT / "functions/fn_directPressureFracturePain.sqf")

    assert "if (_this isEqualType objNull) then {" in gate
    assert "condition = QUOTE([_this] call FUNC(canWake));" in sm
    assert "private _unit = if (_this isEqualType objNull)" in post
    assert '"fracture-pressure"] call ACM_core_fnc_requestWake' in fracture
    assert '["ace_medical_WakeUp", _patient] call CBA_fnc_localEvent' not in fracture

def test_rocuronium_and_seizure_use_canonical_unconscious_entry():
    roc = read(ROOT / "functions/fn_rocuroniumTick.sqf")
    seiz = read(ROOT / "functions/fn_seizureCollapse.sqf")
    assert "[_patient, true, 0, false] call ace_medical_fnc_setUnconscious;" in roc
    assert "[_patient, true, 0, false] call ace_medical_fnc_setUnconscious;" in seiz

def test_sedation_washout_uses_common_wake_path():
    s = read(ROOT / "functions/fn_ketamineSedationTick.sqf")
    assert '"sedation-washout"' in s
    assert "ACM_core_fnc_requestWake" in s

def test_stimuli_use_common_wake_path():
    for rel in (
        "disability/functions/fnc_shakeAwakeLocal.sqf",
        "disability/functions/fnc_slapAwakeLocal.sqf",
        "circulation/functions/fnc_handleMed_AmmoniaInhalantLocal.sqf",
    ):
        s = read(ADDONS / rel)
        assert "requestWake" in s
        assert "canWake" in s

def test_debug_dump_exposes_wake_decision():
    s = read(ROOT / "functions/fn_debugDumpToClipboard.sqf")
    assert "WakeGate Stable=" in s
    assert "ACME_consciousRepairCount" in s
