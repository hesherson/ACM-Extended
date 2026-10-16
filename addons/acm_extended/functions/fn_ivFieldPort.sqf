/* Active downstream socket. A secondary hub replaces the lock as the port, not the vein. */
params ["_row"];
private _state=_row param [15,[]];
private _secondary=(_state param [5,0])>0;
private _y=if (_secondary) then {1189} else {1088};
if (_state param [0,false]) then {[1033.02,_y+334.52]} else {[1006.5,_y]}
