if (!hasInterface) exitWith {};
if (isNil "ace_interact_menu_fnc_createAction") exitWith {};
ACME_tempus_cObj = objNull;
ACME_tempus_rObj = objNull;
ACME_tempus_pool = [];
ACME_tempus_scanAt = 0;
private _icon = "\acme_tempus\data\tempus_icon_ca.paa";
private _free = { isNull (uiNamespace getVariable ["ACME_Tempus_dlg", displayNull]) };
private _on = { (_target getVariable ["acme_tempus_pw", [false]]) select 0 };
private _use = ["ACME_tempus_use", "Use Screen", "", {[_target] call ACME_fnc_tempusUse}, {[_target] call ACME_fnc_tempusCanUse}] call ace_interact_menu_fnc_createAction;
private _pwOn = ["ACME_tempus_on", "Turn On", "", {[_target, true] call ACME_fnc_tempusPower}, {!((_target getVariable ["acme_tempus_pw", [false]]) select 0)}] call ace_interact_menu_fnc_createAction;
private _pwOff = ["ACME_tempus_off", "Turn Off", "", {[_target, false] call ACME_fnc_tempusPower}, _on] call ace_interact_menu_fnc_createAction;
private _conn = ["ACME_tempus_conn", "Connect Patient", "", {}, {isNull (_target getVariable ["acme_tempus_pat", objNull])}, {
	params ["_target"];
	private _list = (nearestObjects [_target, ["CAManBase"], 3]) select { !(_x isKindOf "VirtualMan_F") };
	_list apply {
		private _name = if (_x isEqualTo player) then { "Yourself" } else { [_x, false, true] call ace_common_fnc_getName };
		[["ACME_tempus_conn_" + netId _x, _name, "", {[_target, _this select 2] call ACME_fnc_tempusConnect}, {true}, {}, _x] call ace_interact_menu_fnc_createAction, [], _target]
	}
}] call ace_interact_menu_fnc_createAction;
private _disc = ["ACME_tempus_disc", "Disconnect Patient", "", {[_target, objNull] call ACME_fnc_tempusConnect}, {!isNull (_target getVariable ["acme_tempus_pat", objNull])}] call ace_interact_menu_fnc_createAction;
private _pick = ["ACME_tempus_pick", "Pick Up", "", {[_target] call ACME_fnc_tempusPick}, _free] call ace_interact_menu_fnc_createAction;
private _place = ["ACME_tempus_place", "Place", "", {call ACME_fnc_tempusPlace}, {isNull objectParent _player && {isNull (uiNamespace getVariable ["ACME_Tempus_dlg", displayNull])}}] call ace_interact_menu_fnc_createAction;
private _root = ["ACME_tempus_root", "Tempus Pro", "", {}, {alive player}, {}, [], [0, 0, 0.12], 2.5] call ace_interact_menu_fnc_createAction;
private _self = ["ACME_tempus_self", "Tempus Pro", _icon, {}, {[_player, "ACME_TempusPro_Item"] call ace_common_fnc_hasItem}] call ace_interact_menu_fnc_createAction;
["ACME_TempusPro", 0, [], _root, true] call ace_interact_menu_fnc_addActionToClass;
{
	["ACME_TempusPro", 0, ["ACME_tempus_root"], _x, true] call ace_interact_menu_fnc_addActionToClass;
} forEach [_use, _pwOn, _pwOff, _conn, _disc, _pick];
["CAManBase", 1, ["ACE_SelfActions", "ACE_Equipment"], _self, true] call ace_interact_menu_fnc_addActionToClass;
{
	["CAManBase", 1, ["ACE_SelfActions", "ACE_Equipment", "ACME_tempus_self"], _x, true] call ace_interact_menu_fnc_addActionToClass;
} forEach [_use, _pwOn, _pwOff, _conn, _disc, _place];
["loadout", {
	params ["_unit"];
	if ([_unit, "ACME_TempusPro_Item"] call ace_common_fnc_hasItem) exitWith {};
	if (((_unit getVariable ["acme_tempus_pw", [false]]) select 0) || {!isNull (_unit getVariable ["acme_tempus_pat", objNull])}) then {
		_unit setVariable ["acme_tempus_pw", [false, 0, false], true];
		_unit setVariable ["acme_tempus_pat", objNull, true];
		_unit setVariable ["acme_tempus_v", [], true];
	};
}] call CBA_fnc_addPlayerEventHandler;
if (!isNil "ACME_tempus_pfh") then { [ACME_tempus_pfh] call CBA_fnc_removePerFrameHandler };
ACME_tempus_pfh = [{ call ACME_fnc_tempusMirror }, 0] call CBA_fnc_addPerFrameHandler;
