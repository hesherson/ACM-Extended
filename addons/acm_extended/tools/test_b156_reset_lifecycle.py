"""Real SQF lifecycle tests; engine objects and CBA scheduling are controlled boundaries."""
import re
import pytest
from test_menu_death_lifecycle import ROOT, F, adapt, execute
from test_historical_cardiac_execution import code as engine_code


def native(component, name):
    s = (ROOT / 'addons' / component / 'functions' / ('fnc_' + name + '.sqf')).read_text()
    s = s.replace('IS_UNCONSCIOUS(_patient)', '(_patient getVariable ["ACE_isUnconscious",false])')
    s = s.replace('GET_PAIN(_patient)', '(_patient getVariable ["ace_medical_pain",0])')
    s = s.replace('GET_HEART_RATE(_patient)', '80')
    s = s.replace('GET_BODYPART_DAMAGE(_patient)', '[2,0,0,0,0,0]')
    s = s.replace('owner _patient', '_ownerNum').replace('clientOwner', '_ownerNum')
    s = s.replace('serverTime', 'CBA_missionTime').replace(', _syncValues]', ']')
    s = engine_code(s, component)
    s = s.replace('true _patient', 'true')
    return s


def setup():
    return '''
        private _patientLocal = true;
        private _linear = {params ["_lo","_hi","_x","_a","_b",["_clamp",false]]; private _f=(_x-_lo)/(_hi-_lo); if (_clamp) then {_f=(_f max 0) min 1;}; _a+(_f*(_b-_a))};
        ACME_fnc_clinicalEpoch = {(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACM_damage_fnc_isBodyPartBleeding = {true};
        ACM_damage_fnc_getBodyPartBleeding = {1};
        ACM_circulation_fnc_getNauseaMedicationEffects = {2};
        ace_medical_fnc_adjustPainLevel = {params ["_p","_n"]; _p setVariable ["ace_medical_pain",_n];};
        private _deliver = {private _entry = _waits select _this; (_entry select 1) call (_entry select 0);};
        private _run = {private _h = _handlers select _this; [_h select 1,_this] call (_h select 0);};
        _patient setVariable ["ACE_isUnconscious",true];
        ACM_airway_enable = true;
        ACM_airway_airwayCollapseChance = 100;
        ACM_airway_airwayObstructionBloodChance = 100;
        ACM_airway_airwayObstructionVomitChance = 100;
    '''


def test_old_airway_delays_do_not_reenter_after_heal_and_new_unconscious_episode():
    execute(setup()+'ACM_airway_fnc_handleAirway = {'+native('airway','handleAirway')+'}; private _start=ACM_airway_fnc_handleAirway;'+'''
        CBA_fnc_targetEvent = {if ((_this select 0) == "ACM_airway_handleAirway") then {(_this select 1) call ACM_airway_fnc_handleAirway;} else {_events pushBack _this;};};
        [_patient] call _start;
        [count _waits == 3,"airway callback setup missing"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ACM_airway_AirwayReflex_State",true];
        for "_i" from 0 to 2 do {_i call _deliver;};
        [_patient getVariable ["ACM_airway_AirwayReflex_State",false],"old reflex loss affected healed episode"] call _check;
        [count _events == 0,"old airway delay scheduled a new-episode injury"] call _check;
        [_patient] call _start;
        for "_i" from 3 to 5 do {_i call _deliver;};
        [!(_patient getVariable ["ACM_airway_AirwayReflex_State",true]),"fresh reflex loss was suppressed"] call _check;
        [count _events == 3,"fresh airway episode lost native events"] call _check;
    ''')


@pytest.mark.parametrize('name,field,state',[
    ('handleAirwayCollapse','AirwayCollapse_PFH','AirwayCollapse_State'),
    ('handleAirwayObstruction_Blood','AirwayObstructionBlood_PFH','AirwayObstructionBlood_State'),
])
def test_old_airway_worker_cannot_mutate_or_release_replacement(name,field,state):
    execute(setup()+'private _start = {'+native('airway',name)+'};'+f'''
        [_patient] call _start;
        [count _handlers == 1,"initial worker missing"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ACM_airway_{field}",-1];
        _patient setVariable ["ACM_airway_{state}",0];
        [_patient] call _start;
        [count _handlers == 2,"replacement worker missing"] call _check;
        0 call _run;
        [(_patient getVariable ["ACM_airway_{state}",-1]) == 0,"stale worker injured new episode"] call _check;
        [(_patient getVariable ["ACM_airway_{field}",-1]) == 1,"stale worker cleared replacement handle"] call _check;
        1 call _run;
        [(_patient getVariable ["ACM_airway_{state}",0]) == 1,"fresh worker stopped native progression"] call _check;
    ''')


