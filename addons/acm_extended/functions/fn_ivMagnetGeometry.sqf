/* B235: pure physical-square attraction geometry. Cursor never warps.
   Smooth attraction over 5.2% body height, exact seating only within 0.4%.
   Preserve the authored rotation pivot (and therefore its clipping bounds).
   _target is the chosen logical contact point in the final installed pose. */
params ["_cursor","_target","_rect","_angle","_pivot","_aspect","_bodyH"];
_rect params ["_left","_top","_w","_h"];
if (_w<=0 || {_h<=0} || {_aspect<=0} || {_bodyH<=0}) exitWith {[_rect,_angle,0]};
private _dx=((_cursor select 0)-(_target select 0))/_aspect;
private _dy=(_cursor select 1)-(_target select 1);
private _distance=sqrt (_dx*_dx+_dy*_dy);
private _near=_bodyH*0.004;private _far=_bodyH*0.052;
private _t=((_far-_distance)/(_far-_near)) max 0 min 1;
private _blend=_t*_t*(3-2*_t);
// Shortest angular path, including the EJ orientation across +/-180 degrees.
private _short=(((_angle+180) mod 360)+360) mod 360-180;
private _turn=_short*_blend;
private _px=_left+_w*(_pivot select 0);private _py=_top+_h*(_pivot select 1);
// Recover the contact UV relative to the authored pivot from the final pose.
private _a=((_target select 0)-_px)/_w;private _b=((_target select 1)-_py)/_h;
private _u=_a*cos _angle+_b*sin _angle;private _v=-_a*sin _angle+_b*cos _angle;
private _cx=(_cursor select 0)+((_target select 0)-(_cursor select 0))*_blend;
private _cy=(_cursor select 1)+((_target select 1)-(_cursor select 1))*_blend;
private _x=_cx-_w*(_u*cos _turn-_v*sin _turn)-_w*(_pivot select 0);
private _y=_cy-_h*(_u*sin _turn+_v*cos _turn)-_h*(_pivot select 1);
[[_x,_y,_w,_h],_turn,_blend]
