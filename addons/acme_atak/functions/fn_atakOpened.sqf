// CT_WEBBROWSER documents JSDialog; the bundled HEMTT event table predates it.
private _jsDialogEvent = "JSDialog";
params [["_group", controlNull]];
private _d = ctrlParent _group;
if (isNull _d) exitWith {};
private _b = _d getVariable ["acme_atak_b", controlNull];
if (isNull _b) then {
	_b = _d ctrlCreate ["ACME_ATAK_Web", -1];
	_b ctrlShow false;
	_b ctrlAddEventHandler [_jsDialogEvent, {
		[{ _this call ACME_fnc_atakMessage }, _this] call CBA_fnc_execNextFrame;
		true
	}];
	_d setVariable ["acme_atak_b", _b];
	_b ctrlWebBrowserAction ["OpenDataAsURL", call ACME_fnc_atakHtml];
};
[_d, _b] call ACME_fnc_atakPlace;
if (isNil "ACME_atak_pfh") then { ACME_atak_pfh = [ACME_fnc_atakLoop, 0.2] call CBA_fnc_addPerFrameHandler };
