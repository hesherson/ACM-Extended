// Retire only these captured rows. An observably stale/reused native ID is not stopped.
if (canSuspend) exitWith {private _args = _this; isNil {_args call ACME_fnc_stethoscopeAudioStop;};};
params ["_channels"];
private _now = diag_tickTime;
{
    if ([_x,_now] call ACME_fnc_stethoscopeAudioOwned) then {stopSound (_x select 0);};
    _x set [0,-1];
    _x set [1,""];
    _x set [2,0];
    _x set [6,[]];
} forEach _channels;
