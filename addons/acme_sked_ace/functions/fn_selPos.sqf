/*
 * Position of a body part of a unit, in the unit's model space, as animated: the middle of its hit box in the
 * FireGeometry LOD. Not the first point of that box (the default of the command): that is one corner, up to
 * 20 cm from the middle, and axes built from such corners rolled the casualty 47 degrees on the litter
 * (measured in game, 2026-11-17). The bone points of the Memory LOD are the fallback.
 * Arguments: 0: unit, 1: selection name. Returns: position.
 */
params ["_unit", "_name"];
private _p = _unit selectionPosition [_name, "FireGeometry", "AveragePoint"];
if (_p isEqualTo [0, 0, 0]) then {_p = _unit selectionPosition [_name, "Memory"];};
if (_p isEqualTo [0, 0, 0]) then {_p = _unit selectionPosition _name;};
_p
