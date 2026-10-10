/* Register an accessory to its catheter's connector socket. No independent
   screen-upright rotation, no replacement of the gauge-specific native hub. */
params ["_ctrl","_row",["_socketV",1032/2048]];
private _g=[_row] call ACME_fnc_ivFinishGeometry;
if (isNull _ctrl || {_g isEqualTo []}) exitWith {};
_ctrl setVariable ["ACME_IV_FieldPose",[]];
_g params ["_x","_y","_w","_h","_angle"];
private _u=1006.5/2048;private _v=_socketV;
private _pose=[_x-_w*_u,_y-_h*_v,_w,_h,_angle];
if ((_ctrl getVariable ["ACME_IV_FinishPose",[]]) isNotEqualTo _pose) then {
    _ctrl ctrlSetPosition [_pose select 0,_pose select 1,_w,_h];
    _ctrl ctrlSetAngle [_angle,_u,_v,false];_ctrl ctrlCommit 0;
    _ctrl setVariable ["ACME_IV_FinishPose",_pose];
};
