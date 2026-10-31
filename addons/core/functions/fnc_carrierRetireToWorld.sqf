#include "..\script_component.hpp"
/* B267: retire ONE removed carrier without touching the new worn loadout.
 * Live supplies stay in the SAME ground inventory: no copy, refill or loss of
 * container metadata. The old wearable shell is made separately recoverable.
 * If the engine refuses that shell, retain the prop and full recovery record.
 * Only the patient owner may perform the initial custody handoff.
 */
params ["_patient", "_cargo", "_savedVar", "_saved", ["_props", []]];
if (isNull _patient || {!local _patient} || {count _saved != 2}) exitWith {objNull};
private _class = _saved param [0, "", [""]];
if (_class == "") exitWith {objNull};
if (!isNull _cargo && {
    !((_cargo getVariable ["ACME_carrierPatient", objNull]) isEqualTo _patient)
    || {(_cargo getVariable ["ACME_carrierSavedVar", ""]) != _savedVar}
}) exitWith {objNull};

// The verified physical holder is authoritative even if an older/missing
// bookkeeping flag disagrees. Never refill it from a historical snapshot.
private _hadLive = !isNull _cargo || {_patient getVariable [_savedVar + "Live", false]};
private _legacySnapshot = [[], [], [], []];
if (!_hadLive) then {
    ([_saved] call ACM_core_fnc_carrierLegacySnapshot) params ["_valid", "_decoded"];
    if (_valid) then {_legacySnapshot = _decoded;} else {_legacySnapshot = [];};
};
if (_legacySnapshot isEqualTo []) exitWith {objNull};
private _archive = _cargo;
if (isNull _archive) then {
    _archive = createVehicle ["GroundWeaponHolder_Scripted", getPosATL _patient, [], 0, "CAN_COLLIDE"];
};
if (isNull _archive) exitWith {objNull};
if (!_hadLive) then {
    // This is the first materialization of a validated legacy snapshot, NOT
    // a fallback for destroyed live inventory. Verify every item/ammo once.
    [_archive, _legacySnapshot] call ACME_fnc_carrierCargoPopulate;
};
if (!_hadLive && {!([_legacySnapshot, [_archive] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual)}) exitWith {
    deleteVehicle _archive;
    objNull
};
// Publish recovery evidence before detaching it from the patient. The live
// holder remains independently lootable if the patient later despawns.
_archive setVariable ["ACME_carrierRetiredRecord", [_savedVar, +_saved,
    _patient getVariable ["ACME_equipmentKitEpoch", 0], +_props, _hadLive], true];
_archive setVariable ["ACME_carrierRetired", true, true];
_archive setVariable ["ACME_carrierPatient", objNull, true];
_archive setVariable ["ACME_carrierClosing", false, true];

// Detach an old carrier support prop before its patient moves again. If the
// new wearable shell fails, this visual and the recovery record both survive.
{if (!isNull _x) then {detach _x;};} forEach _props;
// A destroyed live box stays empty: its old inventory snapshot is evidence,
// not spare supplies. Only the still-owned empty carrier shell is returned.
private _shell = createVehicle ["GroundWeaponHolder_Scripted", getPosATL _archive, [], 0, "CAN_COLLIDE"];
private _shellOK = false;
if (!isNull _shell) then {
    _shell addItemCargoGlobal [_class, 1];
    // The newly created holder contains exactly one empty vest container.
    private _expected = [[], [], [], [[_class, false, [[], [], [], []]]]];
    _shellOK = [_expected, [_shell] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual;
    if (_shellOK) then {
        _archive setVariable ["ACME_carrierRetiredShell", _shell, true];
        _archive setVariable ["ACME_carrierRetiredShellCreated", true, true];
        {if (!isNull _x) then {deleteVehicle _x;};} forEach _props;
    } else {
        deleteVehicle _shell;
    };
};
if (!_shellOK) then {
    diag_log format ["[ACME CARRIER B267] retired carrier recovery retained; class=%1 shell=%2 live=%3 archive=%4",
        _class, _shellOK, _hadLive, netId _archive];
};
_archive
