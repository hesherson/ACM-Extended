"""Execute native BVM and real Direct Pressure entry/teardown together.

SQF owns the reservations, callbacks, key handlers and breath loop. Native object,
UI, animation and network operations are simulated; no DP stop is stubbed out.
"""
import re

import pytest

from test_bvm_startup import completion_setup, setup as bvm_setup
from test_menu_death_lifecycle import adapt, execute, read


def pressure_source(name):
    source = read(name)
    replacements = {
        "animationState _medic": "_animation",
        "animationState _m": "_animation",
        "animationState _u": "_animation",
        "alive _u": "_alive",
        "objectParent _u": "objNull",
        "objectParent _m": "objNull",
        "getPosASL _medic": "[0,0,0]",
        "getPosVisual _medic": "[0,0,0]",
        "getPosVisual _patient": "[0,1,0]",
        "eyeDirection _medic": "_look",
        '_medic setUnitPos "MIDDLE";': "",
        '_m setUnitPos "AUTO";': "_stanceFreed = true;",
        'removeMissionEventHandler ["Draw3D", _d3];': "_removedDraw pushBack _d3;",
        "_medic setVariable [_name, _value, _public];": "_medic setVariable [_name, _value];",
    }
    for old, new in replacements.items():
        source = re.sub(re.escape(old) + (r"\b" if old[-1].isalnum() else ""), lambda _: new, source)
    source = re.sub(r'inputAction "[^"]+"', "0", source)
    source = source.replace("[objNull]", "[profileNamespace]")
    return adapt(source)


def setup():
    source = bvm_setup() + '''
        private _animation = "acme_directpressurehold";
        private _look = [0,1,0];
        private _removedDraw = [];
        private _pressureLogs = [];
        ACME_fnc_animBlocked = {false};
        ACME_fnc_doAnim = {_moves pushBack (_this select 1);};
        ACME_fnc_bodyPartName = {_this select 0};
        ACME_fnc_medLog = {_pressureLogs pushBack _this;};
        ACME_fnc_directPressureHasFracture = {false};
        ACM_damage_fnc_clotWoundsOnBodyPart = {};
        CBA_fnc_execNextFrame = {_waits pushBack [_this select 0,_this select 1];};
    '''
    for name in ("doAnimHeld", "directPressureStop", "directPressurePose", "directPressureTick", "directPressureLimb", "directPressureTorso", "directPressureStart"):
        source += f"ACME_fnc_{name} = {{" + pressure_source(name) + "};"
    source += '''
        private _press = {
            [_medic,_patient,_this] call ACME_fnc_directPressureStart;
            [_medic getVariable ["ACME_DP_Active",false],"DP did not start"] call _check;
        };
        private _pressTick = {
            private _id = _medic getVariable ["ACME_DP_PFH",-1];
            if (_id < 0) exitWith {};
            private _h = _handlers select _id;
            [_h select 1,_id] call (_h select 0);
        };
        private _pressReleased = {
            [!(_medic getVariable ["ACME_DP_Active",true]),"DP stayed active"] call _check;
            [(_medic getVariable ["ACME_DP_Patient",_patient]) isEqualTo objNull,"DP target retained"] call _check;
            [(_medic getVariable ["ACME_DP_PFH",0]) == -1,"DP worker retained"] call _check;
            [(_medic getVariable ["ACME_DP_KeyIDs",[1]]) isEqualTo [],"DP inputs retained"] call _check;
            [!(_medic getVariable ["ACME_DP_TreatmentBusy",true]),"DP treatment busy retained"] call _check;
            [!(_medic getVariable ["ACME_DP_Paused",true]),"DP pause retained"] call _check;
            [(_patient getVariable [format ["ACME_DP_press_%1",_this],objNull]) isEqualTo objNull,"DP clinical effect retained"] call _check;
        };
        private _toggle = {
            private _key = (_keys select {(_x select 0) == ACM_breathing_BVMToggle_MouseID}) select 0;
            call (_key select 1); call _tick;
        };
        private _stopBVM = {
            private _key = (_keys select {(_x select 0) == ACM_breathing_BVMCancel_MouseID}) select 0;
            call (_key select 1); call _tick;
        };
    '''
    return source


