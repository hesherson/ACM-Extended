/* Follow native presentation state. Never show, enable, move or select the target control. */
disableSerialization;
params ["_display"];
if (isNull _display || {_display getVariable ["ACME_glassPainting",false]}) exitWith {};
_display setVariable ["ACME_glassPainting",true];
{
    _x params ["_target","_frame","_profile"];
    if (!isNull _target && {!isNull _frame}) then {
        private _color = ctrlBackgroundColor _target;
        // Runtime semantic colors (Prime/Flush, warnings and selected routes) stay authoritative.
        if ((_color param [3,0]) > 0) then {
            _target setVariable ["ACME_glassColor",_color];
            _target ctrlSetBackgroundColor [0,0,0,0];
        };
        private _shown = ctrlShown _target;
        private _rect = ctrlPosition _target;
        private _skin = _profile;
        if (_profile == "button" && {ctrlEnabled _target} && {
            _target getVariable ["ACME_glassHover",false] || {_target getVariable ["ACME_glassFocus",false]}
        }) then {_skin = "selected";};
        private _base = _target getVariable ["ACME_glassColor",[0,0,0,0]];
        private _alpha = if ((_base param [3,0]) > 0) then {_base select 3} else {1};
        private _tint = [1,1,1,_alpha];
        if (count _base == 4 && {(_base select 3) > 0} && {
            abs ((_base select 0) - (_base select 1)) + abs ((_base select 1) - (_base select 2)) > 0.12
        }) then {_tint = [0.6 + 0.4 * (_base select 0),0.6 + 0.4 * (_base select 1),0.6 + 0.4 * (_base select 2),_alpha];};
        [_frame,_rect,_skin,0.007,_shown,_tint] call ACME_fnc_transfusionRoundedFrame;
        private _fade = (ctrlFade _target) max (if (ctrlEnabled _target || {_profile != "button"}) then {0} else {0.45});
        if ((_frame getVariable ["ACME_glassFade",-1]) != _fade) then {
            _frame setVariable ["ACME_glassFade",_fade];_frame ctrlSetFade _fade;_frame ctrlCommit 0;
        };
    };
} forEach (_display getVariable ["ACME_glassEntries",[]]);
// Destroy the decorator when its dynamic target was deleted. Row refreshes cannot leak frames.
private _alive = [];
{
    _x params ["_target","_frame"];
    if (isNull _target || {isNull _frame}) then {
        if (!isNull _frame) then {ctrlDelete _frame;};
    } else {_alive pushBack _x;};
} forEach (_display getVariable ["ACME_glassEntries",[]]);
_display setVariable ["ACME_glassEntries",_alive];
_display setVariable ["ACME_glassPainting",false];
// Existing NV focus blur already supplies the background when enabled; do not stack it.
[_display,true] call ACME_fnc_uiGlassBlur;
