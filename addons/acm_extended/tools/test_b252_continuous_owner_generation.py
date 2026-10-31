"""B252: continuous-action work cannot survive an away/back provider ownership transfer."""
from test_menu_death_lifecycle import execute, hold_setup
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "core" / "functions" / "fnc_beginContinuousAction.sqf"


def test_roundtrip_owner_transfer_cancels_old_head_tilt_controller():
    execute(hold_setup() + r"""
        [_medic,_patient] call _start;
        [_patient getVariable ["ACM_airway_HeadTilt_State",false],"missing accepted hold"] call _check;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        call _tick;
        [!ACM_core_ContinuousAction_Active,"stale owner retained global gate"] call _check;
        [!(_patient getVariable ["ACM_airway_HeadTilt_State",false]),"stale owner retained clinical head tilt"] call _check;
    """)


def test_unchanged_owner_generation_continues_active_hold():
    execute(hold_setup() + r"""
        [_medic,_patient] call _start;
        call _tick;
        [ACM_core_ContinuousAction_Active,"matching owner was unexpectedly cancelled"] call _check;
        [_patient getVariable ["ACM_airway_HeadTilt_State",false],"matching owner released clinical hold"] call _check;
    """)


def test_old_exit_speed_callback_cannot_override_new_owners_speed():
    execute(hold_setup() + r"""
        [_medic,_patient] call _start;
        ACM_core_ContinuousAction_Active=false; call _tick;
        [count _waits>0,"missing bounded exit rate release"] call _check;
        _testAnimationSpeed=0.4;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        private _job=_waits select ((count _waits)-1);
        (_job select 1) call (_job select 0);
        [_testAnimationSpeed==0.4,"old owner reset successor animation speed"] call _check;
    """)


def test_matching_owner_still_releases_exit_speed():
    execute(hold_setup() + r"""
        [_medic,_patient] call _start;
        ACM_core_ContinuousAction_Active=false; call _tick;
        [count _waits>0,"missing exit rate cleanup"] call _check;
        _testAnimationSpeed=1.5;
        private _job=_waits select ((count _waits)-1);
        (_job select 1) call (_job select 0);
        [_testAnimationSpeed==1,"matching owner failed to restore normal rate"] call _check;
    """)


def test_standing_entry_handoff_is_owner_generation_guarded():
    s=CORE.read_text(encoding="utf-8-sig")
    assert 'params ["_medic", "_epoch", "_playerBound", "_localityEpoch"];' in s
    assert '[_medic, _epoch, _playerBound, _localityEpoch]' in s
    assert '&& {(_medic getVariable ["ACME_providerLocalityEpoch", 0]) == _localityEpoch}) then {' in s
