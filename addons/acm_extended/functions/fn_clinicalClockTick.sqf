/* Integrate the server's mission rate without treating calendar edits as elapsed
 * time. The shared anchor changes only when the rate changes, and is retained for JIP. */
private _now = serverTime;
private _inGame = ((missionNamespace getVariable ["ACME_clinicalTiming",[]]) param [11,0]) == 1;
private _rate = if (_inGame) then {timeMultiplier * ([accTime,1] select isMultiplayer)} else {1};
private _anchor = missionNamespace getVariable ["ACME_clinicalClockAnchor",[]];
if (_rate == (_anchor param [2,-1])) exitWith {};
private _next = [_now, ([] call ACME_fnc_clinicalClock) - _now, _rate, _anchor param [3,CBA_missionTime - _now]];
missionNamespace setVariable ["ACME_clinicalClockAnchor",_next];
_next remoteExecCall ["ACME_fnc_clinicalTimingSync",-2,"ACME_clinicalClockAnchor"];
