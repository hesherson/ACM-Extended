from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(path):
    return read_source(ROOT / path, encoding="utf-8", errors="ignore")

def main():
    seq = txt("functions/fn_headElevMedicSeq.sqf")
    start = txt("functions/fn_headElevMedicStart.sqf")
    stop = txt("functions/fn_headElevateStop.sqf")
    post = txt("functions/fn_postInit.sqf")
    cfg = txt("config.cpp")

    first = "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown"
    second = "AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon"
    rest = "AmovPknlMstpSnonWnonDnon"

    # Elevate and lower call the same controller; mode is retained only for call-site/state labeling.
    assert '[_medic, "elevate"] call ACME_fnc_headElevMedicSeq;' in start
    assert '[_medic, "lower"] call ACME_fnc_headElevMedicSeq;' in stop

    # The controller itself has only the lay-flat Putdown sequence for both modes.
    assert f'private _forcePose = _rest;' in seq
    assert f'private _first = "{first}";' in seq
    assert f'private _second = "{second}";' in seq
    assert "DraggerBasenon" not in seq
    assert "AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon" not in seq
    assert '_u setUnitPos "UP";' not in seq
    assert '_u setUnitPos "MIDDLE";' in seq

    # Each finite move is still requested at one site only and final state is forced to unarmed crouch.
    assert seq.count('[_u, _first, 2] call ACME_fnc_doAnim;') == 1
    assert seq.count('[_u, _second, 2] call ACME_fnc_doAnim;') == 1
    assert '_u selectWeapon "";' in seq
    assert '[_u, _rest, 2] call ACME_fnc_doAnim;' in seq

    # Patient path remains present at its existing call site and its animation classes remain untouched.
    assert '[_patient, "ACME_HeadElevPatientRelease", 2] call ACME_fnc_doAnim;' in stop
    assert 'class ACME_HeadElevPatientGrab: AinjPpneMrunSnonWnonDb_grab' in cfg
    assert 'class ACME_HeadElevPatientRelease: AinjPpneMrunSnonWnonDb_release' in cfg

    assert_release_identity()

    print("B89 shared provider Putdown sequence: PASS")

if __name__ == "__main__":
    main()
