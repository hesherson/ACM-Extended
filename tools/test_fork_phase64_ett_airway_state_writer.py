"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase64_ett_airway_state_writer():
    #!/usr/bin/env python3
    """Phase 64 regression: durable ETT airway-state quartet has one mutation endpoint."""
    from pathlib import Path
    import re
    ROOT=Path(__file__).resolve().parents[1]
    FUN=ROOT/'addons/acm_extended/functions'
    def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
    assert 'class ettAirwayStateCommit {};' in read('addons/acm_extended/config.cpp')
    commit=read('addons/acm_extended/functions/fn_ettAirwayStateCommit.sqf')
    for key in ('ACME_ETT_Inserted','ACME_ETT_CuffInflated','ACME_ETT_Secured','ACME_ETT_Unsecured'):
        assert key in commit
    assert 'cuff inflation may exist before seating' in commit
    for snippet in ('if (_newSecured || {_newUnsecured})','if (_newSecured)','if (_newUnsecured)','if (_writeInserted && {!_newInserted})'):
        assert snippet in commit
    for rel in ('fn_laryngoCollarRemove.sqf','fn_laryngoClose.sqf','fn_laryngoCuffDeflate.sqf','fn_laryngoCollarSet.sqf','fn_laryngoTubeEject.sqf','fn_clinicalRestore.sqf','fn_clinicalReset.sqf'):
        assert 'ACME_fnc_ettAirwayStateCommit' in read('addons/acm_extended/functions/'+rel), rel
    from current_source_contracts import assert_inline_owner_route
    assert_inline_owner_route('laryngoExtubate','ettExtubate','ettAirwayStateCommit')
    assert_inline_owner_route('laryngoCuffDone','ettCuffDone','ettAirwayStateCommit')
    viol=[]
    keys='(?:ACME_ETT_Inserted|ACME_ETT_CuffInflated|ACME_ETT_Secured|ACME_ETT_Unsecured)'
    for p in FUN.rglob('*.sqf'):
        if p.name=='fn_ettAirwayStateCommit.sqf': continue
        for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            code=raw.split('//',1)[0]
            if re.search(r'setVariable\s*\[\s*["\']'+keys+r'["\']',code): viol.append((p,i,raw.strip()))
            if 'ACME_fnc_setVarNet' in code and re.search(keys,code): viol.append((p,i,raw.strip()))
    assert not viol, '\n'.join(f'{p.relative_to(ROOT)}:{i}: {s}' for p,i,s in viol)
    print('fork phase 64 ETT airway-state writer checks: PASS')


if __name__ == "__main__":
    test_current_phase64_ett_airway_state_writer()
