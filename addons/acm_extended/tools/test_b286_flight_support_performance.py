"""Execute production support sampling and the paired 1 Hz callback.

Only native ray results, transforms and object state are engine stand-ins. Ray
counts measure work, not Arma frame time. Samples live for one unscheduled
discovery/preoxygenation invocation; independent callbacks must see scene changes
even if they happen in the same rendered frame. No whole-frame/world cache is
permitted because a new blocker can enter a previously empty ray.
"""
import pytest

from b281_flight_fixture import flight_function
from test_b281_aircraft_containment import code, setup
from test_menu_death_lifecycle import adapt, execute, read


def runtime():
    return "ACME_fnc_expansionRegisterRuntime={" + adapt(read("expansionRegisterRuntime")) + "};"


def oxygen():
    return r'''
        private _flightMapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        missionNamespace setVariable ["ace_medical_vitals_oxygenSupplyConditionCache",createHashMap];
    ''' + flight_function("oxygenSupply")


@pytest.mark.parametrize("patients", [0, 1, 10, 50])
def test_actual_paired_callback_queries_each_patient_once_and_discards_the_context(patients):
    # Real VM object identities exercise the per-patient map, rather than giving
    # every casualty the same namespace and accidentally testing one shared key.
    support = code("flightSupport").replace("objNull,[profileNamespace]", "objNull,[objNull,profileNamespace]")
    execute(setup() + support + runtime() + f'''
        private _patients=[];
        for "_i" from 1 to {patients} do {{_patients pushBack ("CAManBase" createVehicle [0,0,0]);}};
        _geom=[];
        private _order=[];
        ACME_fnc_idlePhysDiscovery={{
            _order pushBack "discovery";
            {{[([_x] call ACME_fnc_flightSupport) isEqualTo [],"ground discovery captured air"] call _check;}} forEach _patients;
        }};
        ACME_fnc_preoxygenationTick={{
            _order pushBack "preoxygenation";
            {{[([_x] call ACME_fnc_flightSupport) isEqualTo [],"ground preoxygenation captured air"] call _check;}} forEach _patients;
        }};
        call ACME_fnc_expansionRegisterRuntime;
        private _callback=(_handlers select 0) select 0;
        call _callback;
        [count _rays=={patients * 3},"paired discovery/preoxygenation repeated raw floor rays"] call _check;
        [_order isEqualTo ["discovery","preoxygenation"],"paired physiology order changed"] call _check;
        [isNil "_acmeFlightSupportSamples","geometry context escaped callback scope"] call _check;
        call _callback;
        [count _rays=={patients * 6},"later invocation reused old scene rays"] call _check;
    ''')


def test_unscoped_callbacks_always_see_new_blockers_and_moving_aircraft():
    execute(setup() + r'''
        [count ([_patient] call ACME_fnc_flightSupport)==3,"initial aircraft floor missed"] call _check;
        _phys=[[[101,202,10000.015],[0,0,1],_other,objNull]];
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"new blocker reused earlier support"] call _check;
        _phys=[];_airOrigin=[500,600,10000];call _floor;
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"moved aircraft left stale floor"] call _check;
        _geom=[];
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"empty scene retained aircraft"] call _check;
        _airOrigin=[100,200,10000];call _floor;
        [count ([_patient] call ACME_fnc_flightSupport)==3,"new aircraft in empty ray was not observed"] call _check;
        [count _rays==15,"independent lookups shared a whole-frame geometry cache"] call _check;
    ''')


def test_exact_ray_arguments_invalidate_scoped_samples_and_results_are_not_cached():
    execute(setup() + r'''
        private _acmeFlightSupportSamples=createHashMap;
        private _first=[_patient] call ACME_fnc_flightSupport;
        private _offset=+(_first select 1);
        (_first select 1) set [0,999];_first set [0,objNull];
        private _again=[_patient] call ACME_fnc_flightSupport;
        [(_again select 0) isEqualTo _air && {(_again select 1) isEqualTo _offset},"caller mutated a cached support result"] call _check;
        [count _rays==3,"identical scoped ray arguments were not reused"] call _check;
        _feetPosition=[101,202,10000.03];
        [_patient] call ACME_fnc_flightSupport;
        [count _rays==6,"changed foot point reused old rays"] call _check;
        _airUp=[.8660254,0,.5];
        [_patient,_feetPosition,_air,false] call ACME_fnc_flightSupport;
        [count _rays==9,"changed ray direction reused world-vertical samples"] call _check;
    ''')


def test_scoped_raw_samples_keep_expected_air_alive_and_motion_decisions_live():
    execute(setup() + r'''
        private _acmeFlightSupportSamples=createHashMap;
        [count ([_patient] call ACME_fnc_flightSupport)==3,"initial floor missed"] call _check;
        [([_patient,_feetPosition,_other,false] call ACME_fnc_flightSupport) isEqualTo [],"different expected air accepted cached classification"] call _check;
        _airAlive=false;
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"dead air retained cached support"] call _check;
        _airAlive=true;_animation="halofreefall_non";
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"HALO transition retained cached support"] call _check;
        _animation="amovpercmstpsnonwnondnon";_touching=false;_patientVelocity=[0,0,-30];
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"fast fall retained cached support"] call _check;
        [count ([_patient,_feetPosition,_air,false] call ACME_fnc_flightSupport)==3,"explicit no-motion inspection inherited earlier rejection"] call _check;
        [count _rays==3,"classification or motion options changed identical ray work"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["device", "gear"])
def test_external_oxygen_condition_invalidates_negative_geometry_before_user_code(kind):
    condition = ('{_geom=[[[101,202,10000],[0,0,1],_air,objNull]];'
                 '[count ([_patient] call ACME_fnc_flightSupport)==3,'
                 '"condition itself observed stale negative geometry"] call _check;false}')
    configure = ('_patient setVariable ["ACME_oxygenSupply",' + condition + '];' if kind == "device" else
                 '_patient setVariable ["fixtureHeadgear","ConfiguredSupply"];'
                 'missionNamespace setVariable ["ace_medical_vitals_oxygenSupplyConditionCache",'
                 'createHashMapFromArray [["ConfiguredSupply",' + condition + ']]];')
    execute(setup() + oxygen() + r'''
        private _acmeFlightSupportSamples=createHashMap;
        _geom=[];
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"initial empty floor captured air"] call _check;
    ''' + configure + r'''
        [!([_patient] call ACME_fnc_oxygenSupply),"false custom condition changed supply semantics"] call _check;
        [count ([_patient] call ACME_fnc_flightSupport)==3,"custom condition geometry mutation reused a negative ray"] call _check;
        _phys=[[[101,202,10000.015],[0,0,1],_other,objNull]];
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"invalidated scope began caching again after user code"] call _check;
        [count _rays==12,"external callback did not retire scoped sampling before user code"] call _check;
    ''')


def test_ordinary_room_air_does_not_invalidate_the_read_only_geometry_scope():
    execute(setup() + oxygen() + r'''
        private _acmeFlightSupportSamples=createHashMap;
        _geom=[];
        [_patient] call ACME_fnc_flightSupport;
        [!([_patient] call ACME_fnc_oxygenSupply),"room air acquired oxygen"] call _check;
        [_patient] call ACME_fnc_flightSupport;
        [count _rays==3,"default false equipment conditions invalidated an unchanged scene"] call _check;
    ''')
