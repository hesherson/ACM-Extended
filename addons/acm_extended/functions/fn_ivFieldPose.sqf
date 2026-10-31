/* Field layers are padded square canvases, avoiding non-square rotation distortion
   and clipping for EJ/inverted views. They retain the original pixel density. */
params ["_ctrl","_row"];
private _g=[_row] call ACME_fnc_ivFinishGeometry;
if (isNull _ctrl || {count _g!=5}) exitWith {};
_g params ["_x","_y","_w","_h","_angle"];
private _pose=[_x-_w,_y-_h,2*_w,2*_h,_angle];
if ((_ctrl getVariable ["ACME_IV_FieldPose",[]]) isNotEqualTo _pose) then {
    _ctrl setVariable ["ACME_IV_FinishPose",[]];
    _ctrl ctrlSetPosition (_pose select [0,4]);
    _ctrl ctrlSetAngle [_angle,0.5,0.5,false];_ctrl ctrlCommit 0;
    _ctrl setVariable ["ACME_IV_FieldPose",_pose];
};
