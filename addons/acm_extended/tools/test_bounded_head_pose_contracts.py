"""Protect connected Semi-Fowler states, no teleport, and actual lift dispatch.

Config/token contracts are structural; executed SQF uses explicit engine fixtures.
These tests do not render RTMs, simulate PhysX or certify live multiplayer.
"""
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, execute
from test_bounded_head_completion import setup, source


def tokens(text):
    return tuple(t.value for t in lex(text))


def contains(text, fragment):
    seq, part = tokens(text), tokens(fragment)
    return any(seq[i:i+len(part)] == part for i in range(len(seq)-len(part)+1))


def body(config, name):
    ts=lex(config); pairs=matching(ts)
    found=[]
    for i,t in enumerate(ts[:-2]):
        if t.value=='class' and ts[i+1].value==name:
            j=i+2
            while j<len(ts) and ts[j].value not in ('{',';'): j+=1
            if j<len(ts) and ts[j].value=='{':
                found.append(config[t.offset:ts[pairs[j]].offset+1])
    assert len(found)==1, name
    return found[0]


def sources():
    result={n:source(n) for n in ('headElevApplyTilt','headElevateStart','headElevateStop',
                                   'headElevSuspend','headElevAnimGuard')}
    result['config']=(ROOT/'addons/acm_extended/config.cpp').read_text()
    return result


def assert_connected_patient_states(data=None):
    d=sources() if data is None else data
    for name,parent in (
        ('ACME_HeadElevPatientGrab','AinjPpneMrunSnonWnonDb_grab'),
        ('ACME_HeadElevPatientHold','AinjPpneMrunSnonWnonDb_release'),
        ('ACME_HeadElevPatientRelease','AinjPpneMrunSnonWnonDb_release')):
        assert contains(body(d['config'],name),f'class {name}: {parent}')
    grab=body(d['config'],'ACME_HeadElevPatientGrab')
    hold=body(d['config'],'ACME_HeadElevPatientHold')
    release=body(d['config'],'ACME_HeadElevPatientRelease')
    for fragment in ('looped = 0;', 'ConnectTo[] = {"ACME_HeadElevPatientHold",0.05};',
                     'InterpolateTo[] = {"ACME_HeadElevPatientHold",0.05};'):
        assert contains(grab,fragment)
    for fragment in ('looped = 1;','speed = 0;','ConnectTo[] = {};','InterpolateTo[] = {};'):
        assert contains(hold,fragment)
    assert contains(release,'looped = 0;')
    assert contains(release,'ConnectTo[] = {"ACM_LyingState",0.1};')
    assert contains(d['headElevateStart'],'[_patient] call ACME_fnc_headElevApplyTilt;')
    assert contains(d['headElevApplyTilt'],'[_patient,"ACME_HeadElevPatientGrab",2,"head-elev-lift"')
    assert contains(d['headElevApplyTilt'],'call ACME_fnc_patientAnimRequest;')
    assert contains(d['headElevateStop'],'[_patient,"ACME_HeadElevPatientRelease",2,"head-elev-lower"')
    assert contains(d['headElevateStop'],'call ACME_fnc_patientAnimRequest;')
    assert contains(d['headElevSuspend'],'[_patient,"ACME_HeadElevPatientRelease",2,"head-elev-lower"')


def assert_no_patient_teleport(data=None):
    d=sources() if data is None else data
    for name in ('headElevApplyTilt','headElevateStop','headElevSuspend'):
        ts=lex(d[name])
        for i,t in enumerate(ts[:-1]):
            if t.kind=='ident' and t.value in ('_patient','_p'):
                assert ts[i+1].value.lower() not in ('attachto','setpos','setposatl','setposasl','setposaslw','setposworld','setvectorup','setvectordirandup'), name


def assert_legacy_helper_is_retired(data=None):
    d=sources() if data is None else data
    s=d['headElevApplyTilt']
    # The support-carrier prop is now created here after the actual lift; it is not a patient helper.
    forbidden={'createvehiclelocal','attachto'}
    assert not any(t.kind=='ident' and t.value.lower() in forbidden for t in lex(s))
    ts=lex(s)
    for i,t in enumerate(ts):
        if t.kind=='ident' and t.value.lower()=='createvehicle':
            assert ts[i+1].value=='[' and ts[i+2].value=='GroundWeaponHolder'

    assert contains(s,'[_patient,_helper] call ACME_fnc_releasePatient;')
    assert contains(s,'deleteVehicle _helper;')
    assert contains(s,'_patient setVariable ["ACME_headElev_helper",objNull,true];')
    assert_no_patient_teleport(d)


def assert_startup_grace(data=None):
    d=sources() if data is None else data
    assert contains(d['headElevApplyTilt'],'_patient setVariable ["ACME_headElev_animGraceUntil", CBA_missionTime + 2.5, false];')
    assert contains(d['headElevAnimGuard'],'CBA_missionTime <= _graceUntil')
    assert contains(d['headElevAnimGuard'],'_anim == _restAnim')
    assert_connected_patient_states(d)


def assert_dead_stop_delegates_first(data=None):
    d=sources() if data is None else data
    s=d['headElevateStop']
    guard='if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease;};'
    assert contains(s,guard)
    # Token offsets establish source ordering, not general reachability.
    ts=lex(s)
    death=next(t.offset for t in ts if t.value=='ACME_fnc_headElevDeathRelease')
    animation=next(t.offset for t in ts if t.value=='ACME_fnc_doAnim')
    restore=next(t.offset for t in ts if t.value=='ACME_fnc_headElevVestRestore')
    assert death<animation and death<restore


