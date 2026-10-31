/* Every hit target and cursor uses the same socket/angle as the drawn layer. */
params ["_row",["_point",[1006.5/2048,1032/2048]],["_origin",[1006.5/2048,1032/2048]]];
private _g=[_row] call ACME_fnc_ivFinishGeometry;
if (_g isEqualTo []) exitWith {[]};
_g params ["_x","_y","_w","_h","_a"];
private _du=(_point select 0)-(_origin select 0);
private _dv=(_point select 1)-(_origin select 1);
[_x+_w*(_du*cos _a-_dv*sin _a),_y+_h*(_du*sin _a+_dv*cos _a)]
