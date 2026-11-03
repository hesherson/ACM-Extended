[1.5, [], {
	if !([player, "ACME_TempusLS_Item"] call ace_common_fnc_hasItem) exitWith {};
	private _spot = call ACME_fnc_tempusLsSpot;
	private _o = createVehicle ["ACME_TempusLS", [0, 0, 0], [], 0, "CAN_COLLIDE"];
	_o setDir ((getDir player) + 180);
	_o setVectorUp [0, 0, 1];
	private _put = { _o setPosWorld (_spot vectorAdd [0, 0, 0.005 - (((boundingBoxReal _o) select 0) select 2)]) };
	call _put;
	private _bl = _o selectionPosition ["scr_bl", "Memory"];
	private _n = ((_o selectionPosition ["scr_br", "Memory"]) vectorDiff _bl) vectorCrossProduct ((_o selectionPosition ["scr_tl", "Memory"]) vectorDiff _bl);
	if (((_o vectorModelToWorld _n) vectorDotProduct ((eyePos player) vectorDiff (getPosASL _o))) < 0) then {
		_o setDir (getDir player);
		_o setVectorUp [0, 0, 1];
		call _put;
	};
	[player, _o] call ACME_fnc_tempusLsMove;
	player removeItem "ACME_TempusLS_Item";
}, {}, "Placing Tempus LS", {
	alive player && {isNull objectParent player}
}] call ace_common_fnc_progressBar;
