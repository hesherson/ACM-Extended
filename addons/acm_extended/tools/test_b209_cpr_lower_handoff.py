"""Execute bounded native CPR lowering/transfer against real SQF entry and owner code.

The fixture models object/network/animation boundaries, including delayed owner
acceptance. It does not claim rendered animation or Arma transport validation.
"""
import pytest
from test_cpr_lifecycle import execute as cpr_execute
from test_bounded_head_completion import setup as head_setup, code as head_code
from test_menu_death_lifecycle import read
from unittest.mock import patch
from test_menu_death_lifecycle import execute as owner_execute
from test_server_bvm_lifecycle import execute as bvm_execute


def test_missing_owner_ack_retries_bounded_then_releases_without_compressions():
    cpr_execute('''
        _patient setVariable ["ACME_headElevated", true];
        call _start;
        for "_i" from 1 to 100 do {CBA_missionTime = 20 + _i / 10; call _tick;};
        call _freed;
        [count (_dispatches select {(_x select 1) == "headElevStop"}) == 4, "unbounded or missing lower retries"] call _check;
        [count _anims == 0 && {!("CPR_ActionLog_Started" in _logs)}, "unacknowledged lowering started CPR"] call _check;
    ''')


def test_delayed_owner_ack_waits_for_owner_finish_clock():
    cpr_execute('''
        _patient setVariable ["ACME_headElevated", true];
        call _start;
        CBA_missionTime = 23; call _tick;
        [count _anims == 0, "provider timer bypassed owner acceptance"] call _check;
        _patient setVariable ["ACME_headElevated", false];
        _patient setVariable ["ACME_cprLowerReady", [_medic, ACM_circulation_CPR_Epoch, 26]];
        CBA_missionTime = 25.9; call _tick;
        [count _anims == 0, "provider ignored owner finish time"] call _check;
        CBA_missionTime = 26; call _tick;
        [count _anims == 1 && {[_patient] call ACM_core_fnc_cprActive}, "owner completion did not start CPR"] call _check;
        call _cancel; call _freed;
    ''')


@pytest.mark.parametrize("ack", [
    '[missionNamespace, ACM_circulation_CPR_Epoch, 20]',
    '[_medic, ACM_circulation_CPR_Epoch - 1, 20]',
    '[_medic, ACM_circulation_CPR_Epoch, -1]',
])
def test_wrong_or_rejected_owner_ack_never_starts_compressions(ack):
    cpr_execute('''
        _patient setVariable ["ACME_headElevated", true];
        call _start;
        _patient setVariable ["ACME_headElevated", false];
    ''' + f'ACME_fnc_ownerDispatch = {{}}; _patient setVariable ["ACME_cprLowerReady", {ack}];' + '''
        call _enter;
        [count _anims == 0, "invalid acknowledgment started CPR"] call _check;
        call _cancel; call _freed;
    ''')


def test_cancelled_request_cannot_start_from_late_ack_or_retry():
    cpr_execute('''
        _patient setVariable ["ACME_headElevated", true];
        call _start;
        private _oldEpoch = ACM_circulation_CPR_Epoch;
        call _cancel;
        private _requests = count _dispatches;
        _patient setVariable ["ACME_headElevated", false];
        _patient setVariable ["ACME_cprLowerReady", [_medic, _oldEpoch, 20]];
        call _enter;
        [count _dispatches == _requests && {count _anims == 0}, "cancelled entry issued another request or started CPR"] call _check;
        call _freed;
    ''')


def test_same_vehicle_distant_seats_preserve_cpr_and_bvm_swap():
    cpr_execute('''
        _medicVehicle = missionNamespace; _patientVehicle = missionNamespace;
        _distance = 15; _hasBVM = true;
        call _start; call _enter;
        [[_medic, _patient] call ACM_circulation_fnc_cprSessionValid, "same-vehicle CPR lease rejected"] call _check;
        ["ACM_circulation_CPRToggle_MouseID"] call _key; call _tick;
        ["ACM_circulation_CPRSwap_MouseID"] call _key; call _tick;
        call _freed;
        [_bvmHandoff == 1, "distant passenger seats blocked BVM swap"] call _check;
    ''')


def test_same_vehicle_distant_seats_preserve_bvm_reservation():
    bvm_execute('''
        _medicVehicle = missionNamespace; _patientVehicle = missionNamespace;
        _distance = 15;
        [[_medic, _patient] call ACM_breathing_fnc_bvmSessionValid, "same-vehicle BVM lease rejected"] call _check;
    ''')


