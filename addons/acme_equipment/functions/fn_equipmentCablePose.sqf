/* Eight centered unit-cylinder transforms. No physics, forces, or terrain-height replacement. */
params ["_from","_to"];
if !(_from isEqualType [] && {_to isEqualType []} && {count _from==3} && {count _to==3}
    && {_from isEqualTypeAll 0} && {_to isEqualTypeAll 0}
    && {(_from findIf {!finite _x}) < 0} && {(_to findIf {!finite _x}) < 0}) exitWith {[]};
private _distance=_from distance _to;
if (_distance < 0.01 || {_distance > 7}) exitWith {[]};
private _floor=((_from select 2) min (_to select 2))-0.015;
private _slack=(_distance*0.08) min 0.12;
private _point={
    params ["_t"];
    private _p=_from vectorAdd ((_to vectorDiff _from) vectorMultiply _t);
    _p set [2,((_p select 2)-4*_slack*_t*(1-_t)) max _floor];_p
};
private _out=[];private _a=[0] call _point;
for "_i" from 1 to 8 do {
    private _b=[_i/8] call _point;private _delta=_b vectorDiff _a;
    private _length=vectorMagnitude _delta;
    private _dir=vectorNormalized _delta;
    private _right=_dir vectorCrossProduct [0,0,1];
    if (vectorMagnitude _right < 0.01) then {_right=_dir vectorCrossProduct [1,0,0];};
    private _up=vectorNormalized (_right vectorCrossProduct _dir);
    _out pushBack [(_a vectorAdd _b) vectorMultiply 0.5,_dir,_up,_length];_a=_b;
};
_out
