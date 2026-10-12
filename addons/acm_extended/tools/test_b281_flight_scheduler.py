"""Execute production flight discovery, single-writer cadence and retirement.

Object/locality/airframe/ASL reads and CBA transport use explicit engine stand-ins.
Enrollment, pressure/ceiling mathematics, native-activity gating, registry lifetime
and runtime replacement execute checked-out SQF. Native Arma remains necessary
for aircraft collision and true multiplayer delivery acceptance.
"""
from pathlib import Path
import re

import pytest

from test_menu_death_lifecycle import execute, namespace_public_arguments
from test_historical_vial_execution import map_defaults
from source_scan import lex, matching
from test_historical_medication_rows import iteration_scopes

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def adapt(text):
    # Namespace handles stand in only for engine objects, with independent
    # owner/alive/class values so invalid membership cannot be hidden by a
    # blanket always-local/alive replacement.
    text = re.sub(r'\bisNull (_\w+)', r'(\1 isEqualTo objNull)', text)
    text = text.replace('isNull ([_patient] call ACME_fnc_flightAirframe)',
                        '(([_patient] call ACME_fnc_flightAirframe) isEqualTo objNull)')
    text = re.sub(r'\blocal (_\w+)', r'(\1 getVariable ["fixtureLocal",true])', text)
    text = re.sub(r'\balive (_\w+)', r'(\1 getVariable ["fixtureAlive",true])', text)
    text = re.sub(r'alive \(_u getVariable \["ACM_breathing_BVM_Medic",\s*objNull\]\)', 'false', text)
    text = text.replace('_patient isKindOf "CAManBase"', '_patient getVariable ["fixtureMan",true]')
    text = text.replace('_parent isKindOf "Air"', '_parent getVariable ["fixtureAir",true]')
    text = text.replace('objectParent _patient', '_patient getVariable ["fixtureParent",objNull]')
    text = text.replace('getPosASL _obj', '_obj getVariable ["fixtureASL",[0,0,0]]')
    text = re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', text)
    text = text.replace('clientOwner', '7').replace('toLowerANSI', 'toLower')
    tokens = lex(text); pairs = matching(tokens); edits = []
    for i, token in enumerate(tokens[:-1]):
        if token.kind == "ident" and token.value == "linearConversion":
            end = pairs[i + 1]
            edits.append((token.offset, tokens[end].offset + 1,
                          "(" + text[tokens[i + 1].offset:tokens[end].offset + 1] + " call _linear)"))
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return namespace_public_arguments(map_defaults(iteration_scopes(text)))


def function(name):
    return "ACME_fnc_" + name + "={" + adapt(source(name)) + "};\n"


def fixture():
    return r'''
        private _mapDefault={params ["_map","_args"]; _args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _linear={params ["_a","_b","_value","_lo","_hi",["_clamp",false]];
            private _fraction=(_value-_a)/(_b-_a);if (_clamp) then {_fraction=_fraction max 0 min 1;};_lo+(_hi-_lo)*_fraction};
        private _publications=[];
        private _exactPublications=[];
        private _activations=[];
        private _pressureChanges=[];
        private _datum=0;
        private _airReads=0;
        ACME_fnc_altitudeDatum={_datum};
        ACME_fnc_flightAirframe={_airReads=_airReads+1;(_this select 0) getVariable ["fixtureAirframe",objNull]};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["fixtureEpoch",1]};
        ACME_fnc_oxygenSupply={(_this select 0) getVariable ["fixtureSupply",false]};
        ACME_fnc_setVarNet={params ["_p","_key","_value"]; _publications pushBack [_p,_key,_value];_exactPublications pushBack [_p,_key,_value];_p setVariable [_key,_value];};
        ACME_fnc_setVarNetApprox={params ["_p","_key","_value"]; _publications pushBack [_p,_key,_value];_p setVariable [_key,_value];};
        ACME_fnc_ptxAmbientChange={_pressureChanges pushBack _this;};
        // The supplied ACE activateMedical handler writes this flag immediately.
        // Record its exact event and object payload, then apply that engine API.
        CBA_fnc_localEvent={_activations pushBack _this;
            if ((_this select 0)=="ace_medical_activateMedical") then {
                (_this select 1) setVariable ["ace_medical_medicalActivity",true];
            };
        };
        missionNamespace setVariable ["ACME_sys_flight",true];
        missionNamespace setVariable ["ACME_altitude_enable",true];
        missionNamespace setVariable ["ACM_breathing_altitudeAffectOxygen",false];
        missionNamespace setVariable ["ACME_flightG_enable",false];
        missionNamespace setVariable ["ACME_altitude_minMetres",500];
        missionNamespace setVariable ["ace_medical_const_medicalActivity",false];
        ACME_flight_activePatients=[];
        ACME_clinical_activePatients=[];
        ACME_clinical_ownedUnits=[_patient,_medic];
    ''' + "".join(function(name) for name in (
        "altitudeTrue", "pressureAtAltitude", "altitudeOxygenCeiling",
        "clinicalTickDelta", "altitudeTick", "flightNeedsTick", "flightTick", "idlePhysDiscovery",
    )) + r'''
        // Cabin/equipment classification is tested separately against actual
        // config and geometry. This fixture's engine exposure read still uses
        // production altitude and pressure instead of canned hypoxia values.
        ACME_fnc_flightExposure={params ["_p"];
            private _h=[_p] call ACME_fnc_altitudeTrue;
            private _pressure=[_h] call ACME_fnc_pressureAtAltitude;
            [_h,_pressure,_p getVariable ["fixtureCabin",_pressure],
                [_p] call ACME_fnc_oxygenSupply,[_p] call ACME_fnc_flightAirframe]
        };
    '''


