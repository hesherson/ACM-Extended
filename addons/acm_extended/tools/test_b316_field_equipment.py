"""Exercise the Tempus clock, sensor actions and the new training cases."""
import re

import pytest

from test_b216_spawner import apply_setup, catalog
from test_menu_death_lifecycle import ROOT, adapt, execute

TEMPUS = ROOT / "addons/acme_tempus/functions"
EQUIP = ROOT / "addons/acme_equipment/functions"


@pytest.mark.parametrize("rhythm", [0, 100])
def test_next_reserved_beat_survives_rate_change_and_packet_boundary(rhythm):
    execute("private _plan={" + (TEMPUS / "fn_tempusBeatPlan.sqf").read_text() + "};" + f'''
        private _first = [0,1.2,60/93,{rhythm},[]] call _plan;
        private _last = (_first select 1) select (count (_first select 1)-1);
        private _next = [1.2,2.4,60/131,{rhythm},_first select 0] call _plan;
        [_last in (_next select 1),"next R wave changed across packet boundary"] call _check;
        private _beats = _next select 1;
        for "_i" from 1 to (count _beats-1) do {{
            [(_beats select _i select 0) > (_beats select (_i-1) select 0),"duplicate/reversed R wave"] call _check;
        }};
    ''')


def test_all_leads_project_shared_samples_and_preserve_limb_relations():
    execute("private _project={" + (TEMPUS / "fn_tempusProjectLead.sqf").read_text() + "};" + '''
        private _samples = [-5,-40,25,10,-7,0];
        private _phases = [-3,0,1,2,5,99];
        private _leads = ["I","II","III","AVR","AVL","AVF","V1","V2","V3","V4","V5","V6"];
        private _traces = _leads apply {[_x,_samples,_phases] call _project};
        [{count _x==6} count _traces==12,"a lead lost samples"] call _check;
        [abs ((_traces select 0 select 1)+(_traces select 2 select 1)+40)<0.11,"I + III must equal II"] call _check;
        [(_traces select 6 select 2) > abs (_traces select 6 select 1),"V1 lacked deep S"] call _check;
        [abs (_traces select 10 select 1) > (_traces select 10 select 2),"V5 lacked dominant R"] call _check;
        [(_traces select 3 select 1)>0,"aVR misplaced polarity"] call _check;
    ''')


@pytest.mark.parametrize("case,expected", [
    ("ocular_dust", '[1,1],3'), ("ocular_right", '[0,1],0'), ("ocular_bilateral", '[0,0],0')
])
def test_eye_cases_enter_native_ophthalmology(case, expected):
    eyes,dust = expected.rsplit(",",1)
    execute(apply_setup()+f'''
        ACM_ophthalmology_fnc_reconcile={{_calls pushBack ["eyeWorker",_this];}};
        [_patient,["{case}"] call ACM_mission_fnc_patientPreset,missionNamespace] call _apply;
        [(_patient getVariable ["ACM_ophthalmology_eyeInjuries",[]]) isEqualTo {eyes},"wrong eye damage"] call _check;
        [(_patient getVariable ["ACM_ophthalmology_dustInjuryHeavy",-1]) == {dust},"wrong irrigation burden"] call _check;
        [(_calls select 1 select 0) == "eyeWorker","eye case bypassed native worker"] call _check;
    ''')


@pytest.mark.parametrize("case,stage", [("local_infection",1),("systemic_infection",2),("sepsis",3)])
def test_infection_cases_seed_native_stage_and_enroll(case, stage):
    execute(apply_setup()+f'''
        ACM_infection_fnc_applyInfectionStage={{_calls pushBack ["stage",_this];}};
        ACM_infection_fnc_reconcile={{_calls pushBack ["worker",_this];}};
        [_patient,["{case}"] call ACM_mission_fnc_patientPreset,missionNamespace] call _apply;
        [(_calls select 1) isEqualTo ["stage",[_patient,{stage}]],"wrong infection stage"] call _check;
        [(_calls select 2 select 0) == "worker","infection worker not enrolled"] call _check;
    ''')


def test_inhalation_case_seeds_native_wounds_and_edema():
    execute(apply_setup()+'''
        CBA_fnc_localEvent={_calls pushBack _this;};
        [_patient,["burn_airway"] call ACM_mission_fnc_patientPreset,missionNamespace] call _apply;
        [_patient getVariable ["ACM_burns_AirwayBurned",false],"inhalation injury was randomized away"] call _check;
        [(_patient getVariable ["ACM_burns_AirwayInflammation",0]) > 10,"edema not seeded"] call _check;
        [(_calls select 1 select 1 select 2) == "Burn3","head wound missed native burn intake"] call _check;
    ''')


def test_disabling_new_injury_systems_does_not_replace_presets_with_random_wounds():
    execute(catalog()+'''
        missionNamespace setVariable ["ACM_burns_burnsEnabled",false];
        missionNamespace setVariable ["ACM_ophthalmology_enable",false];
        missionNamespace setVariable ["ACM_infection_infectionEnabled",false];
        {[( [_x] call ACM_mission_fnc_patientPreset) isEqualTo [],"disabled case still available"] call _check;}
            forEach ["burn_airway","ocular_dust","sepsis"];
        [["tension_ptx"] call ACM_mission_fnc_patientPreset isNotEqualTo [],"unrelated case removed"] call _check;
    ''')


def monitor_source():
    text=(EQUIP / "fn_equipmentMonitorAction.sqf").read_text()
    text=text.replace('_medic distance _patient','_distance').replace('_device distance _medic','_distance')
    text=text.replace('_device distance _patient','_distance')
    text=text.replace('isRemoteExecuted','_remote').replace('remoteExecutedOwner','_sender').replace('owner _medic','7')
    text=text.replace('isNull objectParent _patient','true').replace('isNull objectParent _medic','true')
    text=text.replace('isObjectHidden _device','false').replace('_device isKindOf _class','true')
    text=text.replace('_medic isKindOf "CAManBase"','true').replace('_patient isKindOf "CAManBase"','true')
    text=re.sub(r'\[[^;]+?\] remoteExecCall \["ACME_fnc_[A-Za-z]+",2\]', '_calls pushBack _action',text)
    return adapt(text)


def test_sensor_actions_authenticate_and_commit_expected_state_once():
    execute('''
        private _device=missionNamespace;private _calls=[];private _remote=true;private _sender=8;
        _device setVariable ["acme_tempus_pat",_patient];
        _patient setVariable ["ACME_eq_pro",_device];
        ACME_fnc_tempusUse={};ACME_fnc_tempusLsUse={};
        private _actionFn={'''+monitor_source()+'''};
        [!([_medic,_patient,"pro",[1,true],true] call _actionFn),"wrong actor attached sensor"] call _check;
        _sender=7;
        [[_medic,_patient,"pro",[1,true],true] call _actionFn,"patient action failed"] call _check;
        [!([_medic,_patient,"pro",[1,true],true] call _actionFn),"duplicate inverted state"] call _check;
        [(_device getVariable "acme_tempus_sensors") isEqualTo [true,true,false,false,false],"wrong flag changed"] call _check;
        _patient setVariable ["ACME_persistenceFrozen",true];
        [!([_medic,_patient,"pro",[1,false],true] call _actionFn),"sensor changed during checkpoint"] call _check;
    ''')
