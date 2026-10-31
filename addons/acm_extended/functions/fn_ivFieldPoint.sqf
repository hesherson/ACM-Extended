/* Field authoring canvas: 2048 x 2304, primary socket [1006.5,1037].
   Apply a single physical-pixel transform inherited from the placed catheter. */
params ["_row",["_point",[1006.5,1037]]];
private _g=[_row] call ACME_fnc_ivFinishGeometry;
if (count _g!=5) exitWith {[]};
_g params ["_x","_y","_w","_h","_a"];
private _du=((_point select 0)-1006.5)/2048;
private _dv=((_point select 1)-1037)/2048;
[_x+_w*(_du*cos _a-_dv*sin _a),_y+_h*(_du*sin _a+_dv*cos _a)]