def test_hemolysis_delay_cannot_recreate_severity_after_full_heal():
    execute(setup()+'ACM_circulation_fnc_handleHemolyticReaction = {'+native('circulation','handleHemolyticReaction')+'}; private _start=ACM_circulation_fnc_handleHemolyticReaction;'+'''
        [_patient] call _start;
        [count _waits == 1,"initial onset missing"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ACM_circulation_HemolyticReaction_Severity",0];
        0 call _deliver;
        [(_patient getVariable ["ACM_circulation_HemolyticReaction_Severity",-1]) == 0,"old reaction onset resurrected severity"] call _check;
        [count _handlers == 0,"old reaction onset created worker"] call _check;
    ''')


def test_old_mercy_callback_cannot_restore_obtundation_after_heal():
    s=(F/'fn_consciousnessBudget.sqf').read_text()
    s=s.replace('allUnits select {local _x && {alive _x} && {isPlayer _x}}','[_patient]')
    s=s.replace('local _p','_localPatient').replace('owner _p','_ownerNum').replace('owner _u','_ownerNum')
    execute(setup()+'''
        private _localPatient = true; private _obtunded = [];
        missionNamespace setVariable ["ACME_sys_obtunded",true];
        missionNamespace setVariable ["ACME_ko_mercySeconds",0];
        ACME_fnc_setVarNet = {params ["_p","_key","_value"]; _p setVariable [_key,_value];};
        ACM_core_fnc_canWake = {true};
        ACM_core_fnc_requestWake = {(_this select 0) setVariable ["ACE_isUnconscious",false];true};
        ACME_fnc_obtundedSet = {_obtunded pushBack _this;};
    '''+'private _budget = {'+adapt(s)+'};'+'''
        call _budget;
        [count _waits == 1,"mercy callback missing"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",1];
        0 call _deliver;
        [count _obtunded == 0,"mercy callback restored obtundation after full heal"] call _check;
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_ko_holdUntil",0];
        call _budget; 1 call _deliver;
        [count _obtunded == 1,"fresh eligible mercy callback no longer works"] call _check;
    ''')


def reset_setup():
    s=(F/'fn_clinicalReset.sqf').read_text().split('// Physical equipment is detached',1)[0]
    return setup()+'''
        ACME_fnc_headElevHoldClear = {};
        ACME_fnc_aajtDownedStop = {};
        ACME_fnc_ventDeviceFields = {["ACME_vent_batt","ACME_vent_o2"]};
        ACM_breathing_fnc_setRuntimeState = {};
        ACM_circulation_fnc_setRuntimeState = {};
        ACM_airway_fnc_setAirwayState = {};
        ACME_fnc_seizureMotion = {};
    '''+'ACME_fnc_clinicalReset = {'+adapt(s)+'};'+'ACME_fnc_deadPhysiologyFreeze = {'+adapt((F/'fn_deadPhysiologyFreeze.sqf').read_text())+'};'


@pytest.mark.parametrize('death',[False,True])
def test_real_reset_begin_retires_workers_without_erasing_custody_or_corpse_evidence(death):
    transition = ('_patientAlive = false; [_patient] call _death;' if death else '[_patient,"begin"] call ACME_fnc_clinicalReset;')
    execute(reset_setup()+'private _death = {'+adapt((F/'fn_deathFreeze.sqf').read_text())+'};'+'''
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_operator",_medic];
        _patient setVariable ["ACME_vent_batt",71];
        _patient setVariable ["ACME_vent_custodyId","original-device"];
        _patient setVariable ["ACME_Junc_leftleg","xstat"];
        _patient setVariable ["ACME_ETT_Inserted",true];
        _patient setVariable ["ACM_airway_AirwayCollapse_State",2];
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",3];
        _medic setVariable ["inventory",["reusable-equipment"]];
        {private _id=[{},1,[]] call CBA_fnc_addPerFrameHandler; _patient setVariable [_x,_id];}
            forEach ["ACM_airway_AirwayCollapse_PFH","ACM_airway_AirwayObstructionBlood_PFH","ACM_circulation_HemolyticReaction_PFH"];
        {missionNamespace setVariable [_x,[_patient,_medic]];} forEach ["ACME_clinical_activePatients","ACME_coag_activePatients"];
    '''+transition+'''
        [([_patient] call ACME_fnc_clinicalEpoch)==1,"reset did not advance episode"] call _check;
        [(_handlers findIf {_x select 2}) < 0,"reset left native worker alive"] call _check;
        [(_patient getVariable ["ACME_vent_batt",-1])==71 && {(_patient getVariable ["ACME_vent_custodyId",""])=="original-device"},"reset consumed reusable device"] call _check;
        [(_medic getVariable ["inventory",[]]) isEqualTo ["reusable-equipment"],"reset rewrote provider inventory"] call _check;
        [(_patient getVariable ["ACME_Junc_leftleg",""])=="xstat" && {_patient getVariable ["ACME_ETT_Inserted",false]},"begin/death removed interventions"] call _check;
        [(_patient getVariable ["ACM_airway_AirwayCollapse_State",0])==2 && {(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",0])==3},"begin/death erased airway evidence"] call _check;
        [!( _patient in (missionNamespace getVariable ["ACME_coag_activePatients",[]])),"reset retained coagulation membership"] call _check;
    ''')


