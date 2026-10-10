"""Exercise the actual B216 catalog/menu/request and case application in SQF-VM.
Engine creation, locality and clinical endpoints are explicit fixtures. The test
verifies routing and seed inputs; it is not a simulation of Arma physiology.
"""
import re
from pathlib import Path

import pytest
from test_menu_death_lifecycle import adapt, execute

ROOT = Path(__file__).resolve().parents[3]
M = ROOT / 'addons/mission/functions'


def source(name):
    return (M / f'fnc_{name}.sqf').read_text()


def compiled(name):
    return adapt(source(name), component='mission')


def catalog():
    return 'ACM_mission_fnc_patientPreset = {' + compiled('patientPreset') + '};\n'


@pytest.mark.parametrize('triage,minimum', [(1,2),(2,4),(3,6),(4,3)])
def test_each_triage_has_concrete_cases_and_routine_stays_simple(triage, minimum):
    execute(catalog() + f'''
        private _cases = ([] call ACM_mission_fnc_patientPreset) select {{(_x select 2) == {triage} && {{(_x select 10) isEqualTo []}}}};
        [count _cases == {minimum}, "wrong number of triage cases"] call _check;
        {{[count _x == 11, "malformed clinical case"] call _check;}} forEach _cases;
    ''')


@pytest.mark.parametrize('case,blood,chest,tbi,blast', [
    ('tension_ptx',5,'[2,0]','[]',0),
    ('hemothorax',4.5,'[3,0,6,1]','[]',0),
    ('massive_htx',3,'[3,1,9,1.5]','[]',0),
    ('tbi_severe',6,'[]','[0.8,2]',0),
    ('tbi_herniation',6,'[]','[0.95,3]',0),
    ('blast_mild',6,'[]','[]',0.25),
    ('blast_severe',6,'[]','[]',0.7),
])
def test_case_seeds_are_specific_and_treatment_relevant(case,blood,chest,tbi,blast):
    execute(catalog() + f'''
        private _case = ["{case}"] call ACM_mission_fnc_patientPreset;
        [(_case select 5 select 0) == {blood}, "wrong circulating blood volume"] call _check;
        [(_case select 7) isEqualTo {chest}, "wrong pleural case"] call _check;
        [(_case select 8) isEqualTo {tbi}, "wrong TBI case"] call _check;
        [(_case select 9) == {blast}, "wrong blast case"] call _check;
    ''')


def menu():
    return catalog() + '''
        ace_interact_menu_fnc_createAction = {_this};
        ACM_mission_fnc_spawnPatient_childActions = {''' + compiled('spawnPatient_childActions') + '''};
        private _object = missionNamespace;
        private _location = parsingNamespace;
        private _requested = [];
        ACM_mission_fnc_requestTrainingPatient = {_requested pushBack _this;};
    '''


@pytest.mark.parametrize('count', [0,1])
def test_faction_is_top_level_and_clicking_it_requests_one_random_spawn(count):
    execute(menu() + f'''
        private _actions = [_object,_location,{count}] call ACM_mission_fnc_spawnPatient_childActions;
        [count _actions == 2, "faction menu does not have two parents"] call _check;
        {{
            private _action = _x select 0;
            [(_action select 1) == (["Civilian","BLUFOR"] select _forEachIndex), "wrong faction label"] call _check;
            [_object,_medic,_action select 6] call (_action select 3);
        }} forEach _actions;
        [count _requested == 2, "parent click spawned duplicate request"] call _check;
        {{[_x select 3 == {count} && {{_x select 4 == 0}} && {{_x select 5 == 0}} && {{_x select 7 == ""}}, "parent lost random fallback"] call _check;}} forEach _requested;
        [(_requested select 0 select 6) == "Civilian" && {{(_requested select 1 select 6) == "BLUFOR"}}, "request lost faction"] call _check;
    ''')


