"""Execute generic aircraft ancestry and ACE transport handoff decisions.

Native object links, geometry and animation commands are explicit boundaries.
The ancestry walk, enclosure decisions, native KO branch and floor lease run
from production. This does not simulate Arma's ragdoll skeleton/PhysX solver.
"""
import re

import pytest

from test_b281_aircraft_containment import setup
from test_menu_death_lifecycle import ROOT, adapt, execute


def ace_transport_readers():
    # These are ACE's public provider + exact patient-claim contract; no
    # fabricated patient-side isCarried/isDragged variable stands in for it.
    return r'''
        ace_common_fnc_isBeingDragged={
            params ["_target"];
            private _owner=_target getVariable ["ace_common_owner",objNull];
            !(_owner isEqualTo objNull)
                && {(_owner getVariable ["ace_dragging_draggedObject",objNull]) isEqualTo _target}
        };
        ace_common_fnc_isBeingCarried={
            params ["_target"];
            private _owner=_target getVariable ["ace_common_owner",objNull];
            !(_owner isEqualTo objNull)
                && {(_owner getVariable ["ace_dragging_carriedObject",objNull]) isEqualTo _target}
        };
    '''


def native_ko_code():
    source = (ROOT / 'addons/core/overrides/fnc_setUnconsciousAnim.sqf').read_text()
    source = re.sub(r'^\s*(?:TRACE|ERROR)_\d+\([^\n]*$', '', source, flags=re.M)
    for old, new in (
        ('local _unit', '_localOwner'), ('alive _unit', '_patientAlive'),
        ('objectParent _unit', '_parentObject'), ('attachedTo _unit', '_attachment'),
        ('vehicle _unit', '_parentObject'), ('lifeState _unit', '"INCAPACITATED"'),
        ('animationState _unit', '_animation'),
        ('_unit setUnconscious _isUnconscious;', '_nativeEdges pushBack _isUnconscious;'),
        ('_parentObject isKindOf "StaticWeapon"', '(_parentObject getVariable ["fixtureStatic",false])'),
        ('_parentObject isKindOf "Pod_Heli_Transport_04_crewed_base_F"', '(_parentObject getVariable ["fixturePod",false])'),
        ('isNull ([_unit] call ACME_fnc_flightAirframe)', '(([_unit] call ACME_fnc_flightAirframe) isEqualTo objNull)'),
    ):
        source = source.replace(old, new)
    return 'private _nativeEdges=[];private _ejections=[];private _seatAnimations=[];' + r'''
        ace_common_fnc_unloadPerson={_ejections pushBack _this;};
        ace_common_fnc_getDeathAnim={"nativeSeatUnconscious"};
        ace_common_fnc_doAnimation={_seatAnimations pushBack _this;};
    ''' + 'private _nativeKO={' + adapt(source) + '};'


@pytest.mark.parametrize('relationship', ['fixtureAttachedTo', 'fixtureCargoParent', 'fixtureParent'])
def test_live_airframe_is_resolved_through_each_actual_native_transport_relationship(relationship):
    execute(setup() + f'''
        _parentObject=_proxy;_proxy setVariable ["{relationship}",_air];_geom=[];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"actual aircraft ancestry lost"] call _check;
        [!([_patient,_air] call ACME_fnc_flightEnclosed),"exterior attached seat invented cabin enclosure"] call _check;
        _ceiling=[[[101,202,10003],[0,0,-1],_air,objNull]];
        _sideHits=[[[102,202,10001.72],[1,0,0],_air,objNull]];
        [[_patient,_air] call ACME_fnc_flightEnclosed,"inside attached seat lost actual cabin boundaries"] call _check;
        [!([_patient] call ACME_fnc_flightContainmentBegin),"seated helper acquired walking root lease"] call _check;
    ''')


def test_nested_vehicle_cargo_helper_resolves_outer_aircraft_without_class_names():
    execute(setup() + r'''
        _parentObject=_proxy;
        _proxy setVariable ["fixtureCargoParent",_other];
        _other setVariable ["fixtureAttachedTo",_air];_geom=[];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"nested ViV helper lost actual carrier"] call _check;
    ''')


@pytest.mark.parametrize('relationship', ['fixtureAttachedTo', 'fixtureCargoParent', 'fixtureParent'])
def test_attached_casualty_uses_actual_transport_ancestry_but_still_requires_cabin_boundaries(relationship):
    execute(setup() + f'''
        _attachment=_proxy;_proxy setVariable ["{relationship}",_air];_geom=[];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"attached casualty lost actual Air carrier"] call _check;
        [!([_patient,_air] call ACME_fnc_flightEnclosed),"attached casualty gained exterior cabin immunity"] call _check;
        _ceiling=[[[101,202,10003],[0,0,-1],_air,objNull]];
        _sideHits=[[[102,202,10001.72],[1,0,0],_air,objNull]];
        [[_patient,_air] call ACME_fnc_flightEnclosed,"attached casualty inside actual cabin lost enclosure"] call _check;
        [!([_patient] call ACME_fnc_flightContainmentBegin),"attached transport casualty acquired floor lease"] call _check;
    ''')


