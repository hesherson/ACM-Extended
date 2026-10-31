/* B217 fixed ground park, shared by manual custody and chest workspaces.
 * Anatomical left is projected from the shoulder selections, not the observer/camera or world X axis.
 * Capture this target once on the prop; later rolling must not drag the carrier around the casualty.
 */
params ["_patient"];
private _pel = _patient modelToWorldVisual (_patient selectionPosition "pelvis");
private _head = _patient modelToWorldVisual (_patient selectionPosition "head");
private _axis = [(_head select 0) - (_pel select 0), (_head select 1) - (_pel select 1), 0];
if (vectorMagnitude _axis < 0.05) then {_axis = [sin getDir _patient, cos getDir _patient, 0];};
_axis = vectorNormalized _axis;
private _leftShoulder = _patient modelToWorldVisual (_patient selectionPosition "leftshoulder");
private _rightShoulder = _patient modelToWorldVisual (_patient selectionPosition "rightshoulder");
private _left = [(_leftShoulder select 0) - (_rightShoulder select 0), (_leftShoulder select 1) - (_rightShoulder select 1), 0];
// Supported supine fallback when a model supplies no usable shoulder separation.
if (vectorMagnitude _left < 0.05) then {_left = [-(_axis select 1), _axis select 0, 0];};
_left = vectorNormalized _left;
private _gap = missionNamespace getVariable ["ACME_headElev_propGroundGap", 0.45];
private _side = 0.75;
private _pos = (_head vectorAdd (_axis vectorMultiply _gap)) vectorAdd (_left vectorMultiply _side);
_pos set [2, 0.02];
[_pos, _axis, surfaceNormal [_pos select 0, _pos select 1]]
