/*
 * Place a local casualty on a litter. The result (offset, direction and up, in litter axes) is kept on the
 * litter for re-attaching later.
 *
 * A living casualty is in the lying pose, and that pose is flat in the unit's own model space: the back is on
 * the plane z = 0 and the front faces up. So the unit is only turned about its own up axis and slid: its up is
 * the litter's up, the line from its pelvis to its head goes to the litter's +Y, the middle of its chest goes
 * over the litter's chest point, and its back goes on the bed (acmeLitterBedHeight). Nothing here can roll or
 * pitch the body. Measured in game on 2026-11-17: the earlier fit of a full body frame to single hit box
 * corners rolled the casualty 47 degrees, and the same fit to bone points pitched the legs into the air.
 *
 * A dead casualty lies as it fell, in no known pose, so its whole frame is taken from the middles of its hit
 * boxes (pelvis, head, shoulders) and its chest is put over the chest point.
 *
 * Arguments: 0: casualty, 1: litter, 2: second pass <BOOL> (no longer needed: the first pass is exact),
 * 3: only work the place out <BOOL>. Returns with 3: [offset, direction, up] in litter axes.
 */
params ["_patient", "_litter", ["_correct", false], ["_only", false]];
if (_correct) exitWith {};
private _cfg = configOf _litter;
// The middle of the chest, from the config: the laid out SKED has no chest point of its own, and the casualty is
// laid on it before the occupied model takes its place (measured in game, 2026-11-17: SKED 3 cm toward the head
// of its chest strap, Talon II in the middle of the deck).
private _chest = getArray (_cfg >> "acmeLitterChest");
if (count _chest < 2) then {
    _chest = _litter selectionPosition [getText (_cfg >> "acmeLitterChestPoint"), "Memory"];
};
private _target = [
    (_chest select 0) + (missionNamespace getVariable ["acme_sked_offsetX", 0]),
    (_chest select 1) + (missionNamespace getVariable ["acme_sked_offsetY", 0]),
    0
];
private _bed = (if (isNumber (_cfg >> "acmeLitterBedHeight")) then {getNumber (_cfg >> "acmeLitterBedHeight")} else {0})
    + (missionNamespace getVariable ["acme_sked_offsetZ", 0]);
private _pel = [_patient, "pelvis"] call acme_sked_fnc_selPos;
private _head = [_patient, "head"] call acme_sked_fnc_selPos;
private _sp3 = [_patient, "spine3"] call acme_sked_fnc_selPos;

if (alive _patient) exitWith {
    private _axis = _head vectorDiff _pel;
    _axis set [2, 0];
    if (vectorMagnitude _axis < 0.2) then {_axis = [0, 1, 0];};
    _axis = vectorNormalized _axis;
    _axis params ["_ax", "_ay"];
    // The turn about the up axis that takes _axis to +Y takes a point (x, y) to (ay x - ax y, ax x + ay y).
    private _dir = [-_ax, _ay, 0];
    private _off = [
        (_target select 0) - (_ay * (_sp3 select 0) - _ax * (_sp3 select 1)),
        (_target select 1) - (_ax * (_sp3 select 0) + _ay * (_sp3 select 1)),
        _bed
    ];
    if (_only) exitWith {[_off, _dir, [0, 0, 1]]};
    _litter setVariable ["acme_sked_attach", [_off, _dir, [0, 0, 1]], true];
    [_patient, _litter] call acme_sked_fnc_reattach;
};

private _ls = [_patient, "leftshoulder"] call acme_sked_fnc_selPos;
private _rs = [_patient, "rightshoulder"] call acme_sked_fnc_selPos;
private _yb = _head vectorDiff _pel;
if (vectorMagnitude _yb < 0.1) then {_yb = [0, 1, 0]};
_yb = vectorNormalized _yb;
private _xt = _ls vectorDiff _rs;
if (vectorMagnitude _xt < 0.05) then {_xt = [1, 0, 0]};
private _zb = vectorNormalized (_xt vectorCrossProduct _yb);
private _xb = _yb vectorCrossProduct _zb;
// The casualty's model axes, in litter axes.
private _dir = [_xb select 1, _yb select 1, _zb select 1];
private _up = [_xb select 2, _yb select 2, _zb select 2];
private _m = [_xb vectorDotProduct _sp3, _yb vectorDotProduct _sp3, _zb vectorDotProduct _sp3];
// The middle of the chest is about 9 cm over the back.
private _off = [_target select 0, _target select 1, _bed + 0.09] vectorDiff _m;
if (_only) exitWith {[_off, _dir, _up]};
_litter setVariable ["acme_sked_attach", [_off, _dir, _up], true];
[_patient, _litter] call acme_sked_fnc_reattach;
