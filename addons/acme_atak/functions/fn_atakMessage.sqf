params ["_c", "", "_msg"];
if (isNull _c || {!(_msg isEqualType "")} || {(_msg select [0, 7]) != "BATDOK|"}) exitWith {};
private _a = ((_msg select [7]) splitString "|") apply { [_x] call ACME_fnc_batdokText };
switch (_a param [0, ""]) do {
	case "ready": {
		_c setVariable ["acme_atak_ready", true];
		_c setVariable ["acme_atak_at", 0];
		[_a] call ACME_fnc_batdokAction;
	};
	case "kbd": { if (focusedCtrl (ctrlParent _c) isNotEqualTo _c) then { ctrlSetFocus _c } };
	default {
		[_a] call ACME_fnc_batdokAction;
		_c setVariable ["acme_atak_at", diag_tickTime + 0.15];
	};
};
