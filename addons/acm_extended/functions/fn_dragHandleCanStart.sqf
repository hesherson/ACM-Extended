// Experimental drag handles are available only in HEMTT dev/launch builds.
if (getNumber (configFile >> "CfgPatches" >> "ACM_Extended" >> "acme_developmentBuild") != 1) exitWith {false};
// Can this medic attach the hands-free ACME drag handle to this casualty?
params [["_medic",objNull,[objNull]],["_patient",objNull,[objNull]]];
if (isNull _medic || {isNull _patient} || {_medic isEqualTo _patient}) exitWith {false};
if !(missionNamespace getVariable ["ACME_dragHandle_enabled",true]) exitWith {false};
if !(_patient isKindOf "CAManBase") exitWith {false};
if (!alive _medic || {!alive _patient}) exitWith {false};
if (!(isNull (objectParent _medic)) || {!(isNull (objectParent _patient))}) exitWith {false};
if (_medic getVariable ["ACE_isUnconscious",false]) exitWith {false};
if !((_patient getVariable ["ACE_isUnconscious",false]) || {lifeState _patient == "INCAPACITATED"}) exitWith {false};

private _attachDist = missionNamespace getVariable ["ACME_dragHandle_attachDistance",2.3];
if ((_medic distance _patient) > _attachDist) exitWith {false};

if (_patient getVariable ["ACME_dragHandle_active",false]) exitWith {false};
if (_medic getVariable ["ACME_dragHandle_pending",false]) exitWith {false};
if (!isNull (_medic getVariable ["ACME_dragHandle_patient",objNull])) exitWith {false};

// Do not race ACE's attached drag/carry implementation in either direction.
if (_patient call ace_common_fnc_isBeingDragged) exitWith {false};
if (_patient call ace_common_fnc_isBeingCarried) exitWith {false};
if (_medic getVariable ["ace_dragging_isDragging",false]) exitWith {false};
if (_medic getVariable ["ace_dragging_isCarrying",false]) exitWith {false};

// Head elevation is deliberately allowed: the owner start function tears it down through the same transport
// lifecycle as ACE dragging. Any other attachment means another system owns the casualty's transform.
if (!(isNull (attachedTo _patient)) && {!(_patient getVariable ["ACME_headElevated",false])}) exitWith {false};

// A modal patient-animation lease means somebody is actively doing a procedure that owns the casualty pose.
private _lock = _patient getVariable ["ACME_patientAnimLock",[]];
if ((count _lock) >= 5 && {(_lock param [4,-1]) > CBA_missionTime}) exitWith {false};

if (!isNil "ace_common_fnc_canInteractWith") then {
    if !([_medic,_patient,[]] call ace_common_fnc_canInteractWith) exitWith {false};
};

true