@pytest.mark.parametrize('lift,delay', [('1.2',1.2),('2',2),('0',.8),('-2',.8),('"bad"',.8)])
@pytest.mark.parametrize('already_hold',[False,True])
def test_lift_uses_connected_grab_and_one_guarded_hold_completion(lift,delay,already_hold):
    execute(setup()+f'missionNamespace setVariable ["ACME_headElev_liftAnimTime",{lift}];'+'''
        [_patient] call ACME_fnc_headElevApplyTilt;
        [_moves isEqualTo [[_patient,"ACME_HeadElevPatientGrab",2]],"grab wrapper/priority changed"] call _check;
        [count _animRequests==1 && {count _leaseWaits==1},"lift bypassed accepted animation lease"] call _check;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isNotEqualTo [],"lift did not retain its animation lease"] call _check;
        [_testAnimationSpeed==1.5,"lift did not use the shared choreography rate"] call _check;
        [(_patient getVariable ["ACME_headElev_animGraceUntil",0])==12.5,"startup grace changed"] call _check;
        [count _waits==1,"lift scheduled repeated callbacks"] call _check;
    '''+f'''
        [abs (((_waits select 0) select 2)-{delay+0.5})<0.0001,"completion delay changed"] call _check;
        [abs (((_pins select 0) select 1)-{delay+0.6})<0.0001,"pin duration changed"] call _check;
        _animation="{'ACME_HeadElevPatientHold' if already_hold else 'ACME_HeadElevPatientGrab'}";
        _moves=[];
        [_waits select 0] call _deliver;
        [count _moves=={int(not already_hold)},"missing hold or unnecessary hold restart"] call _check;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo [],"completion did not release its animation lease"] call _check;
        [_testAnimationSpeed==1,"completion leaked its moving animation speed"] call _check;
    '''+('' if already_hold else '[_moves isEqualTo [[_patient,"ACME_HeadElevPatientHold",2]],"wrong hold wrapper"] call _check;'))


@pytest.mark.parametrize('change,collision_count',[
    ('_patientLocal=false;',0), ('_patientAlive=false;',1),
    ('_patient setVariable ["ACME_headElev_poseToken","later"];',0),
    ('_patient setVariable ["ACME_headElevated",false];',1),
    ('_patient setVariable ["ACME_headElev_Suspended",true];',1),
    ('_patient setVariable ["ACME_patientAnimLock",["new-owner","roll","provider",3,2000]];',0),
])
def test_lift_completion_retires_own_lease_without_touching_replacement(change,collision_count):
    execute(setup()+'''
        [_patient] call ACME_fnc_headElevApplyTilt;
        _moves=[]; _collisions=[];
    '''+change+f'''
        [_waits select 0] call _deliver;
        [count _moves==0 && {{count _collisions=={collision_count}}},"retired lift used wrong cleanup boundary"] call _check;
    ''')


@pytest.mark.parametrize('helper',[False,True])
@pytest.mark.parametrize('mass',[-1,70])
def test_legacy_helper_cleanup_does_not_start_a_new_positioning_helper(helper,mass):
    execute(setup()+f'''
        _patient setVariable ["ACME_headElev_helper",{'missionNamespace' if helper else 'objNull'}];
        _patient setVariable ["ACME_headElev_mass",{mass}];
        [_patient,false] call ACME_fnc_headElevApplyTilt;
        [count _releases==1 && {{count _deleted=={int(helper)}}},"legacy helper cleanup changed"] call _check;
        [count _masses=={int(mass>0)},"wrong legacy mass recovery"] call _check;
        [(_patient getVariable ["ACME_headElev_helper",missionNamespace]) isEqualTo objNull,"helper reference survived"] call _check;
        [count _moves==0 && {{count _waits==0}},"no-replay cleanup started animation"] call _check;
    ''')


@pytest.mark.parametrize('change,events', [('_patientLocal=false;',1),('_patientAlive=false;',0),('_blocked=true;',0)])
def test_lift_eligibility_blocks_local_presentation(change,events):
    execute(setup()+change+f'''
        [_patient] call ACME_fnc_headElevApplyTilt;
        [count _events=={events},"wrong owner dispatch"] call _check;
        [count _moves==0 && {{count _waits==0}} && {{count _releases==0}},"invalid lift changed patient"] call _check;
    ''')


@pytest.mark.parametrize('validator,filename,old,new',[
    (assert_connected_patient_states,'config','class ACME_HeadElevPatientGrab: AinjPpneMrunSnonWnonDb_grab','class ACME_HeadElevPatientGrab: OtherState'),
    (assert_connected_patient_states,'headElevApplyTilt','"ACME_HeadElevPatientGrab", 2','"ACME_HeadElevPatientGrab", 1'),
    (assert_connected_patient_states,'headElevateStop','"ACME_HeadElevPatientRelease", 2','"ACME_HeadElevPatientRelease", 1'),
    (assert_no_patient_teleport,'headElevateStop','', '_patient setPosASL [0,0,0];'),
    (assert_no_patient_teleport,'headElevSuspend','', '_patient attachTo [objNull];'),
    (assert_legacy_helper_is_retired,'headElevApplyTilt','', 'createVehicle ["Helper",[0,0,0],[],0,"CAN_COLLIDE"];'),
    (assert_startup_grace,'headElevApplyTilt','CBA_missionTime + 2.5','CBA_missionTime + 0'),
    (assert_dead_stop_delegates_first,'headElevateStop','if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease;};',''),
])
def test_contracts_reject_regressions_even_with_original_text_in_comments(validator,filename,old,new):
    d=sources()
    validator(d)
    original=d[filename]
    if old:
        assert old in original
        d[filename]=original.replace(old,new,1)+'\n/* '+old+' */\n'
    else:
        d[filename]=new+'\n'+original
    with pytest.raises(AssertionError): validator(d)
