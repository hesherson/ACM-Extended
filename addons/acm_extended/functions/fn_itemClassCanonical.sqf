/*
 * The class an item is called now, for a name out of a kit, a mission or saved data that may be from an older
 * build. The items were renamed from ACM_ to ACME_ (2026-11-16). Since B378 the old names are no classes any
 * more: each item exists once. A name that is no class is turned into the new name by rule (ACM_x is ACME_x,
 * and the few names in the table below) if that is a class; else it is returned as it came.
 * Arguments: 0: class name <STRING>, 1: the section it belongs to ("CfgWeapons", "CfgMagazines", "CfgVehicles",
 * "CfgGlasses"; default: any of them).
 * Returns: class name <STRING>.
 */
params ["_class", ["_section", ""]];
if (_class == "") exitWith {_class};
private _key = toLowerANSI _class;
if !((_key select [0, 4]) in ["acm_", "ace_", "kat_"]) exitWith {_class};
private _sections = if (_section == "") then {["CfgWeapons", "CfgMagazines", "CfgVehicles", "CfgGlasses"]} else {[_section]};
// an old name that is still a class (the supply crates) names the class it stands for
private _canonical = "";
{
    _canonical = getText (configFile >> _x >> _class >> "ACME_itemReplacement");
    if (_canonical != "") exitWith {};
} forEach _sections;
if (_canonical != "") exitWith {_canonical};
// a class that exists is called what it is called
if (_sections findIf {isClass (configFile >> _x >> _class)} >= 0) exitWith {_class};
if (isNil "ACME_itemOldNames") then {
    ACME_itemOldNames = createHashMapFromArray [
        ["ace_esmololiv_250", "ACME_EsmololIV_250"],
        ["ace_htsiv_250", "ACME_HTSIV_250"],
        ["ace_magnesiumiv_50", "ACME_MagnesiumIV_50"],
        ["ace_mannitoliv_500", "ACME_MannitolIV_500"],
        ["kat_eyewasher", "ACME_Eyewasher"],
        ["kat_eyecovers", "ACME_EyeCover"],
        ["kat_eyecovers_left", "ACME_EyeCover_Left"],
        ["kat_eyecovers_right", "ACME_EyeCover_Right"]
    ];
};
private _new = ACME_itemOldNames getOrDefault [_key, ""];
if (_new == "" && {(_key select [0, 4]) == "acm_"}) then {_new = "ACME_" + (_class select [4]);};
if (_new == "") exitWith {_class};
private _found = _sections findIf {isClass (configFile >> _x >> _new)};
if (_found < 0) exitWith {_class};
configName (configFile >> (_sections select _found) >> _new)
