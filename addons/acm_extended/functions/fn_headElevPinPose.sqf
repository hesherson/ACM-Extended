// Hold the position of a unit while an animation with root motion plays, and hold the direction as an option.
// Call it as [_unit, _seconds, _pinDir] call ACME_fnc_headElevPinPose, immediately after the animation is
// requested. It works on a casualty and on a provider.
// _pinDir is true for a casualty, whose facing must not change. It is false for a provider, who keeps the
// freedom to turn and look while the motion plays.
//
// WHY IT EXISTS.
// The BI grab and release motions move the model along the ground. A recording on 2026-09-11 measured 0.45 m of
// travel during one lay-flat motion. This function records the position and the direction at the start and writes
// them back on each frame for the given time.
//
// The pin runs for a time and not for an animation state. An earlier version stopped when the state changed, and
// the state changed one frame in, so the pin stopped before the motion that moves the body.
// It writes to the unit only and broadcasts nothing. The engine replicates the position of a local unit.
//
// The provider needs this as much as the casualty does. The drag pickup RTM is authored with the provider taking
// a step back as they take the weight, and that step moves the player away from the casualty.
params [["_patient", objNull, [objNull]], ["_seconds", -1, [0]], ["_pinDir", true, [true]]];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
if !(missionNamespace getVariable ["ACME_interventionAnimations", true]) exitWith {};
if (!isNull objectParent _patient) exitWith {};

if (_seconds <= 0) then {_seconds = missionNamespace getVariable ["ACME_headElev_pinTime", 2.5];};
if (!(_seconds isEqualType 0) || {_seconds <= 0}) exitWith {};

// A newer pin retires the one before it. Only one pin runs on a casualty.
private _token = (_patient getVariable ["ACME_headElev_pinToken", 0]) + 1;
_patient setVariable ["ACME_headElev_pinToken", _token, false];

[{
    params ["_args", "_pfh"];
    _args params ["_p", "_token", "_pos", "_dir", "_until", "_pinDir"];
    private _stop = isNull _p || {!local _p} || {!alive _p} || {!isNull objectParent _p}
        || {!(missionNamespace getVariable ["ACME_interventionAnimations", true])}
        || {(_p getVariable ["ACME_headElev_pinToken", -1]) != _token};
    if (!_stop) then {
        if ((getPosASL _p) distance _pos > 0.005) then {_p setPosASL _pos;};
        if (_pinDir && {abs ((getDir _p) - _dir) > 0.5}) then {_p setDir _dir;};
        _stop = CBA_missionTime > _until;
        // The last frame of the pin puts the unit exactly on the recorded spot.
        if (_stop) then {
            _p setPosASL _pos;
            if (_pinDir) then {_p setDir _dir;};
        };
    };
    if (_stop) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
}, 0, [_patient, _token, getPosASL _patient, getDir _patient, CBA_missionTime + _seconds, _pinDir]] call CBA_fnc_addPerFrameHandler;
