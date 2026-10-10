/* Compare cargo as multisets: the engine may reorder equal-class entries while serializing inventory.
   Exact magazine ammo, weapon attachment arrays and recursively nested contents must survive a transfer. */
params ["_left", "_right"];
if (count _left != 4 || {count _right != 4}) exitWith {false};
private _sameBag = {
    params ["_a", "_b"];
    if (count _a != count _b) exitWith {false};
    private _remaining = +_b;
    {
        private _index = _remaining find _x;
        if (_index < 0) exitWith {};
        _remaining deleteAt _index;
    } forEach _a;
    _remaining isEqualTo []
};
private _same = true;
for "_i" from 0 to 2 do {
    if !([_left select _i, _right select _i] call _sameBag) exitWith {_same = false;};
};
if (!_same || {count (_left select 3) != count (_right select 3)}) exitWith {false};
private _remaining = +(_right select 3);
{
    _x params ["_class", "_backpack", "_contents"];
    private _index = _remaining findIf {
        (_x select 0) == _class && {(_x select 1) == _backpack}
            && {[_contents, _x select 2] call ACME_fnc_carrierCargoEqual}
    };
    if (_index < 0) exitWith {_same = false;};
    _remaining deleteAt _index;
} forEach (_left select 3);
_same && {_remaining isEqualTo []}
