#!/usr/bin/env python3
"""B238: execute the reviewed historical contract under pytest and direct CLI."""

def test_current_contract():
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    FUN=ROOT/"addons/acm_extended/functions"
    CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
    helper=(FUN/"fn_tbiStateCommit.sqf").read_text()
    assert 'class tbiStateCommit {};' in CFG
    # B203/B204: exact local state on every tick, bounded public refresh at the owner.
    assert 'setVariable ["ACME_tbi_State", _state, false]' in helper
    assert 'setVariable ["ACME_tbi_State", _state, true]' in helper
    assert 'if (!_public) exitWith {true};' in helper
    assert 'ACME_tbi_stateNetInterval' in helper and 'private _publish =' in helper
    viol=[]
    for p in FUN.glob('*.sqf'):
        if p.name=='fn_tbiStateCommit.sqf': continue
        t=p.read_text()
        if 'setVariable ["ACME_tbi_State"' in t: viol.append((p.name,'direct'))
        if '["ACME_tbi_State", _state]' in t and 'ACME_fnc_setVarNet' in t: viol.append((p.name,'setVarNet-state'))
        if '["ACME_tbi_State", _tbi]' in t and 'ACME_fnc_setVarNet' in t: viol.append((p.name,'setVarNet-tbi'))
    assert not viol,viol
    callers=[p.name for p in FUN.glob('*.sqf') if 'ACME_fnc_tbiStateCommit' in p.read_text()]
    for required in ['fn_tbiInit.sqf','fn_tbiHandle.sqf','fn_tbiBlast.sqf','fn_tbiApplyOsmotherapy.sqf','fn_tbiApplyPressorMAP.sqf','fn_headInjuryTBI.sqf','fn_clinicalReset.sqf','fn_clearAllAilments.sqf','fn_zeusClearTBILocal.sqf','fn_zeusTBIApplyLocal.sqf','fn_circHandle.sqf','fn_clinicalRestore.sqf']:
        assert required in callers,(required,callers)
    print("fork phase 42 TBI authoritative writer checks: PASS")

if __name__ == "__main__":
    test_current_contract()
