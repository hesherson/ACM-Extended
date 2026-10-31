"""Execute owner suction, native emesis and explicit contamination with actual SQF.

Objects, local transport, CBA scheduling and random draws are explicit boundaries.
These cases check retained physical volume and receipts, not native engine networking.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, read, execute
from b282_aspiration_fixture import boundary, definitions, airway_fluid_definitions


def setup():
    producer=(ROOT/'addons/airway/functions/fnc_handleAirwayObstruction_Vomit.sqf').read_text()
    producer=re.sub(r'\brandom (\d+(?:\.\d+)?)',r'(\1 * 0)',producer)
    producer=re.sub(r'playSound3D \[[^;]+;', '_sounds=_sounds+1;',producer)
    explicit=re.sub(r'\brandom (\d+(?:\.\d+)?)',r'(\1 * 0)',read('laryngoConsequenceLocal'))
    explicit=re.sub(r'playSound3D \[[^;]+;', '_sounds=_sounds+1;',explicit)
    return definitions()+airway_fluid_definitions()+\
        'ACM_airway_fnc_handleAirwayObstruction_Vomit={'+boundary(producer,'airway')+'};'+\
        'ACME_fnc_laryngoConsequenceLocal={'+boundary(explicit)+'};'+r'''
        private _sounds=0;private _nativeHandler=[];
        CBA_fnc_addPerFrameHandler={_nativeHandler=_this;0};CBA_fnc_removePerFrameHandler={};
        ACME_fnc_setVarNet={params ["_p","_k","_v"];_p setVariable [_k,_v];};
        ACM_circulation_fnc_getNauseaMedicationEffects={0};ACM_airway_airwayObstructionVomitChance=1;
        ACM_airway_fnc_clearAirwayCheckedTime={};ACME_fnc_laryngoReflexChance={1};
        ACME_fnc_vomitDislodgeOPA={};
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",12];
        _patient setVariable ["ACME_suctionSessions",[["s",_medic,1000,"electric"]]];
        [_patient] call ACM_airway_fnc_handleAirwayObstruction_Vomit;
        private _native={CBA_missionTime=CBA_missionTime+30;[_nativeHandler select 2,0] call (_nativeHandler select 0);};
        private _read={([_patient] call ACME_fnc_laryngoFluidState) select 2};
        private _drain={params ["_id","_amount"];private _stamp=([_patient] call ACME_fnc_laryngoFluidState) select 0;
            [_patient,_medic,1,_id,_stamp,_amount,"s"] call ACME_fnc_laryngoFluidDrainLocal;};
    '''


def test_partial_suction_then_repeated_native_emesis_adds_only_new_volume():
    execute(setup()+r'''
        call _native;call _native;call _native;
        [call _read==6,"three native episodes did not create six stages"] call _check;
        ["drain",3] call _drain;
        [call _read==3,"actual owner debit did not retain partial contents"] call _check;
        call _native;
        [call _read==5,"new native event reconstructed previously removed vomit"] call _check;
        call _native;
        [call _read==7,"later event used stale baseline"] call _check;
        call _native;
        [call _read==8,"finite compartment cap changed"] call _check;
        [((_patient getVariable "ACME_laryngo_emesis") select 4)==6,"native aspiration receipts lost monotonic identity"] call _check;
    ''')


def test_actual_explicit_additive_stage_survives_later_native_event():
    execute(setup()+r'''
        call _native;call _native;["first",3] call _drain;
        [call _read==1,"partial native contents incorrect"] call _check;
        [_patient,_medic,1,"explicit","awakeTube"] call ACME_fnc_laryngoConsequenceLocal;
        [call _read==2,"explicit event lost its exact one-stage addition"] call _check;
        private _receipt=+(_patient getVariable "ACME_laryngo_emesis");
        call _native;
        [call _read==4,"native event replaced prior explicit stage with count times two"] call _check;
        [((_patient getVariable "ACME_laryngo_emesis") select 4)>(_receipt select 4),"new native event reused explicit receipt"] call _check;
        ["second",1] call _drain;call _native;
        [call _read==5,"second partial debit was reconstructed"] call _check;
    ''')


def test_clear_restart_reusing_native_count_cannot_resurrect_old_explicit_stage():
    execute(setup()+r'''
        // Older explicit receipt has count one and an eight-stage volume.
        [_patient,[["vomit",1]],true] call ACM_airway_fnc_setAirwayState;
        private _old=[_patient,"make","old",1,8] call ACME_fnc_aspirationEventKey;
        _patient setVariable ["ACME_laryngo_emesis",_old];
        _patient setVariable ["ACME_laryngo_pool",[[1,0,_old],8]];
        ["partial",3] call _drain;
        [_patient,[["vomit",0]],true] call ACM_airway_fnc_setAirwayState;
        [(_patient getVariable "ACME_laryngo_emesis") isEqualTo _old,"clearing deleted independent aspiration receipt"] call _check;
        // Counter arrives before the next producer receipt.
        [_patient,[["vomit",1]],true] call ACM_airway_fnc_setAirwayState;
        [call _read==2,"same-count old explicit receipt resurrected eight-stage volume"] call _check;
        [_patient,_medic,1,"new-explicit","awakeTube"] call ACME_fnc_laryngoConsequenceLocal;
        [call _read==3,"new real explicit episode was suppressed after clear"] call _check;
    ''')


def test_legacy_partial_pool_and_unrelated_blood_are_preserved():
    execute(setup()+r'''
        // Retained B282 save has the shared partial pool but no new ledger.
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",3];
        _patient setVariable ["ACME_laryngo_pool",[[3,0,[]],1]];
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",3];
        _patient setVariable ["ACME_laryngo_bloodRemaining",[3,2]];
        call _native;
        [call _read==3,"legacy partial pool was not captured before native event"] call _check;
        ["clear-vomit",3] call _drain;
        private _state=[_patient] call ACME_fnc_laryngoFluidState;
        [(_state select 1)=="b" && {(_state select 2)==2},"clearing vomit restored or erased underlying blood"] call _check;
        ["clear-blood",1] call _drain;
        [_patient,[["vomit",1]],true] call ACM_airway_fnc_setAirwayState;
        [_patient,[["vomit",0]],true] call ACM_airway_fnc_setAirwayState;
        [call _read==1,"vomit clear erased partial blood ledger"] call _check;
    ''')


@pytest.mark.parametrize('case',['duplicate','old_stamp','old_epoch','nonlocal','expired'])
def test_actual_drain_rejects_stale_duplicate_and_unowned_requests(case):
    change={
        'duplicate':'',
        'old_stamp':'call _native;',
        'old_epoch':'_patient setVariable ["ACME_clinicalEpoch",2];',
        'nonlocal':'_patient setVariable ["testLocal",false];',
        'expired':'CBA_missionTime=1001;',
    }[case]
    debit_id='once' if case=='duplicate' else 'new-request'
    execute(setup()+r'''
        call _native;call _native;
        private _stamp=([_patient] call ACME_fnc_laryngoFluidState) select 0;
        ["once",1] call _drain;
    '''+change+r'''
        private _before=call _read;
    '''+f'[_patient,_medic,1,"{debit_id}",_stamp,1,"s"] call ACME_fnc_laryngoFluidDrainLocal;'+r'''
        [call _read==_before,"invalid owner debit changed retained volume"] call _check;
    ''')


def test_snapshot_restore_roundtrips_partial_vomit_without_replaying_explicit_volume():
    from test_b271_ptx_stability import execute as restore_execute, restore_setup, function
    from test_historical_medication_rows import iteration_scopes
    restore_execute(restore_setup()+airway_fluid_definitions()+iteration_scopes(function('clinicalSnapshot'))+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",3];
        private _event=["saved",3,7,7,8];
        _patient setVariable ["ACME_laryngo_emesis",_event];
        _patient setVariable ["ACME_laryngo_vomitRemaining",[3,2,_event]];
        _patient setVariable ["ACME_laryngo_pool",[[3,0,_event],2]];
        private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
        [("ACME_laryngo_vomitRemaining" in ((_snapshot select 1) apply {_x select 0})),"snapshot omitted physical vomit remainder"] call _check;
        _patient setVariable ["ACME_laryngo_vomitRemaining",[]];
        _patient setVariable ["ACME_clinicalEpoch",9];
        [_patient,_snapshot,9] call ACME_fnc_clinicalRestore;
        private _state=[_patient] call ACME_fnc_laryngoFluidState;
        [(_state select 1)=="v" && {(_state select 2)==2},"actual restore resurrected explicit stage or lost partial volume"] call _check;
        [((_patient getVariable "ACME_laryngo_emesis") select 3)==9,"actual restore did not rebind receipt epoch"] call _check;
    ''')


def test_restored_receipt_epoch_rebinding_does_not_restore_suctioned_volume():
    execute(setup()+r'''
        [_patient,_medic,1,"saved-explicit","awakeTube"] call ACME_fnc_laryngoConsequenceLocal;
        [_patient,_medic,1,"saved-explicit2","awakeTube"] call ACME_fnc_laryngoConsequenceLocal;
        ["partial",1] call _drain;
        private _before=call _read;
        private _emesis=+(_patient getVariable "ACME_laryngo_emesis");
        _emesis set [3,2];_patient setVariable ["ACME_clinicalEpoch",2];
        _patient setVariable ["ACME_laryngo_emesis",_emesis];
        // Shared pool stamp still has the prior epoch, as a persisted older pool may.
        [call _read==_before,"receipt epoch rebind refilled the explicit compartment"] call _check;
    ''')
