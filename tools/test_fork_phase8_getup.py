"""B240: reviewed current contract, with individually reportable execution."""

def test_current_phase8_getup():
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
    p=ROOT/"addons/core/functions/fnc_getUp.sqf"
    assert p.exists()
    assert not (ROOT/"addons/acm_extended/overrides/fn_getUp.sqf").exists()
    assert "overrides\\fn_getUp.sqf" not in CFG
    t=p.read_text()
    for tok in ("ACME_AAJT_zone3","ACME_headElevated","ACME_obtunded"):
        assert tok in t
    from current_source_contracts import _has
    assert _has(t, 'if (!local _patient) exitWith')
    assert _has(t, '[_patient, _roll, 2] call ACME_fnc_doAnim;')
    assert not _has(t, 'call ACME_fnc_animQueue;')
    assert _has(t, 'if (_carryOwned) exitWith')
    assert t.index('if (_carryOwned) exitWith') < t.index('_patient setVariable ["ACM_core_Lying_State", false, true];')
    print("fork phase 8 getUp native merge checks: PASS")


if __name__ == "__main__":
    test_current_phase8_getup()
