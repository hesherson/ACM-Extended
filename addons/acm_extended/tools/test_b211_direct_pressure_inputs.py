"""Execute DP movement, resume and mission-display cancellation in SQF-VM.

The production claim handshake, worker, pose controller, mouse callback and stop
run unchanged apart from explicit engine boundaries. Native input, coordinates,
display event registration, animation and network delivery are simulated here;
this does not establish real Arma animation or display routing behavior.
"""
import os
import re
import subprocess

from functools import lru_cache
import pytest

from test_b209_direct_pressure_locality import setup as locality_setup, source as locality_source
from test_menu_death_lifecycle import ROOT, execute, read


MOVEMENT_ACTIONS = (
    "MoveForward", "MoveBack", "MoveLeft", "MoveRight", "TurnLeft", "TurnRight",
    "MoveFastForward", "MoveSlowForward", "Evasive",
)


def runtime(name):
    """Optional old-source run proves behavior fails before this fix."""
    revision = os.environ.get("B211_TEST_BASELINE")
    if revision:
        return subprocess.check_output(
            ["git", "show", f"{revision}:addons/acm_extended/functions/fn_{name}.sqf"],
            cwd=ROOT, text=True,
        )
    return read(name)


def source(name):
    text = runtime(name)
    # Keep each action name; the older locality fixture intentionally folds all
    # inputAction reads into zero, which cannot test the reported input failure.
    text = re.sub(r'inputAction "([^"]+)"', r'(["\1"] call _input)', text)
    text = text.replace("getPosASL _medic", "_position")
    text = text.replace("objectParent _medic", "_medicVehicleObject")
    text = text.replace("objectParent _patient", "_patientVehicleObject")
    text = text.replace("findDisplay 46", "_display")
    # Displays use namespace stand-ins too; retain params' actual argument rather
    # than accidentally exercising only the mission-display fallback.
    text = text.replace("[displayNull]", "[profileNamespace]")
    # Preserve the entire production callback, replacing only native registration.
    text = text.replace('_disp displayAddEventHandler ["MouseButtonDown", {',
                        '(["MouseButtonDown", {')
    if name == "installRmbCancelGuard":
        text = text.replace('}];', '}] call _addDisplayHandler);')
    return locality_source(name, text)


@lru_cache(maxsize=1)
def setup():
    text = locality_setup() + '''
        private _inputActions=[]; private _position=[0,0,0];
        private _medicVehicleObject=objNull; private _patientVehicleObject=objNull;
        _input={_inputCalls=_inputCalls+1; if ((_this select 0) in _inputActions) then {1} else {0}};
        private _display=parsingNamespace; private _mouse={false}; private _registrations=0;
        private _addDisplayHandler={_mouse=_this select 1; _registrations=_registrations+1; _registrations};
        private _cancelQueue=[]; private _hangStops=0;
        CBA_fnc_execNextFrame={_cancelQueue pushBack [_this select 0,_this select 1];};
        ACME_fnc_hangBagStop={_hangStops=_hangStops+1;};
        ACME_fnc_providerStanceOwned={false};
    '''
    for name in ("directPressureTick", "directPressurePose", "installRmbCancelGuard"):
        text += f"ACME_fnc_{name}={{" + source(name) + "};"
    return text + '''
        private _start={
            params ["_part",["_self",false]];
            [_medic,[_patient,_medic] select _self,_part] call ACME_fnc_directPressureStart;
            call _deliver; call _deliver;
            [_medic getVariable ["ACME_DP_Active",false],"claim handshake did not activate DP"] call _check;
        };
        private _pressTick={(_medic getVariable ["ACME_DP_PFH",-1]) call _tick;};
        private _finishPressureExit={
            if ((_medic getVariable ["ACME_DP_Exit",[]]) isNotEqualTo []) then {
                private _exitId=count _handlers-1;
                _animation="ainvpknlmstpsnonwnondnon_medicend"; _exitId call _tick;
                CBA_missionTime=CBA_missionTime+1.21; _exitId call _tick;
            };
        };
        private _runCancel={private _work=_cancelQueue deleteAt 0; (_work select 1) call (_work select 0);};
    '''


