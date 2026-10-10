#!/usr/bin/env python3
"""B238: execute the reviewed historical contract under pytest and direct CLI."""

def test_current_contract():
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    FUN=ROOT/"addons/acm_extended/functions"
    CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
    helper=(FUN/"fn_infusionMedicationStateCommit.sqf").read_text()
    assert 'class infusionMedicationStateCommit {};' in CFG
    assert 'setVariable ["ACME_infusion_BagMedications", _entries, false]' in helper
    assert 'setVariable ["ACME_infusion_BagMedications", _entries, true]' in helper
    assert 'ACME_infusion_stateNetInterval' in helper and 'private _publish =' in helper
    assert '[_patient, "ACME_infusion_BagMedications", _entries] call ACME_fnc_setVarNet;' in helper
    assert 'private _has = !(_entries isEqualTo []);' in helper
    assert '[_patient, "ACME_infusion_HasBagMedications", _has] call ACME_fnc_setVarNet;' in helper
    viol=[]
    for p in FUN.glob('*.sqf'):
        if p.name=='fn_infusionMedicationStateCommit.sqf': continue
        t=p.read_text()
        for token in ['setVariable ["ACME_infusion_BagMedications"','setVariable ["ACME_infusion_HasBagMedications"']:
            if token in t: viol.append((p.name,token))
        if '"ACME_infusion_BagMedications"' in t and 'ACME_fnc_setVarNet' in t:
            # targeted writer patterns, not ordinary reads
            for line in t.splitlines():
                if 'ACME_infusion_BagMedications' in line and 'ACME_fnc_setVarNet' in line: viol.append((p.name,line.strip()))
        if '"ACME_infusion_HasBagMedications"' in t and 'ACME_fnc_setVarNet' in t:
            for line in t.splitlines():
                if 'ACME_infusion_HasBagMedications' in line and 'ACME_fnc_setVarNet' in line: viol.append((p.name,line.strip()))
    assert not viol,viol
    callers=[p.name for p in FUN.glob('*.sqf') if 'ACME_fnc_infusionMedicationStateCommit' in p.read_text()]
    for required in ['fn_clinicalReset.sqf','fn_clearAllAilments.sqf','fn_discardYTubingCommit.sqf','fn_transfusionPullCommit.sqf','fn_preparedAttachLocal.sqf','fn_fluidCommit.sqf','fn_infusionClampLocal.sqf','fn_infusionRegisterCore.sqf','fn_infusionRetire.sqf','fn_clinicalBagMove.sqf','fn_handleInfusions.sqf']:
        assert required in callers,(required,callers)
    from owner_route_contract import assert_owner_route
    assert_owner_route('fn_discardYTubing.sqf','discardYTubing','discardYTubingCommit','infusionMedicationStateCommit',ROOT)
    assert_owner_route('fn_transfusionPullBag.sqf','transfusionPull','transfusionPullCommit','infusionMedicationStateCommit',ROOT)
    print("fork phase 44 infusion medication state contract checks: PASS")

if __name__ == "__main__":
    test_current_contract()
