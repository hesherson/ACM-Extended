"""Execute production capture/aggregation; frame clocks and mission EH delivery are engine fixtures.

Work counts and bounded telemetry behavior are testable here. Native handler cost,
rendering, CBA timing and any FPS improvement require the documented Arma capture.
"""
from pathlib import Path
import re

import pytest

from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import adapt, execute
from source_scan import lex, matching

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / f"fn_{name}.sqf").read_text()


def engine(text):
    text = text.replace("diag_tickTime", "_clock").replace("diag_deltaTime", "_frameDelta")
    text = text.replace("isServer", "_server").replace("hasInterface", "_interface")
    text = text.replace("clientOwner", "7").replace("toLowerANSI", "toLower")
    text = re.sub(r"\bfinite (_\w+)", r"([\1] call _finite)", text)
    text = text.replace('addMissionEventHandler ["EachFrame", _code]',
                        '(["EachFrame", _code] call _addMissionEventHandler)')
    text = text.replace('removeMissionEventHandler ["EachFrame", _state get "handle"];',
                        '["EachFrame", _state get "handle"] call _removeMissionEventHandler;')
    return map_defaults(text)


def setup():
    return r'''
        private _clock=10; private _frameDelta=0.016;
        private _server=true; private _interface=true;
        private _missionHandlers=[]; private _missionRemovals=[];
        private _finite={params ["_value"]; _value isEqualType 0 && {abs _value < 1e30}};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _addMissionEventHandler={_missionHandlers pushBack _this;count _missionHandlers-1};
        private _removeMissionEventHandler={_missionRemovals pushBack _this;};
        private _frame={call ((_missionHandlers select ((count _missionHandlers)-1)) select 1);};
    ''' + "".join("ACME_fnc_" + name + "={" + engine(source(name)) + "};\n"
                  for name in ("performanceDiagnostics", "performanceRecord"))


def test_disabled_record_report_and_stop_have_no_observer_or_state_mutation():
    execute(setup() + r'''
        [!(["circHandle",100] call ACME_fnc_performanceRecord),"disabled record accepted work"] call _check;
        private _report=[] call ACME_fnc_performanceDiagnostics;
        [!(_report get "active") && {count (_report get "samples")==0},"default report was active"] call _check;
        ["stop"] call ACME_fnc_performanceDiagnostics;
        ["unknown"] call ACME_fnc_performanceDiagnostics;
        [count _missionHandlers==0 && {count _missionRemovals==0},"passive diagnostics changed observers"] call _check;
        [isNil "ACME_performance_state" && {isNil "ACME_performance_enabled"},"disabled diagnostics created state"] call _check;
    ''')


def test_named_timings_and_every_observed_frame_are_aggregated_per_second():
    execute(setup() + r'''
        ACME_clinical_ownedUnits=[_patient,_medic];ACME_aiProtection_candidates=[_patient];
        ["start",4] call ACME_fnc_performanceDiagnostics;
        ["circHandle",2] call ACME_fnc_performanceRecord;
        ["circHandle",4] call ACME_fnc_performanceRecord;
        ["handleUnitVitalsEvent",3] call ACME_fnc_performanceRecord;
        _frameDelta=0.010;call _frame;
        _clock=10.5;_frameDelta=0.030;call _frame;
        _clock=11.1;_frameDelta=0.020;call _frame;
        ["circHandle",1] call ACME_fnc_performanceRecord;
        private _report=["report"] call ACME_fnc_performanceDiagnostics;
        private _samples=_report get "samples";private _first=_samples select 0;
        [count _samples==2,"second boundary did not close one bucket"] call _check;
        [(_first select [0,4]) isEqualTo [0,2,20,30],"frame count/mean/max incorrect"] call _check;
        [(_first select 4) isEqualTo [["circHandle",2,6,4],["handleUnitVitalsEvent",1,3,3]],"timing calls/total/max incorrect"] call _check;
        [((_first select 5) select 2) isEqualTo ["ACME_aiProtection_candidates",1],"candidate registry count missing"] call _check;
        [((_samples select 1) select [0,4]) isEqualTo [1,1,20,20],"new bucket retained previous frames"] call _check;
        [count _missionHandlers==1 && {count _missionRemovals==0},"capture created extra observers"] call _check;
    ''')


@pytest.mark.parametrize("requested,expected", [(0, 1), (-5, 1), (3, 3), (600, 600), (9000, 600)])
def test_duration_caps_stop_on_deadline_without_catchup_or_unbounded_samples(requested, expected):
    execute(setup() + f'["start",{requested}] call ACME_fnc_performanceDiagnostics;' + f'''
        for "_i" from 0 to {expected - 1} do {{
            _clock=10+_i+0.1;["ownerLifecycle",1] call ACME_fnc_performanceRecord;call _frame;
        }};
        _clock=10+{expected};call _frame;
        private _report=["report"] call ACME_fnc_performanceDiagnostics;
        [!(_report get "active") && {{(_report get "limitSeconds")=={expected}}},"duration cap failed"] call _check;
        [count (_report get "samples")=={expected} && {{count _missionRemovals==1}},"sample cap or observer retirement failed"] call _check;
        ["ownerLifecycle",100] call ACME_fnc_performanceRecord;call _frame;
        [count ((["report"] call ACME_fnc_performanceDiagnostics) get "samples")=={expected},"expired capture kept recording"] call _check;
    ''')


