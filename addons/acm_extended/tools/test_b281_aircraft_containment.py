"""Execute B281 aircraft support and containment state machines.

Only native geometry/transform/position/locality boundaries are fixtures. This
verifies owner-root behavior and lifecycle, not Arma ragdoll skeleton collision.
"""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def code(name):
    s = read(name)
    s = s.replace('objNull,[objNull]', 'objNull,[profileNamespace]')
    # Explicit object/geometry/physics boundaries, leaving production decisions.
    s = s.replace('_air vectorWorldToModel (_foot vectorDiff getPosWorld _air)',
                  '((_foot vectorDiff _airOrigin) call _vectorToModel)')
    s = s.replace('_air vectorWorldToModel ((getPosWorld _patient) vectorDiff getPosWorld _air)',
                  '((_rootPosition vectorDiff _airOrigin) call _vectorToModel)')
    for old, new in (
        ('_air modelToWorldWorld _root', '(_root call _modelToWorld)'),
        ('_air modelToWorldWorld _feet', '(_feet call _modelToWorld)'),
        ('getPosWorld _patient', '_rootPosition'), ('getPosASL _patient', '_feetPosition'),
        ('getPosWorld _air', '_airOrigin'), ('local _patient', '_localOwner'),
        ('alive _patient', '_patientAlive'), ('alive _air', '_airAlive'),
        ('objectParent _patient', '_parentObject'), ('attachedTo _patient', '_attachment'),
        ('animationState _patient', '_animation'), ('isTouchingGround _patient', '_touching'),
        ('velocity _patient', '_patientVelocity'), ('velocity _air', '_airVelocity'),
        ('vectorUp _expectedAir', '_airUp'), ('vectorUp _air', '_airUp'),
        ('_air vectorModelToWorld [1,0,0]', '[1,0,0]'),
        ('eyePos _patient', '_headPosition'), ('clientOwner', '_client'),
        ('objectParent _ancestor', '(_ancestor getVariable ["fixtureParent",objNull])'),
        ('attachedTo _ancestor', '(_ancestor getVariable ["fixtureAttachedTo",objNull])'),
        ('isVehicleCargo _ancestor', '(_ancestor getVariable ["fixtureCargoParent",objNull])'),
        ('alive _ancestor', '(_ancestor getVariable ["fixtureAlive",true])'),
        ('serverTime', 'CBA_missionTime'),
        ('_patient setPosWorld _anchor;', '_positions pushBack +_anchor;_rootPosition=+_anchor;'),
        ('_patient setVelocity _velocity;', '_velocities pushBack +_velocity;'),
    ):
        s = s.replace(old, new)
    s = re.sub(r'(\_\w+) isKindOf "Air"', r'(\1 getVariable ["isAir",false])', s)
    s = re.sub(r'lineIntersectsSurfaces (\[[\s\S]*?\]);', r'(\1 call _ray);', s)
    s = s.replace('isEqualType objNull', 'isEqualType profileNamespace')
    s = s.replace('finite _x', '([_x] call _finite)')
    s = s.replace('finite _lastTime', '([_lastTime] call _finite)')
    s = s.replace('finite CBA_missionTime', '([CBA_missionTime] call _finite)')
    return 'ACME_fnc_' + name + '={' + adapt(s) + '};'