def test_triage_and_cbrn_menus_route_to_catalog_without_spawning_on_hover():
    execute(menu() + '''
        private _actions = [_object,_location,1,"category","Civilian"] call ACM_mission_fnc_spawnPatient_childActions;
        [count _actions == 5, "missing triage/CBRN category"] call _check;
        private _cb = _actions select 4 select 0;
        [(_cb select 1) == "CBRN", "missing CBRN title"] call _check;
        private _children = [_object,_medic,_cb select 6] call (_cb select 5);
        [count _children == 4, "missing chemical exposure cases"] call _check;
        [count _requested == 0, "hover created a patient"] call _check;
        [_object,_medic,_cb select 6] call (_cb select 3);
        [(_requested select 0 select 7) == "cbrn_random", "CBRN parent does not choose chemical case"] call _check;
    ''')


def test_bulk_count_menu_retains_two_through_eight():
    execute(menu() + '''
        private _actions = [_object,_location,0,"count","BLUFOR"] call ACM_mission_fnc_spawnPatient_childActions;
        [count _actions == 7, "bulk count choices changed"] call _check;
        {[_object,_medic,(_x select 0) select 6] call ((_x select 0) select 3);} forEach _actions;
        {[_x select 3 == _forEachIndex + 2, "wrong bulk count requested"] call _check;} forEach _requested;
    ''')


def request_setup():
    s = source('requestTrainingPatient').replace('isServer','_server').replace('alive _initiator','_alive').replace('_initiator distance _object','_distance')
    return catalog() + '''
        private _object = missionNamespace;
        private _location = parsingNamespace;
        private _initiator = uiNamespace;
        private _server = true;
        private _requests = [];
        private _spawns = [];
        CBA_fnc_serverEvent = {_requests pushBack _this;};
        ACM_mission_fnc_generatePatient = {_spawns pushBack ["single",_this];};
        ACM_mission_fnc_generatePatients = {_spawns pushBack ["bulk",_this];};
        private _request = {''' + adapt(s, component='mission') + '''};
    '''


def test_remote_client_only_sends_one_request_and_never_creates_locally():
    execute(request_setup() + '''
        _server = false;
        [_object,_location,_initiator,1,0,0,"Civilian",""] call _request;
        [count _requests == 1 && {count _spawns == 0}, "client created casualty or duplicate event"] call _check;
        _server = true;
        (_requests select 0 select 1) call _request;
        (_requests select 0 select 1) call _request;
        [count _spawns == 1, "duplicate delivery created another casualty"] call _check;
        [(_spawns select 0 select 1 select 6) == "Civilian", "server lost faction"] call _check;
    ''')


@pytest.mark.parametrize('count,kind', [(1,'single'),(0,'bulk'),(4,'bulk')])
def test_server_dispatches_correct_native_generator_once(count,kind):
    execute(request_setup() + f'''
        [_object,_location,_initiator,{count},3,0,"BLUFOR","blast_severe",[7,99]] call _request;
        [count _spawns == 1 && {{(_spawns select 0 select 0) == "{kind}"}}, "wrong native generator"] call _check;
    ''')


@pytest.mark.parametrize('args', [
    '9,0,0,"BLUFOR",""', '1,9,0,"BLUFOR",""', '1,0,99,"BLUFOR",""',
    '1,0,0,"OPFOR",""', '1,0,0,"Civilian","nonexistent"',
])
def test_invalid_requests_do_not_clear_or_create_patients(args):
    execute(request_setup() + f'''
        private _accepted = [_object,_location,_initiator,{args},[7,99]] call _request;
        [!_accepted && {{count _spawns == 0}}, "invalid case mutated patients"] call _check;
    ''')


def apply_setup():
    s = source('applyPatientPreset').replace('_patient addGoggles "G_AirPurifyingRespirator_01_F";', '_goggles = "G_AirPurifyingRespirator_01_F";')
    return catalog() + '''
        private _calls = [];
        private _goggles = "";
        private _state = [1,1,0.25,0,0,0,1,1,1];
        ACM_mission_fnc_spawnCustomPatient = {_calls pushBack ["custom",_this];};
        ACM_airway_fnc_setAirwayState = {_calls pushBack ["airway",_this];};
        ACM_breathing_fnc_setChestInjuryState = {_calls pushBack ["chest",_this];};
        ACM_breathing_fnc_setRuntimeState = {_calls pushBack ["breathing",_this];};
        ACM_breathing_fnc_handleHemothorax = {_calls pushBack ["hemo",_this];};
        ACM_breathing_fnc_updateLungState = {};
        ACME_fnc_ptxInjury = {_calls pushBack ["ptxInjury",_this];};
        ACME_fnc_ptxEnsure = {+_state};
        ACME_fnc_ptxPublish = {_calls pushBack ["ptxPublish",_this];};
        ACME_fnc_zeusTBIApplyLocal = {_calls pushBack ["tbi",_this];};
        ACME_fnc_blastLungInflict = {_calls pushBack ["blast",_this];};
        ACM_CBRN_fnc_seedTrainingExposure = {_calls pushBack ["chemical",_this];};
        private _apply = {''' + adapt(s, component='mission') + '''};
    '''


