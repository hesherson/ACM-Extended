// spawn a junctional hemorrhage on the megacode dummy for the chosen region.
// in this mod junctional wounds are limb-anchored: an arm junctional reads as an axillary bleed and a leg
// junctional as an inguinal bleed. there are two arms and two legs, so each region naturally caps at 2. this finds
// the first free limb in the region and inflicts there, refusing once both are occupied.
// _this is [_region], where _region is "axilla" or "inguinal".
params ["_region"];
private _d = uiNamespace getVariable ["ACME_MC_target", objNull];
if (isNull _d) exitWith {};

private _r = toLower _region;
private _parts = if (_r isEqualTo "axilla") then { ["leftarm", "rightarm"] } else { ["leftleg", "rightleg"] };
private _label = if (_r isEqualTo "axilla") then { "Axilla" } else { "Inguinal" };

// a limb is occupied if it already carries a junctional wound in any state, meaning open, packed or wrapped.
private _free = _parts findIf { ((_d getVariable [format ["ACME_Junc_%1", _x], ""]) isEqualTo "") };
if (_free < 0) exitWith {
    [format ["Megacode: %1 wounds already at the max (2).", _label], 2.5] call ace_common_fnc_displayTextStructured;
    [[format ["%1 wound refused. Already 2 applied", _label], "#ffb24d"]] call ACME_fnc_megacodeLog;
};

private _part = _parts select _free;
[_d, _part] call ACME_fnc_junctionalInflict;

// how many of this region are now applied, for the log.
// counted from the state before this one (the inflict runs on the server and its "open" arrives later).
private _n = 1 + ({((_d getVariable [format ["ACME_Junc_%1", _x], ""]) isNotEqualTo "")} count (_parts - [_part]));
[format ["Megacode: %1 hemorrhage applied (%2/2).", _label, _n], 2] call ace_common_fnc_displayTextStructured;
[[format ["Wound: %1 hemorrhage (%2/2)", _label, _n], "#ff8a8a"]] call ACME_fnc_megacodeLog;
[87300, "wounds"] call ACME_fnc_megacodeMenu;
