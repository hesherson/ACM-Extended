/* Provider-local custody return, also used after Stop All / access removal. The
 * public owner certificate binds this one device to this recipient and deadline. */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_lineWarmerReturn;};
    _result
};
params ["_patient", "_medic", "_id", "_issued", ["_attempt", 0, [0]]];
if (isNull _patient || {isNull _medic} || {_id == ""}
    || {!(_issued isEqualType 0)} || {!finite _issued} || {serverTime - _issued > 30} || {_issued > serverTime + 2}) exitWith {false};
if (!local _medic) exitWith {
    if (_attempt < 4) then {["ACME_lineWarmerReturn", [_patient, _medic, _id, _issued, _attempt + 1], _medic] call CBA_fnc_targetEvent;};
    false
};
private _certificate = (_patient getVariable ["ACME_lineWarmerReturns", createHashMap]) getOrDefault [_id, []];
if !(_certificate isEqualTo [_medic, _issued]) exitWith {
    // Object-state replication and the targeted ACK are allowed to arrive in
    // either order. The owner reconciliation tick also retries after migration.
    if (_attempt < 20) then {
        [{_this call ACME_fnc_lineWarmerReturn;}, [_patient, _medic, _id, _issued, _attempt + 1], 0.1] call CBA_fnc_waitAndExecute;
    };
    false
};
private _seen = _medic getVariable ["ACME_lineWarmerReturned", createHashMap];
if (_id in _seen) exitWith {false};
_seen set [_id, serverTime];
// Custody IDs are unique for this unit's lifetime. This follows the physical
// provider through locality changes and also rejects arbitrarily delayed copies.
_medic setVariable ["ACME_lineWarmerReturned", _seen, true];
[_medic, "ACME_BloodWarmer"] call ace_common_fnc_addToInventory;
uiNamespace setVariable ["ACME_lineWarmerSupplyCache", []];
true
