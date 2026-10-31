/* Import native ACM prepared syringes received from an older/stock workflow.
 * Read actual cargo rather than ACE's cached item list inside inventory events.
 * Match multiplicity as well as class/amount, including identical syringes.
 */
params ["_owner",["_rows",[],[[]]]];
if (isNull _owner || {!local _owner}) exitWith {_rows};
private _out = +_rows;
private _protected = [];
{
    if ((_x param [3,0,[0]]) >= diag_tickTime) then {_protected pushBack [_x select 0,_x select 1];};
} forEach (_owner getVariable ["ACME_nativeSyringePending",[]]);
private _represented = [];
{
    if ((_x param [13,"",[""]]) != "inventoryB279" && {(_x param [6,"",[""]]) == ""}) then {
        _represented pushBack [format ["ACM_Syringe_%1_%2",_x param [1,10],_x param [0,""]],round ((_x param [2,0]) * 100)];
    };
} forEach _rows;
{
    if (isNull _x) then {continue};
    {
        _x params ["_class","_ammo"];
        private _protectedAt = _protected find [_class,_ammo];
        if (_protectedAt >= 0) then {_protected deleteAt _protectedAt; continue;};
        private _cfg = configFile >> "CfgMagazines" >> _class;
        if (_ammo <= 0 || {getNumber (_cfg >> "ACM_isSyringe") != 1}) then {continue};
        private _parts = _class splitString "_";
        if (count _parts < 4 || {(_parts select 0) != "ACM"} || {(_parts select 1) != "Syringe"}) then {continue};
        private _size = parseNumber (_parts select 2);
        private _med = _parts select 3;
        if !(_size in [1,3,5,10] && {_ammo <= _size * 100}) then {continue};
        private _at = _represented find _x;
        if (_at >= 0) then {_represented deleteAt _at;} else {_out pushBack [_med,_size,_ammo/100,""];};
    } forEach magazinesAmmoCargo _x;
} forEach [uniformContainer _owner,vestContainer _owner,backpackContainer _owner];
_out
