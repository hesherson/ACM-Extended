"""Execute head-position continuations with explicit engine-boundary fixtures.

Actual SQF runs, but collision, animation, gear restoration and networking are
recorded calls, not rendered Arma behavior or engine inventory transactions.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute

F = ROOT / 'addons/acm_extended/functions'


def source(name):
    return (F / ('fn_' + name + '.sqf')).read_text()


def code(name):
    text = source(name)
    for unit in ('_patient', '_p'):
        for old, new in (
            ('local ' + unit, '_patientLocal'),
            ('alive ' + unit, '_patientAlive'),
            ('objectParent ' + unit, '_parent'),
            ('animationState ' + unit, '_animation'),
        ):
            text = re.sub(re.escape(old) + r'\b', lambda _: new, text)
        text = text.replace(unit + ' setMass _m;', '_masses pushBack _m;')
        text = text.replace(unit + ' setMass _mass;', '_masses pushBack _mass;')
    for var in ('_helper', '_propObj', '_prop'):
        text = text.replace('deleteVehicle ' + var + ';', '_deleted pushBack ' + var + ';')
        text = text.replace('detach ' + var + ';', '_detached pushBack ' + var + ';')
    text = text.replace('canSuspend', 'false')
    return adapt(text)


def setup():
    pre = r'''
        private _patientLocal=true; private _parent=objNull;
        private _animation="ACME_HeadElevPatientHold"; private _actualSide="front";
        private _collisions=[]; private _pins=[]; private _restores=[];
        private _parks=[]; private _animRequests=[]; private _provider=[];
        private _death=[]; private _holdClears=[]; private _releases=[];
        private _masses=[]; private _deleted=[]; private _detached=[];
        private _blocked=false; private _rolls=[];
        ACME_fnc_headElevCollision={_collisions pushBack _this;};
        ACME_fnc_headElevPinPose={_pins pushBack _this;};
        ACME_fnc_headElevVestRestore={_restores pushBack ["support",_this];};
        ACME_fnc_chestAccessVestRestore={_restores pushBack ["access",_this];};
        ACME_fnc_chestAccessVestPark={_parks pushBack _this;};
        ACME_fnc_patientAnimRequest={_animRequests pushBack _this; "anim:one"};
        ACME_fnc_headElevMedicSeq={_provider pushBack _this;};
        ACME_fnc_headElevDeathRelease={_death pushBack _this;};
        ACME_fnc_headElevHoldClear={_holdClears pushBack _this;};
        ACME_fnc_headElevRestAnim={"ACM_LyingState"};
        ACME_fnc_releasePatient={_releases pushBack _this;};
        ACME_fnc_doAnim={_moves pushBack _this;};
        ACME_fnc_medLog={}; ACME_fnc_animBlocked={_blocked};
        ACME_fnc_chestSealCanPhysicalRoll={true};
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        CBA_fnc_globalEvent={_events pushBack _this;};
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
        CBA_fnc_waitAndExecute={_waits pushBack [_this select 0,_this select 1,_this select 2];};
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_poseToken","placement:one"];
        private _deliver={params ["_job"]; (_job select 1) call (_job select 0);};
    '''
    return pre + ''.join('ACME_fnc_' + n + '={' + code(n) + '};\n' for n in (
        'headElevateStop', 'headElevSuspend', 'headElevApplyTilt'))


def begin(kind):
    call = '[_patient] call ACME_fnc_headElevSuspend;' if kind == 'suspend' else '[_medic,_patient,false] call ACME_fnc_headElevateStop;'
    return call + '''
        [count _waits==1,"missing single authored completion"] call _check;
        private _pending=_waits select 0; _waits=[];
        _collisions=[]; _moves=[]; _animRequests=[]; _restores=[]; _parks=[];
    '''


@pytest.mark.parametrize('change', [
    '_patient setVariable ["ACME_headElev_poseToken","placement:two"];',
    '_patient setVariable ["ACME_headElev_Suspended",false];',
    '_patient setVariable ["ACME_headElev_poseToken","placement:two"]; _patient setVariable ["ACME_headElev_Suspended",false];',
])
def test_stale_suspend_completion_has_no_collision_or_presentation_writes(change):
    execute(setup() + begin('suspend') + change + '''
        [_pending] call _deliver;
        [count _collisions==0,"stale suspension restored collision"] call _check;
        [count _parks==0 && {count _animRequests==0} && {count _restores==0},"stale suspension changed presentation"] call _check;
    ''')


def test_previous_lower_completion_does_not_restore_collision_during_new_elevation():
    execute(setup() + begin('stop') + '''
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_poseToken","placement:two"];
        [_pending] call _deliver;
        [count _collisions==0,"old lower restored collision during new lift"] call _check;
        [count _moves==0 && {count _restores==0},"old lower changed new placement"] call _check;
    ''')


@pytest.mark.parametrize('kind',['suspend','stop'])
@pytest.mark.parametrize('change',['_patientLocal=false;','_patientAlive=false;'])
def test_completion_retains_owner_and_life_guards(kind,change):
    execute(setup() + begin(kind) + change + '''
        [_pending] call _deliver;
        [count _collisions==0 && {count _moves==0} && {count _animRequests==0} && {count _restores==0},"invalid owner/life completion wrote state"] call _check;
    ''')


@pytest.mark.parametrize('kind',['suspend','stop'])
@pytest.mark.parametrize('vehicle',[False,True])
def test_current_completion_preserves_collision_and_gear_handoff(kind,vehicle):
    execute(setup() + begin(kind) + ('_parent=missionNamespace;' if vehicle else '') + '''
        [(_pending select 2)==1.4,"authored lower delay changed"] call _check;
        [_pending] call _deliver;
        [_collisions isEqualTo [[_patient,true]],"current completion failed to restore collision once"] call _check;
    ''' + (f'''
        [count _parks==1 && {{count _restores==0}},"suspension re-wore support instead of parking"] call _check;
        [count _animRequests=={int(not vehicle)},"wrong flat lease request"] call _check;
        [_patient getVariable ["ACME_headElevated",false],"suspension destroyed logical elevation"] call _check;
    ''' if kind=='suspend' else f'''
        [_restores isEqualTo [["support",[_patient]],["access",[_patient]]],"lower lost restore handoff"] call _check;
        [count _moves=={int(not vehicle)},"wrong lower rest request"] call _check;
        [!(_patient getVariable ["ACME_headElevated",true]),"true lower kept elevation"] call _check;
    '''))


@pytest.mark.parametrize('quiet,vehicle',[(True,False),(False,True),(True,True)])
def test_nonvisible_lower_restores_without_delayed_animation(quiet,vehicle):
    execute(setup()+f'_parent={"missionNamespace" if vehicle else "objNull"};'+f'''
        [_medic,_patient,{str(quiet).lower()}] call ACME_fnc_headElevateStop;
        [count _waits==0 && {{count _moves==0}} && {{count _pins==0}},"nonvisible lower started theatre"] call _check;
        [count _restores==2 && {{_collisions isEqualTo [[_patient,true]]}},"nonvisible lower lost recovery"] call _check;
    ''')


def test_dead_lower_delegates_before_living_animation_and_restore():
    execute(setup()+'''
        _patientAlive=false;
        [_medic,_patient,false] call ACME_fnc_headElevateStop;
        [_death isEqualTo [[_patient]],"dead lower did not use death recovery"] call _check;
        [count _moves==0 && {count _waits==0} && {count _restores==0},"dead lower continued through living path"] call _check;
    ''')


@pytest.mark.parametrize('kind',['suspend','stop'])
def test_remote_initial_request_dispatches_without_local_presentation(kind):
    call='[_patient] call ACME_fnc_headElevSuspend;' if kind=='suspend' else '[_medic,_patient,false] call ACME_fnc_headElevateStop;'
    execute(setup()+'_patientLocal=false;'+call+'''
        [count _events==1,"remote operation not dispatched"] call _check;
        [count _collisions==0 && {count _moves==0} && {count _restores==0} && {count _waits==0},"remote machine ran patient presentation"] call _check;
    ''')


@pytest.mark.parametrize('kind',['suspend','stop'])
def test_new_lift_keeps_collision_until_its_own_completion(kind):
    execute(setup()+begin(kind)+'''
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_Suspended",false];
        _patient setVariable ["ACME_headElev_poseToken","placement:two"];
        [_patient] call ACME_fnc_headElevApplyTilt;
        [count _waits==1,"new lift lacks its own completion"] call _check;
        private _newCompletion=_waits select 0;
        _collisions=[];
        [_pending] call _deliver;
        [count _collisions==0,"old completion interfered with actual new lift"] call _check;
        [_newCompletion] call _deliver;
        [_collisions isEqualTo [[_patient,true]],"new lift did not recover its own collision"] call _check;
    ''')
