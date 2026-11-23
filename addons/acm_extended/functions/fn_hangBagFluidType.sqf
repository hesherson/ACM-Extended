// work out what kind of fluid the bag we are raising holds, so the in-hand bag reads correctly: blood, in red,
// plasma, in amber, or fluid, clear, which is the saline, crystalloid and medication default.
// it reads the actual hung bags of the patient, from ACM_circulation_IV_Bags, where the body part maps to
// [[_bagType, _volume, _accessType, _accessSite, _iv, _bloodType], ...].
// a blood bag carries a _bloodType, and blood and plasma also show in the _bagType. it defaults to fluid if nothing
// matches.
// the args are [_patient, _bodyPart, optional, and _accessSite, optional].
params ["_patient", ["_bodyPart", ""], ["_accessSite", -1]];
private _ivBags = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
if !(_ivBags isEqualType createHashMap) exitWith { "fluid" };

_bodyPart = toLower _bodyPart;
private _bags = [];
if (_bodyPart != "" && {_bodyPart in keys _ivBags}) then {
    _bags = _ivBags getOrDefault [_bodyPart, []];
} else {
    { _bags append _x; } forEach (values _ivBags);
};
if (_bags isEqualTo []) exitWith { "fluid" };

// prefer the bag at the selected access site, and otherwise the first.
private _bag = _bags param [0, []];
if (_accessSite >= 0) then {
    private _i = _bags findIf { (_x param [3, -99]) == _accessSite };
    if (_i >= 0) then { _bag = _bags select _i; };
};
if (_bag isEqualTo []) exitWith { "fluid" };

_bag params [["_bagType", ""], "", "", "", "", ["_bloodType", ""]];
// CAUTION: Do not use str on a value that is already a string. str adds quotation marks.
// The tests below use find, which is a substring search, so the quotes did not break them.
// The value is normalised anyway, because the next person to use it with an equality test would be caught.
private _bt = if (_bagType isEqualType "") then { toLower _bagType } else { toLower (str _bagType) };
private _hasBloodType = (_bloodType isEqualType "" && {_bloodType != ""}) || {_bloodType isEqualType 0 && {_bloodType >= 0}};  // B395: ACM blood types are 0 (O) to 7; -1 means none
if ((_bt find "blood" >= 0) || {_hasBloodType}) exitWith { "blood" };
// (Plasma-Lyte is a clear crystalloid, not plasma: B395)
if (_bt find "plasmalyte" >= 0) exitWith { "fluid" };
if (_bt find "plasma" >= 0) exitWith { "plasma" };
"fluid"
