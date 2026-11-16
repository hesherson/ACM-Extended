/*
 * Server: a casualty stowed in a vehicle with their SKED has been unloaded. If they are still down (or
 * dead), the SKED is made again round them where ACE put them. Otherwise (awake and conscious casualties
 * not strapped in, or they cannot be strapped in now) the SKED is left laid out beside them, the shell
 * unsqueezed and their ACE drag and carry given back.
 * Arguments: 0: casualty.
 */
params ["_patient"];
if (!isServer || {!(_patient getVariable ["acme_sked_stowed", false])}) exitWith {};
if (!isNull objectParent _patient) exitWith {};
private _class = _patient getVariable ["acme_sked_stowedOpen", "ACME_SKED_Open"];
_patient setVariable ["acme_sked_stowedOpen", nil, true];
_patient setVariable ["acme_sked_stowed", nil, true];
["unloaded", objNull, _patient, [_class]] call acme_sked_fnc_traceTransport;
private _giveBack = {
    params ["_patient"];
    [_patient, "hpmkSwap", [_patient, false]] call acme_sked_fnc_sendLocal;
    [_patient] call acme_sked_fnc_srvDragOn;
};
private _awake = alive _patient && {lifeState _patient in ["HEALTHY", "INJURED"]};
if (_awake && {!(missionNamespace getVariable ["acme_sked_allowConscious", false])}) exitWith {
    [_class, _patient getRelPos [1.2, 90], getDir _patient] call acme_sked_fnc_place;
    [_patient] call _giveBack;
};
// Lay the SKED along the body: head end toward the head, its casualty point under the chest. If the body
// gives no clear direction (head over pelvis), use the unit's own.
private _headW = _patient modelToWorldVisual ([_patient, "head"] call acme_sked_fnc_selPos);
private _pelW = _patient modelToWorldVisual ([_patient, "pelvis"] call acme_sked_fnc_selPos);
private _dir = if ((_pelW distance2D _headW) > 0.3) then {_pelW getDir _headW} else {getDir _patient};
private _chest = _pelW vectorAdd ((_headW vectorDiff _pelW) vectorMultiply 0.6);
private _pos = _chest vectorDiff [0.40 * sin _dir, 0.40 * cos _dir, 0];
private _open = [_class, _pos, _dir] call acme_sked_fnc_place;
if (isNull ([objNull, _patient, _open] call acme_sked_fnc_srvLoad)) then {
    [_patient] call _giveBack;
};
