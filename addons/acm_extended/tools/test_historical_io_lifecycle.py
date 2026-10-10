"""IO response and callback boundaries from the checked-out SQF.

Engine pain/status calls and scheduling are explicit recording stand-ins. The
actual IO helper and owner Local-event body execute. No kinetics, syncope timing
policy, live engine state-machine transition or multiplayer delivery is modeled.
"""
from pathlib import Path
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_historical_medication_preparation import line_setup
from test_historical_vial_execution import map_defaults

F=ROOT/'addons/acm_extended/functions'


def adapted(text):
    return adapt(map_defaults(text.replace('local _patient','_patientLocal').replace('owner _patient','_patientOwner').replace('alive _unit','_patientAlive')))


def function(name):
    return 'ACME_fnc_'+name+'={'+adapted((F/('fn_'+name+'.sqf')).read_text())+'};'


def setup():
    return function('clinicalEpoch')+function('ioPainResponse')+'''
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _patientLocal=true;
        private _patientOwner=7;
        private _painWrites=[]; private _fallbackWrites=[]; private _sounds=[];
        private _publicRequests=[]; private _rawRequests=[];
        private _adjustWorks=true;
        ace_medical_fnc_adjustPainLevel={
            _painWrites pushBack _this;
            if (_adjustWorks) then {(_this select 0) setVariable ["ace_medical_pain", (((_this select 0) getVariable ["ace_medical_pain",0])+(_this select 1)) min 1];};
        };
        ACM_core_fnc_setAceMedicalState={
            _fallbackWrites pushBack _this;
            {if ((_x select 0)=="pain") then {(_this select 0) setVariable ["ace_medical_pain",_x select 1];};} forEach (_this select 1);
        };
        ace_medical_feedback_fnc_playInjuredSound={_sounds pushBack _this;};
        ace_medical_fnc_setUnconscious={_publicRequests pushBack _this; (_this select 0) setVariable ["ACE_isUnconscious",_this select 1];true};
        ace_medical_status_fnc_setUnconsciousState={_rawRequests pushBack _this; (_this select 0) setVariable ["ACE_isUnconscious",_this select 1];};
        CBA_fnc_waitAndExecute={_waits pushBack (+_this);};
        private _fire={private _job=_waits select _this; (_job select 1) call (_job select 0);};
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ACME_medicationLineGenerations",createHashMapFromArray [["body:-1",1],["leftarm:-1",1]]];
    '''


@pytest.mark.parametrize('pain', [0,0.1,0.34,0.35,0.8,1])
@pytest.mark.parametrize('unconscious', [True,False])
def test_placement_keeps_existing_floor_without_scheduling_syncope(pain,unconscious):
    expected=max(pain,.35)
    execute(setup()+f'_patient setVariable ["ace_medical_pain",{pain}]; _patient setVariable ["ACE_isUnconscious",{str(unconscious).lower()}];'+'''
        [_patient,"body","placement"] call ACME_fnc_ioPainResponse;
    '''+f'[abs ((_patient getVariable ["ace_medical_pain",-1])-{expected})<0.000001,"placement floor changed"] call _check;'+
        f'[count _sounds=={int(.35-pain>.05 and not unconscious)},"placement reaction changed"] call _check;'+'''
        [count _waits==0 && {count _publicRequests==0} && {count _rawRequests==0},"placement scheduled syncope"] call _check;
    ''')


@pytest.mark.parametrize('mode',['fluid','FLUID','medication','MEDICATION'])
@pytest.mark.parametrize('unconscious',[False,True])
def test_flow_and_medication_preserve_pain_but_only_awake_fluid_schedules(mode,unconscious):
    schedule=mode.lower()=='fluid' and not unconscious
    execute(setup()+f'_patient setVariable ["ACE_isUnconscious",{str(unconscious).lower()}];'+
        f'for "_i" from 1 to 5 do {{[_patient,"body","{mode}"] call ACME_fnc_ioPainResponse;}};'+'''
        [count _painWrites==1,"unchanged pain floor repeatedly written"] call _check;
    '''+f'[abs ((_patient getVariable ["ace_medical_pain",0])-{1 if mode.lower()=="fluid" else .45})<0.000001,"fluid and medication pain floors conflated"] call _check;'+
        f'[count _sounds=={int(mode.lower()=="medication" and not unconscious)},"one medication reaction repeated or suppressed"] call _check;'+
        f'[count _waits=={int(schedule)},"wrong number of syncope timers"] call _check;')


