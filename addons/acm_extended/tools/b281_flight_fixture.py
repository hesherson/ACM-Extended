"""Execute B281 production pressure/oxygen SQF; only Arma boundaries are fixtures.

Namespaces represent native objects. Positions, gear/config values, aircraft
lookup/enclosure, native vitals getters and network publications are explicit
engine boundaries; pressure, precedence, conditions, ceilings and integration
run directly from checked-out source.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import pytest
from test_menu_death_lifecycle import ROOT, adapt, read, PREAMBLE
from test_historical_vial_execution import map_defaults
from test_b212_stethoscope_shallow import linear_primitive


def execute(code):
    vm = os.environ.get('SQFVM') or shutil.which('sqfvm')
    if not vm:
        pytest.skip('SQF-VM required')
    with tempfile.TemporaryDirectory(prefix='acme-b281-flight-') as directory:
        path = Path(directory) / 'case.sqf'
        path.write_text(PREAMBLE + code + '\ndiag_log (if (_ok) then {"B281_FLIGHT_OK"} else {"B281_FLIGHT_FAIL"});')
        result = subprocess.run([vm, '--automated', '--suppress-welcome', '--no-execute-print',
                                 '--no-work-print', '--input-sqf', str(path)], capture_output=True, text=True, timeout=20)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert not any(tag in output for tag in ('[ERR]', '[FAT]', '[WRN]', 'MENU_FIX_FAIL', 'B281_FLIGHT_FAIL')), output
    assert 'B281_FLIGHT_OK' in output, output
    return output


def flight_code(text):
    text = re.sub(r'objNull,\s*\[objNull\]', 'objNull, [profileNamespace]', text)
    text = text.replace('clientOwner', '_fixtureOwner')
    text = text.replace('_patient == ACE_player', '_patient isEqualTo ACE_player')
    text = text.replace('local _patient', '_patientLocal')
    text = text.replace('_patient isKindOf "CAManBase"', '_isPatient')
    for command, key in [('goggles', 'fixtureGoggles'), ('headgear', 'fixtureHeadgear'), ('vest', 'fixtureVest')]:
        text = text.replace(command + ' _patient', '(_patient getVariable ["' + key + '",""])')
    text = text.replace('getPosASL _obj', '(_obj getVariable ["fixturePosASL",[0,0,0]])')
    text = text.replace('worldName', '_world').replace('worldSize', '_worldSize')
    text = text.replace('getTerrainHeightASL [_x, _y]', '(call _terrainHeight)')
    text = text.replace('getNumber (configFile >> "CfgWorlds" >> _world >> "elevationOffset")', '_worldBase')
    text = text.replace('configOf _airframe', '(_airframe getVariable ["fixtureClass",""])')
    text = re.sub(r'isNumber \(_cfg >> "([^"]+)"\)', r'([_cfg,"\1"] call _configHas)', text)
    text = re.sub(r'getNumber \(_cfg >> "([^"]+)"\)', r'([_cfg,"\1"] call _configGet)', text)
    text = text.replace('isEngineOn _veh', '(_veh getVariable ["fixtureEngine",false])')
    text = text.replace('velocity _veh', '(_veh getVariable ["fixtureVelocity",[0,0,0]])')
    text = text.replace('vectorUp _veh', '(_veh getVariable ["fixtureUp",[0,0,1]])')
    text = text.replace('vehicle _unit', '(_unit getVariable ["fixtureVehicle",_unit])')
    text = text.replace('_veh == _unit', '_veh isEqualTo _unit')
    text = text.replace('isTurnedOut _unit', '(_unit getVariable ["fixtureTurnedOut",false])')
    text = text.replace('speed _veh', '(_veh getVariable ["fixtureSpeed",0])')
    text = text.replace('_veh isKindOf "Air"', '(_veh getVariable ["fixtureIsAir",false])')
    text = text.replace('getPosATL _veh', '(_veh getVariable ["fixturePosATL",[0,0,0]])')
    # Namespace nil slots differ from Arma's deleted object variables. Adapt
    # only default reads following the actual source cleanup operation.
    for key, default in [('ACME_alt_ptxSample', '[]'), ('ACME_alt_tickStamp', '[]')]:
        text = text.replace(f'_patient getVariable ["{key}", {default}]', f'([_patient,"{key}",{default}] call _namespaceDefault)')
    text = re.sub(r'\bfinite (_\w+)', r'(\1 call _flightFinite)', text)
    text = text.replace('finite (_cache select 2)', '((_cache select 2) call _flightFinite)')
    return adapt(map_defaults(linear_primitive(text))).replace('call _linear','call _flightLinear').replace('call _mapDefault','call _flightMapDefault')


def flight_function(name):
    return 'ACME_fnc_' + name + '={\n' + flight_code(read(name)) + '\n};\n'


def native_oxygen():
    text = (ROOT / 'addons/core/overrides/fnc_updateOxygen.sqf').read_text()
    # Observe the computed production target without altering its branches or
    # native rate integration (native recovery can overshoot by 0.25 per pass).
    text = text.replace('private _po2 = IDEAL_PPO2;',
                        '_fixtureDesired=_desiredOxygenSaturation; private _po2 = IDEAL_PPO2;')
    text = text.replace('_patient setVariable [VAR_SPO2, _oxygenSaturation, _syncValue];',
                        '_patient setVariable [VAR_SPO2, _oxygenSaturation];')
    fields = {
        'ACM_TARGETVITALS_OXYGEN': ('ACM_core_TargetVitals_OxygenSaturation', 99),
        'GET_OXYGEN': ('ace_medical_spo2', 99),
        'GET_HEART_RATE': ('fixtureHR', 80),
        'GET_EFF_BLOOD_VOLUME': ('ACM_circulation_Blood_Volume', 6),
        'GET_AIRWAYSTATE': ('fixtureAirway', 1),
        'GET_BREATHINGSTATE': ('fixtureBreathing', 1),
        'IS_EXPOSED': ('fixtureExposed', 'false'),
        'IS_UNCONSCIOUS': ('ACE_isUnconscious', 'false'),
        'IN_CRDC_ARRST': ('ace_medical_inCardiacArrest', 'false'),
        'HAS_PULSE': ('fixturePulse', 'true'),
        'HAS_SURGICAL_AIRWAY': ('fixtureSurgical', 'false'),
        'GET_AIRWAY_INFLAMMATION': ('fixtureAirwayInflammation', 0),
        'GET_LUNG_TISSUEDAMAGE': ('fixtureLungDamage', 0),
        'GET_EXPOSURE_BREATHING_INCREASESTATE': ('fixtureExposureGain', 1),
        'GET_MAP_PATIENT': ('fixtureMAP', 90),
        'ACM_TARGETVITALS_RR': ('ACM_core_TargetVitals_RespirationRate', 18),
    }
    for symbol, (key, default) in fields.items():
        text = text.replace(symbol + '(_patient)', f'(_patient getVariable ["{key}",{default}])')
    for symbol, value in [('BASE_OXYGEN_USE','-0.25'), ('DEFAULT_BLOOD_VOLUME','6'),
                          ('ACM_BREATHING_MINDECREASE','0.1'), ('ACM_BREATHING_MAXDECREASE','0.12'),
                          ('VAR_OXYGEN_DEMAND','"fixtureOxygenDemand"'), ('VAR_SPO2','"ace_medical_spo2"')]:
        text = re.sub(r'\b' + symbol + r'\b', value, text)
    text = text.replace('#define IDEAL_PPO2 0.255','').replace('IDEAL_PPO2','0.255')
    return 'ace_medical_vitals_fnc_updateOxygen={\n' + flight_code(text) + '\n};\n'


def flight_setup():
    return r'''
      private _patientLocal=true; private _isPatient=true; private _fixtureOwner=7;
      private _world="Terrain_A"; private _worldSize=100; private _worldBase=0;
      private _terrainMinimum=0; private _terrainReads=0;
      private _flightFinite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
      private _flightLinear={params ["_lo","_hi","_value","_a","_b",["_clamp",false]];private _f=(_value-_lo)/(_hi-_lo);if (_clamp) then {_f=(_f max 0) min 1;};_a+(_b-_a)*_f};
      private _terrainHeight={_terrainReads=_terrainReads+1; _terrainMinimum};
      private _config=createHashMap;
      private _configHas={params ["_class","_field"]; (_class+":"+_field) in _config};
      private _configGet={params ["_class","_field"]; _config get (_class+":"+_field)};
      private _flightMapDefault={params ["_map","_args"]; _args params ["_key","_default"]; if (_key in _map) then {_map get _key} else {_default}};
      private _namespaceDefault={params ["_space","_key","_default"]; private _value=_space getVariable [_key,_default]; if (isNil "_value") then {_default} else {_value}};
      private _airframe=parsingNamespace; private _framePresent=false; private _inside=false;
      private _publications=[]; private _ptxPublications=[];
      private _fixtureDesired=-1;
      ACME_fnc_flightAirframe={if (_framePresent) then {_airframe} else {objNull}};
      ACME_fnc_flightEnclosed={_inside};
      ACME_fnc_setVarNet={params ["_p","_key","_value"];_publications pushBack [_key,_value];_p setVariable [_key,_value];};
      ACME_fnc_setVarNetApprox=ACME_fnc_setVarNet;
      ACME_fnc_suctionPhysiologyTick={};
      ACME_fnc_ventEffectiveSettings={["SIMV",12,500,5,_patient getVariable ["fixtureFiO2",21]]};
      ACM_breathing_fnc_updateRespirationRate={(_this select 0) getVariable ["fixtureRR",18]};
      ACM_core_fnc_bvmActive={false}; ACM_core_fnc_cprActive={false}; ACM_CBRN_enable=false;
      ACME_fnc_ventShuntCommit={};
      ACME_fnc_ptxEnsure={_patient getVariable ["ACME_ptx_state",[1,0,0,0,0,0,0,0,0]]};
      ACME_fnc_ptxContext={[0,0,0,0,1,false,false,false]};
      ACME_fnc_ptxPublish={params ["_p","_s","_tension"];_ptxPublications pushBack [+_s,_tension];_p setVariable ["ACME_ptx_state",+_s];_p setVariable ["ACM_breathing_TensionPneumothorax_State",_tension];};
      missionNamespace setVariable ["ACME_sys_flight",true];
      missionNamespace setVariable ["ACME_altitude_enable",true];
      missionNamespace setVariable ["ACME_altitude_datumMode",0];
      missionNamespace setVariable ["ACM_breathing_altitudeAffectOxygen",false];
      missionNamespace setVariable ["ace_medical_vitals_oxygenSupplyConditionCache",createHashMap];
      _patient setVariable ["fixturePosASL",[0,0,0]];
      _patient setVariable ["ACM_core_TargetVitals_OxygenSaturation",99];
      _patient setVariable ["ace_medical_spo2",99];
      _patient setVariable ["ACME_ptx_state",[1,0,0,0,0,0,0,0,0]];
      _airframe setVariable ["fixtureClass","AnyModdedAirframe"];
    ''' + ''.join(flight_function(name) for name in (
        'pressureAtAltitude','altitudeDatum','altitudeTrue','oxygenSupply','flightExposure',
        'altitudeOxygenCeiling','clinicalEpoch','clinicalTickDelta','ptxAmbientChange','altitudeTick','ventOxygenation',
    )) + native_oxygen()


def ground_exposure_setup():
    """New real dependency graph for retained sea-level ventilator scenarios.

    Do not replace their existing ventilator/device fixtures or alter their
    assertions. Only supply the actual pressure/gear/ceiling functions and
    the newly required native position/config/airframe engine boundaries.
    """
    return r'''
      private _world="VentilationGroundFixture";private _worldSize=0;private _worldBase=0;
      private _flightFinite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
      private _flightLinear={params ["_lo","_hi","_value","_a","_b",["_clamp",false]];private _f=(_value-_lo)/(_hi-_lo);if (_clamp) then {_f=(_f max 0) min 1;};_a+(_b-_a)*_f};
      private _flightMapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
      ACME_fnc_flightAirframe={objNull};ACME_fnc_flightEnclosed={false};
    ''' + ''.join(flight_function(name) for name in (
        'pressureAtAltitude','altitudeDatum','altitudeTrue','oxygenSupply','flightExposure','altitudeOxygenCeiling',
    ))
