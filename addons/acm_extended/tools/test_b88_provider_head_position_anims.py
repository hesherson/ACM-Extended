from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(path):
    return read_source(ROOT / path, encoding="utf-8", errors="ignore")

def main():
    seq = txt("functions/fn_headElevMedicSeq.sqf")
    start = txt("functions/fn_headElevMedicStart.sqf")
    stop = txt("functions/fn_headElevateStop.sqf")
    cancel = txt("functions/fn_headElevateCancelSeq.sqf")
    cfg = txt("config.cpp")

    first = "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown"
    second = "AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon"
    rest = "AmovPknlMstpSnonWnonDnon"

    # B89 superseded B88's asymmetric provider lift. Keep this historical test useful by
    # protecting the current shared Putdown contract instead of asserting the retired graph.
    assert '[_medic, "elevate"] call ACME_fnc_headElevMedicSeq;' in start
    assert '[_medic, "lower"] call ACME_fnc_headElevMedicSeq;' in stop
    assert f'private _forcePose = _rest;' in seq
    assert f'private _first = "{first}";' in seq
    assert f'private _second = "{second}";' in seq
    assert "DraggerBasenon" not in seq
    assert "AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon" not in seq
    assert '_u setUnitPos "UP";' not in seq
    assert '_u setUnitPos "MIDDLE";' in seq

    # Each finite move remains exact-once and provider control ends in an unarmed crouch,
    # then releases the stance lock back to AUTO.
    assert seq.count('[_u, _first, 2] call ACME_fnc_doAnim;') == 1
    assert seq.count('[_u, _second, 2] call ACME_fnc_doAnim;') == 1
    assert '_u selectWeapon "";' in seq
    assert '[_u, _rest, 2] call ACME_fnc_doAnim;' in seq
    assert '_unit setUnitPos "AUTO";' in seq
    assert '_m setUnitPos "AUTO";' in cancel

    # Patient release remains the authored lay-flat animation and is independent of the provider graph.
    assert '[_patient, "ACME_HeadElevPatientRelease", 2] call ACME_fnc_doAnim;' in stop
    assert 'class ACME_HeadElevPatientGrab: AinjPpneMrunSnonWnonDb_grab' in cfg
    assert 'class ACME_HeadElevPatientRelease: AinjPpneMrunSnonWnonDb_release' in cfg

    assert_release_identity()
    print("B88 supersession/current provider head-position contract: PASS")

if __name__ == "__main__":
    main()
