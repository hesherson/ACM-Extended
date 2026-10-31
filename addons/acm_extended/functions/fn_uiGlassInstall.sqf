/* B295 appearance only. Static frames are authored below original controls; input stays native. */
disableSerialization;
params ["_display",["_class",""]];
if (!hasInterface || {isNull _display} || {_display getVariable ["ACME_glassInstalled",false]}) exitWith {};
_display setVariable ["ACME_glassInstalled",true];
private _controls = allControls _display;
{
    _x params ["_frameId","_name","_profile"];
    private _at = _controls findIf {ctrlClassName _x == _name};
    if (_at >= 0) then {
        [_display,_controls select _at,_display displayCtrl _frameId,_profile] call ACME_fnc_uiGlassTrack;
    };
} forEach (getArray (configFile >> _class >> "acmeGlassTargets"));
[_display,true] call ACME_fnc_uiGlassBlur;
_display displayAddEventHandler ["Unload",{[_this select 0] call ACME_fnc_uiGlassClose;}];
// Only while this display exists. No global idle scan and no control allocation on refresh.
_display setVariable ["ACME_glassPFH",[{
    params ["_args","_id"];
    _args params ["_view"];
    if (isNull _view) exitWith {[_id] call CBA_fnc_removePerFrameHandler;[_view,false] call ACME_fnc_uiGlassBlur;};
    [_view] call ACME_fnc_uiGlassTick;
},0.05,[_display]] call CBA_fnc_addPerFrameHandler];
[_display] call ACME_fnc_uiGlassTick;
