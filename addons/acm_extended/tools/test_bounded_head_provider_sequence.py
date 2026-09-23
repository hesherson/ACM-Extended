"""Execute provider-only Putdown staging using explicit animation/clock fixtures.

No RTM playback, real input, network ordering or patient physiology is simulated.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute
from test_bounded_head_completion import source
from test_bounded_head_pose_contracts import contains, assert_connected_patient_states

REST='AmovPknlMstpSnonWnonDnon'
FIRST=REST+'_AinvPknlMstpSnonWnonDnon_Putdown'
SECOND='AinvPknlMstpSnonWnonDnon_Putdown_'+REST


def provider_contract(text=None):
    s=source('headElevMedicSeq') if text is None else text
    for frag in (
        'private _rest = "'+REST+'";',
        'private _forcePose = _rest;',
        'private _first = "'+FIRST+'";',
        'private _second = "'+SECOND+'";',
        'if !(_mode in ["elevate", "lower"]) exitWith {};',
        'private _prepDelay = [_medic] call ACME_fnc_medicAnimationPrep;',
        'if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {',
        'private _nextAlreadyRunning = _state == _secondLC;',
        'if (!_nextAlreadyRunning) then {[_u, _second, 2] call ACME_fnc_doAnim;};',
        'if (!_finished) exitWith {};',
        '[_u, _rest, 2] call ACME_fnc_doAnim;',
        'if ([_unit] call ACME_fnc_providerStanceOwned) exitWith {};',
        '_unit setUnitPos "AUTO";',
    ):
        assert contains(s,frag),frag
    assert not contains(s, '_u setUnitPos "UP";')
    assert not contains(s, 'private _dragger = "DraggerBase";')
    # No head-position caller can drift to a different provider controller.
    assert contains(source('headElevMedicStart'), '[_medic, "elevate"] call ACME_fnc_headElevMedicSeq;')
    assert contains(source('headElevateStop'), '[_medic, "lower"] call ACME_fnc_headElevMedicSeq;')


def setup():
    s=source('headElevMedicSeq')
    for name in ('_medic','_u','_unit'):
        for old,new in (
            ('local '+name,'_local'),('alive '+name,'_alive'),
            ('objectParent '+name,'_parent'),('currentWeapon '+name,'_weapon'),
            ('animationState '+name,'_anim'),
            (name+' selectWeapon "";', '_weapon="";'),
        ):
            s=re.sub(re.escape(old)+(r'\b' if old[-1].isalnum() else ''),lambda _:new,s)
        s=s.replace(name+' setUnitPos "MIDDLE";', '_stances pushBack "MIDDLE";')
        s=s.replace(name+' setUnitPos "AUTO";', '_stances pushBack "AUTO";')
    return r'''
        private _local=true; private _parent=objNull; private _blocked=false;
        private _weapon="rifle"; private _anim="idle"; private _stances=[];
        private _jobs=[]; private _prep=0; private _stanceOwned=false;
        ACME_fnc_animBlocked={_blocked};
        ACME_fnc_medicAnimationPrep={_prep=_prep+1;0.1};
        ACME_fnc_providerStanceOwned={_stanceOwned};
        ACME_fnc_doAnim={_moves pushBack _this;};
        CBA_fnc_globalEvent={_events pushBack _this;};
        CBA_fnc_addPerFrameHandler={_jobs pushBack _this; 73};
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
        CBA_fnc_waitAndExecute={_waits pushBack _this;};
        private _tick={params ["_job"]; [_job select 2,73] call (_job select 0);};
        private _deliver={params ["_job"]; (_job select 1) call (_job select 0);};
    '''+'ACME_fnc_headElevMedicSeq={'+adapt(s)+'};\n'


def begin(mode='elevate'):
    return f'''
        [_medic,"{mode}"] call ACME_fnc_headElevMedicSeq;
        [count _jobs==1 && {{_prep==1}},"provider preflight missing/duplicated"] call _check;
        private _job=_jobs select 0;
        [_job] call _tick;
        [count _moves==0,"weapon grace bypassed"] call _check;
        CBA_missionTime=10.2;
        [_job] call _tick;
        [_weapon=="" && {{count _moves==1}},"empty-hand entry lost"] call _check;
        _anim=toLower "{REST}";
        [_job] call _tick;
        [count _moves==2,"first Putdown not requested once"] call _check;
    '''


def finish(adopt=False):
    return f'''
        _anim=toLower "{FIRST}";
        for "_i" from 0 to 3 do {{[_job] call _tick;}};
        [count _moves==2,"first move replayed while running"] call _check;
        _anim=toLower "{SECOND if adopt else REST}";
        [_job] call _tick;
        [count _moves=={2 if adopt else 3},"exit adoption/replay incorrect"] call _check;
        _anim=toLower "{SECOND}";
        for "_i" from 0 to 3 do {{[_job] call _tick;}};
        _anim=toLower "{REST}";
        [_job] call _tick;
    '''


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('adopt',[False,True])
def test_both_modes_request_each_move_at_most_once_then_release_crouch(mode,adopt):
    execute(setup()+begin(mode)+finish(adopt)+f'''
        [count _moves=={3 if adopt else 4},"wrong final move count"] call _check;
        [(_moves select 1) isEqualTo [_medic,"{FIRST}",2],"first animation changed"] call _check;
        [(_moves select ((count _moves)-1)) isEqualTo [_medic,"{REST}",2],"final crouch changed"] call _check;
        [_weapon=="" && {{_prep==1}},"weapon restored or holster restarted"] call _check;
        [_removed isEqualTo [73],"provider PFH not retired exactly once"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"sequence left active"] call _check;
        [count _waits==1 && {{(_waits select 0 select 2)==0.25}},"stance grace changed"] call _check;
        [_waits select 0] call _deliver;
        [(_stances select ((count _stances)-1))=="AUTO","provider left stance locked"] call _check;
    ''')


@pytest.mark.parametrize('stage',[0,1,2])
def test_superseded_provider_pfh_removes_itself_without_animation_or_state_writes(stage):
    execute(setup()+begin()+f'''
        (_job select 2) set [7,{stage}];
        _medic setVariable ["ACME_headElev_medicAnimToken",99];
        _moves=[]; _events=[]; _stances=[];
        [_job] call _tick;
        [count _moves==0 && {{count _events==0}} && {{count _stances==0}} && {{count _waits==0}},"old provider interfered"] call _check;
        [_removed isEqualTo [73],"stale PFH leaked"] call _check;
        [_medic getVariable ["ACME_headElev_seqActive",false],"new active flag cleared"] call _check;
        [(_medic getVariable ["ACME_headElev_medicAnimToken",0])==99,"new token changed"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_local=false;', '_alive=false;', '_parent=missionNamespace;',
    '_medic setVariable ["ACME_headElev_medicAnimToken",99];',
    '_medic setVariable ["ACME_headElev_seqActive",true];',
    '_stanceOwned=true;',
])
def test_delayed_stance_release_respects_current_owner_and_context(change):
    execute(setup()+begin()+finish()+'''
        _stances=[];
    '''+change+'''
        [_waits select 0] call _deliver;
        [count _stances==0,"old stance callback released new/invalid owner"] call _check;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_unseen_animation_timeout_finishes_without_replaying_requested_moves(mode):
    execute(setup()+begin(mode)+'''
        _anim="third-party-state";
        CBA_missionTime=14.3;
        [_job] call _tick;
        [count _moves==3,"missing unseen first-stage timeout handoff"] call _check;
        CBA_missionTime=18.4;
        [_job] call _tick;
        [count _moves==4 && {_removed isEqualTo [73]},"unseen exit timeout stranded provider"] call _check;
    ''')


@pytest.mark.parametrize('old,new',[
    ('private _forcePose = _rest;', 'private _forcePose = "DraggerBase";'),
    ('if (!_nextAlreadyRunning) then {', 'if (true) then {'),
    ('if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {', 'if (false) exitWith {'),
    ('if ([_unit] call ACME_fnc_providerStanceOwned) exitWith {};', ''),
])
def test_contract_rejects_animation_replay_and_stale_ownership_mutations(old,new):
    s=source('headElevMedicSeq'); assert old in s
    with pytest.raises(AssertionError): provider_contract(s.replace(old,new)+'\n/* '+old+' */\n')
