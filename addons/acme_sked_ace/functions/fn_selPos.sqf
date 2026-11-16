/*
 * Position of a body part of a unit, in the unit's model space, as animated. Reads the FireGeometry LOD
 * (pelvis, spine3, head, leftshoulder, rightshoulder are there on the Arma 3 man); falls back to the
 * default search.
 * Arguments: 0: unit, 1: selection name. Returns: position.
 */
params ["_unit", "_name"];
private _p = _unit selectionPosition [_name, "FireGeometry"];
if (_p isEqualTo [0, 0, 0]) then {_p = _unit selectionPosition _name};
_p