def test_direct_body_attachment_to_air_does_not_bypass_enclosure_and_ground_attachment_is_neutral():
    execute(setup() + r'''
        _attachment=_air;_geom=[];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"direct Air attachment lost actual carrier"] call _check;
        [!([_patient,_air] call ACME_fnc_flightEnclosed),"direct exterior attachment invented cabin pressure"] call _check;
        _attachment=_other;
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo objNull,"unrelated ground attachment gained nearby aircraft"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_proxy setVariable ["fixtureAttachedTo",_proxy];',
    '_proxy setVariable ["fixtureAttachedTo",_other];_other setVariable ["fixtureCargoParent",_proxy];',
    '_proxy setVariable ["fixtureAttachedTo",_air];_proxy setVariable ["fixtureAlive",false];',
    '_proxy setVariable ["fixtureAttachedTo",_air];_air setVariable ["fixtureAlive",false];',
    '_proxy setVariable ["fixtureAttachedTo",objNull];',
])
def test_cycles_deleted_helpers_destroyed_air_and_unrelated_ground_seats_do_not_grant_airframe(change):
    execute(setup() + '_parentObject=_proxy;_geom=[];' + change + r'''
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo objNull,"invalid transport ancestry granted Air"] call _check;
        [!([_patient,_air] call ACME_fnc_flightEnclosed),"invalid transport ancestry granted cabin"] call _check;
    ''')


def test_ground_contact_below_nearby_aircraft_stays_ground_and_direct_air_seat_stays_native():
    execute(setup() + r'''
        _parentObject=_proxy;_proxy setVariable ["fixtureAttachedTo",_other];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo objNull,"nearby Air floor bypassed seated ground ancestry"] call _check;
        _parentObject=_air;_geom=[];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"direct native Air seat regressed"] call _check;
        [[_patient,_air] call ACME_fnc_flightEnclosed,"direct native Air seat rejected"] call _check;
    ''')


@pytest.mark.parametrize('relationship', ['fixtureAttachedTo', 'fixtureCargoParent'])
def test_native_unconscious_helper_seat_stays_in_live_aircraft_without_changing_consciousness(relationship):
    execute(setup() + native_ko_code() + f'''
        _parentObject=_proxy;_proxy setVariable ["fixtureStatic",true];
        _proxy setVariable ["{relationship}",_air];
        [_patient,true] call _nativeKO;
        [_nativeEdges isEqualTo [true],"native incapacitated state was omitted"] call _check;
        [count _ejections==0,"actual aircraft helper occupant was ejected on KO"] call _check;
        [count _seatAnimations==1,"native seated KO presentation lost"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"seated helper was root-pinned"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['', '_proxy setVariable ["fixtureAttachedTo",_air];_air setVariable ["fixtureAlive",false];'])
def test_native_unconscious_ground_or_destroyed_carrier_turret_retains_ejection(invalid):
    execute(setup() + native_ko_code() + '_parentObject=_proxy;_proxy setVariable ["fixtureStatic",true];' + invalid + r'''
        [_patient,true] call _nativeKO;
        [_nativeEdges isEqualTo [true] && {count _ejections==1},"ground/destroyed carrier turret stopped native ejection"] call _check;
    ''')


@pytest.mark.parametrize('kind', ['carriedObject', 'draggedObject'])
def test_real_ace_provider_patient_binding_retires_floor_lease_before_attachment(kind):
    execute(setup() + ace_transport_readers() + f'''
        [_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        _patient setVariable ["ace_common_owner",_proxy];
        _proxy setVariable ["ace_dragging_{kind}",_patient];
        _rootPosition=_rootPosition vectorAdd [0.5,0,0];
        private _before=count _positions;call _frame;
        [count _positions==_before,"floor lease moved exact claimed ACE transport patient"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"pre-attach claim retained root worker"] call _check;
        [!([_patient] call ACME_fnc_flightContainmentBegin),"ACE transport claim re-enrolled floor worker"] call _check;
        [(_patient getVariable ["ACME_flightContainmentContext",[]]) isEqualTo [],"pre-attach claim retained transferable context"] call _check;
    ''')


@pytest.mark.parametrize('kind', ['carriedObject', 'draggedObject'])
def test_other_claims_do_not_disable_floor_containment_without_exact_ace_patient_binding(kind):
    execute(setup() + ace_transport_readers() + f'''
        _patient setVariable ["ace_common_owner",_proxy];
        _proxy setVariable ["ace_dragging_{kind}",_other];
        [[_patient] call ACME_fnc_flightContainmentBegin,"unrelated owner claim suppressed floor protection"] call _check;
        call _frame;
        [count _positions==1,"unrelated provider object binding suppressed floor worker"] call _check;
    ''')