@pytest.mark.parametrize("action", MOVEMENT_ACTIONS)
@pytest.mark.parametrize("part,self_pressure", [("body", False), ("leftarm", False), ("head", False), ("leftarm", True)])
# B217 preserves this collected case identity; the new requested resume delay is two seconds.
def test_movement_keeps_exact_pressure_claim_and_resumes_pose_next_tick(action, part, self_pressure):
    execute(setup() + f'''
        ["{part}",{str(self_pressure).lower()}] call _start;
        private _id=_medic getVariable "ACME_DP_PFH";
        private _token=_medic getVariable "ACME_DP_ClaimToken";
        private _target=_medic getVariable "ACME_DP_Patient";
        private _claim=+(_target getVariable "ACME_DP_claim_{part}");
        _inputActions=["{action}"];
        _animation="acme_directpressurehold";
        CBA_missionTime=CBA_missionTime+0.2;
        call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"movement cancelled pressure"] call _check;
        [(_medic getVariable ["ACME_DP_PFH",-1])==_id && {{!(_id in _removed)}},"movement retired pressure worker"] call _check;
        [(_medic getVariable ["ACME_DP_ClaimToken",""])==_token,"movement changed claim token"] call _check;
        [(_target getVariable ["ACME_DP_claim_{part}",[]]) isEqualTo _claim,"movement changed patient reservation"] call _check;
        [count _wire==0,"movement sent a release request"] call _check;
    ''' + ('''
        [!(_medic getVariable ["ACME_DP_InPose",true]),"movement did not yield decorative pose"] call _check;
        // Execute the held-animation worker that was pending before movement.
        // It must retire its own generation without fighting the movement input.
        _moves=[]; (_id-1) call _tick;
        [count _moves==0,"old held worker fought movement"] call _check;
    ''' if not self_pressure else '') + '''
        _inputActions=[]; call _finishPressureExit; _animation="amovpknlmwlksnonwnondf";
        CBA_missionTime=CBA_missionTime+0.016;
        call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"released movement did not preserve DP"] call _check;
        [(_medic getVariable ["ACME_DP_PFH",-1])==_id,"resume replaced the pressure worker"] call _check;
    ''' + ('''
        [!(_medic getVariable ["ACME_DP_InPose",true]),"provider resumed before the two-second pause"] call _check;
        CBA_missionTime=(_medic getVariable "ACME_DP_IdleStart")+2; call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"stationary facing provider did not resume at two seconds"] call _check;
        // Follow the actual new held worker through to the engine animation
        // boundary; InPose alone is merely controller intent.
        _moves=[]; (count _handlers-1) call _tick;
        [count _moves==1 && {((_moves select 0) select 1)=="ACME_DirectPressureHold"},
            "resumed pose never requested the pressure animation"] call _check;
    ''' if not self_pressure else ''))


def test_actual_displacement_yields_pose_and_old_exit_cannot_break_immediate_resume():
    execute(setup() + '''
        ["leftarm"] call _start;
        _animation="acme_directpressurehold";
        _position=[0.1,0,0]; CBA_missionTime=CBA_missionTime+0.2;
        call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"displacement cancelled pressure"] call _check;
        [!(_medic getVariable ["ACME_DP_InPose",true]),"displacement did not yield pose"] call _check;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isNotEqualTo [],"finite movement exit was not reached"] call _check;
        call _finishPressureExit; _animation="amovpknlmstpsnonwnondnon";
        CBA_missionTime=CBA_missionTime+0.016; call _pressTick;
        [!(_medic getVariable ["ACME_DP_InPose",true]),"displacement resumed without two-second pause"] call _check;
        CBA_missionTime=(_medic getVariable "ACME_DP_IdleStart")+2; call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"pose did not resume after two seconds"] call _check;
        private _before=count _moves;
        {(_x select 1) call (_x select 0);} forEach _waits;
        [count _moves==_before,"old movement exit broke the resumed hold"] call _check;
    ''')


@pytest.mark.parametrize("button", [1, 2], ids=["right", "middle-compatibility"])
@pytest.mark.parametrize("part,self_pressure", [("body", False), ("leftarm", False), ("leftarm", True)])
def test_cancel_mouse_button_runs_real_stop_and_releases_exact_patient_claim(button, part, self_pressure):
    execute(setup() + f'''
        ["{part}",{str(self_pressure).lower()}] call _start;
        private _target=_medic getVariable "ACME_DP_Patient";
        private _id=_medic getVariable "ACME_DP_PFH";
        [_display] call ACME_fnc_installRmbCancelGuard;
        [_registrations==1,"mouse guard not installed"] call _check;
        private _consumed=[_display,{button}] call _mouse;
        [_consumed && {{count _cancelQueue==1}},"cancel click not consumed/queued"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"cancel executed inside display handler"] call _check;
        if (count _cancelQueue>0) then {{call _runCancel;}};
        [!(_medic getVariable ["ACME_DP_Active",true]),"mouse click did not stop pressure"] call _check;
        [_id in _removed,"mouse cancel retained pressure worker"] call _check;
        [count _wire==1,"mouse cancel did not release claim"] call _check;
        if (count _wire>0) then {{call _deliver;}};
        [(_target getVariable ["ACME_DP_claim_{part}",[]]) isEqualTo [],"cancelled patient reservation survived"] call _check;
    ''')


