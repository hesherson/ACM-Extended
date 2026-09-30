"""Execute publication gates with only object/locality/transport boundaries mocked.

Actual SQF cache, signatures and scheduling decisions run in SQF-VM. Wire values
are serialized at send time so mutable owner-local containers cannot change the
observed snapshot. This does not simulate Arma network delivery or JIP transport.
"""
import re

import pytest

from test_b156_coagulation_runtime import code
from test_menu_death_lifecycle import execute, read


def instrument(source):
    # Only public object writes are replaced; local writes and suppression logic
    # are the checked-out source. All covered gate payloads are scalar/containers.
    source = re.sub(
        r'(_(?:obj|patient)) setVariable \[((?:"[^"]+"|_name)), (.*?), true\];',
        r'[\1, \2, \3] call _testPublish;', source,
    )
    return code(source)


def function(name):
    return 'ACME_fnc_' + name + '={' + instrument(read(name)) + '};'


def setup():
    return '''
        private _patientLocal=true;
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _wire=createHashMap;
        private _packets=[];
        private _testPublish={params ["_obj","_name","_value"];
            private _serialized=if (isNil "_value") then {"NIL"} else {str _value};
            _wire set [toLower _name,_serialized];
            _packets pushBack [toLower _name,_serialized];
            if (isNil "_value") then {_obj setVariable [_name,nil];} else {_obj setVariable [_name,_value];};
        };
        ACME_net_count=true;
    ''' + ''.join(function(name) for name in (
        'setVarNet', 'setVarNetApprox', 'circStateCommit',
        'tbiStateCommit', 'infusionMedicationStateCommit',
    ))


def test_exact_reset_refreshes_approximate_baseline_and_first_resumed_value():
    execute(setup() + '''
        [_patient,"metric",5,0.1,3] call ACME_fnc_setVarNetApprox;
        [_patient,"metric",0] call ACME_fnc_setVarNet;
        _nowTime=10.1;
        [_patient,"metric",5,0.1,3] call ACME_fnc_setVarNetApprox;
        [(_wire get "metric")=="5","approximate resume stranded observer at exact reset"] call _check;
        [count _packets==3,"resume did not produce exactly one necessary packet"] call _check;
    ''')


def test_approximate_publication_invalidates_older_exact_fingerprint_before_local_prewrite():
    execute(setup() + '''
        [_patient,"metric",0] call ACME_fnc_setVarNet;
        [_patient,"metric",5,0.1,3] call ACME_fnc_setVarNetApprox;
        _patient setVariable ["metric",0];
        [_patient,"metric",0] call ACME_fnc_setVarNet;
        [(_wire get "metric")=="0","exact reset incorrectly matched pre-approximation cache"] call _check;
        [count _packets==3,"exact reset was suppressed"] call _check;
    ''')


def test_alternating_helpers_with_same_value_do_not_turn_into_a_packet_loop():
    execute(setup() + '''
        for "_i" from 1 to 30 do {
            [_patient,"metric",5] call ACME_fnc_setVarNet;
            [_patient,"metric",5,0.1,3] call ACME_fnc_setVarNetApprox;
        };
        [count _packets==1,"equal exact/approximate writes repeatedly invalidated one another"] call _check;
        [_patient,"metric",5.05,0.1,3] call ACME_fnc_setVarNetApprox;
        [(_patient getVariable "metric")==5.05 && {(_wire get "metric")=="5"},"suppression lost exact local physiology"] call _check;
        _nowTime=13.1;
        [_patient,"metric",5.05,0.1,3] call ACME_fnc_setVarNetApprox;
        [count _packets==2 && {(_wire get "metric")=="5.05"},"bounded refresh never reached observer"] call _check;
    ''')


@pytest.mark.parametrize('subsystem', ['circ', 'tbi'])
def test_clearing_neutral_map_publishes_immediately_even_if_worker_stops(subsystem):
    execute(setup() + f'''
        private _state=createHashMapFromArray [["lastTick",10]];
        [_patient,_state] call ACME_fnc_{subsystem}StateCommit;
        _nowTime=10.1;
        [_patient,createHashMap] call ACME_fnc_{subsystem}StateCommit;
        [count _packets==2,"neutral state clear was suppressed until a tick that may never run"] call _check;
        [(_wire get "acme_{subsystem}_state")==str createHashMap,"observer retained a cleared episode"] call _check;
    ''')