def test_suppressed_adjustment_uses_existing_pain_writer_without_extra_timer():
    execute(setup()+'''
        _adjustWorks=false;
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [(_patient getVariable ["ace_medical_pain",0])==1,"fallback failed to preserve max pain policy"] call _check;
        [count _fallbackWrites==1 && {count _waits==1},"fallback repeated scheduler or writer"] call _check;
    ''')


@pytest.mark.parametrize('delay',[0,0.05,3,5])
def test_syncope_uses_public_transition_once_after_the_existing_delay(delay):
    execute(setup()+f'missionNamespace setVariable ["ACME_ioFluidSyncopeDelay",{delay}];'+'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [count _publicRequests==0 && {count _rawRequests==0},"syncope happened before scheduler"] call _check;
    '''+f'[(_waits select 0 select 2)=={max(delay,.1)},"syncope delay changed"] call _check;'+'''
        0 call _fire; 0 call _fire;
        [_publicRequests isEqualTo [[_patient,true,3,true]],"syncope bypassed public medical transition or repeated it"] call _check;
        [count _rawRequests==0,"IO directly changed raw unconscious state"] call _check;
        [(_patient getVariable ["ACME_ioFluidSyncopeEpisode_body",[]]) isEqualTo [1,true,true],"completed physical IO episode lost consumption"] call _check;
    ''')


@pytest.mark.parametrize('flag',['ACE_isUnconscious','ace_medical_unconscious'])
def test_already_unconscious_casualty_consumes_current_timer_without_second_knockout(flag):
    execute(setup()+'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
    '''+f'_patient setVariable ["{flag}",true];'+'''
        0 call _fire;
        [count _publicRequests==0 && {count _rawRequests==0},"another unconscious cause was overwritten"] call _check;
        [(_patient getVariable ["ACME_ioFluidSyncopeEpisode_body",[]]) isEqualTo [1,true,true],"current episode lost one-shot consumption"] call _check;
    ''')


def test_pre_reset_timer_cannot_take_a_reused_post_reset_serial():
    # These are the actual reset identities, not a fabricated global timer order.
    reset=(F/'fn_clinicalReset.sqf').read_text()
    clear=(F/'fn_clearAllAilments.sqf').read_text()
    assert '"ACME_clinicalEpoch", ([_patient] call ACME_fnc_clinicalEpoch) + 1' in reset
    for field in ('ACME_ioSyncopeSerial','ACME_ioSyncopeToken'):assert '"'+field+'"' in clear
    execute(setup()+'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        private _old=+(_patient getVariable ["ACME_ioFluidSyncopeEpisode_body",[]]);
        // Clinical reset clears declared episode fields along with the line-generation map.
        _patient setVariable ["ACME_clinicalEpoch",2];
        _patient setVariable ["ACME_ioFluidSyncopeEpisode_body",[]];
        _patient setVariable ["ace_medical_pain",0];
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [(_patient getVariable ["ACME_ioFluidSyncopeEpisode_body",[]]) isEqualTo _old,"new physical line did not reuse generation 1"] call _check;
        0 call _fire;
        [count _publicRequests==0 && {count _rawRequests==0},"old episode caused new-episode syncope"] call _check;
        [(_patient getVariable ["ACME_ioFluidSyncopeEpisode_body",[]]) isEqualTo _old,"old episode changed new consumption"] call _check;
        1 call _fire;
        [_publicRequests isEqualTo [[_patient,true,3,true]],"new episode lost its own scheduled transition"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientAlive=false;', '_patientLocal=false;', '_patientOwner=8;',
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_clinicalRestoring",true];',
    '_patient setVariable ["ACME_ioSyncopeToken",99];',
])
def test_deferred_io_work_rejects_changed_episode_owner_or_state(change):
    # B190 retired the per-patient serial. It no longer cancels a physical-line episode.
    expected=int("ACME_ioSyncopeToken" in change)
    execute(setup()+'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
    '''+change+'''
        0 call _fire;
        [count _rawRequests==0,"IO used raw state transition"] call _check;
    '''+f'[count _publicRequests=={expected},"wrong ownership/clinical-epoch or retired-token boundary"] call _check;')


@pytest.mark.parametrize('change',['_patientAlive=false;','_patientLocal=false;','_patient setVariable ["ACME_clinicalRestoring",true];'])
def test_invalid_current_patient_does_not_change_pain_or_start_timer(change):
    execute(setup()+change+'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [count _painWrites==0 && {count _fallbackWrites==0} && {count _sounds==0} && {count _waits==0},"invalid patient mutated"] call _check;
    ''')


