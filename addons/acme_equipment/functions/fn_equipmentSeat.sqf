/* Orient first, then seat the actual model's lowest corner on the selected surface. */
params ["_device","_pose"];
_pose params ["_position","_direction"];
_device setVectorDirAndUp [_direction,[0,0,1]];
private _bottom=((boundingBoxReal _device) select 0) select 2;
_device setPosWorld (_position vectorAdd [0,0,0.005-_bottom]);
