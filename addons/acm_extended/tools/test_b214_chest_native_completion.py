"""Execute native-exit clock anchoring with explicit animation/clock boundaries.

The existing B213 SQF-VM fixture records requested moves and carrier readiness.
It does not render RTMs or prove the engine's native animation graph.
"""
import pytest

from test_b213_chest_exit import END, FIRST, REST, provider_setup
from test_menu_death_lifecycle import execute


def observed_late():
    return f'''
        [_medic,"chestsealexit","close1"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0;
        [_job] call _tick;
        CBA_missionTime=10.2;
        _anim=toLower "{END}"; _nativeElapsed=0.3;
        [_job] call _tick;
    '''


@pytest.mark.parametrize("neutral", [REST, "AidlPknlMstpSnonWnonDnon_AI"])
def test_observed_native_completion_survives_late_first_frame_and_native_idle(neutral):
    execute(provider_setup()+observed_late()+f'''
        CBA_missionTime=11.2; _nativeElapsed=1.8;
        [_job] call _tick;
        [count _moves==1,"carrier reach started before native exit finished"] call _check;
        [!((_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2),"carrier gate released before native exit finished"] call _check;
        CBA_missionTime=11.34; _anim=toLower "{neutral}";
        [_job] call _tick;
        [count _moves==2 && {{(_moves select 1 select 1)=="{FIRST}"}},"completed native exit misclassified as interruption"] call _check;
        [(_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2,"completed native exit retained carrier gate"] call _check;
    ''')


def test_early_neutral_transition_is_still_an_interruption():
    execute(provider_setup()+observed_late()+f'''
        CBA_missionTime=10.3; _anim=toLower "{REST}";
        _moves=[]; [_job] call _tick;
        [count _moves==0,"early idle invented completed exit or carrier reach"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"interrupted exit retained provider sequence"] call _check;
    ''')


def test_elapsed_native_progress_cannot_turn_unrelated_motion_into_success():
    execute(provider_setup()+observed_late()+'''
        CBA_missionTime=11.5; _anim="weapon-reload";
        _moves=[]; [_job] call _tick;
        [count _moves==0,"late unrelated motion appended carrier reach"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"unrelated successor retained old sequence"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_input setVariable ["MoveForward",1];',
    '_medic setVariable ["ACME_treatmentPoseState",[99,"scope"]];',
    '_medic setVariable ["ACME_headElev_medicAnimToken",99];',
])
def test_cancellation_and_successor_ownership_precede_native_completion(change):
    execute(provider_setup()+observed_late()+f'''
        CBA_missionTime=11.5; _anim=toLower "{REST}";
    '''+change+f'''
        _moves=[]; [_job] call _tick;
        [(_moves findIf {{(_x select 1)=="{FIRST}"}})<0,"old exit appended reach after cancellation or replacement"] call _check;
    ''')


def test_native_elapsed_remains_authoritative_when_wall_clock_runs_ahead():
    execute(provider_setup()+observed_late()+'''
        CBA_missionTime=11.5; _nativeElapsed=1.8;
        [_job] call _tick;
        [count _moves==1,"wall clock clipped unfinished native exit"] call _check;
        [!((_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2),"unfinished native exit released carrier gate"] call _check;
    ''')


@pytest.mark.parametrize("unavailable", ["0", "-1", '"unavailable"'])
def test_unavailable_native_elapsed_does_not_destroy_the_last_valid_clock_anchor(unavailable):
    execute(provider_setup()+observed_late()+f'''
        CBA_missionTime=10.4; _nativeElapsed={unavailable};
        [_job] call _tick;
        [count _moves==1,"unavailable native elapsed completed exit early"] call _check;
        CBA_missionTime=11.34; _anim=toLower "{REST}";
        [_job] call _tick;
        [count _moves==2 && {{(_moves select 1 select 1)=="{FIRST}"}},"invalid native elapsed discarded last valid progress"] call _check;
    ''')