def setup():
    return r'''
        private _air=missionNamespace;_air setVariable ["isAir",true];
        private _proxy=uiNamespace;_proxy setVariable ["isAir",false];
        private _other=parsingNamespace;_other setVariable ["isAir",false];
        private _localOwner=true;private _client=7;private _airAlive=true;
        private _parentObject=objNull;private _attachment=objNull;
        private _airOrigin=[100,200,10000];private _feetPosition=[101,202,10000.02];
        private _axes=[[1,0,0],[0,1,0],[0,0,1]];private _scale=1;
        private _validFinite=true;private _finite={params ["_value"];_validFinite && {_value isEqualType 0} && {abs _value < 1e30}};
        private _vectorToModel={private _v=+_this;_axes apply {(_v vectorDotProduct _x)/_scale}};
        private _modelToWorld={private _v=+_this;private _p=+_airOrigin;
            {_p=_p vectorAdd (_x vectorMultiply ((_v select _forEachIndex)*_scale));} forEach _axes;_p};
        private _rootPosition=[101,202,10000.02];private _headPosition=[101,202,10001.72];
        private _airUp=[0,0,1];private _patientVelocity=[0,0,0];private _airVelocity=[0,0,0];
        private _touching=true;private _animation="amovpercmstpsnonwnondnon";private _clinicalEpoch=1;
        private _geom=[];private _phys=[];private _road=[];private _ceiling=[];private _sideHits=[];
        private _rays=[];private _positions=[];private _velocities=[];
        private _ray={
            _rays pushBack +_this;
            if (((_this select 1) select 2)>((_this select 0) select 2)) exitWith {_ceiling};
            if ((_this select 0) vectorDistance (_this select 1)>1) exitWith {_sideHits};
            switch (_this select 6) do {case "ROADWAY":{_road};case "GEOM":{_geom};default {_phys};}
        };
        private _floor={
            private _p=_airOrigin vectorAdd [1,2,0];
            _geom=[[_p,+_airUp,_air,objNull]];
        };
        call _floor;
        ACME_fnc_clinicalEpoch={_clinicalEpoch};
        _patient setVariable ["ACE_isUnconscious",true];
        private _frame={
            private _r=_patient getVariable ["ACME_flightContainment",[]];
            if !(_r isEqualTo []) then {[[_patient,_r select 0],_r select 5] call ACME_fnc_flightContainmentTick;};
        };
    ''' + ''.join(code(n) for n in ('flightSupport', 'flightAirframe', 'flightEnclosed',
                                  'flightContainmentStop', 'flightContainmentBegin', 'flightContainmentTick'))


@pytest.mark.parametrize('lod', ['road', 'geom', 'phys'])
@pytest.mark.parametrize('proxy', [False, True])
def test_any_aircraft_contact_uses_each_native_lod_and_true_proxy_parent(lod, proxy):
    hit = '_proxy,_air' if proxy else '_air,objNull'
    execute(setup() + f'''
        _geom=[];_{lod}=[[[101,202,10000],[0,0,1],{hit}]];
        private _r=[_patient] call ACME_fnc_flightSupport;
        [count _r==3 && {{(_r select 0) isEqualTo _air}},"actual aircraft floor/proxy lost"] call _check;
        [abs ((_r select 1 select 2)-.02)<.001 && {{abs ((_r select 2 select 2)-.02)<.001}},"ASL/root capture changed datum"] call _check;
        [count _rays==3 && {{(_rays apply {{_x select 6}}) isEqualTo ["ROADWAY","GEOM","PHYSX"]}},"native independent LOD checks missing"] call _check;
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"shared exposure airframe missing"] call _check;
    ''')


@pytest.mark.parametrize('obstacle', ['objNull', '_other'])
def test_closer_ground_or_nonair_support_wins_over_other_lod_aircraft(obstacle):
    execute(setup() + f'''
        _phys=[[[101,202,10000.015],[0,0,1],{obstacle},objNull]];
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"closer nonair support ignored"] call _check;
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo objNull,"nearby plane granted airframe"] call _check;
    ''')


