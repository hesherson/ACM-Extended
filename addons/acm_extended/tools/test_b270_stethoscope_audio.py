"""Execute display/audio controller ownership, cadence and phase in pinned SQFVM.

Numeric playback IDs, native progress metadata, UI controls and callback delivery
are explicit engine adapters. These tests do not prove native hearing or panning.
ACME_B270_BASELINE substitutes only historical Init/Tick/Close for comparisons;
new audio helpers and read-only physiology remain current production source.
"""
import os
import re
import subprocess
from unittest.mock import patch

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute as execute_native_fixture, read
from test_b212_stethoscope_shallow import audio_engine, linear_primitive, setup


def execute(code):
    """Require clean VM execution as well as behavioral assertions."""
    original = subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        output = result.stdout + result.stderr
        assert '[WRN]' not in output, output
        return result

    with patch('test_menu_death_lifecycle.subprocess.run', side_effect=checked):
        execute_native_fixture(code)


def source(name):
    ref = os.environ.get('ACME_B270_BASELINE')
    if ref and name in ('stethoscopeInit', 'stethoscopeTick', 'stethoscopeClose'):
        return subprocess.check_output(['git', '-C', str(ROOT), 'show',
            f'{ref}:addons/acm_extended/functions/fn_{name}.sqf'], text=True)
    return read(name)


def controller(name):
    s = source(name).replace('disableSerialization;', '')
    s = s.replace('findDisplay 81000', '_currentDisplay').replace('getMousePosition', '_mousePosition')
    s = s.replace('isGameFocused', '_gameFocused')
    s = re.sub(r'(_display|_d) displayCtrl (\d+)', r'\2', s)
    s = s.replace('ctrlPosition (81003)', '[0,0,11.5,22]')
    s = s.replace('ctrlPosition _bell', '[0,0,0.05,0.08]')
    s = s.replace('ctrlPosition (81006)', '[100,100,1,1]')
    s = s.replace('_bell ctrlSetPosition ', '_bellPosition = ')
    s = s.replace('_bell ctrlCommit 0;', '').replace('_bell ctrlEnable false;', '')
    s = s.replace('_display displayAddEventHandler ', '_displayEvents pushBack ')
    s = s.replace('_x ctrlAddEventHandler ', '_controlEvents pushBack ')
    s = s.replace('allControls _display', '[81001,81003,81006]').replace('ctrlIDC _x', '_x')
    # The historical native branch executes as well; no source-code replacement
    # pretends old say3D calls used the new UI backend.
    s = s.replace('"#particlesource" createVehicleLocal (positionCameraToWorld [0,22,0])', '(call _createEmitter)')
    s = s.replace('_emitter setPosASL (AGLToASL (positionCameraToWorld [0,_distance,0]));',
                  '_emitterDistances set [_forEachIndex,_distance];')
    s = s.replace('_emitter say3D [_class,20,_pitch,true]',
                  '([_class,_pitch,true,_index] call _say3D)')
    for variable in ('_oldSound', '_sound'):
        s = s.replace(f'deleteVehicle {variable};', f'[{variable}] call _stopSound;')
    s = s.replace('deleteVehicle _emitter;', '_deletedEmitters pushBack _emitter;')
    return adapt(linear_primitive(s))


