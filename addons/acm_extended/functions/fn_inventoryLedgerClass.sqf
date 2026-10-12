/* Native weight matches the bag(s) and tubing actually committed. Unknown
 * third-party weights retain the legacy carrier instead of inventing a mass. */
params ["_kind",["_payload",[]]];
if (_kind == "syringe") exitWith {"ACME_PreparedSyringe"};
private _fallback = "ACME_PreparedIVSet";
if (count _payload < 2) exitWith {_fallback};
private _set = _payload select 1;
private _y = (_set param [8,""]) == "yset";
private _line = ["ACME_IVLine","ACME_YTubing"] select _y;
private _mass = getNumber (configFile >> "CfgWeapons" >> _line >> "ItemInfo" >> "mass");
private _sources = [_set param [1,""]];
if (_y && {(_set param [3,""]) != ""}) then {_sources pushBack (_set select 3);};
private _known = _mass > 0;
{
    private _part = getNumber (configFile >> "CfgWeapons" >> _x >> "ItemInfo" >> "mass");
    if (_part <= 0) then {_known = false;};
    _mass = _mass + _part;
} forEach _sources;
if (!_known) exitWith {_fallback};
private _weights = [11,21,26,31,37,47,51,52,62,72,77,81,101,102,112,122,127,152,202];
private _match = _weights findIf {abs (_mass - _x / 10) < 0.001};
if (_match < 0) exitWith {_fallback};
format ["ACME_PreparedIVSet_M%1",_weights select _match]
