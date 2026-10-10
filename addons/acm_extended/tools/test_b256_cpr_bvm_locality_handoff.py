"""B256: CPR and delayed BVM->CPR transitions cannot outlive provider locality."""
from pathlib import Path

from test_cpr_lifecycle import execute as cpr_execute
from test_menu_death_lifecycle import adapt, execute

BASE=Path(__file__).resolve().parents[2]


def test_cpr_away_back_transfer_releases_only_original_episode():
    cpr_execute(r"""
        call _start; call _enter;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        call _tick;
        call _freed;
        [_bvmHandoff==0,"stale CPR resumed BVM swap after transfer"] call _check;
    """)


def test_cpr_matching_owner_continues_and_can_exit_normally():
    cpr_execute(r"""
        call _start; call _enter;
        call _tick;
        [(_patient getVariable ["ACM_circulation_CPR_Medic",objNull]) isEqualTo _medic,
            "healthy owner incorrectly lost CPR"] call _check;
        call _cancel;
        call _freed;
    """)


def _bvm_handoff_fixture():
    src=(BASE/"breathing"/"functions"/"fnc_useBVM.sqf").read_text(encoding="utf-8-sig")
    first='        private _localityEpoch = _medic getVariable ["ACME_providerLocalityEpoch", 0];'
    last='        }, [_medic, _patient, _epoch, _localityEpoch], 0.1] call CBA_fnc_waitAndExecute;'
    block=src[src.index(first):src.index(last,src.index(first))+len(last)]
    # Arma supplies distance2D for objects; SQF-VM fixture uses namespaces.
    # Preserve the production range gate but supply the existing test distance.
    block=block.replace("_medic distance2D _patient", "_distance")
    return (
        'private _epoch=4; private _handoff=0; '
        'ACM_core_ContinuousAction_Epoch=4; ACM_core_ContinuousAction_Active=false; '
        'ace_common_fnc_isAwake={true}; '
        'ACM_circulation_fnc_beginCPR={_handoff=_handoff+1;}; '
        'private _schedule={'+adapt(block)+'}; '
    )


def test_stale_bvm_handoff_cannot_start_cpr_after_owner_roundtrip():
    execute(_bvm_handoff_fixture()+r"""
        call _schedule;
        [count _waits==1,"BVM swap did not schedule its bounded callback"] call _check;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        private _job=_waits select 0;
        (_job select 1) call (_job select 0);
        [_handoff==0,"stale BVM callback launched CPR on returned provider"] call _check;
    """)


def test_matching_bvm_handoff_still_starts_cpr():
    execute(_bvm_handoff_fixture()+r"""
        call _schedule;
        private _job=_waits select 0;
        (_job select 1) call (_job select 0);
        [_handoff==1,"healthy BVM swap no longer enters CPR"] call _check;
    """)


def test_newer_continuous_action_blocks_old_bvm_handoff():
    execute(_bvm_handoff_fixture()+r"""
        call _schedule;
        ACM_core_ContinuousAction_Epoch=5;
        private _job=_waits select 0;
        (_job select 1) call (_job select 0);
        [_handoff==0,"old BVM swap entered a newer continuous action"] call _check;
    """)


def test_source_handoff_and_cpr_worker_check_locality_generation():
    bvm=(BASE/"breathing"/"functions"/"fnc_useBVM.sqf").read_text(encoding="utf-8-sig")
    cpr=(BASE/"circulation"/"functions"/"fnc_beginCPR.sqf").read_text(encoding="utf-8-sig")
    assert 'params ["_medic", "_patient", "_epoch", "_localityEpoch"];' in bvm
    assert '[_medic, _patient, _epoch, _localityEpoch], 0.1]' in bvm
    assert '(_medic getVariable ["ACME_providerLocalityEpoch", 0]) != _localityEpoch' in bvm
    assert '"_lowerOwner", "_localityEpoch"];' in cpr
    assert '_lowerRetries, _lowerOwner, _localityEpoch]] call CBA_fnc_addPerFrameHandler;' in cpr
    assert '(_medic getVariable ["ACME_providerLocalityEpoch", 0]) != _localityEpoch' in cpr
