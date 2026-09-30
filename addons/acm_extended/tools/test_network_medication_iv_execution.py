"""Execute actual medication queue cadence and native IV publication code.

CBA time, locality, and network delivery are recording stand-ins. These tests
exercise mass consumption and cache/timer decisions, not engine MP transport.
"""
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute as run_sqf
from test_historical_vial_execution import map_defaults

F = ROOT / "addons/acm_extended/functions"
C = ROOT / "addons/circulation/functions"


def execute(code):
    # This VM supports real HashMaps but not their defaulted-read command.
    preamble = 'private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};'
    run_sqf(preamble + map_defaults(code))


def adapted(source, component="circulation"):
    return adapt(source.replace("local _patient", "_patientLocal")
                 .replace("owner _patient", "_patientOwner")
                 .replace("finite _amount", "true"), component)


def queue_setup():
    source = "".join(
        f"ACME_fnc_{name}={{" + adapted((F / f"fn_{name}.sqf").read_text()) + "};"
        for name in ("medicationDriveAdd", "medicationDriveTick", "clinicalEpoch")
    )
    return source + r'''
        private _patientLocal=true; private _patientOwner=7;
        private _published=[];
        _patient setVariable ["ACME_clinicalEpoch",1];
        ACME_fnc_setVarNet={
            params ["_p","_key","_value"];
            if (_key=="ACME_medicationDriveQueue") then {_published pushBack [_nowTime,str _value];};
            _p setVariable [_key,_value]; true
        };
        ACME_fnc_setVarNetApprox={};
        ACME_fnc_deadPhysiologyFreeze={};
        missionNamespace setVariable ["ACME_driveIsInfusion",true];
        missionNamespace setVariable ["ACME_hcEff_medications",true];
        CBA_fnc_waitAndExecute={_waits pushBack [_this select 0,_this select 1,_nowTime+(_this select 2),false];};
        private _runDue={
            {
                if (!(_x select 3) && {(_x select 2)<=_nowTime}) then {
                    _x set [3,true]; (_x select 1) call (_x select 0);
                };
            } forEach (+_waits);
        };
    '''


def test_four_hz_infusion_chunks_share_one_second_budget_without_changing_delivered_rate():
    execute(queue_setup() + r'''
        for "_i" from 0 to 7 do {
            _nowTime=10+_i*.25;
            call _runDue;
            [_patient,"Norepinephrine_IV",1,.25] call ACME_fnc_medicationDriveAdd;
            private _rates=[_patient,.25] call ACME_fnc_medicationDriveTick;
            [abs ((_rates get "Norepinephrine")-240)<.000001,"cadence changed exact admitted rate"] call _check;
            [(_patient getVariable ["ACME_medicationDriveQueue",[]]) isEqualTo [],"sample consumed incorrectly"] call _check;
        };
        _nowTime=12; call _runDue;
        [count _published==3,"infusion add/completion bypassed one-second budget"] call _check;
        [(_published select 2 select 1)=="[]","final consumed queue stayed on wire"] call _check;
    ''')


def test_manual_bolus_addition_and_completion_bypass_infusion_budget():
    execute(queue_setup() + r'''
        [_patient,"Norepinephrine_IV",1,.25] call ACME_fnc_medicationDriveAdd;
        [_patient,.25] call ACME_fnc_medicationDriveTick;
        _nowTime=10.1;
        missionNamespace setVariable ["ACME_driveIsInfusion",false];
        [_patient,"Lidocaine_IV",10,.25] call ACME_fnc_medicationDriveAdd;
        [count _published==2,"new bolus delayed behind infusion budget"] call _check;
        _nowTime=10.35;
        private _rates=[_patient,.25] call ACME_fnc_medicationDriveTick;
        [count _published==3 && {(_published select 2 select 1)=="[]"},"bolus completion was not immediate"] call _check;
        [abs ((_rates get "Lidocaine")-2400)<.000001,"bolus mass changed"] call _check;
        _nowTime=11; call _runDue;
        [count _published==3,"superseded infusion timer republished after bolus"] call _check;
    ''')


