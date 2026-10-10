/* Virtual drawing row ONLY. No mark/native access is registered for the second catheter.
   Its external socket seats at exactly the authored downstream socket. */
params ["_row",["_gauge",0]];
private _copy=+_row;
private _r=uiNamespace getVariable ["ACME_IV_BodyRect",[]];
if (count _r!=4 || {(_r select 2)<=0} || {(_r select 3)<=0}) exitWith {[]};
private _socket=[_row,[1006.5,1189]] call ACME_fnc_ivFieldPoint;
private _g=[_row] call ACME_fnc_ivFinishGeometry;
_copy set [2,(_row select 2)+((_socket select 0)-(_g select 0))/(_r select 2)];
_copy set [3,(_row select 3)+((_socket select 1)-(_g select 1))/(_r select 3)];
if (_gauge<=0) then {_gauge=(_row param [15,[]]) param [5,16];};
_copy set [7,_gauge];_copy set [5,""];
_copy
