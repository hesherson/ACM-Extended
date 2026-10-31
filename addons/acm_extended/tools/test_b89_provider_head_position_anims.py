from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(path):
    return read_source(ROOT / path, encoding="utf-8", errors="ignore")

def assert_provider_choreography():
    # Execute the current provider controller with native animation, input and
    # scheduler boundaries recorded. This proves requested actor poses and
    # ownership cleanup; it does not certify RTM playback or live networking.
    from test_bounded_head_provider_sequence import (
        provider_contract,
        test_both_modes_request_each_move_at_most_once_then_release_crouch,
        test_superseded_provider_pfh_removes_itself_without_animation_or_state_writes,
        test_delayed_stance_release_respects_current_owner_and_context,
    )
    from test_b212_prone_providers import (
        test_prone_head_provider_sequence_completes_without_waiting_on_kneeling_edges,
        test_prone_head_cancel_preserves_posture_and_old_release_cannot_touch_restart,
    )
    from test_bounded_head_pose_contracts import assert_connected_patient_states
    provider_contract()
    assert_connected_patient_states()
    for mode in ('elevate','lower'):
        for adopt in (False,True):
            test_both_modes_request_each_move_at_most_once_then_release_crouch(mode,adopt)
        test_prone_head_provider_sequence_completes_without_waiting_on_kneeling_edges(mode)
    for stage in (0,1,2):
        test_superseded_provider_pfh_removes_itself_without_animation_or_state_writes(stage)
    for change in (
        '_local=false;',
        '_medic setVariable ["ACME_headElev_medicAnimToken",99];',
        '_stanceOwned=true;',
    ):
        test_delayed_stance_release_respects_current_owner_and_context(change)
    test_prone_head_cancel_preserves_posture_and_old_release_cannot_touch_restart()


def main():
    seq = txt("functions/fn_headElevMedicSeq.sqf")
    start = txt("functions/fn_headElevMedicStart.sqf")
    stop = txt("functions/fn_headElevateStop.sqf")
    post = txt("functions/fn_postInit.sqf")
    cfg = txt("config.cpp")

    first = "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown"
    second = "AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon"
    rest = "AmovPknlMstpSnonWnonDnon"

    # Elevate and lower call the same controller; mode is retained only for call-site/state labeling.
    assert '[_medic, "elevate"] call ACME_fnc_headElevMedicSeq;' in start
    assert '[_medic, "lower"] call ACME_fnc_headElevMedicSeq;' in stop

    # The shared controller resolves both modes for the actor posture. Observable
    # entry/return and stale ownership behavior execute through the CLI gate.
    assert f'private _forcePose = _rest;' in seq
    assert_provider_choreography()
    assert "DraggerBasenon" not in seq
    assert "AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon" not in seq
    assert '_u setUnitPos "UP";' not in seq

    # Kneeling Putdown requests remain at one site each; the execution cases
    # additionally protect conditional return adoption and supported prone poses.
    assert seq.count('[_u, _first, 2] call ACME_fnc_doAnim;') == 1
    assert seq.count('[_u, _second, 2] call ACME_fnc_doAnim;') == 1
    assert '_u selectWeapon "";' in seq
    assert '[_u, _rest, 2] call ACME_fnc_doAnim;' in seq

    # Patient path remains present at its existing call site and its animation classes remain untouched.
    assert 'call ACME_fnc_patientAnimRequest;' in stop
    assert 'class ACME_HeadElevPatientGrab: AinjPpneMrunSnonWnonDb_grab' in cfg
    assert 'class ACME_HeadElevPatientRelease: AinjPpneMrunSnonWnonDb_release' in cfg

    assert_release_identity()

    print("B89 posture-aware shared provider Putdown sequence: PASS")

if __name__ == "__main__":
    main()
