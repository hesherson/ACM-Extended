params ["_o", "_ev", ["_arg", ""], ["_context", []]];
if (isNull _o) exitWith {};
private _play = {
	params ["_file", ["_vol", 3]];
	playSound3D ["\x\ACM\addons\circulation\sound\" + _file, _o, false, getPosASL _o, _vol, 1, 15];
};
switch (_ev) do {
	case "charge": {
        private _started = [_o, "begin", parseNumber _arg] call ACME_fnc_tempusLsCharge;
        if (_started isEqualTo []) exitWith {[]};
        ["aed_charging.wav"] call _play;
        _started
    };
    case "ready": {
        private _charge = [_o, "ready", 0, _context] call ACME_fnc_tempusLsCharge;
        if (_charge isEqualTo []) exitWith {};
        if (((_o getVariable ["acme_tempusls_st", ""]) find """mode"":""AED""") >= 0) then { ["aed_standclear_pushtoshock.wav"] call _play };
        [{
            params ["_args", "_id"];
            _args params ["_o", "_charge"];
            // A previous alarm/expiry callback never owns a replacement charge.
            if (isNull _o || {(_o getVariable ["acme_tempusls_charge", []]) isNotEqualTo _charge}) exitWith {
                [_id] call CBA_fnc_removePerFrameHandler;
            };
            private _patient = _charge select 1;
            if (!(_o getVariable ["acme_tempusls_armed", false])
                || {serverTime > (_charge select 5)} || {isNull _patient}
                || {(_o getVariable ["acme_tempusls_pat", objNull]) isNotEqualTo _patient}
                || {([_patient] call ACME_fnc_clinicalEpoch) != (_charge select 2)}
                || {(_o getVariable ["acme_tempusls_pw", [false]]) isNotEqualTo (_charge select 3)}) exitWith {
                [_o] call ACME_fnc_tempusLsChargeClear;
                [_id] call CBA_fnc_removePerFrameHandler;
            };
            playSound3D ["\x\ACM\addons\circulation\sound\aed_alarm.wav", _o, false, getPosASL _o, 2, 1, 15];
        }, 0.53, [_o, _charge]] call CBA_fnc_addPerFrameHandler;
    };
	case "disarm": {
		[_o] call ACME_fnc_tempusLsChargeClear;
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
