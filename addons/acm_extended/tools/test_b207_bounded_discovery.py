"""Execute manual-carrier registry and ventilator discovery/playback source.

World queries, object state, audio and CBA delivery are recording stand-ins.
No real Arma transport, audio propagation or measured FPS is represented.
"""
import re
import pytest
from test_menu_death_lifecycle import F, adapt, execute as run_sqf
from test_historical_vial_execution import map_defaults
from test_historical_medication_rows import iteration_scopes


def execute(code):
    run_sqf('private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};' + map_defaults(iteration_scopes(code)))


def carrier_source():
    text = (F / 'fn_registerManualPlateCarrierRuntime.sqf').read_text().split('if (hasInterface &&', 1)[0]
    for name in ('_patient', '_p'):
        text = text.replace('local ' + name, f'({name} getVariable ["testLocal",true])')
        text = text.replace('alive ' + name, f'({name} getVariable ["testAlive",true])')
    for old, new in {
        'allUnits': '(call _scanWorld)',
        'objectParent _p': '(_p getVariable ["testVehicle",objNull])',
        'attachedTo _p': '(_p getVariable ["testAttached",objNull])',
        '_p distance2D _origin': '(_p getVariable ["testMoved",0])',
        'vest _p': '(_p getVariable ["testVest",""])',
    }.items(): text = text.replace(old, new)
    # Parent/attachment results are namespace object stand-ins too.
    text = text.replace('!isNull (_p getVariable ["testVehicle",objNull])', '!((_p getVariable ["testVehicle",objNull]) isEqualTo objNull)')
    text = text.replace('!isNull (_p getVariable ["testAttached",objNull])', '!((_p getVariable ["testAttached",objNull]) isEqualTo objNull)')
    return adapt(text)


def carrier_setup():
    return r'''
        private _eventsByName=[]; private _classEvents=[]; private _pfhs=[];
        private _scans=0; private _world=[_patient,_medic]; private _returns=[];
        private _scanWorld={_scans=_scans+1;_world};
        CBA_fnc_addEventHandler={_eventsByName pushBack _this;count _eventsByName};
        CBA_fnc_addClassEventHandler={_classEvents pushBack _this;count _classEvents};
        CBA_fnc_addPerFrameHandler={_pfhs pushBack _this;count _pfhs-1};
        CBA_fnc_localEvent={params ["_event","_args"]; {if ((_x select 0)==_event) then {_args call (_x select 1);};} forEach _eventsByName;};
        CBA_fnc_execNextFrame={_waits pushBack [_this select 0,_this select 1];};
        ACME_fnc_manualPlateCarrierAutoReturn={params ["_p","_reason"];_returns pushBack [_p,_reason];_p setVariable ["ACME_manualPlateCarrierState",""];};
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_manualPlateCarrierState","off"];
        _patient setVariable ["ACME_manualPlateCarrierOriginASL",[0,0,0]];
    ''' + carrier_source() + r'''
        private _watch={[] call (_pfhs select 0 select 0);};
        private _trackPatient={["ACME_manualPlateCarrierTrack",[_patient]] call CBA_fnc_localEvent;};
        private _classEvent={params ["_name","_args"];{if ((_x select 1)==_name) then {_args call (_x select 2);};} forEach _classEvents;};
    '''


def test_hot_carrier_watch_uses_only_active_registry_and_world_audit_is_thirty_seconds():
    execute(carrier_setup() + r'''
        call _watch;
        [ACME_manualPlateCarrierPatients isEqualTo [_patient],"healthy irrelevant unit enrolled"] call _check;
        [(_pfhs select 0 select 1)==.20,"fast active-lease safety cadence changed"] call _check;
        for "_i" from 1 to 100 do {CBA_missionTime=10+_i*.2;call _watch;};
        [_scans==1,"hot watchdog still scans the world"] call _check;
        [count _returns==0,"unchanged unconscious casualty had carrier restored"] call _check;
        CBA_missionTime=40;call _watch;
        [_scans==2,"slow missing-event audit was lost"] call _check;
    ''')


@pytest.mark.parametrize('change,reason', [
    ('_patient setVariable ["ACE_isUnconscious",false];', 'awake'),
    ('_patient setVariable ["testVehicle",_medic];', 'transport'),
    ('_patient setVariable ["testAttached",_medic];', 'transport'),
    ('_patient setVariable ["testMoved",.36];', 'moved'),
    ('_patient setVariable ["testVest","carrier"];', 'external-restore'),
])
def test_active_manual_carrier_still_auto_returns_on_next_fast_pass(change, reason):
    execute(carrier_setup() + 'call _trackPatient;' + change + r'''
        ACME_manualPlateCarrierRecoveryAt=100;call _watch;
    ''' + f'[_returns isEqualTo [[_patient,"{reason}"]],"auto-return condition changed"] call _check;' + r'''
        [ACME_manualPlateCarrierPatients isEqualTo [],"restored patient remained enrolled"] call _check;
        [_scans==0,"fast active return required world discovery"] call _check;
    ''')


