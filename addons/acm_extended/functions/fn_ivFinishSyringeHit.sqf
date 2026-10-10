/* Inverse of the accessory transform: only the actual syringe starts a yank. */
params ["_row","_cursor"];
private _state=_row param [15,[]];
private _direct=(_state param [4,false]) && {!(_state param [0,false])};
_row=[_row,_direct] call ACME_fnc_ivFieldAccessoryRow;
private _g=[_row] call ACME_fnc_ivFinishGeometry;
if (count _g!=5 || {count _cursor!=2}) exitWith {false};
_g params ["_x","_y","_w","_h","_a"];
private _dx=((_cursor select 0)-_x)/(_w max 1e-9);
private _dy=((_cursor select 1)-_y)/(_h max 1e-9);
private _u=1006.5/2048+_dx*cos _a+_dy*sin _a;
private _v=1032/2048-_dx*sin _a+_dy*cos _a;
_u>=980/2048 && {_u<=1085/2048} && {_v>=1380/2048} && {_v<=1960/2048}
