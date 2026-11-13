/* Seat the model at the supplied ASL surface. Heading is measured from the equipment to the operator. */
params ["_device","_pose",["_actor",objNull]];
_pose params ["_position","_direction"];
if (!isNull _actor) then {
    _direction = [_device,_position,_actor,_direction] call ACME_fnc_equipmentFacing;
};
_device setVectorDirAndUp [_direction,[0,0,1]];
private _bottom=((boundingBoxReal _device) select 0) select 2;
_device setPosWorld (_position vectorAdd [0,0,0.005-_bottom]);
