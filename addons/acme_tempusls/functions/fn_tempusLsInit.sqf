if (!hasInterface) exitWith {};
if (isNil "ace_interact_menu_fnc_createAction") exitWith {};
ACME_tempusls_cObj = objNull;
ACME_tempusls_rObj = objNull;
ACME_tempusls_pool = [];
ACME_tempusls_scanAt = 0;
ACME_tempusls_near = [];
ACME_tempusls_ticks = createHashMap;
private _icon = "\acme_tempusls\data\tempusls_icon_ca.paa";
private _free = { isNull (uiNamespace getVariable ["ACME_TempusLS_dlg", displayNull]) };
private _on = { (_target getVariable ["acme_tempusls_pw", [false]]) select 0 };
private _use = ["ACME_tempusls_use", "Use Screen", "", {[_target] call ACME_fnc_tempusLsUse}, {[_target] call ACME_fnc_tempusLsCanUse}] call ace_interact_menu_fnc_createAction;
private _pwOn = ["ACME_tempusls_on", "Turn On", "", {[_target, true] call ACME_fnc_tempusLsPower}, {!((_target getVariable ["acme_tempusls_pw", [false]]) select 0)}] call ace_interact_menu_fnc_createAction;
private _pwOff = ["ACME_tempusls_off", "Turn Off", "", {[_target, false] call ACME_fnc_tempusLsPower}, _on] call ace_interact_menu_fnc_createAction;
private _pick = ["ACME_tempusls_pick", "Pick Up", "", {[_target] call ACME_fnc_tempusLsPick}, _free] call ace_interact_menu_fnc_createAction;
private _place = ["ACME_tempusls_place", "Place", "", {call ACME_fnc_tempusLsPlace}, {isNull objectParent _player && {isNull (uiNamespace getVariable ["ACME_TempusLS_dlg", displayNull])}}] call ace_interact_menu_fnc_createAction;
private _root = ["ACME_tempusls_root", "Tempus LS", "", {}, {alive player}, {}, [], [0, 0, 0.1], 2.5] call ace_interact_menu_fnc_createAction;
private _self = ["ACME_tempusls_self", "Tempus LS", _icon, {}, {[_player, "ACME_TempusLS_Item"] call ace_common_fnc_hasItem}] call ace_interact_menu_fnc_createAction;
["ACME_TempusLS", 0, [], _root, true] call ace_interact_menu_fnc_addActionToClass;
{
	["ACME_TempusLS", 0, ["ACME_tempusls_root"], _x, true] call ace_interact_menu_fnc_addActionToClass;
} forEach [_use, _pwOn, _pwOff, _pick];
["CAManBase", 1, ["ACE_SelfActions", "ACE_Equipment"], _self, true] call ace_interact_menu_fnc_addActionToClass;
{
	["CAManBase", 1, ["ACE_SelfActions", "ACE_Equipment", "ACME_tempusls_self"], _x, true] call ace_interact_menu_fnc_addActionToClass;
} forEach [_pwOn, _pwOff, _place];
["loadout", {
	params ["_unit"];
	if ([_unit, "ACME_TempusLS_Item"] call ace_common_fnc_hasItem) exitWith {};
	private _pat = _unit getVariable ["acme_tempusls_pat", objNull];
	if (((_unit getVariable ["acme_tempusls_pw", [false]]) select 0) || {!isNull _pat}) then {
		if (!isNull _pat) then { [_unit, _pat, false] remoteExecCall ["ACME_fnc_tempusLsPace", _pat] };
		_unit setVariable ["acme_tempusls_pw", [false, 0], true];
		_unit setVariable ["acme_tempusls_pat", objNull, true];
		_unit setVariable ["acme_tempusls_v", [], true];
		[_unit] call ACME_fnc_tempusLsChargeClear;
		_unit setVariable ["acme_tempusls_metro", [false, ""], true];
		_unit setVariable ["acme_tempusls_pace", [false, 70, 0, false], true];
	};
}] call CBA_fnc_addPlayerEventHandler;
if (!isNil "ACME_tempusls_pfh") then { [ACME_tempusls_pfh] call CBA_fnc_removePerFrameHandler };
ACME_tempusls_pfh = [{ call ACME_fnc_tempusLsMirror }, 0] call CBA_fnc_addPerFrameHandler;
