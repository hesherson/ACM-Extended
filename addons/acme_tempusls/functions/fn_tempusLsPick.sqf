params ["_o"];
if (isNull _o) exitWith {};
[1.5, [_o], {
	(_this select 0) params ["_o"];
	if (isNull _o || {_o getVariable ["acme_tempusls_taken", false]}) exitWith {};
	_o setVariable ["acme_tempusls_taken", true, true];
	private _busy = ((player getVariable ["acme_tempusls_pw", [false]]) select 0) || {!isNull (player getVariable ["acme_tempusls_pat", objNull])} || {[player, "ACME_TempusLS_Item"] call ace_common_fnc_hasItem};
	if (player canAdd "ACME_TempusLS_Item") then {
		player addItem "ACME_TempusLS_Item";
		if (!_busy) then { [_o, player] call ACME_fnc_tempusLsMove };
	} else {
		private _wh = createVehicle ["GroundWeaponHolder", getPosATL player, [], 0, "CAN_COLLIDE"];
		_wh addItemCargoGlobal ["ACME_TempusLS_Item", 1];
	};
	_o setVariable ["acme_tempusls_pat", objNull, true];
	deleteVehicle _o;
}, {}, "Picking up Tempus LS", {
	(_this select 0) params [["_o", objNull]];
	alive player && {!isNull _o} && {player distance _o < 4}
}] call ace_common_fnc_progressBar;