@pytest.mark.parametrize('result', ['"invalid"', '[]', 'false', 'nil'])
def test_overridden_ace_transport_readers_must_return_boolean_true_to_claim_root(result):
    execute(setup() + f'''
        ace_common_fnc_isBeingDragged={{{result}}};ace_common_fnc_isBeingCarried={{{result}}};
        [[_patient] call ACME_fnc_flightContainmentBegin,"invalid third-party transport return blocked floor protection"] call _check;
        call _frame;
        [count _positions==1,"invalid third-party transport return seized floor worker"] call _check;
    ''')


def test_missing_ace_transport_readers_and_invalid_legacy_flags_are_neutral():
    execute(setup() + r'''
        ace_common_fnc_isBeingDragged=nil;ace_common_fnc_isBeingCarried=nil;
        _patient setVariable ["ace_dragging_isDragged","invalid"];
        _patient setVariable ["ace_dragging_isCarried",[]];
        [[_patient] call ACME_fnc_flightContainmentBegin,"missing/invalid optional reader disabled floor protection"] call _check;
        call _frame;
        [count _positions==1,"missing/invalid optional reader stopped actual floor worker"] call _check;
    ''')


@pytest.mark.parametrize('elapsed', [.05, .2, .5, 1, 5])
def test_root_integration_from_exact_owned_velocity_survives_low_fps_and_remote_carrier_jumps(elapsed):
    execute(setup() + f'''
        _airVelocity=[100,0,0];[_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        private _before=count _positions;
        [(_velocities select 0) isEqualTo [100,0,0],"patient did not receive captured owned velocity"] call _check;
        CBA_missionTime=CBA_missionTime+{elapsed};
        _rootPosition=_rootPosition vectorAdd [{100*elapsed},0,0];
        _airOrigin=_airOrigin vectorAdd [{200*elapsed},0,0];call _floor;
        call _frame;
        [count _positions==_before+1,"exact owned integration was treated as external teleport"] call _check;
        [count (_patient getVariable ["ACME_flightContainment",[]])==10,"low FPS/remote snapshot retired supported root"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]] select 8)==CBA_missionTime,"owned motion timestamp was not renewed"] call _check;
    ''')


@pytest.mark.parametrize('displacement', ['[5,2,0]', '[7,0,0]', '[0,100,-10000]'])
def test_external_displacement_outside_tight_owned_prediction_still_retires(displacement):
    execute(setup() + f'''
        _airVelocity=[100,0,0];[_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        CBA_missionTime=CBA_missionTime+.05;
        _rootPosition=_rootPosition vectorAdd {displacement};
        _airOrigin=_airOrigin vectorAdd [10,0,0];call _floor;
        private _before=count _positions;call _frame;
        [count _positions==_before,"external teleport was pulled back using prediction"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"outside-prediction displacement retained lease"] call _check;
    ''')


@pytest.mark.parametrize('clock', ['10', '9.95', '16', '1e35'])
def test_zero_negative_excessive_stall_or_nonfinite_clock_cannot_grant_prediction(clock):
    execute(setup() + f'''
        _airVelocity=[100,0,0];[_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        CBA_missionTime={clock};
        _rootPosition=_rootPosition vectorAdd [5,0,0];
        _airOrigin=_airOrigin vectorAdd [10,0,0];call _floor;
        private _before=count _positions;call _frame;
        [count _positions==_before,"invalid/stalled clock authorized unsupported prediction"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"invalid/stalled clock retained displaced body lease"] call _check;
    ''')


def test_future_aircraft_velocity_does_not_replace_last_owned_patient_velocity():
    execute(setup() + r'''
        _airVelocity=[100,0,0];[_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        CBA_missionTime=CBA_missionTime+.05;
        _airVelocity=[1000,0,0];
        _rootPosition=_rootPosition vectorAdd [50,0,0];
        _airOrigin=_airOrigin vectorAdd [100,0,0];call _floor;
        private _before=count _positions;call _frame;
        [count _positions==_before,"future carrier velocity granted unowned motion prediction"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"future carrier sample retained externally displaced root"] call _check;
    ''')


def test_owned_prediction_never_replaces_actual_floor_support_validation():
    execute(setup() + r'''
        _airVelocity=[100,0,0];[_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        CBA_missionTime=CBA_missionTime+.05;
        _rootPosition=_rootPosition vectorAdd [5,0,0];
        _airOrigin=_airOrigin vectorAdd [10,0,0];_geom=[];
        private _before=count _positions;call _frame;
        [count _positions==_before,"motion prediction retained deleted/unsupported floor"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"unsupported floor retained prediction lease"] call _check;
    ''')