@pytest.mark.parametrize('subsystem,interval', [('circ', 2), ('tbi', 1)])
def test_snapshot_keeps_exact_map_locally_and_bounds_continuous_updates(subsystem, interval):
    execute(setup() + f'''
        private _state=createHashMapFromArray [["lastTick",10]];
        [_patient,_state] call ACME_fnc_{subsystem}StateCommit;
        private _before=_wire get "acme_{subsystem}_state";
        _state set ["lastTick",10.25]; _nowTime=10.25;
        [_patient,_state] call ACME_fnc_{subsystem}StateCommit;
        [count _packets==1 && {{(_wire get "acme_{subsystem}_state")==_before}},"continuous bookkeeping sent before cadence"] call _check;
        [((_patient getVariable "ACME_{subsystem}_State") get "lastTick")==10.25,"local snapshot lost exact update"] call _check;
        _nowTime=10+{interval};
        [_patient,_state] call ACME_fnc_{subsystem}StateCommit;
        [count _packets==2 && {{(_wire get "acme_{subsystem}_state")!=_before}},"cadence did not refresh changed map"] call _check;
    ''')


def network_handoff_reset():
    source = read('ownerInit')
    reset = source.split('    _unit setVariable ["ACME_net_scalarCache"', 1)[1]
    reset = '    _unit setVariable ["ACME_net_scalarCache"' + reset.split(
        '    _unit setVariable ["ACME_clinicalLastOwner"', 1)[0]
    return code(reset.replace('_unit', '_patient'))


@pytest.mark.parametrize('subsystem', ['circ', 'tbi', 'infusion'])
def test_away_and_back_to_same_owner_forces_one_fresh_snapshot(subsystem):
    gate = 'infusionMedicationStateCommit' if subsystem == 'infusion' else subsystem + 'StateCommit'
    value = '[]' if subsystem == 'infusion' else 'createHashMapFromArray [["lastTick",10]]'
    count = 2 if subsystem == 'infusion' else 1  # infusion also publishes HasBagMedications
    execute(setup() + f'''
        private _state={value};
        [_patient,_state] call ACME_fnc_{gate};
        [count _packets=={count},"initial snapshot missing"] call _check;
        _patientLocal=false;
    ''' + network_handoff_reset() + '''
        _patientLocal=true;
        _nowTime=10.1;
    ''' + f'''
        [_patient,_state] call ACME_fnc_{gate};
        [count _packets=={count * 2},"returning owner reused its old suppression decision"] call _check;
        [_patient,_state] call ACME_fnc_{gate};
        [count _packets=={count * 2},"handoff refresh duplicated"] call _check;
    ''')


@pytest.mark.parametrize('field,new_value', [(22, '0.25'), (20, '60'), (27, '2'), (0, '"replacement-entry"')])
def test_infusion_treatment_changes_publish_immediately(field, new_value):
    execute(setup() + '''
        private _entry=["entry","leftarm",0,"Saline",0,true,"O+",500,"",500,500,
            "Epinephrine","Epinephrine_IV",1,1,0,10,0,10,600,20,60,1,"bag",0,0,0.002,1];
        private _entries=[_entry];
        [_patient,_entries] call ACME_fnc_infusionMedicationStateCommit;
        _nowTime=10.25;
        _entry set [10,499]; _entry set [14,0.998]; _entry set [17,0.02]; _entry set [18,10.25];
        [_patient,_entries] call ACME_fnc_infusionMedicationStateCommit;
        [count _packets==2,"continuous delivery fields bypassed snapshot cadence"] call _check;
    ''' + f'_entry set [{field},{new_value}];' + '''
        [_patient,_entries] call ACME_fnc_infusionMedicationStateCommit;
        [count _packets==3,"explicit treatment change was delayed"] call _check;
        [(_wire get "acme_infusion_bagmedications")==str _entries,"observer did not receive revised bag"] call _check;
    ''')


def test_mutated_array_and_nil_round_trip_keep_exact_cache_safe():
    execute(setup() + '''
        private _value=[1];
        [_patient,"structured",_value] call ACME_fnc_setVarNet;
        _value set [0,2];
        [_patient,"structured",_value] call ACME_fnc_setVarNet;
        [_patient,"structured",_value] call ACME_fnc_setVarNet;
        [count _packets==2 && {(_wire get "structured")=="[2]"},"mutable cache suppressed a changed array"] call _check;
        [_patient,"structured",nil] call ACME_fnc_setVarNet;
        [_patient,"structured","<ACME:NIL>"] call ACME_fnc_setVarNet;
        [count _packets==4,"nil fingerprint collided with a literal string"] call _check;
    ''')
