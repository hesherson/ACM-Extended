/* World/ASL throughout; surface raycasts keep raised floors, ships and altitude intact. */
params ["_patient","_kind"];
private _hip = _patient modelToWorldVisualWorld (_patient selectionPosition "pelvis");
private _head = _patient modelToWorldVisualWorld (_patient selectionPosition "head");
private _toward = _head vectorDiff _hip;
_toward set [2,0];
if (vectorMagnitude _toward < 0.15) then {_toward=vectorDirVisual _patient;_toward set [2,0];};
_toward=vectorNormalized _toward;
private _right=[_toward select 1,-(_toward select 0),0];
([_kind] call ACME_fnc_equipmentLayout) params ["_x","_y"];
private _position=_hip vectorAdd (_right vectorMultiply _x) vectorAdd (_toward vectorMultiply _y);
private _hits=lineIntersectsSurfaces [_position vectorAdd [0,0,0.6],_position vectorAdd [0,0,-2.5],_patient,objectParent _patient,true,1,"GEOM","VIEW"];
if (_hits isEqualTo []) exitWith {[]};
_position=(_hits select 0) select 0;
[_position,_toward vectorMultiply -1]
