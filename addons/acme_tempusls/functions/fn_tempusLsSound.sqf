params ["_o", "_ev", ["_arg", ""]];
if (isNull _o) exitWith {};
private _play = {
	params ["_file", ["_vol", 3]];
	playSound3D ["\x\ACM\addons\circulation\sound\" + _file, _o, false, getPosASL _o, _vol, 1, 15];
};
switch (_ev) do {
	case "charge": { ["aed_charging.wav"] call _play };
	case "ready": {
		_o setVariable ["acme_tempusls_armed", true, true];
		if (((_o getVariable ["acme_tempusls_st", ""]) find """mode"":""AED""") >= 0) then { ["aed_standclear_pushtoshock.wav"] call _play };
		[{
			params ["_args", "_id"];
			_args params ["_o", "_until"];
			if (isNull _o || {!(_o getVariable ["acme_tempusls_armed", false])} || {diag_tickTime > _until}) exitWith {
				if (!isNull _o && {diag_tickTime > _until}) then { _o setVariable ["acme_tempusls_armed", false, true] };
				[_id] call CBA_fnc_removePerFrameHandler;
			};
			playSound3D ["\x\ACM\addons\circulation\sound\aed_alarm.wav", _o, false, getPosASL _o, 2, 1, 15];
		}, 0.53, [_o, diag_tickTime + 21]] call CBA_fnc_addPerFrameHandler;
	};
	case "disarm": {
		_o setVariable ["acme_tempusls_armed", false, true];
		["aed_3beep.wav"] call _play;
	};
	case "analyse": { ["aed_analyzingnow.wav"] call _play };
	case "advice": {
		if (_arg isEqualTo "1") then {
			["aed_shockadvised.wav"] call _play;
		} else {
			["aed_noshockadvised.wav"] call _play;
			[{
				params ["_o"];
				if (!isNull _o) then { playSound3D ["\x\ACM\addons\circulation\sound\aed_startcpr.wav", _o, false, getPosASL _o, 3, 1, 15] };
			}, [_o], 2.2] call CBA_fnc_waitAndExecute;
		};
	};
};
