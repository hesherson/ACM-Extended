/* B278: one medication uses its full name; mixtures use established aliases.
 * Read-only presentation shared by prepared and attached physical bags.
 * Duplicate components are the same drug, not a multiple-medication mixture. */
params [["_medications", [], [[]]]];
private _names = [];
private _seen = [];
{
    if (_x isEqualType "" && {_x != ""}) then {
        private _key = toLowerANSI _x;
        if !(_key in _seen) then {_seen pushBack _key;_names pushBack _x;};
    };
} forEach _medications;
if (_names isEqualTo []) exitWith {"Infusion"};
if (count _names == 1) exitWith {([_names select 0,true] call ACME_fnc_infusionName) + " infusion"};
((_names apply {[_x] call ACME_fnc_infusionName}) joinString " + ") + " infusion"
