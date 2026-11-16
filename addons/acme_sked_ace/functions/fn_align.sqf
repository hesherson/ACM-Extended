/*
 * Place a local casualty in the SKED. The body axes come from the casualty's pelvis, head and shoulders:
 * toward the head goes to the SKED's +Y, toward their left to +X, the face to +Z. Their chest (spine3)
 * goes to the SKED's memory point pt_spine3, moved by the calibration settings. The result (offset,
 * direction and up, in SKED axes) is kept on the SKED for re-attaching later.
 * With _correct, measure where the chest landed and move the casualty by the difference.
 * Arguments: 0: casualty, 1: SKED, 2: correct <BOOL>.
 */
params ["_patient", "_litter", ["_correct", false]];
private _cal = [
    missionNamespace getVariable ["acme_sked_offsetX", 0],
    missionNamespace getVariable ["acme_sked_offsetY", 0],
    missionNamespace getVariable ["acme_sked_offsetZ", 0]
];
private _point = getText (configOf _litter >> "acmeLitterChestPoint");
private _target = (_litter selectionPosition [_point, "Memory"]) vectorAdd _cal;
if (_correct) exitWith {
    (_litter getVariable ["acme_sked_attach", []]) params [["_off", []], ["_dir", [0, 1, 0]], ["_up", [0, 0, 1]]];
    if (_off isEqualTo [] || {!((attachedTo _patient) isEqualTo _litter)}) exitWith {};
    private _now = _litter worldToModelVisual (_patient modelToWorldVisual ([_patient, "spine3"] call acme_sked_fnc_selPos));
    private _err = _now vectorDiff _target;
    if (vectorMagnitude _err < 0.004 || {vectorMagnitude _err > 1.5}) exitWith {};
    _off = _off vectorDiff _err;
    _patient attachTo [_litter, _off];
    _patient setVectorDirAndUp [_dir, _up];
    _litter setVariable ["acme_sked_attach", [_off, _dir, _up], true];
};
private _pel = [_patient, "pelvis"] call acme_sked_fnc_selPos;
private _head = [_patient, "head"] call acme_sked_fnc_selPos;
private _sp3 = [_patient, "spine3"] call acme_sked_fnc_selPos;
private _ls = [_patient, "leftshoulder"] call acme_sked_fnc_selPos;
private _rs = [_patient, "rightshoulder"] call acme_sked_fnc_selPos;
private _yb = _head vectorDiff _pel;
if (vectorMagnitude _yb < 0.1) then {_yb = [0, 1, 0]};
_yb = vectorNormalized _yb;
private _xt = _ls vectorDiff _rs;
if (vectorMagnitude _xt < 0.05) then {_xt = [1, 0, 0]};
private _zb = vectorNormalized (_xt vectorCrossProduct _yb);
private _xb = _yb vectorCrossProduct _zb;
// The casualty's model axes, in SKED axes.
private _dir = [_xb select 1, _yb select 1, _zb select 1];
private _up = [_xb select 2, _yb select 2, _zb select 2];
private _m = [_xb vectorDotProduct _sp3, _yb vectorDotProduct _sp3, _zb vectorDotProduct _sp3];
private _off = _target vectorDiff _m;
_litter setVariable ["acme_sked_attach", [_off, _dir, _up], true];
[_patient, _litter] call acme_sked_fnc_reattach;
