"""Execute Semi-Fowler lift checks and lower-completion boundaries.

Engine objects, collision/animation calls, provider theatre, inventory delegates
and callback scheduling are fixtures. Complete patient stop/apply bodies execute;
this does not simulate collision physics, loadout replication or live RTMs.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute
from test_historical_chest_workspace import setup as chest_setup, source


def head_source(name):
    text=source(name)
    # Engine boundaries are replaced before the generic adapter (not branch logic).
    for unit in ('_patient','_p'):
        for old,new in [('local '+unit,'_patientLocal'),('alive '+unit,'_patientAlive'),
                        ('objectParent '+unit,'_parent'),('animationState '+unit,'_animation')]:
            text=re.sub(re.escape(old)+r'\b',lambda m:new,text)
    text=text.replace('canSuspend','false').replace('finite _rollTime','(_rollTime call _finite)')
    text=re.sub(r'_patient setMass (_m|_mass);',r'_masses pushBack \1;',text)
    text=re.sub(r'\bdeleteVehicle (_helper|_propObj);',r'_deletes pushBack \1;',text)
    text=re.sub(r'\bdetach (_helper|_propObj);',r'_detaches pushBack \1;',text)
    return adapt(text)


def setup():
    return chest_setup()+'''
        private _collisions=[]; private _pins=[]; private _gear=[]; private _providerSeq=[];
        private _masses=[]; private _releasedHelpers=[]; private _deathCalls=[]; private _holdClears=[];
        _actualSide="front"; _animation="ACME_HeadElevPatientHold";
        ACME_fnc_headElevHoldClear={_holdClears pushBack _this;};
        ACME_fnc_headElevCollision={_collisions pushBack _this;};
        ACME_fnc_headElevPinPose={_pins pushBack _this;};
        ACME_fnc_headElevVestRestore={_gear pushBack "support";};
        ACME_fnc_chestAccessVestRestore={_gear pushBack "chest";};
        ACME_fnc_headElevMedicSeq={_providerSeq pushBack _this;};
        ACME_fnc_headElevRestAnim={"ACM_LyingState"};
        ACME_fnc_releasePatient={_releasedHelpers pushBack _this;};
        ACME_fnc_medLog={};
        // The dedicated corpse cleanup has independent existing coverage. Here
        // record delegation to prove Stop does not enter the living lower path.
        ACME_fnc_headElevDeathRelease={_deathCalls pushBack _this;};
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_poseToken","placement:1"];
        ACME_fnc_headElevateStop={'''+head_source('headElevateStop')+'''};
        ACME_fnc_headElevApplyTilt={'''+head_source('headElevApplyTilt')+'''};
    '''


@pytest.mark.parametrize('quiet',[False,True])
def test_living_lower_preserves_authored_release_and_defers_gear_until_completion(quiet):
    execute(setup()+f'[_medic,_patient,{str(quiet).lower()}] call ACME_fnc_headElevateStop;'+'''
        [!(_patient getVariable ["ACME_headElevated",true])
            && {(_patient getVariable ["ACME_headElev_poseToken","missing"])==""},"elevation episode not retired"] call _check;
        [count _deathCalls==0,"living lower delegated to death cleanup"] call _check;
    '''+('''
        [count _moves==0 && {count _waits==0} && {count _providerSeq==0},"quiet lower animated"] call _check;
        [_gear isEqualTo ["support","chest"],"quiet lower did not restore both gear owners"] call _check;
        [_collisions isEqualTo [[_patient,true]],"quiet lower left collision disabled"] call _check;
    ''' if quiet else '''
        [_moves isEqualTo [[_patient,"ACME_HeadElevPatientRelease",2]],"wrong release request"] call _check;
        [count _gear==0 && {count _waits==1},"gear returned before release completed"] call _check;
        [_pins isEqualTo [[_patient,1.4]] && {_providerSeq isEqualTo [[_medic,"lower"]]},"authored timing or provider handoff changed"] call _check;
        [((_waits select 0) select 3)==1.4,"completion timer changed"] call _check;
        [_waits select 0] call _deliver;
        [_gear isEqualTo ["support","chest"],"completion lost gear restoration"] call _check;
        [_collisions isEqualTo [[_patient,false],[_patient,true]],"normal collision sequence changed"] call _check;
        [(_moves select 1) isEqualTo [_patient,"ACM_LyingState",2],"normal lower missed supine rest"] call _check;
    '''))


@pytest.mark.parametrize('quiet',[False,True])
def test_dead_stop_delegates_before_any_living_pose_or_provider_sequence(quiet):
    execute(setup()+f'_patientAlive=false; [_medic,_patient,{str(quiet).lower()}] call ACME_fnc_headElevateStop;'+'''
        [_deathCalls isEqualTo [[_patient]],"dead stop did not use dedicated corpse cleanup"] call _check;
        [count _moves==0 && {count _providerSeq==0} && {count _waits==0} && {count _gear==0},"dead stop also entered living lower path"] call _check;
        [_holdClears isEqualTo [[_patient]],"manual provider hold not released before death delegation"] call _check;
    ''')


@pytest.mark.parametrize('replay',[False,True])
def test_lift_uses_authored_grab_priority_and_current_startup_grace(replay):
    execute(setup()+f'[_patient,{str(replay).lower()}] call ACME_fnc_headElevApplyTilt;'+('''
        [_moves isEqualTo [[_patient,"ACME_HeadElevPatientGrab",2]],"wrong authored grab request"] call _check;
        [(_patient getVariable ["ACME_headElev_animGraceUntil",0])==12.5,"lift startup grace changed"] call _check;
        [abs (((_pins select 0) select 1)-1.8)<0.000001,"lift pin duration changed"] call _check;
        [count _waits==1 && {abs (((_waits select 0) select 3)-1.7)<0.000001},"lift callback timing changed"] call _check;
    ''' if replay else '''
        [count _moves==0 && {count _waits==0} && {count _pins==0} && {count _collisions==0},"nonreplay lift invented presentation"] call _check;
    '''))


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACME_headElev_poseToken","placement:2"];',
    '_patient setVariable ["ACME_headElev_poseToken",""]; _patient setVariable ["ACME_headElevated",false];',
    '_patient setVariable ["ACME_headElev_Suspended",true];',
    '_patientAlive=false;', '_patientLocal=false;',
])
def test_lift_completion_rejects_changed_token_suspension_death_or_owner_loss(change):
    execute(setup()+'''
        [_patient,true] call ACME_fnc_headElevApplyTilt;
        private _old=_waits select 0; _moves=[]; _collisions=[];
    '''+change+'''
        [_old] call _deliver;
        [count _moves==0 && {count _collisions==0},"invalidated lift changed presentation"] call _check;
    ''')


@pytest.mark.parametrize('observed',['ACME_HeadElevPatientHold','other-state'])
def test_current_lift_completion_does_not_replay_an_already_observed_hold(observed):
    execute(setup()+'''
        [_patient,true] call ACME_fnc_headElevApplyTilt;
        _moves=[]; _collisions=[];
    '''+f'_animation="{observed}";'+'''
        [_waits select 0] call _deliver;
        [_collisions isEqualTo [[_patient,true]],"current completion did not restore collision"] call _check;
    '''+f'[count _moves=={int(observed!="ACME_HeadElevPatientHold")},"observed hold was replayed or missing hold not repaired"] call _check;')


@pytest.mark.parametrize('change',[
    '_patientAlive=false;', '_patientLocal=false;',
])
def test_lower_completion_has_no_effect_after_death_or_owner_loss(change):
    execute(setup()+'''
        [_medic,_patient,false] call ACME_fnc_headElevateStop;
        private _old=_waits select 0; _moves=[]; _collisions=[]; _gear=[];
    '''+change+'''
        [_old] call _deliver;
        [count _moves==0 && {count _collisions==0} && {count _gear==0},"invalid lower callback changed patient"] call _check;
    ''')


@pytest.mark.parametrize('suspended',[False,True])
def test_old_lower_completion_cannot_reenable_collision_during_new_elevation(suspended):
    execute(setup()+'''
        [_medic,_patient,false] call ACME_fnc_headElevateStop;
        private _old=_waits select 0;
        // New placement's owner state is an explicit boundary fixture. Execute
        // its real lift path, which disables collision while the body moves.
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_poseToken","placement:2"];
        [_patient,true] call ACME_fnc_headElevApplyTilt;
    '''+f'_patient setVariable ["ACME_headElev_Suspended",{str(suspended).lower()}];'+'''
        _moves=[]; _collisions=[]; _gear=[];
        [_old] call _deliver;
        [count _collisions==0 && {count _moves==0} && {count _gear==0},"old lower completion altered new elevation"] call _check;
        [(_patient getVariable "ACME_headElev_poseToken")=="placement:2","old lower cleared new placement token"] call _check;
    ''')


def test_lift_and_lower_do_not_teleport_patient_to_cached_world_coordinates():
    from source_scan import lex
    for name in ('headElevApplyTilt','headElevateStop'):
        identifiers={token.value.lower() for token in lex(source(name)) if token.kind=='ident'}
        assert not identifiers.intersection({'setpos','setposasl','setposatl','setposaslw','setposworld','attachto'}),name
