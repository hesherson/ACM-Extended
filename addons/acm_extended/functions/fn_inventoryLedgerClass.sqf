/* Native weight matches the bag(s) and tubing actually committed. Unknown
 * third-party weights retain the legacy carrier instead of inventing a mass. */
params ["_kind",["_payload",[]]];
if (_kind == "cooler") exitWith {
    private _base = (_payload param [1,[]]) param [0,""];
    private _suffix = _base select [17];
    private _class = "ACME_CoolerCarrier_" + _suffix;
    if (_base in ["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"]
        && {isClass (configFile >> "CfgMagazines" >> _class)}) then {_class} else {""}
};
if (_kind == "syringe") exitWith {
    private _row = _payload param [1,[]];
    private _size = _row param [1,0];
    private _class = format ["ACME_PreparedSyringe_%1",_size];
    if (_size in [1,3,5,10] && {isClass (configFile >> "CfgMagazines" >> _class)}) then {_class} else {"ACME_PreparedSyringe"}
};
private _bagOnly = ((_payload param [1,[]]) param [8,""]) == "bagOnly";
private _fallback = if (_bagOnly) then {""} else {"ACME_PreparedIVSet"};
if (count _payload < 2) exitWith {_fallback};
private _set = _payload select 1;
private _y = (_set param [8,""]) == "yset";
private _line = ["ACME_IVLine","ACME_YTubing"] select _y;
private _mass = if (_bagOnly) then {0} else {getNumber (configFile >> "CfgWeapons" >> _line >> "ItemInfo" >> "mass")};
private _sources = [_set param [1,""]];
if (_y && {(_set param [3,""]) != ""}) then {_sources pushBack (_set select 3);};
private _known = _bagOnly || {_mass > 0};
{
    private _part = getNumber (configFile >> "CfgWeapons" >> _x >> "ItemInfo" >> "mass");
    if (_part <= 0) then {_known = false;};
    _mass = _mass + _part;
} forEach _sources;
if (!_known) exitWith {_fallback};
// Resolve only an exact declared carrier. Never silently round a modded bag to a
// lighter native weight. Hundredths also cover a directly spiked propofol bottle.
private _tenths = round (_mass * 10);
private _prefix = ["ACME_PreparedIVSet", "ACME_UnspikedBag"] select _bagOnly;
private _class = format ["%1_M%2",_prefix,_tenths];
if (abs (_mass - _tenths / 10) >= 0.001) then {
    private _whole = floor _mass;
    _class = format ["%1_M%2_%3",_prefix,_whole,round ((_mass - _whole) * 100)];
};
private _cfg = configFile >> "CfgMagazines" >> _class;
if (!isClass _cfg || {abs (getNumber (_cfg >> "mass") - _mass) >= 0.001}) exitWith {_fallback};
_class