def fixture():
    helpers = ''.join('ACME_fnc_' + name + '={' + audio_engine(read(name)) + '};'
                      for name in ('stethoscopeAudioOwned', 'stethoscopeAudioStop', 'stethoscopeAudioUpdate'))
    controllers = ''.join('ACME_fnc_' + name + '={' + controller(name) + '};'
                          for name in ('stethoscopeInit', 'stethoscopeTick', 'stethoscopeClose'))
    return setup() + r'''
        private _currentDisplay=missionNamespace; private _mousePosition=[7,6.6];
        private _bellPosition=[]; private _gameFocused=true;
        private _displayEvents=[]; private _controlEvents=[]; private _emitterDistances=[];
        private _deletedEmitters=[]; private _createdEmitters=[];
        private _native=[]; private _stopped=[]; private _serial=0;
        private _voices=createHashMap;
        private _failPlayback=false; private _missingMetadata=false; private _extendedMetadata=false;
        private _length=2; private _nativePositionBias=0;
        // [ID,class,volume,pitch,effects,startOffset,dispatchTime,path,active]
        private _playSoundUI={
            _serial=_serial+1;
            private _id=if (_failPlayback) then {-1} else {_serial};
            private _row=[_id,_this select 0,_this select 1,_this select 2,_this select 3,
                _this param [4,0],_nowTime,_this select 0,true];
            _native pushBack ["UI",+_row];
            if (_id>=0) then {_voices set [_id,_row];};
            _id
        };
        private _soundParams={
            private _id=_this;private _v=if (_id in keys _voices) then {_voices get _id} else {[]};
            if (_missingMetadata || {count _v==0} || {!(_v select 8)}) exitWith {[]};
            private _elapsed=(_nowTime-(_v select 6)) max 0;
            private _position=(_v select 5)+_elapsed*(_v select 3)+_nativePositionBias;
            if (_position>=_length) exitWith {[]};
            // Native schema: path, normalized file position, duration, elapsed
            // time since THIS playback, volume. 2.22 may append loop status.
            private _info=[_v select 7,_position/_length,_length,_elapsed,_v select 2];
            if (_extendedMetadata) then {_info pushBack false;};_info
        };
        private _stopSound={
            private _id=_this select 0; _stopped pushBack _id;
            private _v=if (_id in keys _voices) then {_voices get _id} else {[]};
            if (count _v>0) then {_v set [8,false];};
        };
        private _createEmitter={private _id=100+count _createdEmitters;
            _createdEmitters pushBack _id;_id};
        private _say3D={
            _serial=_serial+1;private _id=if (_failPlayback) then {objNull} else {_serial};
            _native pushBack ["3D",[_id,_this select 0,1,_this select 1,_this select 2,0,_nowTime,_this select 0,true]];
            _id
        };
        private _plays={_native select {(_x select 0)=="UI"}};
        private _active={keys _voices select {((_voices get _x) select 8)
            && {count (_x call _soundParams)>0}}};
        ACME_fnc_clinicalEpoch={0};
        ACME_fnc_stethoscopeSetView={(_this select 0) setVariable ["ACME_stethView",_this select 1];
            (_this select 0) setVariable ["ACME_stethPressed",false];};
        ace_hearing_fnc_updateHearingProtection={};
        // Unload's clinical/pose work is covered by retained lifecycle suites;
        // these audio probes deliberately use absent provider/patient inputs.
        ACME_fnc_stethoscopePressureRelease={};
        private _runPFH={params ["_handle"];private _row=_handlers select _handle;
            if (_row select 2) then {[_row select 1,_handle] call (_row select 0);};};
    ''' + helpers + controllers + r'''
        [_currentDisplay,_patient,_medic] call ACME_fnc_stethoscopeInit;
        private _advance={params ["_at",["_pressed",true]];
            _nowTime=_at; CBA_missionTime=_at;
            _currentDisplay setVariable ["ACME_stethPressed",_pressed];
            [_currentDisplay getVariable "ACME_stethTickPFH"] call _runPFH;
        };
        private _atPoint={params ["_gx","_gy",["_view","front"]];
            _mousePosition=[_gx-8.5,_gy+5.3];
            _currentDisplay setVariable ["ACME_stethCursor",_mousePosition];
            _currentDisplay setVariable ["ACME_stethView",_view];};
        private _channels={_currentDisplay getVariable "ACME_stethChannels"};
        private _row={[-1,"",0,1,-1,0,[],-1,0,-1,-1]};
        private _apply={params ["_rows","_targets","_dt",["_requests",[]]];
            [_rows,_targets,_dt,_nowTime,_requests] call ACME_fnc_stethoscopeAudioUpdate;};
    '''


def test_lifted_bell_never_launches_audio_or_consumes_diagnostic_cadence():
    execute(fixture() + r'''
        [10.1,false] call _advance;
        [count _native==0,"lifted bell launched hidden audio"] call _check;
        [(missionNamespace getVariable "ACME_stethNextBeat")<0
            && {(missionNamespace getVariable "ACME_stethNextBreath")<0},"hidden cadence advanced"] call _check;
    ''')


@pytest.mark.parametrize('point', [(15.5,1.3,'front'),(24.5,1.3,'front'),(25,1.5,'back')])
def test_anatomical_lungs_use_the_same_nonspatial_effects_dispatch(point):
    x,y,view=point
    execute(fixture() + f'''
        [{x},{y},"{view}"] call _atPoint; [10.1,true] call _advance;
        [count (call _plays)>0,"contact produced no UI diagnostic voices"] call _check;
        [(_native findIf {{(_x select 0)!="UI"}})==-1,"contact still uses spatial emitters"] call _check;
        [((call _plays) findIf {{((_x select 1) select 4) || {{((_x select 1) select 2)<=0}}}})==-1,
            "speech routing or zero-gain UI voice dispatched"] call _check;
        [count _createdEmitters==0,"UI session created spatial emitters"] call _check;
    ''')


