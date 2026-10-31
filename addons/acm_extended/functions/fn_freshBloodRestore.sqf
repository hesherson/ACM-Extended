/* Server startup import BEFORE loading saved bags or allowing new collection.
 * IDs are part of configured native classes. Refuse to overwrite a live donor
 * registry rather than alias its current blood with a different saved donor. */
if (!isServer) exitWith {false};
params ["_snapshot",["_offline",0,[0]]];
if (!([_snapshot] call ACME_fnc_freshBloodSnapshotValid)
    || {!finite _offline} || {_offline < 0} || {_offline > 1e9}) exitWith {false};
private _key = str _snapshot;
private _receipt = missionNamespace getVariable ["ACME_freshBloodRestoreReceipt",[]];
if (_receipt isEqualTo [_key,_offline]) exitWith {true};
private _grants = missionNamespace getVariable ["ACM_circulation_FreshBloodGrants",createHashMap];
if !(_grants isEqualType createHashMap) exitWith {false};
if ((values _grants findIf {(_x param [5,""]) != "delivered"}) >= 0) exitWith {false};
private _registry = missionNamespace getVariable ["ACM_circulation_FreshBloodList",createHashMap];
if !(_registry isEqualType createHashMap) exitWith {false};
// ID zero is the mission's compatibility seed, not an allocated native donor.
if ((keys _registry findIf {!(_x isEqualTo 0)}) >= 0) exitWith {false};
private _plan = createHashMap;
{
    _x params ["_id","_donor","_volume","_type","_alive","_age"];
    _plan set [_id,[_donor,false] call ACME_fnc_clinicalCodec];
    _plan set [_id,[_plan get _id,_volume,_type,_alive,CBA_missionTime - _age - _offline]];
} forEach (_snapshot select 1);
// Preserve the compatibility seed if the historical snapshot omitted it.
if (!(0 in _plan) && {0 in _registry}) then {_plan set [0,+(_registry get 0)];};
if !([_plan] call ACM_circulation_fnc_restoreFreshBloodRegistry) exitWith {false};
missionNamespace setVariable ["ACME_freshBloodRestoreReceipt",[_key,_offline]];
true
