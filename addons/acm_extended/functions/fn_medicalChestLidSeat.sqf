/* The stock drawer front is -Z. The loose lid's painted face is +Y. */
params ["_chest", "_cabinet", "_lid"];
private _outward = vectorNormalized (_cabinet vectorModelToWorld [0, 0, -1]);
private _up = [0, 0, 1] vectorCrossProduct _outward;
private _frontEdge = (0 boundingBoxReal _cabinet) select 0 select 2;
private _drawerFace = _cabinet modelToWorldWorld [0, 0, _frontEdge];
private _shellEdge = (0 boundingBoxReal _chest) select 1 select 1;
private _shellFace = _chest modelToWorldWorld [0, _shellEdge, 0];
(0 boundingBoxReal _lid) params ["_lidMin", "_lidMax"];
private _shellOffset = ((_shellFace vectorDiff _drawerFace) vectorDotProduct _outward) - (_lidMax select 1);
private _drawerClearance = 0.012 - (_lidMin select 1);
private _seat = _drawerFace vectorAdd (_outward vectorMultiply (_shellOffset max _drawerClearance));
[_seat, _outward, _up]
