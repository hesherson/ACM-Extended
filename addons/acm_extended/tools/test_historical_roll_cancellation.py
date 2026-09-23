"""Execute provider-roll ownership and synchronous patient cancellation.

The real pose controller and roll functions run in SQF-VM. Engine animation,
stance, locality, input and network delivery remain explicit fixtures. No RTM
rendering or dedicated-server cancellation is claimed.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute
from test_historical_pose_lifecycle import setup as pose_setup, pose_source, source
from test_historical_chest_workspace import setup as chest_setup, code as chest_code


def provider_setup():
    text = pose_source('rollProviderStart')
    text = re.sub(r'inputAction "[^"]+"', '_movement', text)
    cancel = pose_source('rollProviderCancel').replace('_medic switchMove "";', '_hardStops pushBack "";')
    return pose_setup() + '''
        private _movement=0; private _hardStops=[];
        ACME_fnc_rollProviderStart={''' + text + '''};
        ACME_fnc_rollProviderCancel={''' + cancel + '''};
    '''


@pytest.mark.parametrize('stance', ['CROUCH', 'STAND', 'PRONE'])
def test_roll_enters_shared_empty_hand_medic4_with_current_timeline(stance):
    execute(provider_setup() + f'_stance="{stance}";' + '''
        private _started=[_medic,"chestSealFlip",_patient] call ACME_fnc_rollProviderStart;
        [_started,"roll did not acquire"] call _check;
        private _pose=_medic getVariable ["ACME_treatmentPoseState",[]];
        [(_pose select 1)=="roll" && {(_pose select 2)=="AinvPknlMstpSnonWnonDnon_medic4"},"wrong current roll work state"] call _check;
        [(_pose select 11)==2.2,"retired hold timeline restored"] call _check;
        [_preps==1,"weapon preflight did not run exactly once"] call _check;
        [(_medic getVariable ["ACME_rollProviderSource",""])=="chestSealFlip","wrong roll source"] call _check;
        private _id=_pose select 5;
    ''' + ('' if stance == 'CROUCH' else '''
        [(_pose select 3)==-2,"missing crouch preparation"] call _check;
        [count _moves==1 && {((_moves select 0) select 2)==1},"wrong prep priority"] call _check;
        CBA_missionTime=12; [_id] call _poseTick;
    ''') + '''
        [((_moves select (count _moves-1)) select 1)=="AinvPknlMstpSnonWnonDnon_medic4"
            && {((_moves select (count _moves-1)) select 2)==1},"work entry did not use priority one"] call _check;
        [count _hardStops==0 && {count _seeks==0},"normal entry used hard cancellation"] call _check;
        private _timer=_waits select (count _waits-1);
        [abs ((_timer select 2)-4.7)<0.000001,"fail-safe margin confused with work duration"] call _check;
    ''')


@pytest.mark.parametrize('source', ['chestSealFlip', 'stethoscopeFlip', 'headElevFrontRoll'])
def test_wrong_source_cancel_is_a_noop_and_matching_cancel_retires_immediately(source):
    execute(provider_setup() + f'[_medic,"{source}",_patient] call ACME_fnc_rollProviderStart;' + '''
        private _pose=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
        private _token=_medic getVariable "ACME_rollProviderToken";
        private _pfh=_medic getVariable "ACME_rollProviderPFH";
        _moves=[]; _events=[]; _removed=[]; _positions=[];
        [!([_medic,"wrong-source"] call ACME_fnc_rollProviderCancel),"wrong source accepted"] call _check;
        [(_medic getVariable "ACME_rollProviderToken")==_token && {(_medic getVariable "ACME_treatmentPoseState") isEqualTo _pose},"wrong source changed episode"] call _check;
        [count _moves==0 && {count _removed==0} && {count _hardStops==0},"wrong source had side effects"] call _check;
    ''' + f'[[ _medic,"{source}"] call ACME_fnc_rollProviderCancel,"matching cancellation rejected"] call _check;' + '''
        [(_medic getVariable "ACME_rollProviderToken")=="" && {!(_medic getVariable "ACME_rollProviderActive")},"roll ownership retained"] call _check;
        [_pfh in _removed && {(_pose select 5) in _removed},"roll or pose worker retained"] call _check;
        [(_medic getVariable "ACME_treatmentPoseState") isEqualTo [],"pose not cleared synchronously"] call _check;
        [count _hardStops==1 && {_speed==1} && {"AUTO" in _positions},"explicit cancel did not release current control"] call _check;
        private _effects=[count _moves,count _removed,count _hardStops,count _events];
    ''' + f'[!([_medic,"{source}"] call ACME_fnc_rollProviderCancel),"duplicate cancel accepted"] call _check;' + '''
        [[count _moves,count _removed,count _hardStops,count _events] isEqualTo _effects,"duplicate cancel repeated cleanup"] call _check;
    ''')


@pytest.mark.parametrize('delivery', ['timer', 'worker'])
def test_old_roll_completion_cannot_retire_replacement_provider_episode(delivery):
    execute(provider_setup() + '''
        [_medic,"chestSealFlip",_patient] call ACME_fnc_rollProviderStart;
        private _oldTimer=_waits select (count _waits-1);
        private _oldId=_medic getVariable "ACME_rollProviderPFH";
        [_medic,"chestSealFlip"] call ACME_fnc_rollProviderCancel;
        _nowTime=11;
        [_medic,"stethoscopeFlip",_patient] call ACME_fnc_rollProviderStart;
        private _newPose=+(_medic getVariable "ACME_treatmentPoseState");
        private _newToken=_medic getVariable "ACME_rollProviderToken";
        private _newId=_medic getVariable "ACME_rollProviderPFH";
        _moves=[]; _events=[]; _removed=[]; _hardStops=[];
    ''' + ('[_oldTimer] call _deliver;' if delivery == 'timer' else '[_oldId] call _poseTick;') + '''
        [(_medic getVariable "ACME_rollProviderToken")==_newToken && {(_medic getVariable "ACME_treatmentPoseState") isEqualTo _newPose},"old completion retired replacement"] call _check;
        [!(_newId in _removed) && {count _moves==0} && {count _events==0} && {count _hardStops==0},"old completion touched replacement presentation"] call _check;
    ''')


def patient_setup():
    text = chest_code('patientRollCancel')
    text = text.replace('_patient switchMove _hold;', '_patientStops pushBack _hold;')
    text = text.replace('_patient switchMove "";', '_patientStops pushBack "";')
    return chest_setup() + '''
        private _patientStops=[];
        ACME_fnc_patientRollCancel={''' + text + '''};
        _patient setVariable ["ACME_CS_rollToken","old-roll"];
        _patient setVariable ["ACME_CS_rollUntil",12];
    '''


@pytest.mark.parametrize('side,rest', [('front','ACM_LyingState'),('back','ace_medical_engine_uncon_anim_1')])
@pytest.mark.parametrize('condition', ['unconscious','awake','dead','vehicle'])
def test_patient_cancel_releases_lease_and_uses_only_appropriate_stable_rest(side, rest, condition):
    flags = {
        'unconscious': '_patient setVariable ["ACE_isUnconscious",true];',
        'awake': '', 'dead': '_patientAlive=false;',
        'vehicle': '_parent=missionNamespace; _patient setVariable ["ACE_isUnconscious",true];',
    }[condition]
    expect = ('["' + rest + '"]') if condition == 'unconscious' else ('[""]' if condition == 'awake' else '[]')
    execute(patient_setup()+flags+f'[[ _patient,"{side}"] call ACME_fnc_patientRollCancel,"active cancellation rejected"] call _check;'+'''
        [(_patient getVariable "ACME_CS_rollToken")=="" && {(_patient getVariable "ACME_CS_rollUntil")==-1},"pending patient callbacks not invalidated"] call _check;
        [_releases isEqualTo [[_patient,"old-roll"]],"wrong patient animation lease released"] call _check;
    '''+f'[_patientStops isEqualTo {expect},"wrong cancellation pose for clinical context"] call _check;'+'''
        private _effects=[count _releases,count _patientStops,count _events];
        [!([_patient,"front"] call ACME_fnc_patientRollCancel),"inactive roll accepted"] call _check;
        [[count _releases,count _patientStops,count _events] isEqualTo _effects,"duplicate patient cleanup repeated"] call _check;
    ''')


def test_remote_patient_cancellation_forwards_explicit_supine_target_without_local_mutation():
    execute(patient_setup()+'''
        _patientLocal=false;
        [[_patient,"front"] call ACME_fnc_patientRollCancel,"remote cancellation did not route"] call _check;
        [_events isEqualTo [[_patient,"patientRollCancel",[_patient,"front"]]],"remote cancellation lost explicit supine target"] call _check;
        [(_patient getVariable "ACME_CS_rollToken")=="old-roll" && {count _releases==0} && {count _patientStops==0},"remote patient changed locally"] call _check;
    ''')


def flip_setup():
    functions = ''
    for name in ('chestSealFlip','chestSealFlipTick'):
        text = source(name)
        for old,new in [('local _provider','_providerLocal'), ('objectParent _provider','_providerParent'),
                        ('animationState _provider','_providerAnimation'), ('_provider distance _patient','_distance'),
                        ('lifeState _patient','_lifeState'), ('finite _rollTime','(_rollTime call _finite)')]:
            text = text.replace(old,new)
        text = adapt(text)
        text = re.sub(r'private (_button|_b) = _\w+ displayCtrl \d+;', r'private \1 = objNull;', text)
        text = re.sub(r'_(button|b) ctrlEnable ([^;]+);', r'_buttonStates pushBack (\2);', text)
        text = re.sub(r'_(button|b) ctrlSetText [^;]+;', '', text)
        text = text.replace('local _provider','_providerLocal').replace('objectParent _provider','_providerParent')
        text = text.replace('animationState _provider','_providerAnimation').replace('_provider distance _patient','_distance')
        functions += 'ACME_fnc_'+name+'={'+text+'};'
    return chest_setup() + '''
        private _providerLocal=true; private _providerParent=objNull;
        private _providerAnimation="prep"; private _presentationAvailable=true;
        private _buttonStates=[]; private _rendered=0; private _resumed=0;
        ACME_fnc_chestSealRender={_rendered=_rendered+1;};
        ACME_fnc_treatmentPoseStop={};
        ACME_fnc_chestSealProviderHoldStart={_resumed=_resumed+1; 43};
        // Acquisition is a boundary fixture; provider_start is executed above.
        ACME_fnc_rollProviderStart={
            if (!_presentationAvailable) exitWith {false};
            _medic setVariable ["ACME_treatmentPoseState",[42,"roll","AinvPknlMstpSnonWnonDnon_medic4",-2]];
            _medic setVariable ["ACME_rollProviderToken","roll:42"];
            true
        };
        _patient setVariable ["ACE_isUnconscious",true];
        uiNamespace setVariable ["ACME_CS_Patient",_patient];
        uiNamespace setVariable ["ACME_CS_Medic",_medic];
        uiNamespace setVariable ["ACME_CS_DLG",missionNamespace];
        uiNamespace setVariable ["ACME_CS_SessionToken","session:1"];
        uiNamespace setVariable ["ACME_CS_Side","front"];
        private _flipTick={
            private _id=uiNamespace getVariable ["ACME_CS_FlipPFH",-1];
            private _h=_handlers select _id;
            [_h select 1,_id] call (_h select 0);
        };
    ''' + functions


@pytest.mark.parametrize('stage',[-2,-1,0,1,2])
@pytest.mark.parametrize('observed',['prep','ainvpknlmstpsnonwnondnon_medic4'])
def test_physical_roll_waits_for_observed_work_and_dispatches_only_once(stage,observed):
    expected = int(stage >= 1 and observed == 'ainvpknlmstpsnonwnondnon_medic4')
    execute(flip_setup()+'''
        [] call ACME_fnc_chestSealFlip;
        [count _rolls==0,"successful provider acquisition rolled from the button"] call _check;
        private _pose=_medic getVariable "ACME_treatmentPoseState";
    '''+f'_pose set [3,{stage}]; _providerAnimation="{observed}";'+'''
        call _flipTick; call _flipTick;
    '''+f'[count _rolls=={expected},"prep/observed-state gating or one-shot dispatch changed"] call _check;')


@pytest.mark.parametrize('change',['none','session','token'])
def test_presentation_acquisition_failure_retains_one_physical_roll_and_scoped_completion(change):
    mutate = {'none':'','session':'uiNamespace setVariable ["ACME_CS_SessionToken","session:2"];',
              'token':'uiNamespace setVariable ["ACME_CS_FlipPendingToken","flip:new"];'}[change]
    execute(flip_setup()+'''
        _presentationAvailable=false;
        [] call ACME_fnc_chestSealFlip;
        [_rolls isEqualTo [[_patient,"back",false,_medic]],"missing/duplicate fail-open patient roll"] call _check;
        [count _handlers==0 && {count _waits==1},"failed acquisition started waiting PFH"] call _check;
        [abs (((_waits select 0) select 3)-1.93)<0.000001,"fallback lock duration changed"] call _check;
        _buttonStates=[];
    '''+mutate+'''
        [_waits select 0] call _deliver;
    '''+f'[_resumed=={int(change=="none")} && {{count _buttonStates=={int(change=="none")}}},"old fallback completion changed new workspace"] call _check;')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACE_isUnconscious",false];',
    '_patientAlive=false;', '_parent=missionNamespace;',
])
def test_ineligible_flip_changes_only_virtual_view(change):
    execute(flip_setup()+change+'''
        [] call ACME_fnc_chestSealFlip;
        [count _rolls==0 && {count _handlers==0} && {count _waits==0},"ineligible virtual flip requested physical work"] call _check;
        [(uiNamespace getVariable ["ACME_CS_Side",""])=="back"
            && {uiNamespace getVariable ["ACME_CS_VirtualFlip",false]} && {_rendered==1},"virtual view did not change"] call _check;
    ''')