def test_scheduler_stall_records_only_observed_seconds_and_preserves_long_frame():
    execute(setup() + r'''
        ["start",10] call ACME_fnc_performanceDiagnostics;
        call _frame;
        _clock=17.5;_frameDelta=7.5;call _frame;
        ["stop"] call ACME_fnc_performanceDiagnostics;
        private _samples=(["report"] call ACME_fnc_performanceDiagnostics) get "samples";
        [count _samples==2 && {((_samples select 1) select 0)==7},"stall fabricated catchup buckets"] call _check;
        [((_samples select 1) select 3)==7500,"long frame was hidden"] call _check;
    ''')


def test_start_stop_restart_are_idempotent_and_old_observer_cannot_write_new_capture():
    execute(setup() + r'''
        ["start",5] call ACME_fnc_performanceDiagnostics;
        private _old=(_missionHandlers select 0) select 1;
        ["start",600] call ACME_fnc_performanceDiagnostics;
        [count _missionHandlers==1 && {((["report"] call ACME_fnc_performanceDiagnostics) get "limitSeconds")==5},"repeat start replaced capture"] call _check;
        call _frame;["stop"] call ACME_fnc_performanceDiagnostics;["stop"] call ACME_fnc_performanceDiagnostics;
        [count _missionRemovals==1,"repeat stop retired twice"] call _check;
        _clock=11;["start",5] call ACME_fnc_performanceDiagnostics;call _old;
        ["circHandle",999,-1,1] call ACME_fnc_performanceRecord;
        [count ((["report"] call ACME_fnc_performanceDiagnostics) get "samples")==0,"stale observer sampled restart"] call _check;
        call _frame;
        [count ((["report"] call ACME_fnc_performanceDiagnostics) get "samples")==1,"new observer failed"] call _check;
    ''')


def test_reports_are_independent_and_unknown_names_cannot_grow_timing_state():
    execute(setup() + r'''
        ["start",5] call ACME_fnc_performanceDiagnostics;
        ["circHandle",2] call ACME_fnc_performanceRecord;call _frame;
        _clock=11.1;call _frame;
        private _report=["report"] call ACME_fnc_performanceDiagnostics;
        ((((_report get "samples") select 0) select 4) select 0) set [1,999];
        private _fresh=["report"] call ACME_fnc_performanceDiagnostics;
        [(((((_fresh get "samples") select 0) select 4) select 0) select 1)==1,"report mutated retained timing"] call _check;
        for "_i" from 1 to 100 do {[format ["unknown-%1",_i],1] call ACME_fnc_performanceRecord;};
        ["circHandle",-1] call ACME_fnc_performanceRecord;
        ["circHandle",1e35] call ACME_fnc_performanceRecord;
        private _last=(((["report"] call ACME_fnc_performanceDiagnostics) get "samples") select 1) select 4;
        [count _last==0,"invalid/unbounded timing names entered capture"] call _check;
    ''')


def test_production_capture_has_no_network_world_scan_logging_or_automatic_installation():
    for name in ("performanceDiagnostics", "performanceRecord"):
        identifiers={token.value for token in lex(source(name)) if token.kind == "ident"}
        assert not identifiers & {"allUnits", "allPlayers", "allGroups", "nearestObjects", "remoteExec", "diag_log",
                                  "publicVariable", "CBA_fnc_globalEvent", "CBA_fnc_targetEvent", "CBA_fnc_addPerFrameHandler"}
    text=source("performanceDiagnostics")
    assert text.count('addMissionEventHandler ["EachFrame"') == 1
    assert text.index('case "start"') < text.index('addMissionEventHandler ["EachFrame"')
    assert 'removeMissionEventHandler ["EachFrame"' in text


def test_instrumented_native_vitals_include_event_and_skip_medication_clones_when_empty():
    text=(ROOT.parent / "core/overrides/fnc_handleUnitVitals.sqf").read_text()
    tokens=lex(text);pairs=matching(tokens)
    branch=text.index('if (_adjustments isNotEqualTo []) then {')
    opening=next(i for i,t in enumerate(tokens) if t.offset >= branch and t.value == "{")
    end=tokens[pairs[opening]].offset
    for name in ("_HRAdjustmentMap", "_RRAdjustmentMap", "_painSuppressAdjustmentMap"):
        occurrences=[t.offset for t in tokens if t.value == name]
        assert occurrences and all(tokens[opening].offset < offset < end for offset in occurrences)
    event=text.index('[QACEGVAR(medical,handleUnitVitals), [_unit, _deltaT]] call CBA_fnc_localEvent;')
    assert text.index('private _acmePerfStart') < event < text.index('["handleUnitVitalsEvent"') < text.index('["handleUnitVitals"')


