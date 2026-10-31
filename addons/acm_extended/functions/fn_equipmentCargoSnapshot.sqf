/* Restart-safe removed-carrier cargo: native contents and each container's opaque ledgers.
 * This tree belongs to the patient checkpoint; do not also save its holder independently. */
if (canSuspend) exitWith {private _result = []; isNil {_result = _this call ACME_fnc_equipmentCargoSnapshot;}; _result};
params ["_container",["_depth",0]];
if (isNull _container || {_depth > 8}) exitWith {[]};
if (!local _container) exitWith {[]};
private _native = [_container] call ACME_fnc_carrierCargoSnapshot;
// This versioned tree carries opaque preparations and coolers, but no loose-
// blood exposure ledger. Refuse instead of exporting a silently freshened bag.
if (((_native select 0) findIf {([_x] call ACME_fnc_coolerBagVolume) > 0}) >= 0) exitWith {[]};
// Gear can place a carrier inside a nested pouch without changing the unit's
// top-level projection. Enroll the real physical holder before checkpointing.
private _tracked = missionNamespace getVariable ["ACME_inventoryTracked",[]];
_tracked pushBackUnique _container;
missionNamespace setVariable ["ACME_inventoryTracked",_tracked];
[_container] call ACME_fnc_inventoryLedgerReconcile;
private _inventory = [_container] call ACME_fnc_inventorySnapshot;
private _coolers = [_container,"holder"] call ACME_fnc_coolerSnapshot;
if (_inventory isEqualTo [] || {_coolers isEqualTo []}) exitWith {[]};
private _children = [];
private _ok = true;
{
    private _child = [_x select 1,_depth + 1] call ACME_fnc_equipmentCargoSnapshot;
    if (_child isEqualTo []) exitWith {_ok = false;};
    _children pushBack _child;
} forEach everyContainer _container;
if (!_ok || {!([_native,[_container] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual)}) exitWith {[]};
private _tree = [_native,_inventory,_coolers,_children];
if !([_tree,_depth] call ACME_fnc_equipmentCargoValid) exitWith {[]};
_tree
