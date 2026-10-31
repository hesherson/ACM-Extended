/* Normalize mouse events from a control or a display before the procedure acts. */
disableSerialization;
params [["_event", [], [[]]], ["_phase", "down", [""]]];
if (count _event < 2) exitWith {false};
private _source = _event select 0;
private _display = displayNull;
if (_source isEqualType controlNull) then {_display = ctrlParent _source;};
if (_source isEqualType displayNull) then {_display = _source;};
if (isNull _display) exitWith {false};
private _key = _event param [1,-1,[0]];
// B222: a procedure may reserve a physical button before generic/remapped bindings.
// Returning false here means "not a generic action"; the procedure dispatches it once.
private _priority = _display getVariable ["ACME_InputMousePriority", {false}];
if ([_display, _key, _phase] call _priority) exitWith {false};
private _mods = _display getVariable ["ACME_InputMods", [false,false,false]];
if (count _event >= 7) then {_mods = [_event param [4,false,[true]], _event param [5,false,[true]], _event param [6,false,[true]]];};
if (_phase == "wheel") exitWith {
    if (_key == 0) exitWith {false};
    _key = if (_key > 0) then {0} else {1};
    private _signature = [diag_frameNo,_key,_mods];
    private _last = _display getVariable ["ACME_InputWheel", []];
    if (count _last == 2 && {(_last select 0) isEqualTo _signature}) exitWith {_last select 1};
    private _args = [_display,_key,_mods select 0,_mods select 1,_mods select 2,false,"ACME_WHEEL"];
    private _used = _args call ACME_fnc_minigameInput;
    _args set [5,true]; _args call ACME_fnc_minigameInput;
    _display setVariable ["ACME_InputWheel", [_signature,_used]];
    _used
};
[_display,_key,_mods select 0,_mods select 1,_mods select 2,_phase == "up","MOUSE_BUTTON"] call ACME_fnc_minigameInput