@pytest.mark.parametrize("button", [0, 3], ids=["left", "unrelated"])
def test_other_mouse_buttons_do_not_cancel_or_consume(button):
    execute(setup() + f'''
        ["leftarm"] call _start;
        [_display] call ACME_fnc_installRmbCancelGuard;
        private _consumed=[_display,{button}] call _mouse;
        [!_consumed && {{count _cancelQueue==0}},"unrelated mouse button was consumed"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"unrelated mouse button cancelled pressure"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_medic setVariable ["ACME_DP_ClaimToken","replacement"];',
    '_medic setVariable ["ACME_DP_ClaimEpoch",1];',
    '_medic setVariable ["ACME_DP_PoseToken",100];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_medic setVariable ["TEST_owner",8];',
    'ACE_player=_patient;',
], ids=["claim-token", "claim-generation", "pose-generation", "locality-generation", "ownership", "controlled-unit"])
def test_deferred_mouse_cancel_cannot_touch_replacement_or_transferred_episode(change):
    execute(setup() + '''
        ["leftarm"] call _start;
        [_display] call ACME_fnc_installRmbCancelGuard;
        [_display,1] call _mouse;
        [count _cancelQueue==1,"right click did not queue cancel"] call _check;
    ''' + change + '''
        private _before=count _moves;
        if (count _cancelQueue>0) then {call _runCancel;};
        [_medic getVariable ["ACME_DP_Active",false],"stale cancel stopped changed episode"] call _check;
        [count _wire==0 && {count _moves==_before},"stale cancel altered claim or presentation"] call _check;
    ''')


def test_actor_switch_cannot_cancel_matching_looking_new_actor():
    execute(setup() + '''
        ["leftarm"] call _start;
        [_display] call ACME_fnc_installRmbCancelGuard;
        [_display,1] call _mouse;
        [count _cancelQueue==1,"right click did not queue cancel"] call _check;
        private _newActor=missionNamespace;
        _newActor setVariable ["TEST_owner",7];
        _newActor setVariable ["ACME_DP_Active",true];
        _newActor setVariable ["ACME_DP_PoseToken",_medic getVariable "ACME_DP_PoseToken"];
        _newActor setVariable ["ACME_DP_ClaimToken",_medic getVariable "ACME_DP_ClaimToken"];
        _newActor setVariable ["ACME_DP_ClaimEpoch",_medic getVariable "ACME_DP_ClaimEpoch"];
        ACE_player=_newActor;
        if (count _cancelQueue>0) then {call _runCancel;};
        [_newActor getVariable ["ACME_DP_Active",false],"old click cancelled newly controlled actor"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"old click cancelled abandoned actor"] call _check;
    ''')


def test_guard_installs_once_on_each_display_and_supports_reopened_menu():
    execute(setup() + '''
        [_display] call ACME_fnc_installRmbCancelGuard;
        [_display] call ACME_fnc_installRmbCancelGuard;
        [_registrations==1,"same display registered duplicate mouse handlers"] call _check;
        [missionNamespace] call ACME_fnc_installRmbCancelGuard;
        [_registrations==2,"medical-menu display did not get its own handler"] call _check;
        [missionNamespace] call ACME_fnc_installRmbCancelGuard;
        [_registrations==2,"medical-menu display registered duplicate handlers"] call _check;
        [profileNamespace] call ACME_fnc_installRmbCancelGuard;
        [_registrations==3,"reopened medical-menu display did not get a handler"] call _check;
    ''')


BUSY_STATES = [
    '_medic setVariable ["ACME_DP_Paused",true];',
    '_medic setVariable ["ACME_DP_TreatmentBusy",true];',
    '_medic setVariable ["ACME_treatmentPreflightActive",true];',
    '_medic setVariable ["ACME_chestAccessPreflightActive",true];',
    '_medic setVariable ["ACME_chestAccessProvider",[_patient,"lease"]];',
    '_medic setVariable ["ACME_headElev_seqActive",true];',
    '_medic setVariable ["ACM_circulation_isPerformingCPR",true];',
    '_medic setVariable ["ACM_breathing_isUsingBVM",true];',
    'ACM_core_ContinuousAction_Active=true;',
]


@pytest.mark.parametrize("state", BUSY_STATES, ids=[
    "paused", "treatment", "preflight", "chest-preflight", "chest-lease", "head-position",
    "provider-cpr", "provider-bvm", "continuous-controller",
])
@pytest.mark.parametrize("button", [1, 2], ids=["right", "middle"])
def test_other_interventions_keep_ownership_of_mouse_inputs(state, button):
    execute(setup() + '''
        ["leftarm"] call _start;
        [_display] call ACME_fnc_installRmbCancelGuard;
    ''' + state + f'''
        private _consumed=[_display,{button}] call _mouse;
        [!_consumed && {{count _cancelQueue==0}},"DP consumed another intervention's input"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"another intervention lost preserved pressure"] call _check;
    ''')


@pytest.mark.parametrize("state", BUSY_STATES, ids=[
    "paused", "treatment", "preflight", "chest-preflight", "chest-lease", "head-position",
    "provider-cpr", "provider-bvm", "continuous-controller",
])
def test_other_intervention_start_between_click_and_callback_preempts_old_cancel(state):
    execute(setup() + '''
        ["leftarm"] call _start;
        [_display] call ACME_fnc_installRmbCancelGuard;
        [_display,1] call _mouse;
        [count _cancelQueue==1,"right click did not queue cancel"] call _check;
    ''' + state + '''
        if (count _cancelQueue>0) then {call _runCancel;};
        [_medic getVariable ["ACME_DP_Active",false],"deferred cancel disturbed replacement intervention"] call _check;
        [count _wire==0,"deferred cancel released pressure under replacement intervention"] call _check;
    ''')


@pytest.mark.parametrize("role", ["cpr", "bvm"])
def test_another_medic_working_on_same_patient_does_not_block_own_pressure_cancel(role):
    execute(setup() + f'''
        ["leftarm"] call _start;
        ACM_core_fnc_{role}Active={{true}};
        [_display] call ACME_fnc_installRmbCancelGuard;
        private _consumed=[_display,1] call _mouse;
        [_consumed && {{count _cancelQueue==1}},"other medic prevented pressure cancel"] call _check;
        if (count _cancelQueue>0) then {{call _runCancel;}};
        [!(_medic getVariable ["ACME_DP_Active",true]),"pressure did not stop beside other medic"] call _check;
    ''')


@pytest.mark.parametrize("part", ["body", "leftarm"])
def test_leaving_patient_range_still_releases_pressure(part):
    execute(setup() + f'''
        ["{part}"] call _start;
        ACME_fnc_patientInteractionDistance={{4}};
        call _pressTick;
        [!(_medic getVariable ["ACME_DP_Active",true]),"out-of-range provider retained pressure"] call _check;
        [count _wire==1,"out-of-range provider did not release reservation"] call _check;
        if (count _wire>0) then {{call _deliver;}};
        [(_patient getVariable ["ACME_DP_claim_{part}",[]]) isEqualTo [],"out-of-range reservation survived"] call _check;
    ''')


@pytest.mark.parametrize("stop_condition", [
    '_medic setVariable ["TEST_alive",false];',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_patientVehicleObject=parsingNamespace;',
    '_medicVehicleObject=parsingNamespace;',
], ids=["dead-provider", "unconscious-provider", "patient-enters-vehicle", "provider-enters-vehicle"])
def test_provider_incapacity_or_different_vehicle_still_releases_pressure(stop_condition):
    execute(setup() + '''
        ["leftarm"] call _start;
    ''' + stop_condition + '''
        call _pressTick;
        [!(_medic getVariable ["ACME_DP_Active",true]),"invalid provider retained pressure"] call _check;
        [count _wire==1,"invalid provider did not release reservation"] call _check;
    ''')


def test_matching_vehicle_preserves_pressure_without_forcing_on_foot_pose():
    execute(setup() + '''
        ["leftarm"] call _start;
        _medicVehicleObject=parsingNamespace; _patientVehicleObject=parsingNamespace;
        _moves=[];
        call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"same-vehicle treatment cancelled"] call _check;
        [count _moves==0 && {count _wire==0},"vehicle treatment forced animation or released claim"] call _check;
    ''')


@pytest.mark.parametrize("button,expected", [(1, True), (0, False), (2, False)])
def test_hang_bag_retains_its_right_click_cancel_contract(button, expected):
    execute(setup() + f'''
        _medic setVariable ["ACME_hang_Active",true];
        _medic setVariable ["ACME_hang_Start",10];
        [_display] call ACME_fnc_installRmbCancelGuard;
        private _consumed=[_display,{button}] call _mouse;
        [_consumed isEqualTo {str(expected).lower()},"Hang Bag consumed wrong input"] call _check;
        if (count _cancelQueue>0) then {{call _runCancel;}};
        [_hangStops=={int(expected)},"Hang Bag cancel routing changed"] call _check;
    ''')
