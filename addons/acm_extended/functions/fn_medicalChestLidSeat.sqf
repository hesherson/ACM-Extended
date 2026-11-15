/* Use the placed shell's heading. The open models can have different native axes. */
params ["_chest", "_cabinet", "_lid", "_heading"];
private _forward = [sin _heading, cos _heading, 0];
private _up = [-(cos _heading), sin _heading, 0];
private _center = getPosWorld _chest;
private _shellFront = (0 boundingBoxReal _chest) select 1 select 1;

private _cabinetDir = vectorDir _cabinet;
private _cabinetUp = vectorUp _cabinet;
private _cabinetAxes = [_cabinetDir vectorCrossProduct _cabinetUp, _cabinetDir, _cabinetUp];
(0 boundingBoxReal _cabinet) params ["_cabinetMin", "_cabinetMax"];
private _cabinetFront = (getPosWorld _cabinet vectorDiff _center) vectorDotProduct _forward;
{
    private _projection = _x vectorDotProduct _forward;
    private _edge = [_cabinetMin, _cabinetMax] select (_projection >= 0);
    _cabinetFront = _cabinetFront + _projection * (_edge select _forEachIndex);
} forEach _cabinetAxes;

(0 boundingBoxReal _lid) params ["_lidMin", "_lidMax"];
private _shellSeat = _shellFront - (_lidMax select 1);
private _clearSeat = _cabinetFront - (_lidMin select 1) + 0.012;
private _position = _center vectorAdd (_forward vectorMultiply (_shellSeat max _clearSeat));
[_position, _forward, _up]
