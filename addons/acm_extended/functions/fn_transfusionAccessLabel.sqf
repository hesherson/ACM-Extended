/* B275: occupied access shorthand. Empty placeholders and other sites never label it. */
params [["_bags", [], [[]]], ["_medications", [], [[]]], ["_iv", true, [true]], ["_site", -1, [0]]];
private _abbr = [];
{
    private _type = _x param [0, ""];
    private _remaining = _x param [1, 0];
    private _bagSite = _x param [3, -1];
    private _bagIV = _x param [4, true];
    if (_remaining > 0.01 && {_bagIV isEqualTo _iv} && {!_iv || {_bagSite == _site}}
        && {!(_type in ["ACME_Empty","ACME_EmptySaline"])}) then {
        private _uid = _x param [8, ""];
        private _drugs = if (_uid isEqualTo "") then {[]} else {_medications select {(_x param [23, ""]) isEqualTo _uid}};
        private _a = [_type, _drugs] call ACME_fnc_transfusionFluidShorthand;
        if (_a != "") then {_abbr pushBackUnique _a;};
    };
} forEach _bags;
_abbr joinString "+"