def test_local_transfer_reenrols_immediately_and_delayed_callback_cannot_reenrol_departed_owner():
    execute(carrier_setup() + r'''
        call _trackPatient;
        _patient setVariable ["testLocal",false];["Local",[_patient,false]] call _classEvent;
        [ACME_manualPlateCarrierPatients isEqualTo [],"old owner kept hot lease"] call _check;
        {(_x select 1) call (_x select 0);} forEach (+_waits);
        [ACME_manualPlateCarrierPatients isEqualTo [],"departed owner re-enrolled from retry"] call _check;
        _patient setVariable ["testLocal",true];["Local",[_patient,true]] call _classEvent;
        [ACME_manualPlateCarrierPatients isEqualTo [_patient],"returning owner waited for slow scan"] call _check;
    ''')


def test_init_and_late_local_state_retry_recover_without_world_scan():
    execute(carrier_setup() + r'''
        _patient setVariable ["ACME_manualPlateCarrierState",""];
        ["Local",[_patient,true]] call _classEvent;
        [ACME_manualPlateCarrierPatients isEqualTo [],"empty ownership transfer registered"] call _check;
        _patient setVariable ["ACME_manualPlateCarrierState","off"];
        {(_x select 1) call (_x select 0);} forEach (+_waits);
        [ACME_manualPlateCarrierPatients isEqualTo [_patient],"late replicated lease not recovered"] call _check;
        ACME_manualPlateCarrierPatients=[];_waits=[];
        ["init",[_patient]] call _classEvent;
        {(_x select 1) call (_x select 0);} forEach (+_waits);
        [ACME_manualPlateCarrierPatients isEqualTo [_patient],"init lease not enrolled"] call _check;
        [_scans==0,"event recovery required world scan"] call _check;
    ''')