@pytest.mark.parametrize('case,endpoint', [
    ('tbi_moderate','tbi'),('tbi_severe','tbi'),('tbi_herniation','tbi'),
    ('blast_mild','blast'),('blast_severe','blast'),('simple_ptx','ptxInjury'),
    ('hemothorax','hemo'),('massive_htx','hemo'),('airway','custom'),('fracture','custom'),
])
def test_case_uses_real_clinical_endpoint_and_reuses_existing_patient(case,endpoint):
    execute(apply_setup() + f'''
        private _preset = ["{case}"] call ACM_mission_fnc_patientPreset;
        [_patient,_preset,missionNamespace] call _apply;
        [(_calls findIf {{(_x select 0) == "{endpoint}"}}) >= 0, "case did not seed target disease"] call _check;
        [(_calls select 0 select 1 select 6) isEqualTo _patient, "custom wound code creates a second patient"] call _check;
        private _before = count _calls;
        [_patient,_preset,missionNamespace] call _apply;
        [count _calls == _before, "case seeded twice"] call _check;
    ''')


def test_tension_case_sets_canonical_pressure_not_only_native_display_flag():
    execute(apply_setup() + '''
        [_patient,["tension_ptx"] call ACM_mission_fnc_patientPreset,missionNamespace] call _apply;
        private _idx = _calls findIf {(_x select 0) == "ptxPublish"};
        private _args = _calls select _idx select 1;
        [(_args select 1 select 1) == 4 && {(_args select 1 select 4) == 1} && {_args select 2}, "no active canonical tension"] call _check;
    ''')


@pytest.mark.parametrize('case,hazard,dose', [('cbrn_cs','Chemical_CS',30),('cbrn_chlorine','Chemical_Chlorine',25),('cbrn_sarin','Chemical_Sarin',40),('cbrn_sarin_severe','Chemical_Sarin',80)])
def test_every_cbrn_case_has_mask_and_absorbed_dose(case,hazard,dose):
    execute(apply_setup() + f'''
        [_patient,["{case}"] call ACM_mission_fnc_patientPreset,missionNamespace] call _apply;
        [_goggles == "G_AirPurifyingRespirator_01_F", "CBRN patient missing respirator"] call _check;
        private _idx = _calls findIf {{(_x select 0) == "chemical"}};
        private _args = _calls select _idx select 1;
        [(_args select 1) == "{hazard}" && {{(_args select 2) == {dose}}}, "wrong absorbed exposure"] call _check;
    ''')


def test_native_cbrn_seeding_starts_elimination_without_environmental_zone():
    s = (ROOT/'addons/cbrn/functions/fnc_seedTrainingExposure.sqf').read_text()
    execute('''
        private _hazards = [];
        ACM_CBRN_fnc_initHazardUnit = {_hazards pushBack _this;};
        ACM_CBRN_fnc_updateExposureEffects = {};
        private _seed = {''' + adapt(s, component='CBRN') + '''};
        [_patient,"Chemical_Sarin",80] call _seed;
        [_patient getVariable ["ACM_CBRN_chemical_sarin_Buildup",0] == 80, "absorbed dose missing"] call _check;
        [_patient getVariable ["ACM_CBRN_chemical_sarin_WasExposed",false], "past exposure missing"] call _check;
        [count _hazards == 1, "native hazard elimination not enrolled"] call _check;
    ''')
    assert 'initHazardZone' not in s
    native = (ROOT/'addons/cbrn/functions/fnc_initHazardUnit.sqf').read_text()
    assert 'private _buildup = _patient getVariable [_buildupVarString, 0];' in native
    assert '_buildup = (_buildup + (_eliminationRate * _decreaseModifier)) max 0;' in native