@pytest.mark.parametrize("height", [500, 2000, 10000, 20000, 50000, 100000])
def test_healthy_high_altitude_enrolls_without_injury_or_clinical_worker(height):
    execute(fixture() + f'''
        _patient setVariable ["fixtureASL",[0,0,{height}]];
        _medic setVariable ["fixtureASL",[0,0,{height}]];
        [] call ACME_fnc_idlePhysDiscovery;
        [ACME_flight_activePatients isEqualTo [_patient,_medic],"healthy flight exposure missed an owner"] call _check;
        [ACME_circ_activePatients isEqualTo [] && {{ACME_clinical_activePatients isEqualTo []}},
            "flight-only exposure enrolled heavy clinical maintenance"] call _check;
        [count _publications==0 && {{count _activations==0}},"discovery published healthy state"] call _check;
        call ACME_fnc_flightTick;
        [count _activations==2,"inactive healthy owners did not receive native vitals activation"] call _check;
        [((_activations select 0) select 1) isEqualTo _patient && {{((_activations select 1) select 1) isEqualTo _medic}},
            "native activation did not use the actual object payload"] call _check;
        [(_patient getVariable ["ACME_alt_hypoxia",0])>0 && {{(_medic getVariable ["ACME_alt_hypoxia",0])>0}},
            "healthy exposure did not reach actual altitude tick"] call _check;
        [abs ((_patient getVariable ["ACME_alt_hypoxia",0])-(_medic getVariable ["ACME_alt_hypoxia",0]))<0.0001,
            "equal healthy exposure produced inconsistent altitude diagnostics"] call _check;
        for "_i" from 1 to 12 do {{CBA_missionTime=10+(_i*0.25);call ACME_fnc_flightTick;}};
        [count _activations==2,"stable exposed owners generated periodic native activation"] call _check;
    ''')


@pytest.mark.parametrize("height", [0, 100, 499])
def test_healthy_ground_is_silent_and_never_enters_hot_flight_worker(height):
    execute(fixture() + f'''
        _patient setVariable ["fixtureASL",[0,0,{height}]];
        _medic setVariable ["fixtureASL",[0,0,{height}]];
        for "_i" from 0 to 119 do {{
            CBA_missionTime=10+_i;
            [] call ACME_fnc_idlePhysDiscovery;
            call ACME_fnc_flightTick;
        }};
        [ACME_flight_activePatients isEqualTo [],"healthy ground retained flight enrollment"] call _check;
        [count _publications==0 && {{count _activations==0}},"healthy ground caused network heartbeat"] call _check;
        [_airReads==0,"pristine healthy ground initiated geometry reads"] call _check;
        [isNil {{_patient getVariable "ACME_clock_altitude"}},"healthy ground acquired flight clock"] call _check;
    ''')


@pytest.mark.parametrize("protection", ["oxygen", "cabin"])
def test_protected_healthy_occupants_do_not_activate_native_worker(protection):
    setup = ('_patient setVariable ["fixtureSupply",true];' if protection == "oxygen"
             else '_patient setVariable ["fixtureCabin",1];')
    execute(fixture() + r'''
        _patient setVariable ["fixtureASL",[0,0,10000]];
    ''' + setup + r'''
        [[_patient]] call ACME_fnc_idlePhysDiscovery;
        call ACME_fnc_flightTick;
        [count _activations==0,"protected healthy occupant activated clinical physiology"] call _check;
        [(_patient getVariable ["ACME_alt_hypoxia",-1])==0,"protected occupant retained altitude hypoxia"] call _check;
    ''')