def test_cpr_to_bvm_publishes_both_handoffs_before_releasing_reservation():
    cpr_execute('''
        _hasBVM = true;
        ACME_fnc_ownerDispatch = {
            _dispatches pushBack _this;
            if ((_this select 1) == "headElevStop") then {
                _patient setVariable ["ACME_cprLowerReady", [_medic, (_this select 2) select 6, CBA_missionTime]];
            };
            if ((_this select 1) == "chestAccessManeuverHandoff") then {
                [[_medic, _patient] call ACM_circulation_fnc_cprSessionValid, "owner handoff followed CPR release"] call _check;
                [((_medic getVariable ["ACME_chestAccessManeuverHandoff", []]) select 0) isEqualTo _patient, "provider handoff absent"] call _check;
            };
        };
        call _start; call _enter;
        ["ACM_circulation_CPRToggle_MouseID"] call _key; call _tick;
        ["ACM_circulation_CPRSwap_MouseID"] call _key; call _tick;
        [count (_dispatches select {(_x select 1) == "chestAccessManeuverHandoff"}) == 1 && {_bvmHandoff == 1}, "handoff missing or duplicated"] call _check;
    ''')


def owner_setup():
    raw = read("headElevateStop")
    for old, new in {
        "isMultiplayer": "_testMP", "isServer": "_testServer",
        "local _medic": "_testMedicLocal", "clientOwner": "_testClientOwner",
        "owner _medic": "_testMedicOwner", "finite _providerOwner": "(_providerOwner isEqualType 0)",
    }.items():
        raw = raw.replace(old, new)
    with patch("test_bounded_head_completion.source", return_value=raw):
        owner_code = head_code("headElevateStop")
    return head_setup() + "ACME_fnc_headElevateStop={" + owner_code + "};" + '''
        private _testMP = true;
        private _testServer = true;
        private _testMedicLocal = false;
        private _testClientOwner = 2;
        private _testMedicOwner = 7;
        ace_common_fnc_isAwake = {!_unconscious};
        ACME_fnc_patientAnimRequest = {
            _animRequests pushBack _this;
            _patient setVariable ["ACME_patientAnimLock", ["lower-token","head-elev-lower","",1,_serverClock+4]];
            "lower-token"
        };
        ACME_fnc_patientAnimRelease = {_patient setVariable ["ACME_patientAnimLock", []];};
        _medic setVariable ["ACM_circulation_CPR_Epoch", 42];
        _patient setVariable ["ACM_circulation_CPR_session", [_medic,42]];
        private _request = {[_medic,_patient,false,false,true,true,42,7] call ACME_fnc_headElevateStop;};
    '''


@pytest.mark.parametrize("interruption", [
    '_alive = false;', '_unconscious = true;', '_testMedicOwner = 8;',
    '_medic setVariable ["ACM_circulation_CPR_Epoch", 43];',
    '_patient setVariable ["ACM_circulation_CPR_session", [_medic,43]];',
    '_patient setVariable ["ACM_circulation_CPR_session", []];',
])
def test_owner_rejects_retired_or_invalid_cpr_request_without_touching_posture(interruption):
    owner_execute(owner_setup() + interruption + '''
        call _request;
        [count _holdClears == 0 && {count _animRequests == 0}, "invalid request changed posture"] call _check;
        [_patient getVariable ["ACME_headElevated", false], "invalid request lowered patient"] call _check;
        [isNil {_patient getVariable "ACME_cprLowerReady"}, "invalid request acknowledged"] call _check;
        [(_patient getVariable ["ACME_headElev_startEpoch",0]) == 0, "invalid request cancelled newer placement"] call _check;
    ''')


def test_owner_accepts_once_and_uses_owner_clock():
    owner_execute(owner_setup() + '''
        ACME_headElev_lowerAnimTime = 3;
        call _request; call _request;
        [count _animRequests == 1 && {count _holdClears == 1}, "retry duplicated lower"] call _check;
        private _acceptedEpoch = _patient getVariable ["ACME_headElev_startEpoch",0];
        [_acceptedEpoch == 1, "retry advanced lower generation twice before completion"] call _check;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,-2], "lower acknowledged before owner completion"] call _check;
        _serverClock = 1003;
        [_waits select 0] call _deliver;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,1003], "completion ack used provider clock"] call _check;
        [count _provider == 0, "lower installed competing provider theatre"] call _check;
        // B238 consumes the accepted generation exactly once on completion; a request retry still does not advance it.
        private _retiredEpoch = _patient getVariable ["ACME_headElev_startEpoch",0];
        [_retiredEpoch == _acceptedEpoch + 1, "completion did not retire its accepted generation"] call _check;
        private _restoredOnce = count _restores;
        _serverClock = 1004;
        call _request;
        [_waits select 0] call _deliver;
        [(_patient getVariable ["ACME_headElev_startEpoch",0]) == _retiredEpoch, "completed request or callback retired twice"] call _check;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,1003], "duplicate callback republished a new completion time"] call _check;
        [count _restores == _restoredOnce && {count _animRequests == 1}, "completed request or callback repeated presentation"] call _check;
    ''')


