"""Run monitor feed and charge generations with explicit engine/network boundaries."""
from pathlib import Path
import re

import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_b306_tempus_clinical import shock_setup


def source(addon, name):
    return (ROOT / 'addons' / addon / 'functions' / f'fn_{name}.sqf').read_text()


def charge_setup():
    charge = adapt(source('acme_tempusls', 'tempusLsCharge'))
    charge = charge.replace('finite _energy', '(_energy isEqualType 0)').replace('serverTime', '_nowTime')
    clear = adapt(source('acme_tempusls', 'tempusLsChargeClear'))
    return '''
      private _o=missionNamespace;private _fixtureEpoch=4;
      _o setVariable ["acme_tempusls_pat",_patient];
      _o setVariable ["acme_tempusls_pw",[true,1]];
      _o setVariable ["acme_tempusls_charge",[]];
      _o setVariable ["acme_tempusls_charging",[]];
      ACME_fnc_clinicalEpoch={_fixtureEpoch};
      ACME_fnc_tempusLsChargeClear={'''+clear+'''};
      ACME_fnc_tempusLsCharge={'''+charge+'''};
    '''


@pytest.mark.parametrize('change', [
    '_o setVariable ["acme_tempusls_pat",_medic];',
    '_o setVariable ["acme_tempusls_pat",objNull];',
    '_fixtureEpoch=5;',
    '_o setVariable ["acme_tempusls_pw",[false,1]];',
    '_o setVariable ["acme_tempusls_pw",[true,2]];',
    '_nowTime=26;',
    '_nowTime=9;',
    '[_o] call ACME_fnc_tempusLsChargeClear;',
    '[_o,"begin",200] call ACME_fnc_tempusLsCharge;',
])
def test_ready_from_retired_patient_power_or_charge_cannot_rearm(change):
    execute(charge_setup()+'''
      private _context=[_o,"begin",150] call ACME_fnc_tempusLsCharge;
    '''+change+'''
      private _ready=[_o,"ready",0,_context] call ACME_fnc_tempusLsCharge;
      [_ready isEqualTo [],"stale ready retained authorization"] call _check;
      [!(_o getVariable ["acme_tempusls_armed",false]),"stale ready armed the device"] call _check;
    ''')


@pytest.mark.parametrize('energy', [0, -1, 201])
def test_out_of_range_charge_never_starts(energy):
    execute(charge_setup()+f'''
      private _context=[_o,"begin",{energy}] call ACME_fnc_tempusLsCharge;
      [_context isEqualTo [],"invalid energy started a charge"] call _check;
    ''')


def test_charge_ready_is_single_use_and_bound_to_original_energy():
    execute(charge_setup()+'''
      private _context=[_o,"begin",150] call ACME_fnc_tempusLsCharge;
      private _charge=[_o,"ready",0,_context] call ACME_fnc_tempusLsCharge;
      [count _charge==6 && {(_charge select 4)==150} && {(_charge select 5)==30},"charge context lost energy/expiry"] call _check;
      [(_o getVariable ["acme_tempusls_armed",false]),"current ready failed"] call _check;
      [([_o,"ready",0,_context] call ACME_fnc_tempusLsCharge) isEqualTo [],"ready replay reauthorized charge"] call _check;
    ''')


def sound_setup():
    sound = adapt(source('acme_tempusls', 'tempusLsSound')).replace('serverTime', '_nowTime')
    sound = re.sub(r'playSound3D \[[^\]]+\]', '_sounds=_sounds+1', sound)
    return charge_setup()+'''
      private _sounds=0;private _callbacks=[];private _removedPFHs=[];
      CBA_fnc_addPerFrameHandler={_callbacks pushBack _this;count _callbacks-1};
      CBA_fnc_removePerFrameHandler={_removedPFHs pushBack (_this select 0)};
      ACME_fnc_tempusLsSound={'''+sound+'''};
    '''


