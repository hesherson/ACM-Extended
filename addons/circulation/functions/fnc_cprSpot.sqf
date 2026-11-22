#include "..\script_component.hpp"
/*
 * Author: mavis
 * B373: the place and the direction at which the authored compressions (ACME_CPR) put the provider's hands on
 * the casualty's sternum, on the side of the casualty where the provider is now.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 *
 * Return Value:
 * [position ASL, direction, loop state, entry state, hold state, exit state] <ARRAY>, or [] when there is no usable place
 *
 * Example:
 * [player, cursorTarget] call ACM_circulation_fnc_cprSpot;
 *
 * Public: No
 */

params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]]];
if (isNull _medic || {isNull _patient}) exitWith {[]};

// From the build of the animation: the sternum is 0.733 m in front of the unit and 0.021 m to its right,
// and 0.063 m from the spine3 bone toward the pelvis.
#define CPR_FRONT 0.733
#define CPR_RIGHT 0.021
#define CPR_STERNUM_DOWN 0.063
#define CPR_MAX_MOVE 3

private _spine3 = _patient modelToWorldVisualWorld (_patient selectionPosition "spine3");
private _pelvis = _patient modelToWorldVisualWorld (_patient selectionPosition "pelvis");
private _head = _patient modelToWorldVisualWorld (_patient selectionPosition "head");
private _axis = _head vectorDiff _pelvis;
_axis set [2, 0];
if ((vectorMagnitude _axis) < 0.2) exitWith {[]};
_axis = vectorNormalized _axis;

private _sternum = _spine3 vectorAdd (_axis vectorMultiply (-CPR_STERNUM_DOWN));
private _perp = [-(_axis select 1), _axis select 0, 0];
private _medicPos = getPosASL _medic;

private _side = [1, -1] select (((_medicPos vectorDiff _sternum) vectorDotProduct _perp) < 0);
private _face = _perp vectorMultiply (-_side);
private _rightDir = [_face select 1, -(_face select 0), 0];
private _pos = (_sternum vectorDiff (_face vectorMultiply CPR_FRONT)) vectorDiff (_rightDir vectorMultiply CPR_RIGHT);
_pos set [2, _medicPos select 2];
if ((_medicPos distance2D _pos) > CPR_MAX_MOVE) exitWith {[]};

// Nothing solid between the provider and the place, at the height of the hips.
private _hits = lineIntersectsSurfaces [_medicPos vectorAdd [0, 0, 0.9], _pos vectorAdd [0, 0, 0.9], _medic, _patient, true, 1, "GEOM", "NONE"];
if (_hits isNotEqualTo []) exitWith {[]};

// The looks to the casualty's face go to the left in ACME_CPR and to the right in ACME_CPR_L.
private _leftDir = [-(_face select 1), _face select 0, 0];
private _headLeft = (_axis vectorDotProduct _leftDir) > 0;

// On a litter whose bed is well off the ground (the Talon II: 0.148 m) the hands of the ground animations would be
// inside the chest: the raised set (ACME_CPR_T*, the hands that much higher over the same place) is used.
// ("there needs to be a small adjusted version for doing CPR on the TALON II litter", 2026-11-21)
private _litter = _patient getVariable ["acme_sked_litter", objNull];
private _set = if (!isNull _litter && {getNumber (configOf _litter >> "acmeLitterBedHeight") >= 0.1}) then {"ACME_CPR_T"} else {"ACME_CPR"};

[_pos, (_face select 0) atan2 (_face select 1), [_set + "_L", _set] select _headLeft, [_set + "_In_L", _set + "_In"] select _headLeft, _set + "_Hold", _set + "_Out"]