def test_old_hemolysis_worker_cannot_write_after_owner_replacement():
    execute(setup()+'ACM_circulation_fnc_handleHemolyticReaction = {'+native('circulation','handleHemolyticReaction')+'};'+'''
        [_patient,true] call ACM_circulation_fnc_handleHemolyticReaction;
        _patientLocal = false; 0 call _run;
        [!((_handlers select 0) select 2),"departed owner worker kept running"] call _check;
        _patientLocal = true; _ownerNum = 8;
        _patient setVariable ["ACM_circulation_HemolyticReaction_PFH",-1];
        _patient setVariable ["ACM_circulation_HemolyticReaction_Severity",5];
        [_patient,true] call ACM_circulation_fnc_handleHemolyticReaction;
        [(_patient getVariable ["ACM_circulation_HemolyticReaction_Severity",0])==5,"migration restarted reaction severity"] call _check;
        0 call _run;
        [(_patient getVariable ["ACM_circulation_HemolyticReaction_Severity",0])==5 && {(_patient getVariable ["ACM_circulation_HemolyticReaction_PFH",-1])==1},"old worker altered resumed reaction"] call _check;
        _patient setVariable ["ACM_circulation_HemolyticReaction_Volume",1];
        1 call _run;
        [(_patient getVariable ["ACM_circulation_HemolyticReaction_Severity",0])==10,"resumed reaction no longer progresses"] call _check;
    ''')


def test_native_delayed_effect_rechecks_epoch_on_recipient_after_transport_delay():
    execute(setup()+'ACM_airway_fnc_handleAirway = {'+native('airway','handleAirway')+'};'+'''
        [_patient] call ACM_airway_fnc_handleAirway;
        0 call _deliver;
        [count _events==1,"reflex delivery missing"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ACM_airway_AirwayReflex_State",true];
        ((_events select 0) select 1) call ACM_airway_fnc_handleAirway;
        [_patient getVariable ["ACM_airway_AirwayReflex_State",false],"queued old-owner delivery survived recipient reset"] call _check;
    ''')


def test_due_hemolysis_onset_moves_to_new_owner_without_a_second_delay():
    execute(setup()+'ACM_circulation_fnc_handleHemolyticReaction = {'+native('circulation','handleHemolyticReaction')+'};'+'''
        [_patient] call ACM_circulation_fnc_handleHemolyticReaction;
        _patientLocal=false; 0 call _deliver;
        [count _events==1 && {count _handlers==0},"old owner committed delayed hemolysis"] call _check;
        _patientLocal=true; _ownerNum=8;
        ((_events select 0) select 1) call ACM_circulation_fnc_handleHemolyticReaction;
        [count _waits==1 && {count _handlers==1},"migration lost or restarted due onset delay"] call _check;
    ''')


def test_owner_register_resumes_each_native_worker_once_and_retains_severity():
    registration=(F/'fn_ownerRegister.sqf').read_text().split('// Resume only native physiology workers',1)[1].split('\n',1)[1].split('// Recovery is keyed',1)[0]
    execute(setup()+
        'ACM_airway_fnc_handleAirwayCollapse={'+native('airway','handleAirwayCollapse')+'};'+
        'ACM_airway_fnc_handleAirwayObstruction_Blood={'+native('airway','handleAirwayObstruction_Blood')+'};'+
        'ACM_circulation_fnc_handleHemolyticReaction={'+native('circulation','handleHemolyticReaction')+'};'+
        'private _register={'+adapt(registration)+'};'+'''
        call _register;
        [count _handlers==0,"registration invented native workers from no active flags"] call _check;
        {_patient setVariable [_x,true];} forEach ["ACME_nativeCollapseActive","ACME_nativeBloodObstructionActive","ACME_nativeHemolysisActive"];
        _patient setVariable ["ACM_circulation_HemolyticReaction_Severity",5];
        call _register; call _register;
        [count _handlers==3,"registration duplicated or lost active workers"] call _check;
        [(_patient getVariable ["ACM_circulation_HemolyticReaction_Severity",0])==5,"registration reset existing reaction severity"] call _check;
    ''')


def test_awake_airway_recovery_preserves_b125_collapse_clear():
    execute(setup()+'private _start={'+native('airway','handleAirwayCollapse')+'};'+'''
        _patient setVariable ["ACME_nativeCollapseActive",true];
        _patient setVariable ["ACM_airway_AirwayCollapse_State",2];
        _patient setVariable ["ACE_isUnconscious",false];
        [_patient] call _start;
        [count _handlers==0 && {(_patient getVariable ["ACM_airway_AirwayCollapse_State",-1])==0},"awake migrated collapse was retained"] call _check;
        [!(_patient getVariable ["ACME_nativeCollapseActive",true]),"awake collapse remained enrolled"] call _check;
    ''')
