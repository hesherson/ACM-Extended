params ["", "_id"];
private _any = false;
{
	private _d = uiNamespace getVariable [_x, displayNull];
	if (isNull _d) then { continue };
	private _b = _d getVariable ["acme_atak_b", controlNull];
	if (isNull _b) then { continue };
	_any = true;
	private _menu = [_x, "showMenu"] call cTab_fnc_getSettings;
	if !(_menu isEqualType []) then { _menu = [] };
	private _on = ((_menu param [0, ""]) isEqualTo "ACME_BATDOK") && {_menu param [1, false]}
		&& {([_x, "mode"] call cTab_fnc_getSettings) isEqualTo "BFT"} && {ctrlShown (_d displayCtrl 21650)};
	if (_on isNotEqualTo (ctrlShown _b)) then {
		if (_on) then { [_d, _b] call ACME_fnc_atakPlace };
		_b ctrlShow _on;
		_b ctrlEnable _on;
	};
	if (_on && {_b getVariable ["acme_atak_ready", false]} && {diag_tickTime >= (_b getVariable ["acme_atak_at", 0])}) then {
		_b setVariable ["acme_atak_at", diag_tickTime + 1];
		_b ctrlWebBrowserAction ["ExecJS", "batdok.set(" + str (toArray str (call ACME_fnc_batdokState)) + ")"];
	};
} forEach ["cTab_Android_dlg", "cTab_Android_dsp"];
if (!_any) then {
	[_id] call CBA_fnc_removePerFrameHandler;
	ACME_atak_pfh = nil;
};
