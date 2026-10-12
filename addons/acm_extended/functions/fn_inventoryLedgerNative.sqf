/* Only the engine magazine tuple proves possession. Ammo is an opaque ID, never a dose. */
params ["_owner", ["_kind", ""]];
if (isNull _owner) exitWith {[]};
private _containers = if (_owner isKindOf "CAManBase") then {[uniformContainer _owner, vestContainer _owner, backpackContainer _owner]} else {[_owner]};
private _rows = [];
{
    if (isNull _x) then {continue;};
    {
        _x params ["_class", "_token"];
        private _k = switch (_class) do {case "ACME_PreparedIVSet": {"prepared"}; case "ACME_PreparedSyringe": {"syringe"}; default {""};};
        if (_k != "" && {_kind == "" || {_kind == _k}} && {_token > 0} && {_token < 65535}) then {_rows pushBack [_token, _k];};
    } forEach magazinesAmmoCargo _x;
} forEach _containers;
_rows
