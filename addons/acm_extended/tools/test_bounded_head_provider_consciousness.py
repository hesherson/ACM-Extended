"""Run actual provider controller/cancel code; unconscious provider is not a patient guard.

Animation, time, vehicles and keys are recorded engine substitutes, not live Arma.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute
from test_bounded_head_completion import source
from test_bounded_head_provider_sequence import setup as controller_setup, begin, finish, REST


def setup():
    s=source('headElevateCancelSeq')
    for name in ('_medic','_m'):
        for old,new in (
            ('local '+name,'_local'),('alive '+name,'_alive'),
            ('objectParent '+name,'_parent'),
            (name+' selectWeapon "";', '_weapon="";'),
            (name+' setUnitPos "MIDDLE";', '_stances pushBack "MIDDLE";'),
            (name+' setUnitPos "AUTO";', '_stances pushBack "AUTO";'),
        ):
            s=re.sub(re.escape(old)+(r'\b' if old[-1].isalnum() else ''),lambda _:new,s)
    return controller_setup()+'ACME_fnc_headElevateCancelSeq={'+adapt(s)+'};\n'+'''
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_poseToken","casualty:original"];
        private _patientUntouched={
            [_patient getVariable ["ACME_headElevated",false],"provider cleanup lowered casualty"] call _check;
            [(_patient getVariable ["ACME_headElev_poseToken",""])=="casualty:original","provider cleanup touched placement"] call _check;
        };
    '''


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('local',[False,True])
def test_already_unconscious_provider_never_acquires_or_dispatches_sequence(mode,local):
    execute(setup()+f'''
        _local={str(local).lower()};
        _medic setVariable ["ACE_isUnconscious",true];
        [_medic,"{mode}"] call ACME_fnc_headElevMedicSeq;
        [count _jobs==0 && {{_prep==0}} && {{count _events==0}},"unconscious entry acquired presentation"] call _check;
        [(_medic getVariable ["ACME_headElev_medicAnimToken",-1])==-1,"rejected entry wrote token"] call _check;
        [_weapon=="rifle" && {{count _moves==0}} && {{count _stances==0}},"rejected entry altered provider"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('stage',[-1,0,1,2])
def test_unconsciousness_at_each_stage_retires_without_any_new_pose_or_weapon_request(mode,stage):
    execute(setup()+begin(mode)+f'''
        (_job select 2) set [7,{stage}];
        CBA_missionTime=20;
        _moves=[]; _stances=[]; _waits=[]; _weapon="rifle"; _anim="unconscious";
        _medic setVariable ["ACE_isUnconscious",true];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","acme_elevatehead"];
        _medic setVariable ["ACME_DP_Paused",true];
        [_job] call _tick;
        [count _moves==0 && {{count _stances==0}} && {{count _waits==0}} && {{_weapon=="rifle"}},"unconscious interruption requested upright theatre"] call _check;
        [_removed isEqualTo [73],"interrupted PFH not retired"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"interrupted active state leaked"] call _check;
        [(_medic getVariable ["ACME_headElev_medicAnimStage",99])==-1,"interrupted stage leaked"] call _check;
        [!(_medic getVariable ["ACME_DP_Paused",true]),"existing DP pause cleanup lost"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_provider_falls_unconscious_after_finish_before_stance_release(mode):
    execute(setup()+begin(mode)+finish()+'''
        _stances=[];
        _medic setVariable ["ACE_isUnconscious",true];
        [_waits select 0] call _deliver;
        [count _stances==0,"finished sequence changed unconscious stance"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_explicit_cancel_cleans_ownership_without_crouching_unconscious_provider(mode):
    execute(setup()+begin(mode)+'''
        _moves=[]; _stances=[]; _waits=[]; _weapon="rifle";
        _medic setVariable ["ACE_isUnconscious",true];
        call ACME_fnc_headElevateCancelSeq;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"cancel left sequence active"] call _check;
        [count _moves==0 && {count _stances==0} && {count _waits==0} && {_weapon=="rifle"},"cancel animated unconscious provider"] call _check;
        [_job] call _tick;
        [_removed isEqualTo [73],"cancelled PFH survived token retirement"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('later_unconscious',[False,True])
def test_conscious_cancel_keeps_crouch_and_gates_its_delayed_release(mode,later_unconscious):
    execute(setup()+begin(mode)+f'''
        _moves=[]; _stances=[]; _waits=[];
        call ACME_fnc_headElevateCancelSeq;
        [_moves isEqualTo [[_medic,"{REST}",2]],"normal cancellation crouch changed"] call _check;
        [_stances isEqualTo ["MIDDLE"],"normal cancellation stance changed"] call _check;
        [count _waits==1 && {{(_waits select 0 select 2)==0.25}},"normal cancellation delay changed"] call _check;
        _stances=[];
        _medic setVariable ["ACE_isUnconscious",{str(later_unconscious).lower()}];
        [_waits select 0] call _deliver;
        [_stances isEqualTo {('[]' if later_unconscious else '["AUTO"]')},"incorrect post-cancel stance release"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_dead_casualty_does_not_block_conscious_provider_sequence(mode):
    execute(setup()+'_patientAlive=false;'+begin(mode)+finish()+'''
        [count _moves==4 && {_removed isEqualTo [73]},"provider life check became casualty exclusion"] call _check;
        [_waits select 0] call _deliver;
        [(_stances select ((count _stances)-1))=="AUTO","normal conscious finish remained locked"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_newer_token_is_not_retired_by_old_unconscious_tick(mode):
    execute(setup()+begin(mode)+'''
        _medic setVariable ["ACME_headElev_medicAnimToken",99];
        _medic setVariable ["ACE_isUnconscious",true];
        _moves=[]; _events=[]; _stances=[];
        [_job] call _tick;
        [_removed isEqualTo [73],"old PFH survived"] call _check;
        [_medic getVariable ["ACME_headElev_seqActive",false],"old callback cleared newer sequence"] call _check;
        [count _moves==0 && {count _events==0} && {count _stances==0},"old callback affected newer owner"] call _check;
        call _patientUntouched;
    ''')