def callback_containing(name, target):
    text=source(name);tokens=lex(text);pairs=matching(tokens)
    index=next(i for i,t in enumerate(tokens) if t.kind == "ident" and t.value == target)
    opening,closing=min(((a,b) for a,b in pairs.items()
                         if tokens[a].value == "{" and a < index < b), key=lambda pair: pair[1]-pair[0])
    return text[tokens[opening].offset+1:tokens[closing].offset]


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_worker_callbacks_preserve_work_counts_when_diagnostics_off_or_on(enabled):
    callbacks=[
        ("expansionRegisterRuntime", "ACME_fnc_idlePhysDiscovery"),
        ("expansionRegisterRuntime", "ACME_fnc_coagulationTick"),
        ("registerCirculationRuntime", "ACME_fnc_flightTick"),
        ("registerCirculationRuntime", "ACME_fnc_circHandle"),
    ]
    code=setup()+r'''
        private _calls=[];
        ACME_fnc_idlePhysDiscovery={_calls pushBack "idlePhysDiscovery";};
        ACME_fnc_preoxygenationTick={_calls pushBack "preoxygenationTick";};
        ACME_fnc_coagulationTick={_calls pushBack "coagulationTick";};
        ACME_fnc_flightTick={_calls pushBack "flightTick";};
        ACME_fnc_circHandle={_calls pushBack "circHandle";};
    '''
    if enabled:
        code+='["start",5] call ACME_fnc_performanceDiagnostics;'
    for registration,target in callbacks:
        code+='call {'+engine(callback_containing(registration,target))+'};\n'
    code+=r'''
        [_calls isEqualTo ["idlePhysDiscovery","preoxygenationTick","coagulationTick","flightTick","circHandle"],
            "instrumentation altered clinical callback work/order"] call _check;
        private _samples=(["report"] call ACME_fnc_performanceDiagnostics) get "samples";
    '''
    if enabled:
        code+=r'''
            private _rows=(_samples select 0) select 4;
            [count _rows==5 && {(_rows findIf {(_x select 1)!=1})<0},"actual callback timings lost/doubled calls"] call _check;
        '''
    else:
        code+=r'''
            [count _samples==0 && {count _missionHandlers==0} && {isNil "ACME_performance_state"},
                "disabled callbacks created performance work"] call _check;
        '''
    execute(code)


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_native_admission_gates_and_event_boundary_preserve_one_hz(enabled):
    # Execute the production admission prefix and complete event/timing suffix.
    # The intervening clinical body is an explicit opaque 6 ms engine fixture;
    # this tests observer admission/attribution, not native clinical integration.
    text=(ROOT.parent / "core/overrides/fnc_handleUnitVitals.sqf").read_text()
    prefix=text[:text.index('BEGIN_COUNTER(Vitals);')]
    prefix=re.sub(r'WARNING_1\([^;\n]*\);', '', prefix)
    prefix=prefix.replace('local _unit', '(_unit getVariable ["fixtureLocal",true])')
    stamp=next(line for line in text.splitlines() if 'setVariable [QACEGVAR(medical_vitals,lastTimeUpdated)' in line)
    suffix=text[text.index('//placed outside the ACE counter'):]
    body=engine(adapt((prefix + stamp + '\n_clock=_clock+0.006;\n' + suffix).replace('diag_tickTime', '_clock')))
    code=setup()+r'''
        _patient setVariable ["ace_medical_vitals_lastTimeUpdated",10];
        ACM_core_NextWarningTime=1000;
        private _nativeEvents=[];
        CBA_fnc_localEvent={_nativeEvents pushBack _this;_clock=_clock+0.004;};
    '''+'private _native={'+body+'};\n'
    if enabled:
        code+='["start",5] call ACME_fnc_performanceDiagnostics;'
    code+=r'''
        CBA_missionTime=10;[!([_patient] call _native),"zero elapsed entered native timing"] call _check;
        CBA_missionTime=10.99;[!([_patient] call _native),"subsecond entered native timing"] call _check;
        CBA_missionTime=11;[[_patient] call _native,"accepted native update rejected"] call _check;
        CBA_missionTime=11.5;[!([_patient] call _native),"native timing bypassed updated timestamp"] call _check;
        CBA_missionTime=12;_patient setVariable ["fixtureLocal",false];
        [!([_patient] call _native),"nonlocal unit entered native timing"] call _check;
        [count _nativeEvents==1 && {((_nativeEvents select 0) select 0)=="ace_medical_handleUnitVitals"},
            "observer altered native event count/name"] call _check;
        private _samples=(["report"] call ACME_fnc_performanceDiagnostics) get "samples";
    '''
    if enabled:
        code+=r'''
            private _rows=(_samples select 0) select 4;
            [count _rows==2 && {(_rows findIf {(_x select 1)!=1})<0},"native timing counted rejected gates"] call _check;
            private _total=(_rows select 0) select 2;private _event=(_rows select 1) select 2;
            [abs (_total-10)<0.001 && {abs (_event-4)<0.001},"native total omitted event or included recorder time"] call _check;
        '''
    else:
        code+='[count _samples==0 && {count _missionHandlers==0},"disabled native timing started capture"] call _check;'
    execute(code)
