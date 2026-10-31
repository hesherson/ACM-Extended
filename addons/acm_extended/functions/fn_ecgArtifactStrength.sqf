/* Visual-only motion/jostling strength. It reads treatment leases and active hands-on procedures; it never writes physiology. */
params ["_patient"];
if (isNull _patient) exitWith {0};
private _now = CBA_missionTime;
private _leases = (_patient getVariable ["ACME_ecgJostleLeases", []]) select {(_x param [1,-1]) > _now};
private _s = if (_leases isEqualTo []) then {0} else {(0.48 + 0.10 * ((count _leases) - 1)) min 0.85};
// direct pressure is continuous hands-on movement and may not use a stock ACE progress timer.
private _dp = false;
{
    private _part = _x;
    private _provider = _patient getVariable [format ["ACME_DP_press_%1", _part], objNull];
    if (!isNull _provider
        && {alive _provider}
        && {_provider getVariable ["ACME_DP_Active", false]}
        && {!(_provider getVariable ["ACME_DP_Paused", false])}
        && {(_provider getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}
        && {(_provider getVariable ["ACME_DP_Part", ""]) == _part}) exitWith {_dp = true;};
} forEach ["head","body","leftarm","rightarm","leftleg","rightleg"];
if (_dp) then {_s = _s max 0.62;};
// suction and recent bagging can tug the head/circuit/pads, but are milder than CPR.
// Suction records store expiry at index 2; index 4 is the clinical episode.
private _sessions = (_patient getVariable ["ACME_suctionSessions", []]) select {(_x param [2,-1]) > _now};
if !(_sessions isEqualTo []) then {_s = _s max 0.42;};
if (((serverTime - (_patient getVariable ["ACME_bvm_lastBreathServer", -99])) max 0) < 1.2) then {_s = _s max 0.30;};
if (!isNull (_patient getVariable ["ace_medical_CPR_provider", objNull])) then {_s = 1.0;};
(_s max ([_patient] call ACME_fnc_ecgMotionStrength)) min 1
