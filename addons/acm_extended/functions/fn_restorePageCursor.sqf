/* One cursor restoration during a page constructor, fenced to its navigation and display.
 * No PFH, retry or later frame can pull the pointer back after the user moves. */
disableSerialization;
params ["_display",["_navigation",[],[[]]]];
if (isNull _display || {count _navigation != 2}) exitWith {false};
_navigation params ["_epoch","_mouse"];
if (!(_epoch isEqualType 0) || {_epoch != (uiNamespace getVariable ["ACME_pageTransitionEpoch",-1])}
    || {!(_mouse isEqualType [])} || {count _mouse != 2}
    || {(_mouse findIf {!(_x isEqualType 0) || {!finite _x} || {_x < 0} || {_x > 1}}) >= 0}
    || {_display isNotEqualTo (findDisplay 84000) && {_display isNotEqualTo (findDisplay 86000)}}
    || {_display getVariable ["ACME_pageCursorRestored",false]}) exitWith {false};
_display setVariable ["ACME_pageCursorRestored",true];
setMousePosition _mouse;
true
