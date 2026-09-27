"""Execute Semi-Fowler -> CPR cancellation against the actual CPR controller.

The existing SQF-VM fixture simulates engine animation/network boundaries. These
checks exercise ownership and input callbacks, not rendered Arma animation.
"""
import pytest

from test_cpr_lifecycle import execute


SETUP = '''
    private _lowers = 0;
    private _handoffs = 0;
    _patient setVariable ["ACME_headElevated", true];
    ACME_fnc_ownerDispatch = {
        if ((_this select 1) == "headElevStop") then {
            _lowers = _lowers + 1;
            _patient setVariable ["ACME_headElevated", false];
        };
        if ((_this select 1) == "chestAccessManeuverHandoff") then {
            _handoffs = _handoffs + 1;
        };
    };
'''


@pytest.mark.parametrize('cancel_key', [
    'ACM_circulation_CPRCancel_EscapeID',
    'ACM_circulation_CPRCancel_MouseID',
])
def test_cancel_during_patient_lower_never_starts_compressions(cancel_key):
    execute(SETUP + '''
        call _start;
        [_lowers == 1 && {_handoffs == 1}, "lower or custody handoff missing"] call _check;
        [count _anims == 0, "compressions started before lower"] call _check;
    ''' + f'["{cancel_key}"] call _key;' + '''
        call _tick;
        call _enter;
        call _freed;
        [count _anims == 0 && {!("ACM_CPR" in _moves)}, "cancelled lower started CPR later"] call _check;
        [_reopens == 1, "cancelled lower did not reopen medical menu"] call _check;
    ''')


@pytest.mark.parametrize('interruption', [
    '_alive = false;',
    '_awake = false;',
    '_local = false;',
    '_distance = 10;',
    '_medicVehicle = missionNamespace;',
    '_dialog = true;',
])
def test_interruption_during_lower_retires_cpr_entry(interruption):
    execute(SETUP + 'call _start;' + interruption + '''
        call _tick;
        call _enter;
        call _freed;
        [count _anims == 0 && {!("ACM_CPR" in _moves)}, "invalid lower started compressions"] call _check;
    ''')


def test_compressions_wait_for_configured_patient_lower_once():
    execute(SETUP + '''
        ACME_headElev_lowerAnimTime = 3;
        call _start;
        CBA_missionTime = 22; call _tick;
        [count _anims == 0, "provider entry bypassed longer patient lower"] call _check;
        CBA_missionTime = 23.06; call _tick;
        [count _anims == 1 && {_lowers == 1}, "lower did not finish exactly once"] call _check;
        call _cancel; call _freed;
    ''')


def test_patient_stays_reserved_through_lower_and_rejects_duplicate_start():
    execute(SETUP + '''
        call _start;
        private _epoch = ACM_circulation_CPR_Epoch;
        [[_medic, _patient] call ACM_circulation_fnc_cprSessionValid, "lower left patient unreserved"] call _check;
        [[_patient] call ACM_core_fnc_cprActive, "lower lost chest custody after handoff"] call _check;
        call _start;
        [_lowers == 1 && {ACM_circulation_CPR_Epoch == _epoch}, "duplicate start replaced lower session"] call _check;
        call _cancel; call _freed;
    ''')


def test_replacement_episode_is_not_restarted_by_old_lower_controller():
    execute(SETUP + '''
        call _start;
        private _oldController = _handlers select ACM_circulation_CPR_ControllerPFH;
        private _oldId = ACM_circulation_CPR_ControllerPFH;
        call _cancel;
        call _start;
        private _newEpoch = ACM_circulation_CPR_Epoch;
        [_oldController select 1, _oldId] call (_oldController select 0);
        [ACM_circulation_CPR_Epoch == _newEpoch, "old lower replaced new CPR"] call _check;
        call _enter;
        [count _anims == 1 && {_lowers == 1}, "old lower duplicated animation or patient lowering"] call _check;
        call _cancel; call _freed;
    ''')
