/* Register one decorative frame without replacing its target, handler, ID or rectangle. */
disableSerialization;
params ["_display","_target","_frame",["_profile","button"]];
if (isNull _display || {isNull _target} || {isNull _frame} || {_target getVariable ["ACME_glassTracked",false]}) exitWith {};
_target setVariable ["ACME_glassTracked",true];
_frame ctrlEnable false;
for "_i" from 0 to 8 do {(_frame controlsGroupCtrl _i) ctrlEnable false;};
private _entries = _display getVariable ["ACME_glassEntries",[]];
_entries pushBack [_target,_frame,_profile];
_display setVariable ["ACME_glassEntries",_entries];
_target setVariable ["ACME_glassColor",ctrlBackgroundColor _target];
_target ctrlSetBackgroundColor [0,0,0,0];
if (_profile == "button") then {
    _target ctrlAddEventHandler ["MouseEnter",{(_this select 0) setVariable ["ACME_glassHover",true];[ctrlParent (_this select 0)] call ACME_fnc_uiGlassTick;}];
    _target ctrlAddEventHandler ["MouseExit",{(_this select 0) setVariable ["ACME_glassHover",false];[ctrlParent (_this select 0)] call ACME_fnc_uiGlassTick;}];
    _target ctrlAddEventHandler ["SetFocus",{(_this select 0) setVariable ["ACME_glassFocus",true];[ctrlParent (_this select 0)] call ACME_fnc_uiGlassTick;}];
    _target ctrlAddEventHandler ["KillFocus",{(_this select 0) setVariable ["ACME_glassFocus",false];[ctrlParent (_this select 0)] call ACME_fnc_uiGlassTick;}];
};
