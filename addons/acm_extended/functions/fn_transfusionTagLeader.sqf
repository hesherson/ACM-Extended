/* B275: RscLine ending exactly on the tag's top inner corner.
   Positive width plus signed height matches the native AED monitor convention. */
params ["_anchor", "_tag", ["_left", false]];
if (count _anchor != 4 || {count _tag != 4}) exitWith {[]};
_anchor params ["_ax", "_ay", "_aw", "_ah"];
_tag params ["_tx", "_ty", "_tw", "_th"];
private _startX = if (_left) then {_ax} else {_ax + _aw};
private _startY = _ay + _ah / 2;
private _endX = if (_left) then {_tx + _tw} else {_tx};
if (_endX < _startX) then {
    [_endX, _ty, _startX - _endX, _startY - _ty]
} else {
    [_startX, _startY, _endX - _startX, _ty - _startY]
}