def test_cross_lod_blocker_is_ranked_from_ray_start_instead_of_foot_gap():
    execute(setup() + '''
        _geom=[[[101,202,10000.12],[0,0,1],_other,objNull]];
        _phys=[[[101,202,10000],[0,0,1],_air,objNull]];
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"above-foot blocker was bypassed by smaller below-foot gap"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['[101,202]', '[101,202,"invalid"]', '[101,202,10000.02]'])
def test_invalid_foot_coordinate_shape_type_and_nonfinite_values_never_query_or_capture_geometry(invalid):
    finite = '_validFinite=false;' if invalid.endswith('10000.02]') else ''
    execute(setup() + finite + f'''
        [([_patient,{invalid}] call ACME_fnc_flightSupport) isEqualTo [],"invalid foot coordinate captured Air"] call _check;
        [count _rays==0,"invalid coordinate reached native geometry"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_geom=[[[101,202,9999.5],[0,0,1],_air,objNull]];',
    '_geom=[[[101,202,10000],[1,0,0],_air,objNull]];',
    '_animation="halofreefall_non";',
    '_touching=false;_patientVelocity=[0,0,-30];',
    '_airAlive=false;',
])
def test_far_floor_wall_native_freefall_fast_fall_and_destroyed_air_are_not_captured(change):
    execute(setup() + change + '''
        [([_patient] call ACME_fnc_flightSupport) isEqualTo [],"unsupported freefall/geometry captured"] call _check;
        [!([_patient] call ACME_fnc_flightContainmentBegin) && {count _handlers==0},"unsupported lease installed"] call _check;
    ''')


def test_seated_airframe_keeps_native_vehicle_path_without_walking_lease():
    execute(setup() + '''
        _parentObject=_air;_geom=[];
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"seated lookup failed"] call _check;
        [[_patient,_air] call ACME_fnc_flightEnclosed,"seated cabin identity rejected"] call _check;
        [!([_patient] call ACME_fnc_flightContainmentBegin) && {count _positions==0},"seated aircraft seized by floor lease"] call _check;
    ''')


def test_aircraft_floor_on_roof_never_counts_as_enclosed_cabin():
    execute(setup() + '''
        [([_patient] call ACME_fnc_flightAirframe) isEqualTo _air,"roof support missing"] call _check;
        [!([_patient,_air] call ACME_fnc_flightEnclosed),"roof support invented cabin enclosure"] call _check;
        _ceiling=[[[101,202,10003],[0,0,-1],_proxy,_air]];
        [!([_patient,_air] call ACME_fnc_flightEnclosed),"exterior wing/rotor overhang invented protected cabin"] call _check;
        _sideHits=[[[102,202,10001.72],[1,0,0],_air,objNull]];
        [[_patient,_air] call ACME_fnc_flightEnclosed,"same-airframe proxy ceiling rejected"] call _check;
        _ceiling=[[[101,202,10003],[0,0,-1],_other,objNull]];
        [!([_patient,_air] call ACME_fnc_flightEnclosed),"foreign overhead object protected cabin"] call _check;
    ''')


def test_aircraft_relative_root_follows_flight_descent_and_aircraft_teleport_without_clinical_changes():
    execute(setup() + '''
        [[_patient] call ACME_fnc_flightContainmentBegin,"supported begin failed"] call _check;
        [_patient] call ACME_fnc_flightContainmentBegin;
        [count _handlers==1,"duplicate KO installed duplicate PFH"] call _check;
        call _frame;
        _airOrigin=[500,600,9900];_airVelocity=[40,50,-10];call _floor;call _frame;
        [(_positions select 1) isEqualTo [501,602,9900.02],"flight/descent did not follow airframe-relative root"] call _check;
        [(_velocities select 1) isEqualTo _airVelocity,"aircraft motion was not inherited"] call _check;
        [_patient getVariable ["ACE_isUnconscious",false],"containment changed medical unconscious state"] call _check;
        [_patient getVariable ["ACME_flightContainment",[]] isNotEqualTo [],"descent retired inside-aircraft casualty"] call _check;
    ''')


