/*
 * Where a litter's interaction points are, in the litter's own axes. They float over the litter: on the deck they
 * lay inside the casualty, among his own points, and could not be reached ("move the sked ace interaction to be
 * floating a little bit above the sked because it interferes with being able to reach the interaction",
 * 2026-11-20).
 *   "mid"   the litter's menu, half a metre over its middle: over a casualty who lies on it
 *   "head"  over the two handles of the head end (a litter with four handles: the Talon II)
 *   "foot"  over the two handles of the foot end
 * Arguments: 0: litter, 1: which. Returns: position in model space.
 */
params ["_litter", ["_which", "mid"]];
private _handles = (getArray (configOf _litter >> "acmeLitterHandles")) apply {_litter selectionPosition [_x, "Memory"]};
if (count _handles != 4 || {(_handles findIf {_x isEqualTo [0, 0, 0]}) >= 0}) exitWith {
    (_litter selectionPosition ["center", "Memory"]) vectorAdd [0, 0, 0.5]
};
_handles params ["_hl", "_hr", "_fl", "_fr"];
if (_which == "head") exitWith {((_hl vectorAdd _hr) vectorMultiply 0.5) vectorAdd [0, 0, 0.3]};
if (_which == "foot") exitWith {((_fl vectorAdd _fr) vectorMultiply 0.5) vectorAdd [0, 0, 0.3]};
// (a litter that is laid out has no casualty on it: its menu need not be as high)
private _up = [0.3, 0.55] select (!isNull (_litter getVariable ["acme_sked_patient", objNull]));
((_hl vectorAdd _hr vectorAdd _fl vectorAdd _fr) vectorMultiply 0.25) vectorAdd [0, 0, _up]
