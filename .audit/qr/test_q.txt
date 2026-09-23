"""Execute the whole Elevate Head startup with explicit engine boundaries.

Roll completion, equipment and physical side detection are fixtures. Tests record
facing/gear/animation requests, not actual RTM, PhysX or multiplayer behavior.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_head_start_contracts import start_setup
from test_bounded_head_completion import source
from test_bounded_head_pose_contracts import contains


def retry_contract(text=None):
    s = source('headElevateStart') if text is None else text
    for required in (
        'private _startPoseToken = _patient getVariable ["ACME_headElev_poseToken", ""];',
        'params ["_m","_p","_body","_auto","_startPoseToken"];',
        'if ((_p getVariable ["ACME_headElev_poseToken", ""]) != _startPoseToken) exitWith {};',
        '[_m,_p,_body,_auto,true] call ACME_fnc_headElevateStart;',
        '[_medic,_patient,_bodyPart,_auto,_startPoseToken]',
    ):
        assert contains(s, required), required
    delayed = s.split('params ["_m","_p","_body","_auto","_startPoseToken"];', 1)[1].split('call CBA_fnc_waitAndExecute;', 1)[0]
    assert not contains(delayed, '_p setVariable ["ACME_CS_facing","front",true];')
    assert delayed.index('!= _startPoseToken') < delayed.index('call ACME_fnc_headElevateStart')


def pending(physical=True):
    return start_setup() + f'''
        _actualSide="back"; _canRoll={str(physical).lower()};
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        [count _waits==1,"missing normalization continuation"] call _check;
        private _retry=_waits select 0; _waits=[];
        _events=[]; _rolls=[]; _restores=[];
        _patient setVariable ["ACME_CS_facing","sentinel"];
    '''


@pytest.mark.parametrize('physical', [False, True])
@pytest.mark.parametrize('change', [
    '_patient setVariable ["ACME_headElev_poseToken","later"];',
    '_patient setVariable ["ACME_headElev_poseToken","later"]; _patient setVariable ["ACME_headElevated",true];',
    '_patient setVariable ["ACME_headElevated",true];',
    '_canStart=false;',
    '_medic=objNull;',
    '_patientLocal=false;',
    '_patientAlive=false;',
])
def test_retired_or_ineligible_retry_cannot_rewrite_facing_or_start_gear_work(physical, change):
    # Medic loss must be applied to the captured argument, not just the outer fixture.
    if change == '_medic=objNull;':
        change = '(_retry select 1) set [0,objNull];'
    execute(pending(physical) + change + '''
        [_retry] call _deliver;
        [(_patient getVariable ["ACME_CS_facing",""])=="sentinel","stale retry rewrote facing"] call _check;
        [count _tilts==0 && {count _starts==0} && {count _watches==0},"stale retry started elevation"] call _check;
        [count _restores==0 && {count _waits==0} && {count _rolls==0},"stale retry repeated gear/roll work"] call _check;
    ''')


@pytest.mark.parametrize('physical', [False, True])
@pytest.mark.parametrize('auto', [False, True])
def test_current_retry_keeps_supine_lift_and_duplicate_delivery_has_no_writes(physical, auto):
    execute(pending(physical) + f'''
        (_retry select 1) set [3,{str(auto).lower()}];
        [_retry] call _deliver;
        [_patient getVariable ["ACME_headElevated",false],"current retry failed"] call _check;
        [count _tilts==1 && {{count _starts==1}} && {{count _watches==1}},"current retry lost handoff"] call _check;
        [(_patient getVariable ["ACME_CS_facing",""])=="front","supine cache lost"] call _check;
        [count _restores==1 && {{count _waits==0}},"unexpected gear/timer work"] call _check;
        _patient setVariable ["ACME_CS_facing","new-facing"];
        [_retry] call _deliver;
        [(_patient getVariable ["ACME_CS_facing",""])=="new-facing","duplicate delivery rewrote facing"] call _check;
        [count _tilts==1 && {{count _restores==1}},"duplicate delivery repeated startup"] call _check;
    ''')


@pytest.mark.parametrize('physical', [False, True])
def test_retry_loses_ownership_to_a_real_new_start_without_undoing_it(physical):
    execute(pending(physical) + '''
        _actualSide="front";
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        private _laterToken=_patient getVariable ["ACME_headElev_poseToken",""];
        [count _tilts==1 && {_laterToken!=""},"new actual startup not exercised"] call _check;
        _patient setVariable ["ACME_CS_facing","later-facing"];
        [_retry] call _deliver;
        [(_patient getVariable ["ACME_CS_facing",""])=="later-facing","old retry touched later placement"] call _check;
        [(_patient getVariable ["ACME_headElev_poseToken",""])==_laterToken,"old retry replaced later token"] call _check;
        [count _tilts==1 && {count _restores==1},"old retry repeated later work"] call _check;
    ''')
