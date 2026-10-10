"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase79_aajt_state_owner():
    from pathlib import Path
    import re
    ROOT=Path(__file__).resolve().parents[1]
    FUN=ROOT/'addons/acm_extended/functions'
    owner=FUN/'fn_aajtStateCommit.sqf'
    assert owner.exists()
    config=(ROOT/'addons/acm_extended/config.cpp').read_text(errors='ignore')
    assert 'class aajtStateCommit {};' in config
    fields=['ACME_AAJT_inguinal','ACME_AAJT_axillaleft','ACME_AAJT_axillaright','ACME_AAJT_inguinalAt','ACME_AAJT_axillaleftAt','ACME_AAJT_axillarightAt','ACME_AAJT_legs']
    pat=re.compile(r'setVariable\s*\[\s*["\']('+'|'.join(map(re.escape,fields))+r')["\']')
    viol=[]
    for p in FUN.glob('*.sqf'):
        if p==owner: continue
        for m in pat.finditer(p.read_text(errors='ignore')):
            viol.append((p.name,m.group(1)))
    assert not viol, viol
    for n in ['fn_aajtApply.sqf','fn_aajtRemove.sqf','fn_junctionalFullHeal.sqf']:
        assert 'ACME_fnc_aajtStateCommit' in (FUN/n).read_text(errors='ignore')
    # New injury must preserve existing physical AAJT placement rather than overwrite it.
    inflict=(FUN/'fn_junctionalInflict.sqf').read_text(errors='ignore')
    assert 'if (!local _unit) exitWith' in inflict and 'ACME_fnc_ownerDispatch' in inflict
    assert 'if ([_unit, _partIndex] call ACME_fnc_aajtOccludes)' in inflict
    assert 'call ACME_fnc_aajtSetLegTQ' in inflict
    assert 'ACME_fnc_aajtStateCommit' not in inflict
    print('phase79 aajt state owner: PASS')


if __name__ == "__main__":
    test_current_phase79_aajt_state_owner()
