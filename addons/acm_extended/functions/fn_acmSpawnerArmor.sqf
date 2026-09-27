// Compatibility armor repair for unmarked legacy/external ACM training casualties.
// The fork's patient spawners create an armored unit class and mark the watcher
// complete immediately; they do not depend on this post-spawn fallback.
params ["_patient"];

if (!(missionNamespace getVariable ["ACME_acmSpawnerPlateCarrierEnabled", true])) exitWith {};
if (isNull _patient) exitWith {};
// Recheck on the owner too: a request queued before Done replicated can arrive
// after a treatment deliberately removed the already-equipped carrier.
if (_patient getVariable ["ACME_acmSpawnerPlateCarrierDone", false]) exitWith {};
if (!alive _patient) exitWith {};
if (isPlayer _patient) exitWith {};
if (!local _patient) exitWith {
    ["ACME_acmSpawnerArmorLocal", [_patient], _patient] call CBA_fnc_targetEvent;
};

private _grp = missionNamespace getVariable ["ACM_mission_TrainingCasualtyGroup", grpNull];
if (isNull _grp) exitWith {};
if ((group _patient) != _grp) exitWith {};

private _vestClass = missionNamespace getVariable ["ACME_acmSpawnerPlateCarrierClass", "V_PlateCarrier1_rgr"];
if !(isClass (configFile >> "CfgWeapons" >> _vestClass)) exitWith {
    if !(_patient getVariable ["ACME_acmSpawnerPlateCarrierBadClassLogged", false]) then {
        _patient setVariable ["ACME_acmSpawnerPlateCarrierBadClassLogged", true, false];
    };
};

// if another script intentionally gave the patient a vest already, preserve it.
if ((vest _patient) isEqualTo "") then {
    _patient addVest _vestClass;
};

_patient setVariable ["ACME_acmSpawnerPlateCarrierDone", true, true];
