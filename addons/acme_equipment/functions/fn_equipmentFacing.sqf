/* Convert the visible face to the object's +Y heading. The Tempus screen normal comes from its model. */
params ["_device","_position","_actor","_fallback"];
private _direction = (getPosWorld _actor) vectorDiff _position;
_direction set [2,0];
if (vectorMagnitude _direction < 0.04) then {
    _direction = (vectorDir _actor) vectorMultiply -1;
    _direction set [2,0];
};
if (vectorMagnitude _direction < 0.04) exitWith {_fallback};
private _offset = 0;
if (_device isKindOf "ACME_AccuvacRescue") then {
    private _keypad = _device selectionPosition ["keypad","Memory"];
    if ((_keypad select 0) != 0 || {(_keypad select 1) != 0}) then {
        _offset = (_keypad select 0) atan2 (_keypad select 1);
    };
};
if (_device isKindOf "ACME_TempusPro" || {_device isKindOf "ACME_TempusLS"}) then {
    private _bl = _device selectionPosition ["scr_bl","Memory"];
    private _right = (_device selectionPosition ["scr_br","Memory"]) vectorDiff _bl;
    private _up = (_device selectionPosition ["scr_tl","Memory"]) vectorDiff _bl;
    private _normal = _right vectorCrossProduct _up;
    if (vectorMagnitude _normal > 0.00001) then {_offset = (_normal select 0) atan2 (_normal select 1);};
};
private _angle = ((_direction select 0) atan2 (_direction select 1)) - _offset;
[sin _angle,cos _angle,0]