@pytest.mark.parametrize("part", ["body", "leftarm", "head"])
def test_pressure_to_bvm_breath_pause_resume_stop_and_repeat(part):
    execute(setup() + f'private _part = "{part}";' + '''
        for "_round" from 1 to 2 do {
            _part call _press; call _pressTick;
            private _pressureKeys = +(_medic getVariable "ACME_DP_KeyIDs");
            private _pressurePFH = _medic getVariable "ACME_DP_PFH";
            private _oldPoseToken = _medic getVariable "ACME_DP_PoseToken";
            [_medic,_patient] call ACM_breathing_fnc_useBVM;
            _part call _pressReleased;
            [ACM_core_ContinuousAction_Active,"BVM did not start from DP"] call _check;
            [!((_handlers select _pressurePFH) select 2),"old pressure worker still scheduled"] call _check;
            [(_pressureKeys findIf {!(_x in _removed)}) == -1,"old pressure input still registered"] call _check;
            [(_medic getVariable "ACME_DP_PoseToken") > _oldPoseToken,"old pose callbacks not retired"] call _check;
            private _before = _squeezes;
            CBA_missionTime = CBA_missionTime + 3; call _tick;
            CBA_missionTime = CBA_missionTime + 7; call _tick;
            [_squeezes == _before + 2,"BVM failed after direct pressure"] call _check;
            call _toggle;
            [(_patient getVariable ["ACM_breathing_BVM_Medic",objNull]) isEqualTo _medic,"pause lost reservation"] call _check;
            CBA_missionTime = CBA_missionTime + 30; call _tick;
            [_squeezes == _before + 2 && {ACM_core_ContinuousAction_Active},"pause stopped BVM or delivered breath"] call _check;
            call _toggle;
            [_squeezes == _before + 3,"resume failed"] call _check;
            call _stopBVM;
            [!ACM_core_ContinuousAction_Active,"BVM stop retained controller"] call _check;
            [(_patient getVariable ["ACM_breathing_BVM_Medic",objNull]) isEqualTo objNull,"BVM stop retained patient"] call _check;
        };
    ''')


def test_pending_pressure_workers_and_pose_callback_cannot_disturb_bvm():
    execute(setup() + '''
        "leftarm" call _press;
        private _heldID = (_medic getVariable "ACME_DP_PFH") - 1;
        private _held = _handlers select _heldID;
        private _pressureID = _medic getVariable "ACME_DP_PFH";
        private _pressure = _handlers select _pressureID;
        _look = [0,-1,0];
        [_medic,_patient] call ACME_fnc_directPressurePose;
        [count _waits > 0,"pose exit callback not captured"] call _check;
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        private _before = count _moves;
        [_held select 1,_heldID] call (_held select 0);
        [_pressure select 1,_pressureID] call (_pressure select 0);
        {(_x select 1) call (_x select 0);} forEach _waits;
        [count _moves == _before,"old pressure callback changed BVM animation"] call _check;
        CBA_missionTime = 13; call _tick;
        [ACM_core_ContinuousAction_Active && {_squeezes == 1},"old pressure callback cancelled BVM"] call _check;
    ''')


def test_another_providers_pressure_is_untouched():
    execute(setup() + '''
        private _other = missionNamespace;
        _other setVariable ["ACME_DP_Active",true];
        _other setVariable ["ACME_DP_Patient",_patient];
        _patient setVariable ["ACME_DP_LimbMedic",_other];
        _patient setVariable ["ACME_DP_press_leftarm",_other];
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        CBA_missionTime = 13; call _tick;
        [_squeezes == 1,"BVM failed alongside another provider's DP"] call _check;
        [_other getVariable "ACME_DP_Active","other provider's DP stopped"] call _check;
        [(_patient getVariable "ACME_DP_press_leftarm") isEqualTo _other,"other provider's pressure effect cleared"] call _check;
    ''')