def test_ground_ptx_still_observes_low_altitude_pressure_without_healthy_enrollment():
    execute(fixture() + r'''
        _patient setVariable ["ACM_breathing_Pneumothorax_State",0.4];
        _patient setVariable ["fixtureASL",[0,0,100]];
        [] call ACME_fnc_idlePhysDiscovery;
        [ACME_flight_activePatients isEqualTo [_patient],"low altitude PTX did not receive pressure worker"] call _check;
        call ACME_fnc_flightTick;
        _patient setVariable ["fixtureASL",[0,0,300]];
        CBA_missionTime=10.25;call ACME_fnc_flightTick;
        [count _pressureChanges==1 && {((_pressureChanges select 0) select 1)>1},"low climb did not change existing trapped gas"] call _check;
        [count _activations==0,"subthreshold PTX pressure activated healthy oxygenation"] call _check;
    ''')


@pytest.mark.parametrize("master,native,expected", [(True, True, True), (False, True, False), (True, False, False)])
def test_native_only_altitude_option_still_enrolls_healthy_ai_and_master_switch_wins(master, native, expected):
    execute(fixture() + f'''
        missionNamespace setVariable ["ACME_sys_flight",{str(master).lower()}];
        missionNamespace setVariable ["ACME_altitude_enable",false];
        missionNamespace setVariable ["ACM_breathing_altitudeAffectOxygen",{str(native).lower()}];
        _patient setVariable ["fixtureASL",[0,0,10000]];
        [[_patient]] call ACME_fnc_idlePhysDiscovery;
        [(count ACME_flight_activePatients>0) isEqualTo {str(expected).lower()},"native-only enrollment ignored configured flight switches"] call _check;
        call ACME_fnc_flightTick;
        [(count _activations>0) isEqualTo {str(expected).lower()},"native activation ignored master/native altitude switches"] call _check;
    ''')


@pytest.mark.parametrize("height,expected", [(0, False), (100, True)])
def test_native_only_altitude_applies_below_custom_cutoff_but_sea_level_stays_neutral(height, expected):
    execute(fixture() + f'''
        missionNamespace setVariable ["ACME_altitude_enable",false];
        missionNamespace setVariable ["ACM_breathing_altitudeAffectOxygen",true];
        _patient setVariable ["fixtureASL",[0,0,{height}]];
        [[_patient]] call ACME_fnc_idlePhysDiscovery;
        [(count ACME_flight_activePatients>0) isEqualTo {str(expected).lower()},"native below-cutoff exposure enrollment differs from oxygen calculation"] call _check;
        call ACME_fnc_flightTick;
        [(count _activations>0) isEqualTo {str(expected).lower()},"native below-cutoff exposure did not activate its actual oxygen worker"] call _check;
    ''')


@pytest.mark.parametrize("occupancy", ["seated", "walking_hypovolemic"])
def test_low_air_occupancy_enrolls_for_maneuver_monitoring(occupancy):
    setup = ('_patient setVariable ["fixtureParent",_medic];' if occupancy == "seated" else
             '_patient setVariable ["ACM_circulation_Blood_Volume",4];_patient setVariable ["fixtureAirframe",_medic];')
    execute(fixture() + r'''
        _patient setVariable ["fixtureASL",[0,0,100]];
    ''' + setup + r'''
        [[_patient]] call ACME_fnc_idlePhysDiscovery;
        [ACME_flight_activePatients isEqualTo [_patient],"low air occupant missed maneuver enrollment"] call _check;
        [count _publications==0,"low air discovery published state"] call _check;
    ''')


@pytest.mark.parametrize("exit_kind", ["descent", "disable", "altitude_toggle"])
def test_descent_and_live_disable_make_final_cleanup_then_retire(exit_kind):
    change = {
        "descent": '_patient setVariable ["fixtureASL",[0,0,100]];',
        "disable": 'missionNamespace setVariable ["ACME_sys_flight",false];',
        "altitude_toggle": 'missionNamespace setVariable ["ACME_altitude_enable",false];',
    }[exit_kind]
    execute(fixture() + r'''
        _patient setVariable ["fixtureASL",[0,0,10000]];
        [[_patient]] call ACME_fnc_idlePhysDiscovery;call ACME_fnc_flightTick;
        _publications=[];
    ''' + change + r'''
        CBA_missionTime=10.25;call ACME_fnc_flightTick;
        [ACME_flight_activePatients isEqualTo [],"final flight cleanup did not retire"] call _check;
        [(_patient getVariable ["ACME_alt_hypoxia",-1])==0,"flight exit retained hypoxia"] call _check;
        [(_patient getVariable ["ACME_alt_pRatio",-1])==1,"flight exit retained pressure mirror that enrolls preoxygenation"] call _check;
        [!(_patient getVariable ["ACME_flight_tickActive",true]),"final exit retained active marker"] call _check;
        [isNil {_patient getVariable "ACME_alt_ptxSample"} && {isNil {_patient getVariable "ACME_clock_altitude"}},
            "retired flight retained pressure or elapsed history"] call _check;
        private _count=count _publications;
        for "_i" from 1 to 120 do {CBA_missionTime=11+_i;[] call ACME_fnc_idlePhysDiscovery;call ACME_fnc_flightTick;};
        [count _publications==_count,"flight exit produced permanent quiet-state heartbeat"] call _check;
    ''')