def locality_body():
    text=(F/'fn_ownerInit.sqf').read_text()
    begin=text.index('["CAManBase", "Local", {')
    opening=text.index('{',begin)
    ts=lex(text);pairs=matching(ts)
    index=next(i for i,t in enumerate(ts) if t.offset==opening)
    return text[opening:ts[pairs[index]].offset+1]


@pytest.mark.parametrize('fire_away',[False,True])
def test_owner_handoff_invalidates_old_timer_and_allows_new_local_flow(fire_away):
    execute(setup()+f'private _firedAway={str(fire_away).lower()};'+'''
        ACME_fnc_aiProtectionSync={}; ACME_fnc_aajtDownedStop={}; ACME_fnc_ownerRegister={}; ACME_fnc_providerStanceOwned={false}; CBA_fnc_execNextFrame={};
    '''+'private _locality='+adapted(locality_body())+';'+'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        _patientLocal=false;
        [_patient,false] call _locality;
    '''+('0 call _fire;' if fire_away else '')+'''
        _patientLocal=true;
        // Registration retries are unrelated to the IO timer recorder.
        private _scheduler=CBA_fnc_waitAndExecute; CBA_fnc_waitAndExecute={};
        [_patient,true] call _locality;
        CBA_fnc_waitAndExecute=_scheduler;
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [count _waits==1,"ownership return retriggered consumed physical IO"] call _check;
        if (!_firedAway) then {0 call _fire;};
        [count _publicRequests==0 && {count _rawRequests==0},"old owner's timer acted after handoff"] call _check;
        // Removing/replacing the IO, not changing owner, establishes another eligible episode.
        (_patient getVariable "ACME_medicationLineGenerations") set ["body:-1",2];
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [count _waits==2,"fresh physical IO failed to schedule"] call _check;
        if (count _waits>1) then {
            1 call _fire;
            [_publicRequests isEqualTo [[_patient,true,3,true]],"new local timer did not complete"] call _check;
        };
    ''')


@pytest.mark.parametrize('site,operation,expected_mode',[
    (-1,'administer','medication'),(-1,'flush','fluid'),
    (0,'administer',''),(0,'flush',''),(-2,'administer',''),
])
def test_actual_medication_line_routes_only_io_and_debounces_receipts(site,operation,expected_mode):
    # Entire current owner-line transaction runs; catheter and delivery are existing fixture boundaries.
    execute(line_setup()+setup()+'''
        private _ioCalls=[]; private _io=ACME_fnc_ioPainResponse;
        ACME_fnc_ioPainResponse={_ioCalls pushBack _this;_this call _io;};
        missionNamespace setVariable ["ACME_flushReqEnabled",false];
    '''+f'private _site={site}; private _operation="{operation}";'+'''
        _lineIdentity=[_site,3,100];
        private _iv=_site!=-2;
        private _doses=if (_operation=="flush") then {[]} else {[["Ketamine_IV",2,_iv,"mix",3,true]]};
        private _id=if (_iv) then {_lineIdentity} else {[]};
        [_patient,_medic,1,"one",_operation,"leftarm",_doses,_site,_id] call ACME_fnc_medicationLineLocal;
        [_patient,_medic,1,"one",_operation,"leftarm",_doses,_site,_id] call ACME_fnc_medicationLineLocal;
    '''+(f'[_ioCalls isEqualTo [[_patient,"leftarm","{expected_mode}"]],"wrong IO response or duplicate receipt"] call _check;' if expected_mode else
        '[count _ioCalls==0,"non-IO medication caused IO response"] call _check;')+
        f'[count _waits=={int(expected_mode=="fluid")},"bolus/flush syncope distinction lost"] call _check;')
