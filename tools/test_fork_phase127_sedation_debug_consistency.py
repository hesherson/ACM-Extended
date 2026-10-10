"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase127_sedation_debug_consistency():
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    DEBUG = (ROOT / "addons/acm_extended/functions/fn_debugMenu.sqf").read_text(encoding="utf-8")
    assert "call ACME_fnc_debugMenuClinical;" in DEBUG
    DEBUG = (ROOT / "addons/acm_extended/functions/fn_debugMenuClinical.sqf").read_text(encoding="utf-8")
    COMP = (ROOT / "addons/acm_extended/functions/fn_sedationComponents.sqf").read_text(encoding="utf-8")
    TICK = (ROOT / "addons/acm_extended/functions/fn_ketamineSedationTick.sqf").read_text(encoding="utf-8")

    assert "1 = configured induction" in COMP, "shared sedation contract must remain induction-normalized"
    assert '([_patient] call ACME_fnc_sedationComponents) params ["_ket", "_prop", "_mid", "_fent", "_adjunct", "_sed"];' in DEBUG
    assert 'if (_sed >= 1 || {_sedated})' in DEBUG, "debug must use induction-normalized total"
    assert "_ketLoad * _adjunct >= _indThr" not in DEBUG, "debug must not apply the raw ketamine threshold twice"
    assert '["Sedation load", _sed toFixed 2' in DEBUG
    assert 'private _sedated = _patient getVariable ["ACME_ket_sedated", false];' in DEBUG
    assert "private _active = [_patient] call ACME_fnc_sedationActive;" in TICK
    ACTIVE = (ROOT / "addons/acm_extended/functions/fn_sedationActive.sqf").read_text(encoding="utf-8")
    assert "private _load = [_patient] call ACME_fnc_sedationOnBoard;" in ACTIVE
    assert "private _maintenance = call ACME_fnc_sedationThreshold;" in ACTIVE
    assert 'private _owned = _patient getVariable ["ACME_ket_sedated", false];' in ACTIVE
    assert "(_load >= 1) || {_owned && {_load >= _maintenance}}" in ACTIVE, "induction stays 1.0; only already-induced sedation uses maintenance"
    assert '[_patient, false, "sedation-washout"] call ACM_core_fnc_requestWake;' in TICK

    print("phase127 sedation debug consistency: PASS")


if __name__ == "__main__":
    test_current_phase127_sedation_debug_consistency()
