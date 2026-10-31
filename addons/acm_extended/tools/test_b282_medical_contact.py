"""Execute contact across native helper seats and real aircraft floor support.

Only per-object native links, positions, geometry and finite checks are fixtures.
The actual contact, distance, ancestry and support decisions execute from source.
"""
import re

import pytest

from test_b281_aircraft_containment import code as flight_code, setup as flight_setup
from test_menu_death_lifecycle import adapt, execute, read


def contact_code(name):
    text = read(name).replace('objNull,[objNull]', 'objNull,[profileNamespace]')
    for old, new in (
        ('objectParent _medic', '(_medic getVariable ["fixtureParent",objNull])'),
        ('objectParent _patient', '(_patient getVariable ["fixtureParent",objNull])'),
        ('_medic distance _patient', '((_medic getVariable "fixturePosition") vectorDistance (_patient getVariable "fixturePosition"))'),
        ('attachedTo _patient', '(_patient getVariable ["fixtureAttachedTo",objNull])'),
        ('typeOf _helper', '(_helper getVariable ["fixtureClass",""])'),
        ('getPosASL _helper', '(_helper getVariable "fixturePosition")'),
        ('getPosASL _patient', '(_patient getVariable "fixturePosition")'),
        ('getPosASL _medic', '(_medic getVariable "fixturePosition")'),
        ('finite _maxDistance', '([_maxDistance] call _finite)'),
        ('finite _distance', '([_distance] call _finite)'),
        ('finite _x', '([_x] call _finite)'),
        ('isNull (_patient getVariable ["fixtureParent",objNull])', '((_patient getVariable ["fixtureParent",objNull]) isEqualTo objNull)'),
    ):
        text = text.replace(old, new)
    return 'ACME_fnc_' + name + '={' + adapt(text) + '};'


def actor_flight_code(name):
    text = flight_code(name)
    for old, new in (
        ('_parentObject', '(_patient getVariable ["fixtureParent",objNull])'),
        ('_attachment', '(_patient getVariable ["fixtureAttachedTo",objNull])'),
        ('_patientAlive', '(_patient getVariable ["fixtureAlive",true])'),
        ('_airAlive', '(_air getVariable ["fixtureAlive",true])'),
        ('_feetPosition', '(_patient getVariable "fixturePosition")'),
    ):
        text = text.replace(old, new)
    return text


def setup():
    return flight_setup() + r'''
        _medic setVariable ["fixturePosition",[102,202,10000.02]];
        _patient setVariable ["fixturePosition",[101,202,10000.02]];
        _ray={
            _rays pushBack +_this;
            if (((_this select 1) select 2)>((_this select 0) select 2)) exitWith {[]};
            if ((_this select 0) vectorDistance (_this select 1)>1) exitWith {[]};
            private _unit=_this select 2;
            private _support=_unit getVariable ["fixtureFloor",objNull];
            if (_support isEqualTo objNull) exitWith {[]};
            [[(_unit getVariable "fixturePosition") vectorDiff [0,0,.02],[0,0,1],_support,objNull]]
        };
        missionNamespace setVariable ["ace_medical_gui_maxDistance",3];
    ''' + ''.join(actor_flight_code(name) for name in ('flightSupport','flightAirframe')) + ''.join(
        contact_code(name) for name in ('patientInteractionDistance','patientInteractionContact'))


@pytest.mark.parametrize('range_limit', [0,3,100])
def test_direct_native_vehicle_seating_retains_exact_ace_contract(range_limit):
    execute(setup() + f'''
        _medic setVariable ["fixtureParent",_air];_patient setVariable ["fixtureParent",_air];
        _medic setVariable ["fixturePosition",[500,600,10000]];
        [[_medic,_patient,{range_limit}] call ACME_fnc_patientInteractionContact,"native same-seat carrier contract changed"] call _check;
        [count _rays==0 && {{count _positions==0}},"direct native seats queried or changed geometry"] call _check;
    ''')


def test_distinct_adjacent_static_helper_seats_share_actual_air_but_not_whole_airframe_reach():
    execute(setup() + r'''
        _medic setVariable ["fixtureParent",_other];_other setVariable ["fixtureAttachedTo",_air];
        _patient setVariable ["fixtureParent",_proxy];_proxy setVariable ["fixtureAttachedTo",_air];
        [[_medic,_patient] call ACME_fnc_patientInteractionContact,"adjacent actual aircraft helper seats were isolated"] call _check;
        _medic setVariable ["fixturePosition",[200,202,10000.02]];
        [!([_medic,_patient] call ACME_fnc_patientInteractionContact),"helper ancestry granted unlimited aircraft reach"] call _check;
        [count _rays==0,"native attachment ancestry unnecessarily queried floors"] call _check;
    ''')


