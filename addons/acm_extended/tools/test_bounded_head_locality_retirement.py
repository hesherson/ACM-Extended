"""Former owner retires private state without publishing animation cleanup.
Locality/animation/network boundaries are fixtures, not real ownership migration.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_head_cancel_generation import setup
from test_bounded_head_provider_sequence import begin


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('stage',[-1,0,1,2])
def test_lost_locality_clears_private_state_without_global_animation_writes(mode,stage):
    execute(setup()+begin(mode)+f'''
        (_job select 2) set [7,{stage}];
        _medic setVariable ["ACME_headElev_medicAnimStage",{stage}];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Paused",true];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","acme_elevatehead"];
        private _token=_medic getVariable ["ACME_headElev_medicAnimToken",-99];
        private _pin=_medic getVariable ["ACME_headElev_pinToken",-99];
        _local=false;_moves=[];_stances=[];_events=[];_waits=[];_removed=[];
        [_job] call _tick;
        [_removed isEqualTo [100],"former-owner PFH not retired"] call _check;
        [count _events==0 && {{count _moves==0}} && {{count _stances==0}} && {{count _waits==0}},"former owner issued animation/stance cleanup"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"former owner left private active flag"] call _check;
        [(_medic getVariable ["ACME_headElev_seqMode",""])=="" && {{(_medic getVariable ["ACME_headElev_medicAnimStage",99])==-1}},"former owner left private mode/stage"] call _check;
        [!(_medic getVariable ["ACME_DP_Paused",true]) && {{!(_medic getVariable ["ACME_DP_TreatmentBusy",true])}},"former owner left private pressure pause"] call _check;
        [(_medic getVariable ["ACME_headElev_medicAnimToken",-98])==_token && {{(_medic getVariable ["ACME_headElev_pinToken",-98])==(_pin+1)}},"former owner lost private pin retirement"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_still_local_invalid_provider_keeps_existing_state_retirement(mode):
    execute(setup()+begin(mode)+'''
        _medic setVariable ["ACE_isUnconscious",true];
        _moves=[];_events=[];_removed=[];
        [_job] call _tick;
        [_removed isEqualTo [100] && {!(_medic getVariable ["ACME_headElev_seqActive",true])},"local invalid provider failed to retire"] call _check;
        [count _moves==0 && {count _events==1},"local invalid cleanup changed"] call _check;
        call _patientUntouched;
    ''')
