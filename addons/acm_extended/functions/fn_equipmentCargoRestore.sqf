/* Restore only into already populated, verified native cargo. Never repopulate on retry:
 * a rejected asynchronous ledger enqueue retains its exact funding journal on that object. */
params ["_container","_tree",["_depth",0]];
if (isNull _container || {!local _container} || {!([_tree,_depth] call ACME_fnc_equipmentCargoValid)}) exitWith {false};
private _receipt = _container getVariable ["ACME_equipmentCargoRestoreReceipt",""];
private _key = str _tree;
if (_receipt == _key) exitWith {true};
if ((_container getVariable ["ACME_equipmentCargoRestoreKey",""]) != _key
    && {!([_tree select 0,[_container] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual)}) exitWith {false};
// Resolve child objects before changing their native token tuples. Engine cargo ordering is unspecified.
private _actualChildren = +(everyContainer _container);
private _plan = [];
private _valid = true;
{
    private _spec = ((_tree select 0) select 3) select _forEachIndex;
    private _childTree = _x;
    private _index = _actualChildren findIf {(_x select 0) == (_spec select 0) && {
        [_childTree select 0,[_x select 1] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual
        || {((_x select 1) getVariable ["ACME_equipmentCargoRestoreKey",""]) == str _childTree}
    }};
    if (_index < 0) exitWith {_valid = false;};
    private _child = (_actualChildren deleteAt _index) select 1;
    _plan pushBack [_child,_childTree,_depth + 1];
} forEach (_tree select 3);
if (!_valid || {count _actualChildren != 0}) exitWith {false};
_container setVariable ["ACME_equipmentCargoRestoreKey",_key,false];
private _ok = [_container,_tree select 1] call ACME_fnc_inventoryRestore;
if !([_container,_tree select 2,0] call ACME_fnc_coolerRestore) then {_ok = false;};
{if !(_x call ACME_fnc_equipmentCargoRestore) then {_ok = false;};} forEach _plan;
// An accepted enqueue is not an inventory grant. The holder must remain alive
// until exact native tuples and settled metadata are visible on its owner.
private _inventoryNow = [_container] call ACME_fnc_inventorySnapshot;
private _coolersNow = [_container,"holder"] call ACME_fnc_coolerSnapshot;
if (_inventoryNow isEqualTo [] || {_coolersNow isEqualTo []}) then {_ok = false;} else {
    if (count (_inventoryNow select 1) != count ((_tree select 1) select 1)
        || {count (_coolersNow select 2) != count ((_tree select 2) select 2)}) then {_ok = false;};
};
if (_ok) then {_container setVariable ["ACME_equipmentCargoRestoreReceipt",_key,false];};
_ok
