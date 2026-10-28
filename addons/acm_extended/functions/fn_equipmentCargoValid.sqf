/* Validate the entire bounded cargo tree before creating or changing an object. */
params ["_tree",["_depth",0]];
if (isNil "_tree" || {_depth > 8}) exitWith {false};
if !(_tree isEqualType [] && {count _tree == 4}) exitWith {false};
if (([0,1,2,3] findIf {isNil {_tree select _x}}) >= 0) exitWith {false};
_tree params ["_cargo","_inventory","_coolers","_children"];
if !(_cargo isEqualType [] && {count _cargo == 4} && {_children isEqualType []} && {count _children <= 64}) exitWith {false};
if (([0,1,2,3] findIf {isNil {_cargo select _x} || {!((_cargo select _x) isEqualType [])} || {count (_cargo select _x) > 4096}}) >= 0) exitWith {false};
if !([_inventory] call ACME_fnc_inventorySnapshotValid && {[_coolers] call ACME_fnc_coolerSnapshotValid} && {(_coolers select 1) == "holder"}) exitWith {false};
private _valid = true;
{if !(_x isEqualType "" && {count _x > 0} && {count _x <= 256}) exitWith {_valid = false;};} forEach (_cargo select 0);
if (!_valid) exitWith {false};
if (((_cargo select 0) findIf {([_x] call ACME_fnc_coolerBagVolume) > 0}) >= 0) exitWith {false};
{
    if !(_x isEqualType [] && {count _x == 2}) exitWith {_valid = false;};
    if (isNil {_x select 0} || {isNil {_x select 1}}) exitWith {_valid = false;};
    _x params ["_class","_ammo"];
    if !(_class isEqualType "" && {count _class > 0} && {count _class <= 256} && {_ammo isEqualType 0} && {finite _ammo} && {_ammo >= 0} && {_ammo <= 1e9} && {_ammo == floor _ammo}) exitWith {_valid = false;};
} forEach (_cargo select 1);
if (!_valid) exitWith {false};
// Weapon arrays may contain nested partial magazines, but never executable/object values.
private _valueValid = {
    params ["_value",["_level",0]];
    if (isNil "_value" || {_level > 8}) exitWith {false};
    if (_value isEqualType "") exitWith {count _value <= 256};
    if (_value isEqualType 0) exitWith {finite _value && {abs _value <= 1e9}};
    if !(_value isEqualType [] && {count _value <= 32}) exitWith {false};
    private _ok = true;
    {if (isNil "_x" || {!([_x,_level + 1] call _valueValid)}) exitWith {_ok = false;};} forEach _value;
    _ok
};
{if !(_x isEqualType [] && {[_x] call _valueValid}) exitWith {_valid = false;};} forEach (_cargo select 2);
if (!_valid || {count (_cargo select 3) != count _children}) exitWith {false};
{
    if !(_x isEqualType [] && {count _x == 3}) exitWith {_valid = false;};
    private _entry = _x;
    if (([0,1,2] findIf {isNil {_entry select _x}}) >= 0) exitWith {_valid = false;};
    _x params ["_class","_pack","_contents"];
    if !(_class isEqualType "" && {count _class > 0} && {count _class <= 256} && {_pack isEqualType false}) exitWith {_valid = false;};
    private _child = _children select _forEachIndex;
    if !([_child,_depth + 1] call ACME_fnc_equipmentCargoValid) exitWith {_valid = false;};
    if (_contents isNotEqualTo (_child select 0)) exitWith {_valid = false;};
} forEach (_cargo select 3);
_valid
