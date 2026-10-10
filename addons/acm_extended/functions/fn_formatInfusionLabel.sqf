/* Describe the remaining contents of one physical bag, including every component. */
params ["_entry", ["_all", [], [[]]]];
private _id = _entry param [23, ""];
private _parts = if (_id == "") then {[_entry]} else {_all select {(_x param [23, ""]) == _id}};
if (_parts isEqualTo []) then {_parts = [_entry];};
private _hasDose = (_parts findIf {(_x param [14,0]) > 0.000001}) >= 0;
private _marker = if (!_hasDose) then {"(done) "} else {if ((_entry param [21,0]) > 0) then {"(infusing) "} else {"(paused) "}};
private _names = _parts apply {[_x select 11] call ACME_fnc_infusionName};
_marker + format ["%1 | %2 mL remaining", _names joinString " + ", (_entry param [10,0]) toFixed 1]
