params ["_u"];
if (isNull _u) exitWith {[]};
private _temp = _u getVariable ["ACME_hypo_temp", 37];
if (!alive _u) exitWith {[0, 0, 1, 0, 0, 0, 0, 0, _temp]};
private _hr = _u getVariable ["ace_medical_heartRate", 80];
private _ehr = if (isNil "ACM_circulation_fnc_getEKGHeartRate") then { _hr } else { [_u] call ACM_circulation_fnc_getEKGHeartRate };
private _rh = if (isNil "ACME_fnc_rhythmGet") then {
	_u getVariable ["ACM_circulation_Cardiac_RhythmState", [0, 1] select (_u getVariable ["ace_medical_inCardiacArrest", false])]
} else {
	[_u] call ACME_fnc_rhythmGet
};
private _bp = [_u] call ace_medical_status_fnc_getBloodPressure;
private _spo2 = if (isNil "ACM_breathing_fnc_getSpO2") then { _u getVariable ["ace_medical_spo2", 99] } else { [_u] call ACM_breathing_fnc_getSpO2 };
private _rr = _u getVariable ["ACM_breathing_RespirationRate", 18];
private _co2 = if (isNil "ACM_breathing_fnc_getEtCO2") then { -1 } else { [_u] call ACM_breathing_fnc_getEtCO2 };
[round _hr, round _ehr, _rh, round (_bp select 1), round (_bp select 0), round _spo2, round _rr, round _co2, _temp]