def test_contact_reacquisition_after_hidden_time_starts_an_audible_breath_immediately():
    execute(fixture() + r'''
        [10.1,false] call _advance;private _old=count _native;
        [12.2,true] call _advance;
        private _new=_native select [_old,count _native-_old];
        [(_new findIf {((_x select 1) select 1) find "Breath" >=0})>=0,
            "reacquired contact waited for hidden breathing cadence"] call _check;
    ''')


def test_first_zero_dt_contact_is_audible_and_duplicate_frame_does_not_replay():
    execute(fixture() + r'''
        [10,true] call _advance; private _old=count _native;
        [count (call _plays)>0,"zero-dt initial contact consumed silent voices"] call _check;
        [10,true] call _advance;
        [count _native==_old,"same frame repeated diagnostic voices"] call _check;
    ''')


@pytest.mark.parametrize('reason', ['release','focus','flip','apnea','arrest','dead'])
def test_immediate_silence_stops_only_the_affected_owned_numeric_ids(reason):
    change={'release':'','focus':'_gameFocused=false;',
            'flip':'missionNamespace setVariable ["ACME_stethFlipActive",true];',
            'apnea':'_patient setVariable ["ACM_breathing_RespirationRate",0];',
            'arrest':'_patient setVariable ["ace_medical_inCardiacArrest",true];',
            'dead':'_patientAlive=false;'}[reason]
    indexes={'apnea':'[0,1,3,4]','arrest':'[2,5,6,7]'}.get(reason,'[0,1,2,3,4,5,6,7]')
    execute(fixture() + f'''
        [10.1,true] call _advance;private _oldIds=(call _channels) apply {{_x select 0}};{change}
        [10.11,{str(reason!='release').lower()}] call _advance;
        private _current=call _channels;
        [({indexes} findIf {{((_current select _x) select 2)!=0 || {{((_current select _x) select 0)>=0}}}})==-1,
            "silence retained a positive gain or live native ID"] call _check;
        {{private _id=_oldIds select _x;
            if (_id isEqualType 0 && {{_id>=0}}) then {{[_id in _stopped,"owned stream was not stopped"] call _check;}};
        }} forEach {indexes};
    ''')


def test_play_failure_retries_are_bounded_and_do_not_wait_an_entire_breath_period():
    execute(fixture() + r'''
        _failPlayback=true; [10.1,true] call _advance;private _old=count _native;
        [10.11,true] call _advance;[10.19,true] call _advance;
        [count _native==_old,"native failure retried every frame"] call _check;
        _failPlayback=false;[10.4,true] call _advance;
        [count _native>_old && {count (call _active)>0},"failure consumed full breath cadence"] call _check;
    ''')


@pytest.mark.parametrize('metadata', ['missing','five','six'])
def test_fresh_native_ids_with_invalid_metadata_are_retired_without_retry_overlap(metadata):
    execute(fixture() + f'''
        _missingMetadata={str(metadata=='missing').lower()};
        _extendedMetadata={str(metadata=='six').lower()};
        [10.1,true] call _advance;
        if (_missingMetadata) then {{
            [(_native findIf {{!(((_x select 1) select 0) in _stopped)}})==-1,
                "fresh ID without metadata remained untracked"] call _check;
            private _old=count _native;[10.11,true] call _advance;
            [count _native==_old,"metadata failure retried too early"] call _check;
            _missingMetadata=false;[10.4,true] call _advance;
        }};
        [count (call _active)>0,"valid native metadata did not retain playable ID"] call _check;
    ''')


def test_stable_voice_preserves_its_id_and_material_gain_changes_seek_native_phase_at_most_five_hz():
    execute(fixture() + r'''
        private _rows=[call _row];
        [_rows,[0.9],0,[[0,"ACM_Stethoscope_Breath_Normal_Normal",1.1,3]]] call _apply;
        private _first=(_rows select 0) select 0;private _old=count _native;
        _nowTime=10.1;[_rows,[0.9],0.1] call _apply;
        [((_rows select 0) select 0)==_first && {count _native==_old},"stable gain restarted clip"] call _check;
        _nativePositionBias=0.2;_nowTime=10.3;[_rows,[0.5],0.1] call _apply;
        private _seek=(_native select (count _native-1)) select 1;
        [(_seek select 0)!=_first && {_first in _stopped},"material gain change did not retire own voice"] call _check;
        [abs ((_seek select 5)-0.53)<0.0001,"gain seek ignored native normalized clip phase"] call _check;
        _nativePositionBias=0;private _after=count _native;
        _nowTime=10.31;[_rows,[0.1],0.1] call _apply;
        [count _native==_after,"gain seek exceeded five Hz bound"] call _check;
    ''')