def test_residual_maneuver_effect_finishes_decay_and_exact_neutralization_before_retirement():
    execute(fixture() + r'''
        _patient setVariable ["ACME_flightG_resistAdd",-28];
        _patient setVariable ["ACME_flightG_stress",1];
        [[_patient]] call ACME_fnc_idlePhysDiscovery;
        [ACME_flight_activePatients isEqualTo [_patient],"retained maneuver effect was not rediscovered"] call _check;
        call ACME_fnc_flightTick;
        [ACME_flight_activePatients isEqualTo [_patient],"maneuver recovery retired before its first elapsed tick"] call _check;
        CBA_missionTime=10.25;call ACME_fnc_flightTick;
        [abs ((_patient getVariable ["ACME_flightG_resistAdd",0])+23.5)<0.0001,
            "maneuver recovery did not use actual elapsed flight clock"] call _check;
        [ACME_flight_activePatients isEqualTo [_patient],"maneuver recovery retired with active resistance"] call _check;
        for "_i" from 2 to 8 do {CBA_missionTime=10+(_i*0.25);call ACME_fnc_flightTick;};
        [ACME_flight_activePatients isEqualTo [] && {(_patient getVariable ["ACME_flightG_resistAdd",1])==0},
            "maneuver recovery did not finish and retire"] call _check;
        [[_patient,"ACME_flightG_resistAdd",0] in _exactPublications
            && {[_patient,"ACME_alt_hypoxia",0] in _exactPublications},
            "flight retirement left its final remote reset to approximate suppression"] call _check;
    ''')


@pytest.mark.parametrize("invalid", ["fixtureLocal", "fixtureAlive", "fixtureMan", "restoring"])
def test_departed_dead_and_restoring_owner_cannot_mutate_flight_physiology(invalid):
    setting = ('_patient setVariable ["ACME_clinicalRestoring",true];' if invalid == "restoring"
               else f'_patient setVariable ["{invalid}",false];')
    execute(fixture() + r'''
        _patient setVariable ["fixtureASL",[0,0,10000]];
        ACME_flight_activePatients=[_patient,_patient];
    ''' + setting + r'''
        call ACME_fnc_flightTick;
        [ACME_flight_activePatients isEqualTo [],"invalid owner remained in hot worker"] call _check;
        [count _publications==0 && {count _activations==0},"invalid owner mutated flight physiology"] call _check;
        [!([_patient] call ACME_fnc_flightNeedsTick),"read-only discovery accepted invalid owner"] call _check;
    ''')


def test_discovery_partial_refresh_preserves_other_owner_and_prevents_duplicates():
    execute(fixture() + r'''
        _patient setVariable ["fixtureASL",[0,0,10000]];
        _medic setVariable ["fixtureASL",[0,0,10000]];
        [] call ACME_fnc_idlePhysDiscovery;
        [[_patient,_patient]] call ACME_fnc_idlePhysDiscovery;
        [count ACME_flight_activePatients==2 && {_patient in ACME_flight_activePatients} && {_medic in ACME_flight_activePatients},
            "owner refresh erased peer or duplicated enrollment"] call _check;
        ACME_flight_activePatients pushBack _patient;
        call ACME_fnc_flightTick;
        [count _activations==2 && {count ACME_flight_activePatients==2},"duplicate registry integrated owner twice"] call _check;
    ''')


def test_departed_owner_does_not_abort_later_local_owner_tick():
    execute(fixture() + r'''
        _patient setVariable ["fixtureLocal",false];
        _medic setVariable ["fixtureASL",[0,0,10000]];
        ACME_flight_activePatients=[_patient,_medic];
        call ACME_fnc_flightTick;
        [ACME_flight_activePatients isEqualTo [_medic],"departed first owner aborted later local owner"] call _check;
        [count _activations==1 && {((_activations select 0) select 1) isEqualTo _medic},"invalid entry prevented native owner activation"] call _check;
    ''')