def test_trailing_flush_reads_current_queue_and_does_not_replay_captured_sample():
    execute(queue_setup() + r'''
        [_patient,"Norepinephrine_IV",1,.25] call ACME_fnc_medicationDriveAdd;
        [_patient,.25] call ACME_fnc_medicationDriveTick;
        _nowTime=10.25;
        [_patient,"Norepinephrine_IV",2,3] call ACME_fnc_medicationDriveAdd;
        [count _published==1,"second infusion sample published too early"] call _check;
        _nowTime=11; call _runDue;
        [count _published==2,"trailing flush missing"] call _check;
        [(_published select 1 select 1)==str (_patient getVariable ["ACME_medicationDriveQueue",[]]),"timer sent captured stale queue"] call _check;
    ''')


@pytest.mark.parametrize("invalidate", [
    "_patientLocal=false;",
    "_patientOwner=9;",
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_medicationDriveFlushToken",[]];',
    "_patientAlive=false;",
])
def test_old_trailing_callback_cannot_publish_after_locality_reset_or_death(invalidate):
    execute(queue_setup() + r'''
        [_patient,"Norepinephrine_IV",1,.25] call ACME_fnc_medicationDriveAdd;
        [_patient,.25] call ACME_fnc_medicationDriveTick;
    ''' + invalidate + r'''
        _nowTime=11; call _runDue;
        [count _published==1,"obsolete infusion timer published state"] call _check;
    ''')


def iv_setup():
    body = adapted((C / "fnc_setIVBagsState.sqf").read_text())
    # Namespace object stand-ins do not accept the engine public flag.
    # The VM retains nil-valued namespace slots; Arma deletes them and uses this fallback.
    body = body.replace('_patient getVariable ["ACME_ivBagsPublishedSig", ""]',
                        '(if (isNil {_patient getVariable "ACME_ivBagsPublishedSig"}) then {""} else {_patient getVariable "ACME_ivBagsPublishedSig"})')
    body = body.replace('["ACM_circulation_IV_Bags", _bags, _public]', '["ACM_circulation_IV_Bags", _bags]')
    return "private _patientLocal=true; private _patientOwner=7; ACM_circulation_fnc_setIVBagsState={" + body + r'''};
        missionNamespace setVariable ["ACME_net_count",true];
        private _sentCount={ (missionNamespace getVariable ["ACME_net_sent",createHashMap]) getOrDefault ["ACM_circulation_IV_Bags",0] };
    '''


def test_iv_cache_suppresses_repeats_but_preserves_in_place_change_and_restore():
    execute(iv_setup() + r'''
        private _bags=createHashMapFromArray [["leftarm",[["Saline",100]]]];
        [_patient,_bags,true] call ACM_circulation_fnc_setIVBagsState;
        [_patient,_bags,true] call ACM_circulation_fnc_setIVBagsState;
        [call _sentCount==1,"unchanged IV map was duplicated"] call _check;
        (_bags get "leftarm" select 0) set [1,50];
        [_patient,_bags,true] call ACM_circulation_fnc_setIVBagsState;
        (_bags get "leftarm" select 0) set [1,100];
        [_patient,_bags,true] call ACM_circulation_fnc_setIVBagsState;
        [call _sentCount==3,"mutable IV map change/restore disappeared"] call _check;
        [_patient,_bags,false] call ACM_circulation_fnc_setIVBagsState;
        [_patient,_bags,true] call ACM_circulation_fnc_setIVBagsState;
        [call _sentCount==4,"local staging retained stale publication cache"] call _check;
    ''')


def test_native_iv_writers_share_cache_and_final_nil_explicitly_invalidates_it():
    expected = {
        C / "fnc_getBloodVolumeChange.sqf": "[_unit, _fluidBags, _acmeBagUiPublish] call FUNC(setIVBagsState);",
        C / "fnc_resetVariables.sqf": "[_patient, createHashMap, true] call FUNC(setIVBagsState);",
        C / "fnc_setIVLocal.sqf": "[_patient, _map, true] call FUNC(setIVBagsState);",
        ROOT / "addons/core/overrides/fnc_ivBagLocal.sqf": "[_patient, _IVBags, true] call EFUNC(circulation,setIVBagsState);",
    }
    for path, call in expected.items():
        assert call in path.read_text(), path
    volume = (C / "fnc_getBloodVolumeChange.sqf").read_text()
    assert '_unit setVariable ["ACME_ivBagsPublishedSig", nil, false];\n        _unit setVariable [QEGVAR(circulation,IV_Bags), nil, true];' in volume