def test_airframe_translation_rotation_and_scale_preserve_captured_root_model_offset():
    execute(setup() + '''
        [_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        _axes=[[0,1,0],[-1,0,0],[0,0,1]];_scale=2;_airOrigin=[1000,2000,5000];
        _geom=[[[996,2002,5000],[0,0,1],_air,objNull]];call _frame;
        private _actual=_positions select 1;
        [(_actual select 0)==996 && {(_actual select 1)==2002} && {abs ((_actual select 2)-5000.04)<.002},"rotation/scale mixed world and relative coordinates"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_patientAlive=false;', '_airAlive=false;', '_clinicalEpoch=2;',
    '_patient setVariable ["ACE_isUnconscious",false];',
    '_parentObject=_air;', '_attachment=_other;',
    '_patient setVariable ["ace_dragging_isDragged",true];',
    '_patient setVariable ["ace_dragging_isCarried",true];',
    '_patient setVariable ["ACME_patientAnimLock",["new","treatment","medic",1,30]];',
    '_geom=[];', '_animation="halofreefall_non";',
    '_rootPosition=[104,202,10000.02];',
])
def test_wake_life_transport_controller_floor_freefall_and_external_teleport_retire_without_reassertion(change):
    execute(setup() + '''[_patient] call ACME_fnc_flightContainmentBegin;call _frame;''' + change + '''
        private _before=count _positions;call _frame;
        [count _positions==_before,"retired lease pulled casualty back"] call _check;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"invalid state retained local worker"] call _check;
        [(_patient getVariable ["ACME_flightContainmentContext",[]]) isEqualTo [],"invalid state retained transfer context"] call _check;
        [!((_handlers select 0) select 2),"invalid state retained PFH"] call _check;
        [[_patient,1],0] call ACME_fnc_flightContainmentTick;
        [count _positions==_before,"stale callback reasserted containment"] call _check;
    ''')


def test_owner_transfer_resumes_exact_floor_context_with_new_generation_and_old_callbacks_cannot_clear_it():
    execute(setup() + '''
        [_patient] call ACME_fnc_flightContainmentBegin;call _frame;
        _localOwner=false;call _frame;
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"old owner kept PFH"] call _check;
        [count (_patient getVariable ["ACME_flightContainmentContext",[]])==5,"old owner erased transfer context"] call _check;
        _localOwner=true;_client=8;
        [[_patient,true] call ACME_fnc_flightContainmentBegin,"new owner did not resume supported same life"] call _check;
        [(_patient getVariable "ACME_flightContainment" select 0)==2,"handoff reused old generation"] call _check;
        [[_patient,1],0] call ACME_fnc_flightContainmentTick;
        [_patient,1] call ACME_fnc_flightContainmentStop;
        [(_patient getVariable "ACME_flightContainment" select 0)==2,"old callback cleared new owner"] call _check;
        call _frame;
        [count _positions==2,"new owner failed to continue exact floor context"] call _check;
    ''')


def test_handoff_cannot_recapture_a_player_teleported_away_before_context_adoption():
    execute(setup() + '''
        [_patient] call ACME_fnc_flightContainmentBegin;
        [_patient,-1,true] call ACME_fnc_flightContainmentStop;
        _rootPosition=[104,202,10000.02];
        [!([_patient,true] call ACME_fnc_flightContainmentBegin),"resume accepted externally displaced unit"] call _check;
        [count _positions==0 && {(_patient getVariable ["ACME_flightContainmentContext",[]]) isEqualTo []},"resume dragged player back to old floor"] call _check;
    ''')


def test_banked_cached_floor_uses_airframe_up_and_does_not_interpret_world_vertical_as_support_normal():
    execute(setup() + '''
        _airUp=[.8660254,0,.5];_geom=[[[101,202,10000],+.(_airUp),_air,objNull]];
    '''.replace('+.(_airUp)', '+_airUp') + '''
        private _r=[_patient,_feetPosition,_air,false] call ACME_fnc_flightSupport;
        [count _r==3,"banked owned floor rejected against world up"] call _check;
        [((_rays select 0 select 0 select 0)-101)>.17,"cached ray did not follow airframe up"] call _check;
    ''')


@pytest.mark.parametrize('change', ['', '_clinicalEpoch=2;', '_localOwner=false;', '_client=8;'])
def test_local_gain_bounded_retries_adopt_delayed_context_only_in_same_owner_life(change):
    execute(setup() + code('registerFlightContainmentRuntime') + '''
        private _classHandler={};
        private _classInstalls=0;
        CBA_fnc_addClassEventHandler={_classHandler=_this select 2;_classInstalls=_classInstalls+1;31};
        CBA_fnc_waitAndExecute={_waits pushBack +_this;};
        [_patient] call ACME_fnc_flightContainmentBegin;
        private _context=+(_patient getVariable "ACME_flightContainmentContext");
        [_patient,-1,true] call ACME_fnc_flightContainmentStop;
        _patient setVariable ["ACME_flightContainmentContext",[]];
        call ACME_fnc_registerFlightContainmentRuntime;
        call ACME_fnc_registerFlightContainmentRuntime;
        [_classInstalls==1 && {(missionNamespace getVariable ["ACME_flightContainmentLocalHandler",-1])==31},"repeated startup installed another Local bridge"] call _check;
        [_patient,true] call _classHandler;
        [(_waits apply {_x select 2}) isEqualTo [0,.5,2],"Local adoption retry is not bounded"] call _check;
        private _first=_waits deleteAt 0;(_first select 1) call (_first select 0);
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"missing delayed context fabricated lease"] call _check;
        _patient setVariable ["ACME_flightContainmentContext",_context];
    ''' + change + '''
        private _next=_waits deleteAt 0;(_next select 1) call (_next select 0);
    ''' + ('[count (_patient getVariable ["ACME_flightContainment",[]])==10,"delayed live context was lost"] call _check;'
           if not change else '[(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [],"old owner/life retry acquired casualty"] call _check;'))


def test_supported_climbing_aircraft_with_stale_infantry_velocity_is_not_mistaken_for_freefall():
    execute(setup() + '''
        _touching=false;_patientVelocity=[0,0,0];_airVelocity=[100,0,12];
        [count ([_patient] call ACME_fnc_flightSupport)==3,"moving ROADWAY contact mistaken for freefall from stale infantry velocity"] call _check;
    ''')


def test_actual_native_hook_captures_before_ragdoll_and_keeps_native_incapacitated_state():
    s = (ROOT / 'addons/core/overrides/fnc_setUnconsciousAnim.sqf').read_text()
    start = s.index('// B281 captures')
    end = s.index('\nif (_isUnconscious) then {', start)
    hook = s[start:end].replace('_unit setUnconscious _isUnconscious;', '_nativeEdges pushBack _isUnconscious;')
    execute(setup() + 'private _unit=_patient;private _isUnconscious=true;private _nativeEdges=[];' +
            adapt(hook) + '''
        [count (_patient getVariable ["ACME_flightContainment",[]])==10 && {_nativeEdges isEqualTo [true]},"native unconscious edge omitted or unsupported order"] call _check;
        _isUnconscious=false;
    ''' + adapt(hook) + '''
        [(_patient getVariable ["ACME_flightContainment",[]]) isEqualTo [] && {_nativeEdges isEqualTo [true,false]},"wake did not retire and preserve native wake edge"] call _check;
    ''')
    assert s.index('call ACME_fnc_flightContainmentBegin') < s.index('_unit setUnconscious _isUnconscious;')
    for name in ('flightContainmentBegin', 'flightContainmentTick', 'flightContainmentStop'):
        t = read(name)
        assert 'setUnconscious ' not in t
        assert 'disableCollisionWith' not in t and 'setMass' not in t and 'allowDamage' not in t
        assert ' attachTo ' not in t and 'detach ' not in t
        assert not re.search(r'setVariable\s*\[\s*"ACE_isUnconscious"', t)