def test_previous_alarm_expiry_cannot_disarm_replacement_charge():
    execute(sound_setup()+'''
      private _first=[_o,"charge","150"] call ACME_fnc_tempusLsSound;
      [_o,"ready","",_first] call ACME_fnc_tempusLsSound;
      _nowTime=15;
      private _second=[_o,"charge","150"] call ACME_fnc_tempusLsSound;
      [_o,"ready","",_second] call ACME_fnc_tempusLsSound;
      _nowTime=31;
      [(_callbacks select 0) select 2,0] call ((_callbacks select 0) select 0);
      [(_o getVariable ["acme_tempusls_armed",false]),"retired timer disarmed replacement charge"] call _check;
      [0 in _removedPFHs,"retired timer remained registered"] call _check;
      _nowTime=36;
      [(_callbacks select 1) select 2,1] call ((_callbacks select 1) select 0);
      [!(_o getVariable ["acme_tempusls_armed",true]),"current charge did not expire"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_o setVariable ["acme_tempusls_charge",[]];',
    '_request set [9,"retired-charge"];',
    '_request set [3,200];',
    '_o setVariable ["acme_tempusls_charge",["charge-1",_medic,4,[true],150,30]];',
    '_o setVariable ["acme_tempusls_charge",["charge-1",_patient,3,[true],150,30]];',
    '_o setVariable ["acme_tempusls_charge",["charge-1",_patient,4,[true,2],150,30]];',
    '_o setVariable ["acme_tempusls_charge",["charge-1",_patient,4,[true],150,9]];',
])
def test_retired_or_changed_charge_cannot_shock(change):
    execute(shock_setup()+change+'''
      _request call ACME_fnc_tempusLsShock;
      [count _calls==0,"invalid charge reached clinical shock backend"] call _check;
    ''')


@pytest.mark.parametrize('target', ['objNull','_medic'])
def test_pad_change_clears_charge_and_old_pacer_configuration(target):
    connect=source('acme_tempusls','tempusLsConnect')
    connect=re.sub(r'(\[[^;\n]+\]) remoteExecCall \["ACME_fnc_tempusLs(?:Feed|Pace)", _\w+\]',r'_routes pushBack \1',connect)
    execute(charge_setup()+'''
      private _routes=[];
      ace_common_fnc_getName={"QA"};ace_common_fnc_displayTextStructured={};
      ace_medical_treatment_fnc_addToLog={};
      private _context=[_o,"begin",150] call ACME_fnc_tempusLsCharge;
      [_o,"ready",0,_context] call ACME_fnc_tempusLsCharge;
      _o setVariable ["acme_tempusls_st","old-browser-state"];
      _o setVariable ["acme_tempusls_pace",[true,80,100,true]];
      ACME_fnc_tempusLsConnect={'''+adapt(connect)+'''};
      [_o,'''+target+'''] call ACME_fnc_tempusLsConnect;
      [!(_o getVariable ["acme_tempusls_armed",true]),"pads carried a live charge"] call _check;
      [(_o getVariable "acme_tempusls_st")=="","pad change retained old browser state"] call _check;
      [!((_o getVariable "acme_tempusls_pace") select 0),"pad change restarted old pacing settings"] call _check;
      [count _routes>=1,"old patient pacing was not retired"] call _check;
    ''')


def test_device_move_retires_both_charge_authorizations():
    move=source('acme_tempusls','tempusLsMove')
    move=re.sub(r'\[[^;\n]+\] remoteExecCall \["ACME_fnc_tempusLsPace", _pat\];','_routes=_routes+1;',move)
    move=move.replace('[_to, _pat] remoteExecCall ["ACME_fnc_tempusLsFeed", _pat];','_feeds=_feeds+1;')
    execute(charge_setup()+'''
      private _routes=0;private _feeds=0;
      _o setVariable ["acme_tempusls_pace",[false,70,0,false]];
      private _context=[_o,"begin",150] call ACME_fnc_tempusLsCharge;
      [_o,"ready",0,_context] call ACME_fnc_tempusLsCharge;
      _medic setVariable ["acme_tempusls_armed",true];
      _medic setVariable ["acme_tempusls_charge",["older-destination-charge"]];
      ACME_fnc_tempusLsMove={'''+adapt(move)+'''};
      [_o,_medic] call ACME_fnc_tempusLsMove;
      [!(_o getVariable ["acme_tempusls_armed",true]),"source retained live charge"] call _check;
      [!(_medic getVariable ["acme_tempusls_armed",true]),"destination retained live charge"] call _check;
      [(_medic getVariable "acme_tempusls_operator") isEqualTo _medic,"moving provider was not assigned"] call _check;
      [_routes==1 && {_feeds==1},"move did not retire source pacing and start destination feed"] call _check;
    ''')


@pytest.mark.parametrize('addon,fn,prefix', [
    ('acme_tempus','tempusFeed','acme_tempus'),
    ('acme_tempusls','tempusLsFeed','acme_tempusls'),
])
@pytest.mark.parametrize('sequence', ['replacement','delayed_request','handoff','duplicate','range'])
def test_feed_callback_has_exclusive_generation(addon, fn, prefix, sequence):
    feed=source(addon,fn).replace('local _u','_patientLocal').replace('_u distance _o','_cableReach')
    feed=feed.replace(f'[_o, _u] remoteExecCall ["ACME_fnc_{fn}", _u]', '_routes pushBack [_o,_u]')
    feed=adapt(feed)
    setup=f'''
      private _o=missionNamespace;private _patientLocal=true;private _cableReach=1;
      private _callbacks=[];private _routes=[];private _removedPFHs=[];private _clears=0;
      _o setVariable ["{prefix}_pat",_patient];
      _o setVariable ["{prefix}_pw",[true]];
      CBA_fnc_addPerFrameHandler={{_callbacks pushBack _this;count _callbacks-1}};
      CBA_fnc_removePerFrameHandler={{_removedPFHs pushBack (_this select 0)}};
      ACME_fnc_tempusVitals={{[73]}};ACME_fnc_tempusLsVitals={{[73]}};
      ACME_fnc_tempusLsPace={{}};ACME_fnc_tempusLsChargeClear={{_clears=_clears+1}};
      ACME_fnc_{fn}={{'''+feed+f'''}};
      private _tickFeed={{params ["_index"];[(_callbacks select _index) select 2,_index] call ((_callbacks select _index) select 0);}};
      [_o,_patient] call ACME_fnc_{fn};
    '''
    cases={
      'replacement': f'''
        _o setVariable ["{prefix}_pat",_medic];
        [_o,_medic] call ACME_fnc_{fn};
        private _replacement=_o getVariable "{prefix}_feeding";
        [0] call _tickFeed;
        [(_o getVariable "{prefix}_feeding") isEqualTo _replacement,"old callback cleared new feed"] call _check;
        [1] call _tickFeed;
        [(_o getVariable "{prefix}_v") isEqualTo [73],"replacement feed did not publish"] call _check;
      ''',
      'delayed_request': f'''
        _o setVariable ["{prefix}_pat",_medic];
        [_o,_medic] call ACME_fnc_{fn};
        [_o,_patient] call ACME_fnc_{fn};
        [count _callbacks==2,"delayed old request installed a third feed"] call _check;
      ''',
      'handoff': f'''
        _patientLocal=false;[0] call _tickFeed;
        [count _routes==1 && {{0 in _removedPFHs}},"locality handoff failed"] call _check;
        [(_o getVariable "{prefix}_feeding") isEqualTo [],"handoff left local feeding marker"] call _check;
      ''',
      'duplicate': f'''
        [_o,_patient] call ACME_fnc_{fn};
        [count _callbacks==1,"duplicate request installed competing feeds"] call _check;
      ''',
      'range': f'''
        _cableReach=6.01;[0] call _tickFeed;
        [(_o getVariable "{prefix}_pat") isEqualTo objNull,"range break retained connection"] call _check;
        [(_o getVariable "{prefix}_v") isEqualTo [],"range break retained vitals"] call _check;
      ''',
    }
    execute(setup+cases[sequence])
