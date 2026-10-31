"""B240: reviewed current contract, with individually reportable execution."""

def test_current_phase125_chest_firstpass_flip():
    #!/usr/bin/env python3
    """Phase 125: local-server chest holes exist on first draw and grounded flips hold their endpoint."""
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    F=ROOT/'addons/acm_extended/functions'
    init=(F/'fn_chestSealInit.sqf').read_text()
    roll=(F/'fn_chestSealRoll.sqf').read_text()
    assert init.count('displayAddEventHandler ["MouseButtonUp"') == 1
    idx_gen=init.index('if (isServer) then {[_patient] call ACME_fnc_chestSealGenHoles;};')
    idx_cache=init.index('private _cached = _patient getVariable ["ACME_CS_netSnapshot", []];')
    assert idx_gen < idx_cache
    assert '[_patient, _token, _hold, true, _target]' in roll
    endpoint=roll[roll.index('[{',roll.index('private _rollTime')):]
    assert 'private _stillRollable = [_p] call ACME_fnc_chestSealCanPhysicalRoll;' in endpoint
    assert 'if ((_lock param [0, ""]) != _tok) exitWith {};' in endpoint
    assert 'if ((_p getVariable ["ACME_CS_rollToken", ""]) != _tok) exitWith {};' in endpoint
    assert '[_p] call ACME_fnc_animBlocked' not in endpoint
    assert 'ace_common_switchMove' in endpoint and '_needsHold && {_stillRollable}' in endpoint
    print('PASS phase125: chest first-pass snapshot and grounded roll endpoint are deterministic')


if __name__ == "__main__":
    test_current_phase125_chest_firstpass_flip()
