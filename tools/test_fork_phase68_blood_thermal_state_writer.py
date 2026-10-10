"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase68_blood_thermal_state_writer():
    #!/usr/bin/env python3
    """Phase 68 regression: blood thermal flags/clocks have one mutation endpoint."""
    from pathlib import Path
    import re
    ROOT=Path(__file__).resolve().parents[1]
    FUN=ROOT/'addons/acm_extended/functions'
    def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
    assert 'class bloodThermalStateCommit {};' in read('addons/acm_extended/config.cpp')
    commit=read('addons/acm_extended/functions/fn_bloodThermalStateCommit.sqf')
    for name in ('ACME_warmedBlood','ACME_coldBlood','ACME_coldBloodHungAt','ACME_tempFlagHoldUntil'):
        assert name in commit
    for rel in ('fn_yLineAttach.sqf','fn_clinicalRestore.sqf','fn_clinicalReset.sqf'):
        assert 'ACME_fnc_bloodThermalStateCommit' in read('addons/acm_extended/functions/'+rel), rel
    from owner_route_contract import assert_owner_route
    assert_owner_route('fn_hangPreparedSet.sqf','preparedHang','preparedHangCommit','bloodThermalStateCommit')
    assert_owner_route('fn_transfusionSpikeOrAdd.sqf','yRefill','yRefillCommit','bloodThermalStateCommit')
    viol=[]
    for p in FUN.rglob('*.sqf'):
        if p.name=='fn_bloodThermalStateCommit.sqf': continue
        for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            code=raw.split('//',1)[0]
            if re.search(r'setVariable\s*\[\s*["\']ACME_(?:warmedBlood|coldBlood|coldBloodHungAt|tempFlagHoldUntil)["\']',code):
                viol.append((p,i,raw.strip()))
            if 'ACME_fnc_setVarNet' in code and re.search(r'ACME_(?:warmedBlood|coldBlood|coldBloodHungAt|tempFlagHoldUntil)',code):
                viol.append((p,i,raw.strip()))
    assert not viol, '\n'.join(f'{p.relative_to(ROOT)}:{i}: {s}' for p,i,s in viol)
    restore=read('addons/acm_extended/functions/fn_clinicalRestore.sqf')
    assert '_bloodThermalRestore' in restore
    reset=read('addons/acm_extended/functions/fn_clinicalReset.sqf')
    assert '"ACME_coldBloodHungAt", "ACME_tempFlagHoldUntil"' in reset
    print('fork phase 68 blood-thermal state writer checks: PASS')


if __name__ == "__main__":
    test_current_phase68_blood_thermal_state_writer()
