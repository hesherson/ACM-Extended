/* Retire only this menu's visual worker and owned scene effect. */
params ["_display"];
private _id = _display getVariable ["ACME_glassPFH",-1];
_display setVariable ["ACME_glassPFH",-1];
if (_id >= 0) then {[_id] call CBA_fnc_removePerFrameHandler;};
_display setVariable ["ACME_glassEntries",[]];
[_display,false] call ACME_fnc_uiGlassBlur;
