"""B166 Semi-Fowler regression contracts.

These are source/ownership contracts. They protect the clean patient/provider tandem, direct lay-flat exit,
absence of post-lower body rolls, and recovery from stale provider locks.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FUN=ROOT/"functions"
CORE=ROOT.parent/"core"/"overrides"


def read(name):
    return (FUN/f"fn_{name}.sqf").read_text(encoding="utf-8")


def test_patient_and_provider_start_together_without_ready_handshake():
    start=read("headElevateStart")
    tandem=start[start.index('missionNamespace setVariable ["ACME_headElev_TunePatient"'):]
    assert 'private _tiltAccepted = [_patient] call ACME_fnc_headElevApplyTilt;' in tandem
    assert '[_medic, _patient] call ACME_fnc_headElevMedicStart;' in tandem
    assert 'ACME_headElev_pendingLift", [], true' in tandem
    assert 'headElevMedicReady' not in tandem


def test_provider_sequence_is_presentation_only_and_not_bound_to_menu_lifetime():
    seq=read("headElevMedicSeq")
    assert 'params [' in seq
    assert '["_mode", "elevate"' in seq
    assert 'headElevMedicReady' not in seq
    assert 'ACME_headElev_pendingMove' not in seq
    assert 'ace_medical_gui_menuDisplay' not in seq
    assert '_watchMenu' not in seq
    assert 'private _hardDeadline = CBA_missionTime + 6.0;' in seq
    assert 'call ACME_fnc_headElevateCancelSeq;' in seq  # movement cancellation remains provider-only


def test_lower_suspend_and_resume_never_insert_a_body_roll():
    for name in ("headElevateStop","headElevSuspend","headElevResume"):
        source=read(name)
        assert 'ACME_fnc_chestSealRoll' not in source, name
        assert 'ACME_fnc_chestSealActualSide' not in source, name
    stop=read("headElevateStop")
    assert '[_medic, "lower"] call ACME_fnc_headElevMedicSeq;' in stop
    assert '[_patient, "ACME_HeadElevPatientRelease", 2, "head-elev-lower"' in stop


def test_interrupted_lift_always_retires_its_own_patient_lease():
    tilt=read("headElevApplyTilt")
    release='[_patient, _animToken] call ACME_fnc_patientAnimRelease;'
    logical='if (!alive _patient || {_replacementPlacement}'
    assert release in tilt and logical in tilt
    assert tilt.index(release) < tilt.index(logical)
    assert '[_patient, true] call ACME_fnc_headElevCollision;' in tilt
    assert '_visualAccepted = false;' in tilt
    assert 'true\n' in tilt[-20:]


def test_lower_head_can_supersede_inflight_lift_without_waiting():
    stop=read("headElevateStop")
    assert '(_activePatientLock param [1, ""]) == "head-elev-lift"' in stop
    assert '[_patient, _liftToken] call ACME_fnc_patientAnimRelease;' in stop
    assert '[_patient, true] call ACME_fnc_headElevCollision;' in stop


def test_reentry_waits_for_previous_patient_animation_to_retire():
    can=read("headElevateCanStart")
    assert 'ACME_patientAnimLock' in can
    assert '_until > serverTime' in can
    resume=read("headElevTryResume")
    assert 'ACME_patientAnimLock' in resume
    assert '_lockUntil > serverTime' in resume


def test_stale_provider_and_continuous_locks_cannot_disable_future_treatments():
    treatment=(CORE/"fnc_treatment.sqf").read_text(encoding="utf-8")
    assert 'ACME_headElev_seqActive' in treatment
    assert 'call ACME_fnc_headElevateCancelSeq;' in treatment
    assert 'ACM_core_ContinuousAction_LastSeen' in treatment
    assert '(CBA_missionTime - _lastSeen) > 4' in treatment
    assert 'missionNamespace setVariable ["ACM_core_ContinuousAction_Active", false];' in treatment


def test_obsolete_pending_lift_watchdog_is_gone():
    watch=read("headElevWatch")
    assert 'headElevMedicReady' not in watch
    assert 'ACME_headElev_pendingLift' not in watch


def test_stale_stance_ownership_is_heartbeat_bounded():
    stance=(FUN/"fn_providerStanceOwned.sqf").read_text(encoding="utf-8")
    assert 'ACME_headElev_seqLastSeen' in stance
    assert '(CBA_missionTime - _headSeen) <= 1' in stance
    assert 'ACM_core_ContinuousAction_LastSeen' in stance
    assert '(CBA_missionTime - _lastSeen) <= 4' in stance
