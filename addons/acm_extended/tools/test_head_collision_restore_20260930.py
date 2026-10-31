"""Execute actual posture callers and the deferred mass helper in SQF-VM.

Engine mass writes and broadcasts are recorded, not simulated PhysX or real
network delivery. The tests cover the ordering that prevents a local-only
restore from cancelling the all-peer restore.
"""
import pytest

from test_bounded_head_completion import code, setup
from test_menu_death_lifecycle import execute


def collision_setup():
    helper = code("headElevCollision").replace("getMass _patient", "_massValue")
    return setup() + r'''
        private _nextFrames = [];
        private _massValue = 1e-12;
        private _peerMass = 1e-12;
        private _massEvents = [];
        _patient setVariable ["ACME_headElev_mass", 70];
        CBA_fnc_execNextFrame = {_nextFrames pushBack _this;};
        CBA_fnc_globalEvent = {
            _events pushBack _this;
            if ((_this select 0) == "ace_common_setMass") then {
                _massValue = (_this select 1) select 1;
                _peerMass = _massValue;
                _massEvents pushBack _massValue;
            };
        };
        private _nextFrame = {
            private _jobs = +_nextFrames;
            _nextFrames = [];
            {(_x select 1) call (_x select 0);} forEach _jobs;
        };
    ''' + "ACME_fnc_headElevCollision={" + helper + "};\n"


@pytest.mark.parametrize("action", [
    "[_patient,false] call ACME_fnc_headElevApplyTilt;",
    "[_medic,_patient,true] call ACME_fnc_headElevateStop;",
])
def test_cleanup_restores_owner_and_peers_after_next_frame_only(action):
    execute(collision_setup() + action + r'''
        [count _masses == 0 && {count _massEvents == 0}, "mass restored inside root-motion frame"] call _check;
        [!isNil {_patient getVariable "ACME_headElev_mass"} && {(_patient getVariable "ACME_headElev_mass") == 70}, "original mass cleared before broadcast"] call _check;
        call _nextFrame;
        [_massEvents isEqualTo [70], "deferred restore did not publish exactly once"] call _check;
        [_massValue == 70 && {_peerMass == 70}, "owner and peer mass diverged"] call _check;
        [isNil {_patient getVariable "ACME_headElev_mass"}, "completed restore retained saved mass"] call _check;
    ''')


@pytest.mark.parametrize("action", [
    "[_patient,true] call ACME_fnc_headElevApplyTilt;",
    "[_medic,_patient,false] call ACME_fnc_headElevateStop;",
])
def test_accepted_motion_invalidates_old_restore_and_recovers_on_completion(action):
    execute(collision_setup() + r'''
        [_patient,true] call ACME_fnc_headElevCollision;
    ''' + action + r'''
        [count _masses == 0, "replacement motion briefly restored full local mass"] call _check;
        call _nextFrame;
        [count _massEvents == 0 && {_peerMass < 1}, "old restore interrupted new motion"] call _check;
        [(_patient getVariable ["ACME_headElev_mass", -1]) == 70, "new motion lost original mass"] call _check;
        [_waits select 0] call _deliver;
        [count _massEvents == 0, "completion restored mass before next frame"] call _check;
        call _nextFrame;
        [_massEvents isEqualTo [70] && {_peerMass == 70}, "current motion failed global restore"] call _check;
    ''')


@pytest.mark.parametrize("action", [
    "[_patient,true] call ACME_fnc_headElevApplyTilt;",
    "[_medic,_patient,false] call ACME_fnc_headElevateStop;",
])
def test_rejected_posture_does_not_restore_a_competing_moving_lease(action):
    execute(collision_setup() + r'''
        _patient setVariable ["ACME_patientAnimLock", ["roll:new", "roll", "other", 3, 1010, 1.5]];
        _patient setVariable ["ACME_patientAnimSpeedToken", "roll:new"];
    ''' + action + r'''
        call _nextFrame;
        [count _masses == 0 && {count _massEvents == 0}, "rejected posture restored another motion's mass"] call _check;
        [(_patient getVariable ["ACME_headElev_mass", -1]) == 70, "rejected posture discarded original mass"] call _check;
        [(_patient getVariable ["ACME_patientAnimSpeedToken", ""]) == "roll:new", "competing motion token changed"] call _check;
    ''')


def test_expired_motion_does_not_block_legacy_cleanup():
    execute(collision_setup() + r'''
        _patient setVariable ["ACME_patientAnimLock", ["old", "head-elev-lift", "", 1, 999, 1.5]];
        _patient setVariable ["ACME_patientAnimSpeedToken", "old"];
        [_patient,false] call ACME_fnc_headElevApplyTilt;
        call _nextFrame;
        [_massEvents isEqualTo [70], "expired motion stranded legacy mass"] call _check;
    ''')
