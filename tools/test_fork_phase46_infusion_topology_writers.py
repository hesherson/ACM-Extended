#!/usr/bin/env python3
"""B238: execute the reviewed historical contract under pytest and direct CLI."""

def test_current_contract():
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    FUN=ROOT/"addons/acm_extended/functions"
    CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
    for fn,file,var in [
     ("yLinesCommit","fn_yLinesCommit.sqf","ACME_YLines"),
     ("detachedBagsCommit","fn_detachedBagsCommit.sqf","ACME_detachedBags")]:
        t=(FUN/file).read_text()
        assert f'class {fn} {{}};' in CFG
        assert f'setVariable ["{var}"' in t
        viol=[]
        for p in FUN.glob('*.sqf'):
            if p.name==file: continue
            for line in p.read_text().splitlines():
                if var in line and ('setVariable' in line or 'ACME_fnc_setVarNet' in line): viol.append((p.name,line.strip()))
        assert not viol,(var,viol)
    from owner_route_contract import assert_owner_route
    assert_owner_route('fn_discardYTubing.sqf','discardYTubing','discardYTubingCommit','yLinesCommit',ROOT)
    # Refilling changes an existing access's bag map, not its Y-line identity.
    assert_owner_route('fn_transfusionSpikeOrAdd.sqf','yRefill','yRefillCommit','ivBagsCommit',ROOT)
    assert 'ACME_YLines' in (FUN/'fn_yRefillCommit.sqf').read_text()
    assert 'ACME_fnc_detachedBagsCommit' in (FUN/'fn_clinicalBagMove.sqf').read_text()
    print("fork phase 46 infusion topology writer checks: PASS")

if __name__ == "__main__":
    test_current_contract()