def test_hidden_anatomical_side_can_join_a_live_breath_phase_without_a_new_cadence():
    execute(fixture() + r'''
        private _rows=[call _row,call _row];
        [_rows,[0.8,0],0,[[0,"normal",1,3],[1,"dull",1,3]]] call _apply;
        [count _native==1 && {((_rows select 1) select 0)<0},"hidden side launched a silent voice"] call _check;
        _nowTime=10.4;[_rows,[0,0.8],0.1] call _apply;
        private _right=(_native select (count _native-1)) select 1;
        [(_right select 1)=="dull" && {abs ((_right select 5)-0.4)<0.0001},
            "new side did not retain current clinical phase/class"] call _check;
    ''')


@pytest.mark.parametrize('mismatch', ['path','progress','elapsed','complete'])
def test_observable_native_id_reuse_or_completion_cannot_stop_another_sound(mismatch):
    change={'path':'_v set [7,"foreign"];','progress':'_v set [5,-0.5];',
            'elapsed':'_v set [6,_nowTime];','complete':'_v set [8,false];'}[mismatch]
    execute(fixture() + f'''
        private _rows=[call _row];[_rows,[0.8],0,[[0,"normal",1,3]]] call _apply;
        private _id=(_rows select 0) select 0;
        _nowTime=10.4;[[_rows select 0,_nowTime] call ACME_fnc_stethoscopeAudioOwned,"normal progress rejected"] call _check;
        private _v=_voices get _id;{change}
        [_rows] call ACME_fnc_stethoscopeAudioStop;
        [!(_id in _stopped),"reused/completed ID was stopped without matching progress proof"] call _check;
        [((_rows select 0) select 0)<0,"stale row retained native ID"] call _check;
    ''')


def test_repeated_init_and_delivered_old_callback_preserve_the_successor_resources():
    execute(fixture() + r'''
        [10.1,true] call _advance;private _oldIds=call _active;
        private _oldHandle=missionNamespace getVariable "ACME_stethTickPFH";
        private _retired=_handlers select _oldHandle;
        [missionNamespace,_patient,_medic] call ACME_fnc_stethoscopeInit;
        [10.3,true] call _advance;private _new=missionNamespace getVariable "ACME_stethTickPFH";
        private _newIds=call _active;private _stops=count _stopped;
        (_retired select 1) set [1,objNull];
        [_retired select 1,_oldHandle] call (_retired select 0);
        [(_oldIds findIf {!(_x in _stopped)})==-1,"Init abandoned original native IDs"] call _check;
        [(missionNamespace getVariable "ACME_stethTickPFH")==_new && {(_handlers select _new) select 2},
            "retired callback cleared successor PFH"] call _check;
        [count _stopped==_stops && {(call _active) isEqualTo _newIds},"old callback stopped successor audio"] call _check;
    ''')


def test_missing_patient_pfh_retires_only_captured_audio():
    execute(fixture() + r'''
        [10.1,true] call _advance;private _old=call _active;
        private _id=missionNamespace getVariable "ACME_stethTickPFH";
        ((_handlers select _id) select 1) set [1,objNull];[_id] call _runPFH;
        [!((_handlers select _id) select 2),"invalid patient PFH remained live"] call _check;
        [(_old findIf {!(_x in _stopped)})==-1,"invalid patient callback abandoned captured native IDs"] call _check;
        [(missionNamespace getVariable "ACME_stethTickPFH")==-1,"invalid callback retained its handle marker"] call _check;
    ''')


def test_old_display_unload_cannot_stop_a_current_display_and_duplicate_unload_is_idempotent():
    execute(fixture() + r'''
        [10.1,true] call _advance;private _old=call _active;
        _currentDisplay=uiNamespace;[_currentDisplay,_patient,_medic] call ACME_fnc_stethoscopeInit;
        [10.3,true] call _advance;private _new=(call _active) select {!(_x in _old)};
        missionNamespace setVariable ["ACME_stethMedic",objNull];
        missionNamespace setVariable ["ACME_stethPatient",objNull];
        [missionNamespace] call ACME_fnc_stethoscopeClose;
        [(_old findIf {!(_x in _stopped)})==-1,"Unload did not stop exact old display IDs"] call _check;
        [(_new findIf {_x in _stopped})==-1,"old display stopped current UI voices"] call _check;
        private _count=count _stopped;[missionNamespace] call ACME_fnc_stethoscopeClose;
        [count _stopped==_count,"duplicate Unload stopped IDs twice"] call _check;
    ''')
