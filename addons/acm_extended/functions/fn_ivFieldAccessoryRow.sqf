/* Reuse B233 accessory sprites unchanged, translated to the current upstream socket.
   For bare-port flushing/lines, the synthetic transform maps their distal anchor to that port. */
params ["_row",["_direct",false]];
private _state=_row param [15,[]];
if !(_state param [4,false]) exitWith {+_row};
private _y=if ((_state param [5,0])>0) then {1189} else {1088};
private _point=[1006.5,_y];
if (_direct) then {_point=[1006.5-(1033.02-1006.5),_y-(1386.52-1052)];};
private _socket=[_row,_point] call ACME_fnc_ivFieldPoint;
private _g=[_row] call ACME_fnc_ivFinishGeometry;
private _r=uiNamespace getVariable ["ACME_IV_BodyRect",[]];
if (count _g!=5 || {count _r!=4}) exitWith {+_row};
private _copy=+_row;
_copy set [2,(_row select 2)+((_socket select 0)-(_g select 0))/(_r select 2)];
_copy set [3,(_row select 3)+((_socket select 1)-(_g select 1))/(_r select 3)];
_copy
