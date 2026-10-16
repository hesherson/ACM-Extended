"""B216 ordinary chest seals: execute owner receipts and per-panel quick-view logging.

Arma objects, clocks, networking, lung update and PTX relief are fixtures. Production
request validation, receipt retention, log dedupe, seal removal and surgical drainage run.
"""
import pytest
from test_b212_pleural_drainage_execution import drain_setup, execute
from test_historical_cardiac_execution import function


def ordinary_setup():
    return drain_setup()+function('chestSealBurp',extended=True)+function('chestSealLogOnce',extended=True)+function('chestSealEffectLocal',extended=True)+'''
        uiNamespace setVariable ["ACME_CS_SessionToken","panel-1"];
        _patient setVariable ["ACME_CS_ProcedureTokens",["panel-1"]];
        _patient setVariable ["ACM_breathing_ChestSeal_State",true];
        _patient setVariable ["ACME_CS_holeData",[[0,0,0,0,true],[0,0,0,0,true]]];
        private _noBloodChange={
            [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==1.1,"ordinary seal drained pleural blood"] call _check;
            [(_patient getVariable "ACM_breathing_Hemothorax_State")==8,"ordinary seal healed bleeding"] call _check;
            [(_patient getVariable "ACM_breathing_Hemothorax_PFH")==44,"ordinary seal stopped hemorrhage worker"] call _check;
            [count _events==0,"ordinary seal displayed a blood drainage popup"] call _check;
        };
    '''


def test_repeated_opposite_side_burps_treat_each_lift_but_log_one_quick_view_per_panel():
    execute(ordinary_setup()+'''
        {[_medic,_patient,"body",1,[7,_x,100],"panel-1"] call ACME_fnc_chestSealBurp;} forEach [1,2,3];
        [count _effects==3,"repeated burps stopped treating air pressure"] call _check;
        [count _logs==1 && {((_logs select 0) select 1)=="quick_view"},"ordinary burp spammed activity or quick view"] call _check;
        [((_logs select 0) select 2)=="Burped chest seal","quick-view message changed"] call _check;
        call _noBloodChange;
    ''')


def test_close_reopen_allows_one_new_log_and_rejects_old_session_inputs():
    execute(ordinary_setup()+'''
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        _patient setVariable ["ACME_CS_ProcedureTokens",[]];
        [_medic,_patient,"body",1,[7,2,100],"panel-1"] call ACME_fnc_chestSealBurp;
        _patient setVariable ["ACME_CS_ProcedureTokens",["panel-2"]];
        [count _logs==1 && {count _effects==1},"closed panel emitted a burp"] call _check;
        [_medic,_patient,"body",1,[7,3,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [_medic,_patient,"body",1,[7,4,100],"panel-2"] call ACME_fnc_chestSealBurp;
        [_medic,_patient,"body",1,[7,5,100],"panel-2"] call ACME_fnc_chestSealBurp;
        [count _logs==2 && {count _effects==3},"reopened panel dedupe incorrect"] call _check;
        call _noBloodChange;
    ''')


def test_simultaneous_viewers_each_get_one_entry_without_replacing_other_receipt():
    execute(ordinary_setup()+'''
        _patient setVariable ["ACME_CS_ProcedureTokens",["panel-1","panel-2"]];
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [missionNamespace,_patient,"body",1,[8,1,100],"panel-2"] call ACME_fnc_chestSealBurp;
        [_medic,_patient,"body",1,[7,2,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [missionNamespace,_patient,"body",1,[8,2,100],"panel-2"] call ACME_fnc_chestSealBurp;
        [count _logs==2 && {count _effects==4},"concurrent viewers erased each other receipt"] call _check;
    ''')


def test_owner_handoff_keeps_receipts_and_remote_packet_carries_panel_identity():
    execute(ordinary_setup()+'''
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        _patientLocal=false;
        [_medic,_patient] call ACME_fnc_chestSealBurp;
        [count _logs==1 && {count _effects==1},"non-owner emitted physiology or log"] call _check;
        private _forward=((_events select 0) select 1) select 2;
        [(_forward select 5)=="panel-1","session identity lost across locality"] call _check;
        _events=[]; _patientLocal=true;
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [_medic,_patient,"body",1,[7,2,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [count _logs==1 && {count _effects==2},"handoff replay duplicated log or effect"] call _check;
        call _noBloodChange;
    ''')


