/* B276 pure viewport math. Offset is clamped after a filter/refresh; slots have no phantom row. */
params ["_count","_capacity",["_offset",0],["_selected",-1],["_reveal",false]];
_capacity = (floor _capacity) max 1;
_count = (floor _count) max 0;
_offset = (floor _offset) max 0 min ((_count - _capacity) max 0);
if (_reveal && {_selected >= 0} && {_selected < _count}) then {
    if (_selected < _offset) then {_offset = _selected;};
    if (_selected >= _offset + _capacity) then {_offset = _selected - _capacity + 1;};
};
private _rows = [];
for "_slot" from 0 to (_capacity - 1) do {
    _rows pushBack (if (_offset + _slot < _count) then {_offset + _slot} else {-1});
};
[_offset,_rows,_offset > 0,_offset + _capacity < _count]
