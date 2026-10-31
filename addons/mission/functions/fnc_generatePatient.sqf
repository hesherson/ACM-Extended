#include "..\script_component.hpp"
/*
 * Author: Blue
 * Spawn patient
 *
 * Arguments:
 * 0: Interaction Object <OBJECT>
 * 1: Spawn Reference Object <OBJECT>
 * 2: Initiator Unit <OBJECT>
 * 3: Severity Preset <NUMBER>
 * 4: Injury Type <NUMBER>
 * 5: Single Patient Spawning <BOOL>
 *
 * Return Value:
 * Patient <OBJECT>
 *
 * Example:
 * [_object, _location, player, 0, 0, true] call ACM_mission_fnc_generatePatient;
 *
 * Public: No
 */

params ["_object", "_location", "_initiator", "_severity", "_type", ["_singlePatient", true], ["_faction", "BLUFOR"], ["_presetID", ""]];

private _preset = [_presetID] call FUNC(patientPreset);
if (_presetID == "") then {_preset = [];};
if (_preset isNotEqualTo []) then {_severity = _preset select 2;};

private _acmeRequestedSeverity = _severity;
missionNamespace setVariable ["ACME_pendingSpawnSeverity", _acmeRequestedSeverity];

if (_singlePatient) then {
    [_object] call FUNC(clearPatients);
};

private _fnc_generateWounds = {
    params ["_type", "_severity", ["_multiplier", 1]];

    private _targetPart = "body";
    private _mechanism = "";
    private _damageAmount = _multiplier;

    if (_type == 0) then { // Random
        _type = switch (_severity) do {
            case 1: {[1,2,5,6] select (round (random 3))};
            case 2: {[1,2,3,4] select (round (random 3))};
            case 3: {[1,3] select (round (random 1))};
            case 4: {[1,2,3] select (round (random 2))};
        };
    };

    _targetPart = ALL_BODY_PARTS select (round (random 5));

    switch (_type) do {
        case 1: { // Gunshot
            _mechanism = "bullet";
        };
        case 2: { // Shrapnel
            _mechanism = "grenade";
        };
        case 3: { // Explosion
            _mechanism = "explosive";
        };
        case 4: { // Collision
            _mechanism = "collision";
            _targetPart = "body";
        };
        case 5: { // Falling
            _mechanism = "falling";
            _targetPart = ALL_BODY_PARTS select (4 + (round (random 1)));
        };
        case 6: { // Backblast
            _mechanism = "backblast";
        };
    };

    [_targetPart,_mechanism,_damageAmount];
};

private _patient = objNull;
if (_faction == "Civilian") then {
    _patient = GVAR(TrainingCasualtyGroup) createUnit [QGVAR(TrainingCivilian), position _location, [], 0, "FORM"];
} else {
    // Keep the legacy group contract for mission scripts; explicit UI requests
    // use the server's west-side group and the same carrier-equipped unit class.
    private _group = missionNamespace getVariable [QGVAR(TrainingBluforGroup), GVAR(TrainingCasualtyGroup)];
    _patient = _group createUnit [QGVAR(TrainingPatient), position _location, [], 0, "FORM"];
};
if (isNull _patient || {!local _patient}) exitWith {
    missionNamespace setVariable ["ACME_pendingSpawnSeverity", -1];
    objNull
};

// The unit class supplies its carrier during creation. Mark the legacy armor
// watcher complete before any treatment can remove the carrier intentionally.
_patient setVariable ["ACME_acmSpawnerPlateCarrierDone", true, true];
_patient setVariable ["ACME_patientSpawnerVestClass", vest _patient, true];
_patient setVariable ["ACME_trainingCrouchOnly",true,true];
[_patient] call FUNC(trainingPatientHold);
_patient setVariable [QGVAR(PatientFaction), _faction, true];

if (_preset isNotEqualTo []) exitWith {
    [_patient, _preset, _location] call FUNC(applyPatientPreset);
    if (_singlePatient) then {_object setVariable [QGVAR(ActivePatients), [_patient], true];};
    missionNamespace setVariable ["ACME_pendingSpawnSeverity", -1];
    _patient setVariable ["ACME_spawnSeverity", _severity, true];
    _patient
};

_patient disableAI "MOVE";

removeAllWeapons _patient;
removeAllItems _patient;
removeAllAssignedItems _patient;
removeGoggles _patient;

_patient setVariable [QACEGVAR(medical_statemachine,AIUnconsciousness), true, true];

[_patient, true, 30] call ACEFUNC(medical,setUnconscious);

_patient setVariable [QEGVAR(damage,InstantDeathImmune), true, true];

private _injuryArray = [];
_patient setVariable ["ACME_trainingSpawnInProgress", true, false];

if (_severity == 0) then { // Random
    _severity =  1 + (round (random 3));
};
// Stamp the resolved triage tier before synchronous wound hooks, including random Priority.
_patient setVariable ["ACME_spawnSeverity", _severity, true];

private _damageMultiplier = 1;

private _woundCount = 2;

switch (_severity) do {
    case 1: { // Routine
        _damageMultiplier = random [1,1.25,1.5];
        _woundCount = round (random [2,2,3]);
    };
    case 2: { // Priority
        _damageMultiplier = random [2.5,3,4];
        _woundCount = round (random [3,4,5]);
    };
    case 3: { // Immediate
        _damageMultiplier = random [3.5,4,5];
        _woundCount = round (random [5,6,7]);
    };
    case 4: { // Expectant
        _damageMultiplier = random [7,8,9];
        _woundCount = round (random [7,8,10]);
    };
};

for "_i" from 1 to _woundCount do {
    _injuryArray pushBack ([_type, _severity, _damageMultiplier] call _fnc_generateWounds);
};

{
    _x params ["_targetPart", "_mechanism", "_damageAmount"];

    [_patient, _damageAmount, _targetPart, _mechanism, objNull] call ACEFUNC(medical,addDamageToUnit);
} forEach _injuryArray;

// Evaluate Priority only after ALL random hits have settled, not at the first hit.
_patient setVariable ["ACME_trainingSpawnFinalize", true, false];
if (_severity == 2) then {
    [_patient, _patient getVariable ["ace_medical_openWounds", createHashMap]] call ACME_fnc_junctionalRollSpawn;
};
_patient setVariable ["ACME_trainingSpawnInProgress", false, false];
_patient setVariable ["ACME_trainingSpawnFinalize", false, false];

if (_singlePatient) then {
    _object setVariable [QGVAR(ActivePatients), [_patient], true];
};

missionNamespace setVariable ["ACME_pendingSpawnSeverity", -1];
_patient setVariable ["ACME_spawnSeverity", _severity, true];
_patient;
