#include "..\script_component.hpp"
/* B267: equipment-only boundary after an intentional patient kit replacement.
 * Retire old carrier callbacks and preserve physical inventory independently;
 * never restore old gear into the new kit, copy clinical state or heal wounds.
 * The caller has already advanced ACME_equipmentKitEpoch on the unit owner.
 */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {false};
private _contexts = ["ACME_chestAccess_vestLoadout", "ACME_CS_vestLoadout", "ACME_headElev_vestLoadout"];
private _propVars = ["ACME_chestAccess_vestProp", "ACME_CS_vestProp", "ACME_headElev_propObj"];
private _cargo = _patient getVariable ["ACME_carrierCargo", objNull];
private _savedVar = if (isNull _cargo) then {""} else {_cargo getVariable ["ACME_carrierSavedVar", ""]};
private _saved = _patient getVariable [_savedVar, []];
private _props = [];
private _hasSaved = false;
private _records = [];
{
    private _record = _patient getVariable [_x, []];
    if (count _record == 2 && {!(_patient getVariable [_x + "Settled", false])}) then {
        _hasSaved = true;
        _records pushBack [_x, +_record];
        // Pre-B267 records lacked an equipment stamp. Even archive failure
        // must leave them unable to overwrite an intentionally newer kit.
        if (isNil {_patient getVariable (_x + "KitEpoch")}) then {
            _patient setVariable [_x + "KitEpoch", (_patient getVariable ["ACME_equipmentKitEpoch", 0]) - 1, true];
        };
        if (_savedVar == "") then {_savedVar = _x; _saved = +_record;};
        private _prop = _patient getVariable [_propVars select _forEachIndex, objNull];
        if (!isNull _prop) then {_props pushBackUnique _prop;};
    };
} forEach _contexts;

// An extant box without a matching unsettled vest record is ambiguous.
// Retain the object and its metadata rather than orphaning/deleting it.
if (!isNull _cargo && {!_hasSaved}) exitWith {false};
if (count _records > 1 && {
    !(_patient getVariable ["ACME_headElev_manualCarrierBorrowed", false])
    || {count _records != 2}
    || {((_records select 0) select 0) != "ACME_chestAccess_vestLoadout"}
    || {((_records select 1) select 0) != "ACME_headElev_vestLoadout"}
    || {((_records select 0) select 1) isNotEqualTo ((_records select 1) select 1)}
}) exitWith {false};
// One shared live holder is authoritative, including manual-carrier support
// borrowed by Semi-Fowler. Borrowed aliases do NOT produce another shell.
private _archived = !_hasSaved;
if (_hasSaved) then {
    private _archive = [_patient, _cargo, _savedVar, _saved, _props] call ACM_core_fnc_carrierRetireToWorld;
    // Keep ambiguous/corrupt custody intact rather than clearing its evidence.
    if (isNull _archive) exitWith {};
    _archived = true;
    _patient setVariable ["ACME_carrierCargo", objNull, true];
};
// A failed archive must not lose the only remaining recovery record. Epoch
// checks already prevent its old contents being returned to the new loadout.
if (!_archived) exitWith {false};

// Cancel only carrier animation ownership. CPR/BVM/seizures and other patient
// controllers retain their own tokens; no generic animation reset is used.
{
    private _busy = _patient getVariable [_x, ""];
    if (_busy != "") then {[_patient, _busy] call ACME_fnc_patientAnimRelease;};
    _patient setVariable [_x, "", false];
} forEach ["ACME_chestAccess_vestBusy", "ACME_CS_vestBusy"];
{
    private _id = _patient getVariable [_x, -1];
    if (_id isEqualType 0 && {_id >= 0}) then {[_id] call CBA_fnc_removePerFrameHandler;};
    _patient setVariable [_x, -1, false];
} forEach ["ACME_chestAccess_vestPFH", "ACME_CS_vestPFH"];
private _hadSupport = _patient getVariable ["ACME_headElev_vestRemoved", false];
{
    _patient setVariable [_x, [], true];
    _patient setVariable [_x + "Live", false, true];
    _patient setVariable [_x + "Settled", true, true];
    _patient setVariable [_x + "KitEpoch", -1, true];
} forEach _contexts;
{_patient setVariable [_x, objNull, true];} forEach ["ACME_chestAccess_vestProp", "ACME_CS_vestProp"];
if (_hadSupport) then {
    _patient setVariable ["ACME_headElev_propObj", objNull, true];
    _patient setVariable ["ACME_headElev_vestRemoved", false, true];
    _patient setVariable ["ACME_headElev_manualCarrierBorrowed", false, true];
    _patient setVariable ["ACME_headElev_propVest", "", true];
    _patient setVariable ["ACME_headElev_propVestItems", [], true];
};
_patient setVariable ["ACME_chestAccess_frontBusy", "", false];
_patient setVariable ["ACME_CS_frontBusy", "", false];
[_patient, keys (_patient getVariable ["ACME_chestAccess_leases", createHashMap])]
    call ACME_fnc_chestAccessLeaseRetire;
_patient setVariable ["ACME_chestAccess_leases", createHashMap, true];
_patient setVariable ["ACME_chestAccess_requestToken", "", true];
_patient setVariable ["ACME_chestAccess_readyLease", "", true];
_patient setVariable ["ACME_chestAccess_readyServer", -1, true];
_patient setVariable ["ACME_CS_vestReadyServer", -1, true];
_patient setVariable ["ACME_Thora_ChestAccessActive", false, true];

// End membership, not completed chest treatment. Late Begin retries are
// rejected by the existing bounded tombstones, even before client UI closes.
private _closed = +(_patient getVariable ["ACME_CS_ClosedTokens", []]);
_closed = _closed select {(_x param [1, 0]) > serverTime};
{
    private _token = _x;
    if ((_closed findIf {(_x param [0, ""]) == _token}) < 0) then {_closed pushBack [_token, serverTime + 180];};
} forEach (_patient getVariable ["ACME_CS_ProcedureTokens", []]);
if (count _closed > 64) then {_closed deleteRange [0, count _closed - 64];};
_patient setVariable ["ACME_CS_ClosedTokens", _closed, true];
_patient setVariable ["ACME_CS_ProcedureTokens", [], true];
_patient setVariable ["ACME_CS_PreparationToken", "", true];
_patient setVariable ["ACME_CS_ProcedureActive", false, true];
_patient setVariable ["ACME_CS_ProcedureGeneration", 1 + (_patient getVariable ["ACME_CS_ProcedureGeneration", 0]), true];
_patient setVariable ["ACME_CS_ProcedureReadyAt", -1, true];
_patient setVariable ["ACME_manualPlateCarrierState", "", true];
_patient setVariable ["ACME_manualPlateCarrierLease", "", true];
_patient setVariable ["ACME_manualPlateCarrierProvider", objNull, true];
_patient setVariable ["ACME_manualPlateCarrierRemoved", false, true];
_patient setVariable ["ACME_manualPlateCarrierStartedAt", -1, true];
["ACME_manualPlateCarrierTrack", [_patient]] call CBA_fnc_localEvent;
// Fence both pending head-elevation start and delayed lowering callbacks.
_patient setVariable ["ACME_headElev_startEpoch", 1 + (_patient getVariable ["ACME_headElev_startEpoch", 0]), false];
if (_hadSupport && {_patient getVariable ["ACME_headElevated", false]}) then {
    [objNull, _patient, true, true] call ACME_fnc_headElevateStop;
};
true
