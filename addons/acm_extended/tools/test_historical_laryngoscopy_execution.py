"""Batch 6: laryngoscopy events, passage and delayed reset with explicit boundaries.

The actual reflex helper, consequence transaction and native airway writer run.
Engine control IDs, object/network boundaries and random draws are fixtures;
medication inputs are effect vectors, not a replacement dose/kinetic model.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute
from test_historical_cardiac_execution import code as clinical_code, setup as clinical_setup, function as clinical_function
from test_historical_procedure_trays import source, ui_code, controls


def code(text):
    # Use explicit draws to exercise both branches without probabilistic tests.
    text = re.sub(r'\brandom (\d+(?:\.\d+)?)',r'(\1 * _draw)',text)
    text = re.sub(r'playSound3D \[[^;]+;',lambda m: '_sounds pushBack "'+('wet' if 'wet_gag' in m[0] else 'dry' if 'dry_gag' in m[0] else 'teeth')+'";',text)
    text = text.replace('playSound "ACME_VentClick";', '_clicks=_clicks+1;')
    text = text.replace('_med removeItem "ACME_ETTube";', '_tubeDebits=_tubeDebits+1;')
    text = text.replace('_oldDisplay !=', '_oldDisplay isNotEqualTo').replace('_oldPatient !=','_oldPatient isNotEqualTo')
    return ui_code(clinical_code(text))


def function(name):
    return 'ACME_fnc_'+name+'={'+code(source(name))+'};\n'


def setup():
    return clinical_setup()+controls()+'''
        private _draw=0;private _sounds=[];private _dislodges=0;private _clicks=0;
        private _tubeDebits=0;private _ejections=[];private _placements=[];private _dispatches=[];
        private _logs=[];private _cuffFinishes=0;private _slotRefreshes=0;
        private _effects=[0,0,0,0,1,0];
        ACME_fnc_treatmentSupplyCount={1};
        ACME_fnc_treatmentSupplyTake={_tubeDebits=_tubeDebits+1;[_medic,"ACME_ETTube",objNull,"fixture"]};
        ACME_fnc_treatmentSupplyRefund={true};
        ACME_fnc_sedationComponents={_effects};
        ACME_fnc_vomitDislodgeOPA={_dislodges=_dislodges+1;};
        ACM_airway_fnc_clearAirwayCheckedTime={};
        ACME_fnc_medLog={_logs pushBack _this;};
        ACME_fnc_ettMigrationStateCommit={_placements pushBack _this;};
        ACME_fnc_laryngoRefreshSlots={_slotRefreshes=_slotRefreshes+1;};
        ACME_fnc_laryngoTubeFrames={};ACME_fnc_laryngoTubePose={};
        ACME_fnc_laryngoCuffDone={_cuffFinishes=_cuffFinishes+1;};
        ACME_fnc_laryngoTubeEject={_ejections pushBack _this;};
        uiNamespace setVariable ["ACME_laryngo_dlg",missionNamespace];
        uiNamespace setVariable ["ACME_laryngo_patient",_patient];
        uiNamespace setVariable ["ACME_laryngo_medic",_medic];
        _patient setVariable ["ACM_airway_AirwayReflex_State",true];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",4];
        _patient setVariable ["ACME_laryngo_gagMisses",4];
    '''+clinical_function('setAirwayState','airway')+function('laryngoFluidState')+function('laryngoReflexChance')+function('laryngoConsequenceLocal')+function('laryngoConsequence')+function('laryngoPassTube')+'''
        ACME_fnc_ownerDispatch={params ["_p","_command","_payload"];_dispatches pushBack _this;
            if (_patientLocal && {_command=="laryngoConsequence"}) then {_payload call ACME_fnc_laryngoConsequenceLocal;};};
    '''


BLOCKERS={
    'dead':'_patientAlive=false;',
    'arrest':'_patient setVariable ["ace_medical_inCardiacArrest",true];',
    'paralyzed':'_patient setVariable ["ACME_roc_paralyzed",true];',
    'absent_reflex':'_patient setVariable ["ACM_airway_AirwayReflex_State",false];',
}


@pytest.mark.parametrize('reason',['awakeTube','tubeManip'])
@pytest.mark.parametrize('blocker',list(BLOCKERS))
def test_explicit_tube_events_recheck_owner_live_reflex_exclusions(reason,blocker):
    execute(setup()+BLOCKERS[blocker]+f'[_patient,_medic,1,"event","{reason}"] call ACME_fnc_laryngoConsequenceLocal;'+'''
        [(_patient getVariable ["ACM_airway_AirwayObstructionVomit_State",0])==0,"excluded reflex created emesis"] call _check;
        [(_patient getVariable ["ACM_airway_AirwayObstructionVomit_Count",0])==4,"excluded reflex consumed stomach contents"] call _check;
        [count _sounds==0 && {_dislodges==0},"excluded reflex made gag sound or ejected OPA"] call _check;
        [isNil {_patient getVariable "ACME_laryngo_pool"},"excluded reflex manufactured pool"] call _check;
        [isNil {_patient getVariable "ACME_laryngo_irritationUntil"},"excluded event started irritation"] call _check;
    ''')


@pytest.mark.parametrize('reason',['awakeTube','tubeManip'])
def test_valid_explicit_gag_remains_one_finite_owner_event_without_a_second_roll(reason):
    execute(setup()+f'[_patient,_medic,1,"event","{reason}"] call ACME_fnc_laryngoConsequenceLocal;'+'''
        private _after=[_patient] call ACME_fnc_laryngoFluidState;
        [(_after select 1)=="v" && {(_after select 2)>0},"valid gag no longer creates finite emesis"] call _check;
        [(_patient getVariable ["ACM_airway_AirwayObstructionVomit_Count",0])==3,"event did not consume once"] call _check;
    '''+f'[_patient,_medic,1,"event","{reason}"] call ACME_fnc_laryngoConsequenceLocal;'+'''
        [([_patient] call ACME_fnc_laryngoFluidState) isEqualTo _after,"duplicate event changed fluid"] call _check;
        [_sounds isEqualTo ["wet"] && {_dislodges==1},"duplicate event repeated reflex"] call _check;
    ''')


@pytest.mark.parametrize('reason',['awakeTube','tubeManip'])
def test_existing_drug_owned_reflex_model_is_not_replaced_with_blanket_sedation_immunity(reason):
    execute(setup()+'''
        _effects=[1,0,0,0,1,1];
        _patient setVariable ["ACME_ket_sedated",true];
        _patient setVariable ["ACM_airway_AirwayReflex_State",false];
        [([_patient] call ACME_fnc_laryngoReflexChance)>0,"existing drug-owned reflex disappeared"] call _check;
    '''+f'[_patient,_medic,1,"event","{reason}"] call ACME_fnc_laryngoConsequenceLocal;'+'''
        [_sounds isEqualTo ["wet"],"positive explicit reflex was sampled a second time or suppressed"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_alive=false;', '_distance=6;',
])
def test_stale_or_invalid_provider_events_cannot_consume_or_create_receipts(change):
    execute(setup()+change+'''
        [_patient,_medic,1,"event","awakeTube"] call ACME_fnc_laryngoConsequenceLocal;
        [count _sounds==0 && {_dislodges==0},"invalid event produced reflex"] call _check;
        [(_patient getVariable ["ACME_laryngoEventReceipts",[]]) isEqualTo [],"invalid event created receipt"] call _check;
    ''')


def test_remote_consequence_is_forwarded_without_local_clinical_mutation():
    execute(setup()+'''
        _patientLocal=false;
        [_patient,_medic,1,"event","awakeTube"] call ACME_fnc_laryngoConsequenceLocal;
        [count _dispatches==1 && {count _sounds==0},"remote event mutated locally or was not routed"] call _check;
        [(_patient getVariable ["ACME_laryngoEventReceipts",[]]) isEqualTo [],"nonowner committed receipt"] call _check;
    ''')


@pytest.mark.parametrize('blocker',list(BLOCKERS))
def test_passage_respects_live_reflex_exclusions_without_hiding_postmortem_interaction(blocker):
    execute(setup()+BLOCKERS[blocker]+'''
        call ACME_fnc_laryngoPassTube;
        [uiNamespace getVariable ["ACME_laryngo_tubePassed",false],"hard reflex exclusion incorrectly rejected tube interaction"] call _check;
        [count _ejections==0 && {count _sounds==0},"excluded patient gagged or bucked tube"] call _check;
        [_tubeDebits==1 && {count _placements>0},"legitimate tube placement not retained"] call _check;
        [(_patient getVariable ["ACME_laryngo_gagMisses",-1])==0,"successful passage did not reset miss streak"] call _check;
    ''')


@pytest.mark.parametrize('existing',[True,False])
def test_sedated_success_resets_streak_and_passage_is_idempotent(existing):
    execute(setup()+f'_patient setVariable ["ACME_ETT_Inserted",{str(existing).lower()}];'+'''
        _effects=[0,1,0,0,1,1];_draw=0.99;
        uiNamespace setVariable ["ACME_laryngo_cuffDone",true];
        call ACME_fnc_laryngoPassTube;
        private _placementCount=count _placements;
        call ACME_fnc_laryngoPassTube;
        [count _dispatches==1 && {count _placements==_placementCount},"duplicate passage created another transaction"] call _check;
        [(_patient getVariable ["ACME_laryngo_gagMisses",-1])==0,"success did not reset misses"] call _check;
        [(_patient getVariable ["ACME_laryngo_missTolerance",-1])==5,"success did not reset tolerance"] call _check;
        [_cuffFinishes==1 && {count _ejections==0},"preinflated cuff handoff repeated or ejected"] call _check;
    '''+f'[_tubeDebits=={int(not existing)},"existing or duplicate tube consumed another item"] call _check;')


def test_unsedated_reactive_passage_retains_existing_buck_and_cuff_order():
    execute(setup()+'''
        _draw=0.99;
        uiNamespace setVariable ["ACME_laryngo_cuffDone",true];
        call ACME_fnc_laryngoPassTube;
        [_tubeDebits==1 && {count _ejections==1} && {_cuffFinishes==0},"unsedated response or cuff order changed"] call _check;
        [_sounds isEqualTo ["wet"],"real unsedated event lost its owner reflex"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    'uiNamespace setVariable ["ACME_laryngo_dlg",profileNamespace];',
    'uiNamespace setVariable ["ACME_laryngo_patient",missionNamespace];',
    'uiNamespace setVariable ["ACME_laryngo_dlg",objNull];',
])
def test_abort_callback_cannot_reset_a_different_patient_or_reopened_display(change):
    execute(setup()+function('laryngoAbort')+'''
        ACME_fnc_laryngoFail={};
        ["trauma"] call ACME_fnc_laryngoAbort;
        [count _waits==1,"abort callback missing"] call _check;
    '''+change+'''
        uiNamespace setVariable ["ACME_laryngo_lift",0.75];
        uiNamespace setVariable ["ACME_laryngo_state","new-session"];
        private _job=_waits select 0;(_job select 1) call (_job select 0);
        [(uiNamespace getVariable "ACME_laryngo_lift")==0.75 && {(uiNamespace getVariable "ACME_laryngo_state")=="new-session"},"old callback changed new session"] call _check;
    ''')


@pytest.mark.parametrize('held',['scope','tube'])
def test_valid_abort_resets_once_without_consuming_or_putting_away_the_scope(held):
    execute(setup()+function('laryngoAbort')+'''
        private _fails=0;ACME_fnc_laryngoFail={_fails=_fails+1;};
    '''+f'uiNamespace setVariable ["ACME_laryngo_held","{held}"];'+'''
        uiNamespace setVariable ["ACME_laryngo_lift",1];
        ["trauma"] call ACME_fnc_laryngoAbort;["trauma"] call ACME_fnc_laryngoAbort;
        [count _waits==1 && {_fails==1},"repeated abort scheduled multiple resets"] call _check;
        private _job=_waits select 0;(_job select 1) call (_job select 0);
        [!(uiNamespace getVariable ["ACME_laryngo_done",true]) && {(uiNamespace getVariable "ACME_laryngo_lift")==0},"valid abort did not release attempt"] call _check;
        [_tubeDebits==0 && {count _placements==0},"abort consumed tube or changed clinical placement"] call _check;
    '''+f'[(uiNamespace getVariable "ACME_laryngo_held")=="{"scope" if held=="scope" else ""}","abort put scope away or left tube in hand"] call _check;')


@pytest.mark.parametrize('opening',[-0.5,0,0.1,0.25,1/3,0.5,2/3,0.85,1,1.5])
def test_tongue_frames_are_complementary_adjacent_crossfade_not_opaque_stacking(opening):
    execute(setup()+function('laryngoFrames')+f'[missionNamespace,{opening}] call ACME_fnc_laryngoFrames;'+'''
        private _alpha=[87801,87851,87852,87853] apply {(_controlValues get ((str _x)+":ctrlSetTextColor")) select 3};
        private _sum=0;{_sum=_sum+_x;} forEach _alpha;
        [abs (_sum-1)<0.000001,"tongue frames do not sum to one opacity"] call _check;
        private _active=[];{if (_x>0) then {_active pushBack _forEachIndex;};} forEach _alpha;
        [count _active>=1 && {count _active<=2},"more than two tongue frames active"] call _check;
        if (count _active==2) then {[(_active select 1)==(_active select 0)+1,"nonadjacent tongue frames blended"] call _check;};
    ''')


@pytest.mark.parametrize('selection',[0,1])
@pytest.mark.parametrize('inserted',[True,False])
@pytest.mark.parametrize('alive',[True,False])
def test_airway_device_rows_do_not_disclose_unassessed_patency(selection,inserted,alive):
    text=source('airwayInjuryRelabel')
    for key,value in [('NPA','NPA'),('OPA','OPA'),('IGel','iGel')]:
        text=text.replace('localize "STR_ACM_Airway_'+key+'"','"'+value+'"')
    execute(setup()+'private _relabel={'+code(text)+'};'+f'_patientAlive={str(alive).lower()}; _patient setVariable ["ACME_ETT_Inserted",{str(inserted).lower()}];'+'''
        private _rows=[["NPA",[1,1,1,1]],["OPA",[1,1,1,1]],["iGel",[1,1,1,1]],["Other finding",[1,0,0,1]]];
        private _initial=+_rows;
    '''+f'[objNull,_patient,{selection},_rows] call _relabel;[objNull,_patient,{selection},_rows] call _relabel;'+
        f'[count _rows=={5 if inserted and selection==0 else 4},"device row duplicated or appeared off-head"] call _check;'+'''
        [(_rows select [0,4]) isEqualTo _initial,"existing finding or device labels changed"] call _check;
        [(_rows findIf {((toLower (_x select 0)) find "patent")>=0})<0,"device row disclosed unassessed patency"] call _check;
    ''')