def test_classes_and_completion_marker_preserve_faction_equipment_at_creation():
    config = (ROOT/'addons/mission/CfgVehicles.hpp').read_text()
    military = config.split('class GVAR(TrainingPatient): B_Survivor_F {',1)[1].split('\n    };',1)[0]
    civilian = config.split('class GVAR(TrainingCivilian): C_man_1 {',1)[1].split('\n    };',1)[0]
    assert 'linkedItems[] = {"V_PlateCarrier1_rgr"};' in military
    assert 'linkedItems[] = {};' in civilian
    s = source('generatePatient')
    assert s.index('"ACME_acmSpawnerPlateCarrierDone", true, true') < s.index('call FUNC(applyPatientPreset)')
    assert 'createUnit [QGVAR(TrainingCivilian)' in s
    assert 'createUnit [QGVAR(TrainingPatient)' in s
    assert 'addVest' not in s
    assert '_patient setVariable ["ACME_spawnSeverity", _severity, true];' in s


def test_precise_cases_skip_random_mechanism_injuries_and_native_generator_remains():
    s = source('generatePatient')
    assert s.index('if (_preset isNotEqualTo []) exitWith') < s.index('call ACEFUNC(medical,addDamageToUnit)')
    assert '_type == 0' in s and '_severity == 0' in s
    custom = source('spawnCustomPatient')
    assert 'private _patient = _existingPatient;' in custom
    assert 'if (isNull _patient) then {' in custom
    assert 'if (isNull _patient || {!local _patient}) exitWith {objNull};' in custom


def test_new_functions_registered_under_native_components():
    prep = (ROOT/'addons/mission/XEH_PREP.hpp').read_text()
    for name in ('patientPreset','applyPatientPreset','requestTrainingPatient'):
        assert prep.count(f'PREP({name});') == 1
    assert (ROOT/'addons/cbrn/XEH_PREP.hpp').read_text().count('PREP(seedTrainingExposure);') == 1
    assert 'call CBA_fnc_serverEvent' in source('requestTrainingPatient')
    assert 'call CBA_fnc_globalEvent' not in source('requestTrainingPatient')


def test_new_precise_airway_case_is_not_reapplied_by_legacy_delayed_callback():
    execute(apply_setup() + '''
        [_patient,["airway"] call ACM_mission_fnc_patientPreset,missionNamespace] call _apply;
        [(_calls select 0 select 1 select 4) isEqualTo [0,0], "delayed custom airway seed remains armed"] call _check;
        private _idx = _calls findIf {(_x select 0) == "airway"};
        [(_calls select _idx select 1 select 1) isEqualTo [["vomit",0.8],["collapse",0.6]], "airway was not seeded immediately"] call _check;
    ''')


@pytest.mark.parametrize('case,unconscious', [('abrasions','false'),('fracture','false'),('airway','true')])
def test_low_acuity_cases_do_not_force_unconsciousness(case,unconscious):
    execute(apply_setup() + f'''
        [_patient,["{case}"] call ACM_mission_fnc_patientPreset,missionNamespace] call _apply;
        [(_calls select 0 select 1 select 7) isEqualTo {unconscious}, "case has wrong initial consciousness"] call _check;
    ''')


def test_blufor_and_civilian_both_retain_junctional_caps_before_wounds():
    s = (ROOT/'addons/acm_extended/functions/fn_junctionalRollSpawn.sqf').read_text()
    assert 'ACM_mission_TrainingCasualtyGroup' in s
    assert 'ACM_mission_TrainingBluforGroup' in s
    assert '_cap = [2, 4] select (_sev >= 4);' in s
    s = source('generatePatient')
    resolved = s.index('// Stamp the resolved triage tier')
    assert resolved < s.index('call ACEFUNC(medical,addDamageToUnit)')
    assert 'ACME_trainingSpawnFinalize' in s
    assert '_cap = 1;' in (ROOT/'addons/acm_extended/functions/fn_junctionalRollSpawn.sqf').read_text()
