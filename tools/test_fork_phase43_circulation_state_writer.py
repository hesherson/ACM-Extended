#!/usr/bin/env python3
"""B238: execute the reviewed historical contract under pytest and direct CLI."""

def test_current_contract():
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    FUN=ROOT/"addons/acm_extended/functions"
    CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
    helper=(FUN/"fn_circStateCommit.sqf").read_text()
    assert 'class circStateCommit {};' in CFG
    # B203/B204: exact local state on every tick, bounded public refresh at the owner.
    assert 'setVariable ["ACME_circ_State", _state, false]' in helper
    assert 'setVariable ["ACME_circ_State", _state, true]' in helper
    assert 'if (!_public) exitWith {true};' in helper
    assert 'ACME_circ_stateNetInterval' in helper and 'private _publish =' in helper
    viol=[]
    for p in FUN.glob('*.sqf'):
        if p.name=='fn_circStateCommit.sqf': continue
        t=p.read_text()
        if p.name == 'fn_shockPhenotypeTick.sqf':
            # A no-change phenotype tick maintains the exact owner-local map without publishing.
            assert 'isNull _u || {!local _u} || {!alive _u}' in t
            assert '_u setVariable ["ACME_circ_State",_circ,false];' in t
            assert '[_u, _circ] call ACME_fnc_circStateCommit;' in t
            t=t.replace('_u setVariable ["ACME_circ_State",_circ,false];','')
        if 'setVariable ["ACME_circ_State"' in t: viol.append((p.name,'direct'))
        if '["ACME_circ_State", _state]' in t and 'ACME_fnc_setVarNet' in t: viol.append((p.name,'setVarNet'))
    assert not viol,viol
    callers=[p.name for p in FUN.glob('*.sqf') if 'ACME_fnc_circStateCommit' in p.read_text()]
    for required in ['fn_circHandle.sqf','fn_toggleShock.sqf','fn_epinephrineBolusLocal.sqf','fn_clinicalReset.sqf','fn_clearAllAilments.sqf','fn_clinicalRestore.sqf']:
        assert required in callers,(required,callers)
    print("fork phase 43 circulation authoritative writer checks: PASS")

if __name__ == "__main__":
    test_current_contract()
