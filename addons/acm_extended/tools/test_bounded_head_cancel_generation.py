"""Execute real cancel/start callbacks through recorded engine boundaries.

CBA handles are unique fixtures here. No live input, PhysX, scheduling or
ownership migration is simulated; the delayed deliveries are explicit.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_head_provider_consciousness import setup as old_setup
from test_bounded_head_provider_sequence import begin, finish, REST


def setup():
    return old_setup()+'''
        CBA_fnc_addPerFrameHandler={
            private _handle=100+count _jobs;
            _jobs pushBack (_this+[_handle]);
            _handle
        };
        private _tick={params ["_job"]; [_job select 2,_job select 3] call (_job select 0);};
    '''


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('stage',[-1,0,1,2])
@pytest.mark.parametrize('seed',[-1,11])
def test_repeated_cancel_restart_never_reuses_a_still_pending_controller_generation(mode,stage,seed):
    execute(setup()+f'''
        _medic setVariable ["ACME_headElev_medicAnimToken",{seed}];
        for "_i" from 0 to 2 do {{
            [_medic,"{mode}"] call ACME_fnc_headElevMedicSeq;
            call ACME_fnc_headElevateCancelSeq;
        }};
        [_medic,"{mode}"] call ACME_fnc_headElevMedicSeq;
        private _current=_medic getVariable ["ACME_headElev_medicAnimToken",-99];
        private _pin=_medic getVariable ["ACME_headElev_pinToken",-99];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Paused",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","acme_elevatehead"];
        _moves=[];_stances=[];_events=[];_removed=[];_waits=[];
        _weapon="rifle";_anim=toLower "{REST}";CBA_missionTime=100;
        {{
            (_x select 2) set [7,{stage}];
            (_x select 2) set [8,true];
            [_x] call _tick;
        }} forEach (_jobs select [0,3]);
        [_removed isEqualTo [100,101,102],"stale handles not retired individually"] call _check;
        [count _moves==0 && {{count _stances==0}} && {{count _events==0}} && {{count _waits==0}} && {{_weapon=="rifle"}},"cancel-restart reused generation and altered later provider"] call _check;
        [_medic getVariable ["ACME_headElev_seqActive",false],"old controller retired later sequence"] call _check;
        [(_medic getVariable ["ACME_headElev_medicAnimToken",-99])==_current && {{(_medic getVariable ["ACME_headElev_pinToken",-99])==_pin}},"old controller changed later tokens"] call _check;
        [_medic getVariable ["ACME_DP_Paused",false],"old controller released later DP pause"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('later',['finish','cancel'])
def test_old_cancel_release_does_not_run_after_a_new_sequence_has_already_ended(mode,later):
    end=finish() if later=='finish' else 'call ACME_fnc_headElevateCancelSeq;'
    execute(setup()+begin(mode)+'''
        call ACME_fnc_headElevateCancelSeq;
        private _oldRelease=_waits select 0;
        _jobs=[];_moves=[];_stances=[];_waits=[];_removed=[];_prep=0;
        _weapon="rifle";_anim="idle";CBA_missionTime=10;
    '''+begin(mode)+end+'''
        private _currentRelease=_waits select 0;
        _stances=[];
        [_oldRelease] call _deliver;
        [count _stances==0,"old cancel released stance after a newer completed episode"] call _check;
        _stances=[];
        [_currentRelease] call _deliver;
        [_stances isEqualTo ["AUTO"],"current completion lost its release"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_duplicate_cancel_is_noop_and_current_cancel_keeps_exact_authored_exit(mode):
    execute(setup()+begin(mode)+f'''
        _moves=[];_stances=[];_waits=[];
        call ACME_fnc_headElevateCancelSeq;
        private _token=_medic getVariable ["ACME_headElev_medicAnimToken",-99];
        private _pin=_medic getVariable ["ACME_headElev_pinToken",-99];
        call ACME_fnc_headElevateCancelSeq;
        [(_medic getVariable ["ACME_headElev_medicAnimToken",-98])==_token && {{(_medic getVariable ["ACME_headElev_pinToken",-98])==_pin}},"duplicate cancel changed ownership"] call _check;
        [_moves isEqualTo [[_medic,"{REST}",2]] && {{_stances isEqualTo ["MIDDLE"]}},"normal cancel choreography changed"] call _check;
        [count _waits==1 && {{(_waits select 0 select 2)==0.25}},"normal cancellation delay changed"] call _check;
        [_waits select 0] call _deliver;
        [_stances isEqualTo ["MIDDLE","AUTO"],"current cancel left provider locked"] call _check;
        call _patientUntouched;
    ''')