@pytest.mark.parametrize("part", ["body", "leftarm", "head"])
def test_pressure_cannot_start_over_an_existing_bvm(part):
    execute(setup() + f'private _part = "{part}";' + '''
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        private _before = count _moves;
        private _keyCount = count _keys;
        [_medic,_patient,_part] call ACME_fnc_directPressureStart;
        [!(_medic getVariable ["ACME_DP_Active",false]),"pressure started on BVM provider"] call _check;
        [(_patient getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo objNull,"rejected DP applied clinical effect"] call _check;
        [count _moves == _before && {count _keys == _keyCount},"rejected DP changed BVM animation or inputs"] call _check;
        CBA_missionTime = 13; call _tick;
        [_squeezes == 1 && {ACM_core_ContinuousAction_Active},"rejected DP interrupted BVM"] call _check;
    ''')


def test_late_legacy_pressure_stop_preserves_bvm_controls_and_pose():
    execute(setup() + '''
        "body" call _press;
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        private _hidden = 0;
        ace_interaction_fnc_hideMouseHint = {_hidden = _hidden + 1;};
        private _before = count _moves;
        _medic setVariable ["ACME_DP_OwnsContinuous",true];
        [true,_medic,true] call ACME_fnc_directPressureStop;
        [ACM_core_ContinuousAction_Active,"legacy DP stop cancelled BVM controller"] call _check;
        [_hidden == 0 && {count _moves == _before},"legacy DP stop changed BVM controls or pose"] call _check;
        [count _waits == 0,"legacy DP stop queued menu reopen"] call _check;
        CBA_missionTime = 13; call _tick;
        [_squeezes == 1,"legacy DP stop prevented BVM breath"] call _check;
    ''')


def test_delayed_treatment_completion_cannot_restore_released_pressure():
    execute(setup() + completion_setup() + '''
        [true,_medic] call ACME_fnc_directPressureStop;
        "leftarm" call _press;
        "FieldDressing" call _completed;
        [count _waits > 0,"no delayed completion captured"] call _check;
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        call _finishWaits; call _tick;
        "leftarm" call _pressReleased;
        [!_dialog && {ACM_core_ContinuousAction_Active},"old completion reopened menu or ended BVM"] call _check;
        CBA_missionTime = 13; call _tick;
        [_squeezes == 1,"old completion blocked ventilation"] call _check;
    ''')


@pytest.mark.parametrize("reject", [
    'ACM_core_ContinuousAction_Active = true;',
    '_patient setVariable ["ACM_breathing_BVM_Medic",missionNamespace];',
    '_patientAwake = true;',
    '_alive = false;',
    '_unconscious = true;',
])
def test_rejected_bvm_start_preserves_direct_pressure(reject):
    execute(setup() + '''
        "leftarm" call _press;
        private _id = _medic getVariable "ACME_DP_PFH";
        private _keysBefore = +(_medic getVariable "ACME_DP_KeyIDs");
    ''' + reject + '''
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        [_medic getVariable ["ACME_DP_Active",false],"rejected BVM ended pressure"] call _check;
        [(_medic getVariable "ACME_DP_PFH") == _id && {(_handlers select _id) select 2},"rejected BVM removed pressure worker"] call _check;
        [(_medic getVariable "ACME_DP_KeyIDs") isEqualTo _keysBefore,"rejected BVM removed pressure keys"] call _check;
        [(_patient getVariable "ACME_DP_press_leftarm") isEqualTo _medic,"rejected BVM removed pressure effect"] call _check;
        [isNil "ACM_breathing_BVM_LocalSession","rejected BVM acquired local session"] call _check;
    ''')


@pytest.mark.parametrize("lying", [False, True])
def test_native_awake_patient_eligibility_after_pressure(lying):
    execute(setup() + f'private _lying = {str(lying).lower()};' + '''
        "leftarm" call _press;
        _patientAwake = true;
        _patient setVariable ["ACM_core_Lying_State",_lying];
        [[_medic,_patient] call ACM_breathing_fnc_canUseBVM isEqualTo _lying,"native awake eligibility changed"] call _check;
        if (_lying) then {
            [_medic,_patient] call ACM_breathing_fnc_useBVM;
            CBA_missionTime = 13; call _tick;
            [_squeezes == 1 && {ACM_core_ContinuousAction_Active},"awake lying patient could not receive BVM"] call _check;
            _patient setVariable ["ACM_core_Lying_State",false];
            call _tick; call _tick;
            [!ACM_core_ContinuousAction_Active,"upright awake patient remained on BVM"] call _check;
        };
    ''')