@pytest.mark.parametrize('receipt',['[]','[7,1]','[7,1,100,0]','[7,"bad",100]','[-1,1,100]','[7.5,1,100]','[7,0,100]','[7,1.5,100]','[7,1,84]','[7,1,103]'])
def test_invalid_receipts_do_not_treat_or_log(receipt):
    execute(ordinary_setup()+f'''
        [_medic,_patient,"body",1,{receipt},"panel-1"] call ACME_fnc_chestSealBurp;
        [count _effects==0 && {{count _logs==0}},"invalid receipt accepted"] call _check;
        call _noBloodChange;
    ''')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_CS_ProcedureTokens",[]];',
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];', '_distance=6;',
    '_patient setVariable ["ACM_breathing_ChestSeal_State",false]; _patient setVariable ["ACME_CS_holeData",[]];',
])
def test_invalid_provider_patient_or_session_does_not_treat_or_log(change):
    execute(ordinary_setup()+change+'''
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [count _effects==0 && {count _logs==0},"invalid clinical input accepted"] call _check;
        call _noBloodChange;
    ''')


def test_old_reordered_receipts_rejected_and_fresh_reconnected_origin_accepted():
    execute(ordinary_setup()+'''
        [_medic,_patient,"body",1,[7,200,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [_medic,_patient,"body",1,[7,199,100],"panel-1"] call ACME_fnc_chestSealBurp;
        serverTime=116;
        [_medic,_patient,"body",1,[7,200,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [_medic,_patient,"body",1,[7,1,116],"panel-1"] call ACME_fnc_chestSealBurp;
        [count _effects==2 && {count _logs==1},"receipt expiry/reconnection fence wrong"] call _check;
        call _noBloodChange;
    ''')


@pytest.mark.parametrize('sealed_remaining',[False,True])
def test_ordinary_peel_never_drains_even_with_a_sealed_thoracostomy_elsewhere(sealed_remaining):
    execute(ordinary_setup()+f'''
        _patient setVariable ["ACME_thora_open_left","sealed"];
        _patient setVariable ["ACME_thora_sealed_left",true];
        ACME_fnc_chestSealLogOnce={{_logs pushBack _this;true}};
        [_patient,_medic,"peel",[{str(sealed_remaining).lower()}],"owner-epoch",100,1] call ACME_fnc_chestSealEffectLocal;
        [count _effects==1 && {{((_effects select 0) select 1)=="peel"}},"peel air-seal update missing"] call _check;
        [_patient getVariable "ACME_thora_sealed_left","ordinary peel removed surgical seal"] call _check;
        call _noBloodChange;
    ''')


@pytest.mark.parametrize('pressure,drained',[(0,0.3),(0.8,0.48),(1,0.6)])
def test_only_surgical_seal_drains_and_reports_pressure_scaled_blood(pressure,drained):
    execute(drain_setup()+f'''
        _patient setVariable ["ACME_thora_open_left","sealed"];
        _patient setVariable ["ACME_thora_sealed_left",true];
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.6];
        _patient setVariable ["ACME_ptx_state",[1,3,0.8,0,{pressure},0,1,3,0.5]];
        [_patient,_medic,"left","burp",1,[7,1,100]] call ACME_fnc_thoraAftercareLocal;
        [abs ((_patient getVariable "ACM_breathing_Hemothorax_Fluid")-(0.6-{drained}))<0.000001,"surgical drainage changed"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_State")==8,"surgical drainage cured hemorrhage"] call _check;
        [count _events==1 && {{count _effects==1}},"surgical drainage popup or pressure relief lost"] call _check;
        [((((_events select 0) select 1) select 0) select 2)==(round ({drained}*10000))/10,"surgical popup volume wrong"] call _check;
    ''')
