/* ACE-compatible debit of one carrier supply. Respect shared-equipment order/medic-only policy.
   The fourth result identifies the exact cargo source for ACME's single-settlement receipt. */
params ["_unit", "_items"];
private _cargo = [_unit] call ACME_fnc_carrierInventoryGet;
if (isNull _cargo) exitWith {[objNull, "", false, objNull]};
private _result = [objNull, "", false, objNull];
{
    if (_x in itemCargo _cargo) exitWith {
        _cargo addItemCargoGlobal [_x, -1];
        _result = [_unit, _x, false, _cargo];
    };
    if (_x in magazineCargo _cargo) exitWith {
        [_cargo, _x] call ace_common_fnc_adjustMagazineAmmo;
        _result = [_unit, _x, false, _cargo];
    };
} forEach _items;
_result