def test_runtime_reload_replaces_flight_pfh_and_runs_before_circulation():
    execute(r'''
        private _removedIDs=[];
        private _registered=[];
        private _nextID=40;
        CBA_fnc_removePerFrameHandler={_removedIDs pushBack (_this select 0);};
        CBA_fnc_addPerFrameHandler={_registered pushBack _this;_nextID=_nextID+1;_nextID};
        private _order=[];
        ACME_fnc_salineAcidosisTrack={_order pushBack "saline";};
        ACME_fnc_flightTick={_order pushBack "flight";};
        ACME_fnc_circHandle={_order pushBack "circ";};
        ACME_fnc_autoBPTick={_order pushBack "bp";};
    ''' + function("registerCirculationRuntime") + r'''
        call ACME_fnc_registerCirculationRuntime;
        private _flightID=missionNamespace getVariable ["ACME_PFH_flightTick",-1];
        [((_registered select 1) select 1)==0.25,"flight PFH cadence changed"] call _check;
        {call (_x select 0);} forEach _registered;
        [_order isEqualTo ["saline","flight","circ","bp"],"flight state ran after clinical circulation"] call _check;
        call ACME_fnc_registerCirculationRuntime;
        [_flightID in _removedIDs && {count _removedIDs==4},"reload left duplicate runtime PFHs"] call _check;
        [(missionNamespace getVariable ["ACME_PFH_flightTick",-1])!=_flightID,"reload reused stale flight handler"] call _check;
    ''')


def test_healthy_owner_discovery_to_native_oxygen_uses_actual_exposure_pipeline():
    from b281_flight_fixture import flight_setup, execute as shared_execute

    shared_execute(flight_setup() + r'''
        // The shared physiology fixture keeps its native primitives separate
        // from retained ventilation adapters. Bind the scheduler's equivalents
        // explicitly without changing production decisions or test assertions.
        private _mapDefault=_flightMapDefault;
        private _finite=_flightFinite;
        private _linear=_flightLinear;
    ''' + "".join(function(name) for name in (
        "flightNeedsTick", "flightTick", "idlePhysDiscovery",
    )) + r'''
        private _activations=[];
        CBA_fnc_localEvent={_activations pushBack _this;
            if ((_this select 0)=="ace_medical_activateMedical") then {
                (_this select 1) setVariable ["ace_medical_medicalActivity",true];
            };
        };
        missionNamespace setVariable ["ace_medical_const_medicalActivity",false];
        ACME_flight_activePatients=[];ACME_clinical_activePatients=[];
        ACME_clinical_ownedUnits=[_patient,_medic];
        _patient setVariable ["fixturePosASL",[0,0,10000]];
        _medic setVariable ["fixturePosASL",[0,0,10000]];
        _medic setVariable ["ace_medical_spo2",99];
        _medic setVariable ["ACM_core_TargetVitals_OxygenSaturation",99];
        [] call ACME_fnc_idlePhysDiscovery;call ACME_fnc_flightTick;
        [count _activations==2 && {ACME_circ_activePatients isEqualTo []},"actual healthy exposure did not reach native activation without heavy clinical enrollment"] call _check;
        private _first=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
        private _second=[_medic,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
        [_first<99 && {_first>98.8} && {abs (_first-_second)<0.0001},"same healthy owners had different native altitude oxygenation"] call _check;
        [_patient getVariable ["ACM_core_TargetVitals_OxygenSaturation",0]==99
            && {_medic getVariable ["ACM_core_TargetVitals_OxygenSaturation",0]==99},"flight scheduler overwrote native clinical targets"] call _check;
    ''')


def test_single_writer_and_bounded_registry_are_registered_production_contracts():
    assert "call ACME_fnc_altitudeTick" not in source("circHandle")
    assert source("flightTick").count("call ACME_fnc_altitudeTick") == 1
    for worker in ("flightTick", "flightNeedsTick"):
        text = source(worker)
        assert "allUnits" not in text and "allPlayers" not in text and "ACME_clinical_ownedUnits" not in text
        assert "ACME_circ_activePatients" not in text and "ACME_clinical_activePatients" not in text
    config = (ROOT / "config.cpp").read_text()
    for helper in ("flightTick", "flightNeedsTick"):
        assert f"class {helper} {{}};" in config
    for lifecycle in ("ownerInit", "clinicalReset"):
        text = source(lifecycle)
        assert '"ACME_flight_activePatients"' in text
        assert '"ACME_flight_tickActive"' in text
