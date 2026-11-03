params ["_u"];
if (isNull _u) exitWith {[]};
if (!alive _u) exitWith {[0, "asystole", false, false, false]};
private _hr = _u getVariable ["ace_medical_heartRate", 80];
private _ehr = if (isNil "ACM_circulation_fnc_getEKGHeartRate") then { _hr } else { [_u] call ACM_circulation_fnc_getEKGHeartRate };
private _rh = if (isNil "ACME_fnc_rhythmGet") then {
	_u getVariable ["ACM_circulation_Cardiac_RhythmState", [0, 1] select (_u getVariable ["ace_medical_inCardiacArrest", false])]
} else {
	[_u] call ACME_fnc_rhythmGet
};
private _name = switch (true) do {
	case (_rh == 1): {"asystole"};
	case (_rh == 2): {"vf"};
	case (_rh in [3, 4, 102]): {"vt"};
	default {"sinus"};
};
private _recent = !isNil "ACM_circulation_fnc_recentAEDShock" && {[_u] call ACM_circulation_fnc_recentAEDShock};
private _shock = (_rh in ([2, 3] + (missionNamespace getVariable ["ACME_sync_defibrillatableRhythms", [102]]))) && {!_recent};
private _cpr = alive (_u getVariable ["ace_medical_CPR_provider", objNull]);
[round (_ehr max 0), _name, _shock, _cpr, _u getVariable ["acme_tempusls_capture", false]]