@pytest.mark.parametrize('standing_medic', [True,False])
@pytest.mark.parametrize('dead_patient', [True,False])
def test_standing_floor_and_seated_care_is_symmetric_and_dead_patients_remain_reachable(standing_medic,dead_patient):
    standing,seated=('_medic','_patient') if standing_medic else ('_patient','_medic')
    dead='_patient setVariable ["fixtureAlive",false];' if dead_patient else ''
    execute(setup() + dead + f'''
        {standing} setVariable ["fixtureFloor",_air];{seated} setVariable ["fixtureParent",_air];
        [[_medic,_patient] call ACME_fnc_patientInteractionContact,"actual walking-floor/seated medical contact lost"] call _check;
        [count _rays==3 && {{count _positions==0}},"floor contact was skipped or altered physical state"] call _check;
    ''')


@pytest.mark.parametrize('seated', [True,False])
def test_contact_can_inspect_dead_body_without_activating_default_flight_or_containment(seated):
    attachment='_patient setVariable ["fixtureParent",_air];' if seated else '_patient setVariable ["fixtureFloor",_air];'
    execute(setup() + attachment + r'''
        _patientAlive=false;_patient setVariable ["fixtureAlive",false];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo objNull,"default dead-body flight physiology changed"] call _check;
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"default dead-body floor support changed"] call _check;
        [([_patient,true] call ACME_fnc_flightAirframe) isEqualTo _air,"explicit dead contact could not inspect live carrier"] call _check;
        [!([_patient] call ACME_fnc_flightContainmentBegin),"contact enabled corpse floor containment"] call _check;
        [count _positions==0 && {count _handlers==0},"contact inspection installed a physical controller"] call _check;
    ''')


@pytest.mark.parametrize('edge', [
    '_medic setVariable ["fixtureParent",_other];',
    '_medic setVariable ["fixtureFloor",_other];',
    '_medic setVariable ["fixturePosition",[101,202,10004]];_medic setVariable ["fixtureFloor",_air];',
    '_medic setVariable ["fixturePosition",[101,202,0]];_medic setVariable ["fixtureFloor",_air];',
    '_medic setVariable ["fixtureFloor",_air];_air setVariable ["fixtureAlive",false];',
    '_medic setVariable ["fixtureParent",_other];_other setVariable ["isAir",true];',
])
def test_unrelated_ground_air_dead_carrier_vertical_distance_and_teleport_do_not_grant_contact(edge):
    execute(setup() + '_patient setVariable ["fixtureParent",_air];' + edge + r'''
        [!([_medic,_patient] call ACME_fnc_patientInteractionContact),"unrelated/distant transport granted treatment contact"] call _check;
        [count _positions==0,"rejected contact wrote physical state"] call _check;
    ''')


def test_exterior_aircraft_roof_contact_grants_only_physical_reach_without_cabin_side_effects():
    execute(setup() + r'''
        _medic setVariable ["fixtureFloor",_air];_patient setVariable ["fixtureParent",_air];
        _air setVariable ["ACME_cabinPressureRatio",.8];
        [[_medic,_patient] call ACME_fnc_patientInteractionContact,"nearby actual exterior contact was denied"] call _check;
        [!([_medic,_air] call ACME_fnc_flightEnclosed),"contact invented cabin enclosure"] call _check;
        [(_air getVariable "ACME_cabinPressureRatio")==.8 && {count _positions==0},"contact modified pressure or pose"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['-2','"invalid"','[]','true','1e35'])
@pytest.mark.parametrize('seated', [True,False])
def test_invalid_explicit_range_rejects_ground_and_native_seats_before_geometry(invalid,seated):
    seating='_medic setVariable ["fixtureParent",_air];_patient setVariable ["fixtureParent",_air];' if seated else ''
    execute(setup() + seating + f'''
        [!([_medic,_patient,{invalid}] call ACME_fnc_patientInteractionContact),"invalid explicit range granted contact"] call _check;
        [count _rays==0,"invalid range reached aircraft geometry"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['-2','"invalid"','[]','true','1e35'])
def test_invalid_configured_range_cannot_bypass_native_seat_guard(invalid):
    execute(setup() + f'''
        _medic setVariable ["fixtureParent",_air];_patient setVariable ["fixtureParent",_air];
        missionNamespace setVariable ["ace_medical_gui_maxDistance",{invalid}];
        [!([_medic,_patient] call ACME_fnc_patientInteractionContact),"invalid config range granted same native seat contact"] call _check;
    ''')


@pytest.mark.parametrize('which', ['medic','patient'])
def test_null_actor_never_grants_contact(which):
    args='objNull,_patient' if which=='medic' else '_medic,objNull'
    execute(setup() + f'''[!([{args}] call ACME_fnc_patientInteractionContact),"null actor granted medical contact"] call _check;''')


def test_ground_uses_real_existing_anchor_distance_and_differing_parent_uses_real_three_dimensional_distance():
    execute(setup() + r'''
        [[_medic,_patient] call ACME_fnc_patientInteractionContact,"nearby ground care rejected"] call _check;
        _medic setVariable ["fixturePosition",[101,202,10004]];
        [!([_medic,_patient] call ACME_fnc_patientInteractionContact),"vertical ground separation ignored"] call _check;
        [count _rays==0,"ground care performed aircraft surface work"] call _check;
    ''')
