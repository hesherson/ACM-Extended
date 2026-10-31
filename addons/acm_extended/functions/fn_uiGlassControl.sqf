/* Dynamic UI factory. Decorator first, original control last; preserve its input surface. */
disableSerialization;
params ["_display","_class","_id",["_parent",controlNull],["_profile","button"]];
private _frameArgs = ["ACME_TransfusionRoundedFrame",-1];
private _targetArgs = [_class,_id];
if (!isNull _parent) then {_frameArgs pushBack _parent;_targetArgs pushBack _parent;};
private _frame = _display ctrlCreate _frameArgs;
private _target = _display ctrlCreate _targetArgs;
if (!isNull _target && {!isNull _frame}) then {[_display,_target,_frame,_profile] call ACME_fnc_uiGlassTrack;};
_target
