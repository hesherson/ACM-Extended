/*
 * Where the rescuer is local, eight times a second while he drags a SKED: the SKED's strap is turned so that it
 * runs from the SKED's head end up to his left hip (two animations of the model, "strap_pitch" and "strap_yaw").
 * The engine carries the two numbers to every machine and each machine eases the strap to them (0.3 s), so the
 * strap swings after him rather than snapping; nothing is sent while the angle stays within 1.5 degrees, which is
 * all the time the SKED rides straight behind him.
 * (The engine's rope was tried first, for real sag. Measured 2026-11-18: a rope whose ends hang on attached
 * things stays where it was made, taut or slack, woken or not.)
 * Arguments: 0: rescuer, 1: the SKED, 2: lay the strap flat again <BOOL> (default: false).
 */
params ["_unit", "_body", ["_flat", false]];
if (isNull _body) exitWith {};
private _pitch = 0;
private _yaw = 0;
if (!_flat) then {
    private _hip = _unit modelToWorldVisualWorld ((_unit selectionPosition "pelvis") vectorAdd [-0.2, 0.02, 0]);
    private _pivot = _body modelToWorldVisualWorld (_body selectionPosition [getText (configOf _body >> "acmeDragStrapFrom"), "Memory"]);
    private _to = _body vectorWorldToModelVisual (_hip vectorDiff _pivot);
    _yaw = ((_to select 0) atan2 (_to select 1)) max -80 min 80;
    _pitch = ((_to select 2) atan2 (sqrt ((_to select 0) ^ 2 + (_to select 1) ^ 2))) max 0 min 80;
};
// (which way each animation turns was measured in game; the test can turn them over)
(missionNamespace getVariable ["acme_drag_strapSigns", [1, -1]]) params ["_pitchSign", "_yawSign"];
private _last = _body getVariable ["acme_drag_strapAimed", [0, 0]];
if (_flat || {abs (_pitch - (_last select 0)) > 1.5} || {abs (_yaw - (_last select 1)) > 1.5}) then {
    _body setVariable ["acme_drag_strapAimed", [_pitch, _yaw]];
    _body animateSource ["strap_pitch", _pitchSign * _pitch / 90];
    _body animateSource ["strap_yaw", _yawSign * _yaw / 90];
};