def test_rejected_animation_cannot_become_success_on_retry():
    owner_execute(owner_setup() + '''
        ACME_fnc_patientAnimRequest = {_animRequests pushBack _this; ""};
        call _request; call _request;
        [count _animRequests == 1, "rejected lower replayed"] call _check;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,-1], "rejected lower acknowledged ready"] call _check;
    ''')


def test_owner_accepts_after_request_preceded_replication():
    owner_execute(owner_setup() + '''
        _patient setVariable ["ACM_circulation_CPR_session", []];
        call _request;
        [count _animRequests == 0, "missing session accepted"] call _check;
        _patient setVariable ["ACM_circulation_CPR_session", [_medic,42]];
        call _request;
        [count _animRequests == 1 && {count (_patient getVariable ["ACME_cprLowerReady", []]) == 3}, "retry after replication did not recover"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_patientLocal = false;', '_patientAlive = false;', '_alive = false;', '_unconscious = true;',
    '_testMedicOwner = 8;', '_medic setVariable ["ACM_circulation_CPR_Epoch",43];',
    '_patient setVariable ["ACM_circulation_CPR_session",[]];',
    '_patient setVariable ["ACME_patientAnimLock",["replacement","roll","",1,1010]];',
    '_patient setVariable ["ACME_headElevated",true];',
    '_patient setVariable ["ACME_headElev_startEpoch",2];',
])
def test_late_owner_completion_cannot_acknowledge_retired_or_replaced_motion(change):
    owner_execute(owner_setup() + "call _request;" + change + '''
        _serverClock = 1003;
        [_waits select 0] call _deliver;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,-2], "stale owner completion authorized CPR"] call _check;
    ''')


def test_restart_waits_for_previous_lower_to_actually_finish():
    owner_execute(owner_setup() + '''
        call _request;
        _medic setVariable ["ACM_circulation_CPR_Epoch",43];
        _patient setVariable ["ACM_circulation_CPR_session",[_medic,43]];
        [_medic,_patient,false,false,true,true,43,7] call ACME_fnc_headElevateStop;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,-2], "restart acknowledged still-running lower"] call _check;
        _serverClock = 1003;
        [_waits select 0] call _deliver;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,-2], "old completion acknowledged replacement"] call _check;
        [_medic,_patient,false,false,true,true,43,7] call ACME_fnc_headElevateStop;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,43,1003], "restart failed after old lower retired"] call _check;
        [count _animRequests == 1, "restart replayed lower"] call _check;
    ''')


@pytest.mark.parametrize("mp,server,local,client,owner,sender,accepted", [
    (True, False, False, 9, 0, 7, True),  # player-owned patient; remote provider owner unavailable
    (True, True, False, 2, 7, 7, True),   # dedicated-server AI patient
    (True, True, False, 2, 8, 7, False),  # authoritative server sees changed owner
    (True, False, True, 7, 0, 7, True),   # local provider client
    (True, False, True, 8, 0, 7, False),  # local provider moved to another client
    (False, True, True, 0, 0, 0, True),   # valid local single player zero ID
    (True, True, True, 0, 0, 0, False),   # zero must stay invalid in multiplayer
    (False, True, False, 0, 0, 0, False), # remote provider has no meaning in single player
])
def test_owner_identity_policy_at_admission_and_completion(mp,server,local,client,owner,sender,accepted):
    owner_execute(owner_setup() + f'''
        _testMP={str(mp).lower()}; _testServer={str(server).lower()};
        _testMedicLocal={str(local).lower()}; _testClientOwner={client}; _testMedicOwner={owner};
        [_medic,_patient,false,false,true,true,42,{sender}] call ACME_fnc_headElevateStop;
    ''' + ('''
        [count _animRequests == 1, "valid machine context rejected admission"] call _check;
        _serverClock = 1003;
        [_waits select 0] call _deliver;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,1003], "valid machine context rejected completion"] call _check;
    ''' if accepted else '''
        [count _animRequests == 0 && {isNil {_patient getVariable "ACME_cprLowerReady"}}, "invalid machine context admitted request"] call _check;
    '''))


def test_local_provider_identity_change_during_lower_rejects_completion():
    owner_execute(owner_setup() + '''
        _testServer = false; _testMedicLocal = true; _testClientOwner = 7;
        call _request;
        _testClientOwner = 8;
        [_waits select 0] call _deliver;
        [(_patient getVariable ["ACME_cprLowerReady", []]) isEqualTo [_medic,42,-2], "changed local provider acknowledged completion"] call _check;
    ''')