def test_death_preserves_custody_while_reset_prunes_the_fast_registry():
    execute(carrier_setup() + r'''
        call _trackPatient;
        _patient setVariable ["testAlive",false];["Killed",[_patient]] call _classEvent;
        [ACME_manualPlateCarrierPatients isEqualTo [],"corpse retained in hot registry"] call _check;
        [(_patient getVariable ["ACME_manualPlateCarrierState",""])=="off" && {count _returns==0},"death altered intervention evidence"] call _check;
        _patient setVariable ["testAlive",true];call _trackPatient;
        _patient setVariable ["ACME_manualPlateCarrierState",""];call _watch;
        [ACME_manualPlateCarrierPatients isEqualTo [],"cleared reset state retained"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["testLocal",false];',
    '_patient setVariable ["testAlive",false];',
    '_patient setVariable ["ACME_manualPlateCarrierState",""];',
])
def test_fast_pass_prunes_stale_entries_without_skipping_other_active_lease(change):
    execute(carrier_setup()+r'''
        _medic setVariable ["ACE_isUnconscious",true];
        _medic setVariable ["ACME_manualPlateCarrierState","off"];
        ACME_manualPlateCarrierPatients=[objNull,_patient,_medic];
        ACME_manualPlateCarrierRecoveryAt=100;
    '''+change+r'''
        call _watch;
        [ACME_manualPlateCarrierPatients isEqualTo [_medic],"stale lease blocked a live lease or survived pruning"] call _check;
        [_scans==0 && {count _returns==0},"stale cleanup required world scan or restored another patient"] call _check;
    ''')


@pytest.mark.parametrize('event', ['ace_dragging_setupDrag','ace_dragging_setupCarry'])
def test_transport_event_preserves_immediate_return_before_fast_pass(event):
    execute(carrier_setup() + f'["{event}",[_medic,_patient]] call CBA_fnc_localEvent;' + r'''
        [_returns isEqualTo [[_patient,"transport"]],"transport waited for registry discovery"] call _check;
        [_scans==0,"transport event scanned world"] call _check;
    ''')


def test_state_transitions_all_notify_existing_registry_event():
    commit=(F/'fn_manualPlateCarrierCommit.sqf').read_text()
    auto=(F/'fn_manualPlateCarrierAutoReturn.sqf').read_text()
    for state in ('removing','restoring','off',''):
        assert re.search(r'setVariable \["ACME_manualPlateCarrierState", "'+state+r'", true\];\s*\["ACME_manualPlateCarrierTrack",',commit)
    assert 'setVariable ["ACME_manualPlateCarrierState", "", true];\n["ACME_manualPlateCarrierTrack", [_patient]] call CBA_fnc_localEvent;' in auto


def alarm_setup():
    text=(F/'fn_registerVentilatorAudioRuntime.sqf').read_text().split('// ventilator alarm tones.',1)[1].split('// client side. Play the baked',1)[0]
    for old,new in {
        '(_plr nearEntities [["CAManBase", "LandVehicle", "Air", "Ship"], 25])':'(call _discover)',
        '_x isKindOf "CAManBase"':'(_x getVariable ["testMan",true])',
        'crew _x':'(_x getVariable ["testCrew",[]])',
        'crew _listenerVehicle':'(_listenerVehicle getVariable ["testCrew",[]])',
        'vehicle _plr':'(_plr getVariable ["testVehicle",_plr])',
        'vehicle ACE_player':'(ACE_player getVariable ["testVehicle",ACE_player])',
        '_mv != ACE_player':'_mv isNotEqualTo ACE_player',
        '_plr distance _pat':'(_pat getVariable ["testDistance",1])',
        'alive _pat':'(_pat getVariable ["testAlive",true])',
        'netId _pat':'(_pat getVariable ["testId","patient"])',
        '_mv isKindOf "Air"':'false',
        'isEngineOn _mv':'false',
        'getPosASL _src':'[0,0,0]',
        'playSound3D':'_beeps pushBack',
        'serverTime':'_nowTime',
    }.items(): text=text.replace(old,new)
    return r'''
        private _scans=0;private _nearby=[_patient];private _beeps=[];private _pfhs=[];
        private _discover={_scans=_scans+1;_nearby};
        CBA_fnc_addPerFrameHandler={_pfhs pushBack _this;count _pfhs-1};
        _patient setVariable ["ACME_vent_alarms",["pressure"]];
        _patient setVariable ["ACME_vent_alarmPrio",3];
    '''+adapt(text)+r'''
        private _alarmTick={[_pfhs select 0 select 2] call (_pfhs select 0 select 0);};
    '''


def test_nearby_discovery_is_two_hz_and_high_priority_beep_pattern_stays_five_per_burst():
    execute(alarm_setup()+r'''
        private _beepAt=[];
        for "_i" from 0 to 40 do {
            _nowTime=10+_i*.05;private _before=count _beeps;call _alarmTick;
            if (count _beeps>_before) then {_beepAt pushBack _nowTime;};
        };
        [_scans==5,"20Hz beep clock still rediscovers entities"] call _check;
        [(_pfhs select 0 select 1)==.05,"beep timing resolution changed"] call _check;
        [_beepAt isEqualTo [10,10.4,10.8,11.2,11.6,12],"HIGH burst cadence changed"] call _check;
    ''')


@pytest.mark.parametrize('priority,expected',[(1,1),(2,3)])
def test_medium_and_low_patterns_are_unchanged(priority,expected):
    execute(alarm_setup()+f'_patient setVariable ["ACME_vent_alarmPrio",{priority}];'+r'''
        for "_i" from 0 to 90 do {_nowTime=10+_i*.05;call _alarmTick;};
    '''+f'[count _beeps=={expected},"medium/low alarm pattern changed"] call _check;')


def test_crew_discovery_includes_own_and_nearby_vehicles_and_deduplicates_patients():
    execute(alarm_setup()+r'''
        private _vehicle=missionNamespace;
        _vehicle setVariable ["testMan",false];_vehicle setVariable ["testCrew",[_patient]];
        _medic setVariable ["testVehicle",_vehicle];_nearby=[_vehicle,_patient];
        call _alarmTick;
        [ACME_vent_alarmCandidates isEqualTo [_patient],"crew duplicate or omitted"] call _check;
        [count _beeps==1 && {(_beeps select 0 select 1) isEqualTo ACE_player},"embarked alarm not emitted at listener"] call _check;
        _nearby=[];_nowTime=10.5;call _alarmTick;
        [ACME_vent_alarmCandidates isEqualTo [_patient],"own vehicle crew lost when vehicle omitted from query"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["testDistance",26];',
    '_patient setVariable ["testAlive",false];',
    '_patient setVariable ["ACME_vent_alarmSilencedUntil",100];',
])
def test_out_of_range_death_and_silence_retire_alarm_on_next_audio_tick(change):
    execute(alarm_setup()+'call _alarmTick;'+change+r'''
        _nowTime=10.1;call _alarmTick;
        [_scans==1 && {count ACME_vent_alarmSnd==0},"inactive alarm waited for discovery cadence"] call _check;
        [count _beeps==1,"inactive alarm played again"] call _check;
    ''')


def test_listener_and_vehicle_switch_force_immediate_candidate_refresh():
    execute(alarm_setup()+r'''
        call _alarmTick;
        _nowTime=10.1;_medic setVariable ["testVehicle",missionNamespace];call _alarmTick;
        [_scans==2,"entering vehicle waited for cached discovery"] call _check;
        ACE_player=missionNamespace;_nowTime=10.2;call _alarmTick;
        [_scans==3,"player replacement inherited old listener cache"] call _check;
    ''')


def test_new_nearby_alarm_is_discovered_within_half_second_then_priority_changes_remain_immediate():
    execute(alarm_setup()+r'''
        _nearby=[];call _alarmTick;
        _nearby=[_patient];_nowTime=10.45;call _alarmTick;
        [count _beeps==0 && {_scans==1},"candidate query escaped its bound"] call _check;
        _nowTime=10.5;call _alarmTick;
        [count _beeps==1 && {_scans==2},"new nearby alarm missed next discovery"] call _check;
        _patient setVariable ["ACME_vent_alarmPrio",2];_nowTime=10.55;call _alarmTick;
        [count _beeps==2 && {_scans==2},"priority change waited for candidate discovery"] call _check;
    ''')
