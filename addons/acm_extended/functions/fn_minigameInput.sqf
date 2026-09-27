/* Procedure-local input bridge. UI callbacks may call this more than once for one event.
   The physical press record prevents repeats and duplicate handler delivery from acting twice. */
disableSerialization;
params [["_display", displayNull, [displayNull]], ["_key", -1, [0]],
    ["_shift", false, [true]], ["_ctrl", false, [true]], ["_alt", false, [true]],
    ["_up", false, [true]], ["_device", "KEYBOARD", [""]]];
if (isNull _display || {!hasInterface} || {!(_display getVariable ["ACME_InputInstalled", false])}) exitWith {false};
private _held = _display getVariable ["ACME_InputHeld", createHashMap];
// Arma can lose KeyUp/MouseUp while the game or display loses focus (Alt-Tab, overlay, monitor focus change).
// A long input silence is therefore a hard episode boundary: discard stale held tokens before interpreting the
// next physical event. Normal key repeat arrives continuously and never crosses this window.
private _lastInputAt = _display getVariable ["ACME_InputLastAt", -1];
if (_lastInputAt >= 0 && {(diag_tickTime - _lastInputAt) > 1.5}) then {
    _held = createHashMap;
    _display setVariable ["ACME_InputHeld", _held];
    _display setVariable ["ACME_InputTaps", createHashMap];
};
_display setVariable ["ACME_InputLastAt", diag_tickTime];
private _token = format ["%1:%2", _device, _key];
_display setVariable ["ACME_InputMods", [_shift,_ctrl,_alt]];
if (_up) exitWith {
    private _old = _held getOrDefault [_token, []];
    private _claimed = _old param [0,false,[true]];
    if !(_old isEqualTo []) then {
        _held deleteAt _token;
        _display setVariable ["ACME_InputReleased", [diag_frameNo, _token, _claimed]];
    } else {
        private _released = _display getVariable ["ACME_InputReleased", []];
        _claimed = count _released == 3 && {(_released select 0) == diag_frameNo}
            && {(_released select 1) == _token} && {_released select 2};
    };
    _display setVariable ["ACME_InputHeld", _held];
    _claimed
};
private _repeat = _held getOrDefault [_token, []];
if !(_repeat isEqualTo []) exitWith {_repeat param [0,false,[true]]};
// Record even unclaimed keys for non-modifier chords. Text editing retains all its keys.
_held set [_token, [false]];
_display setVariable ["ACME_InputHeld", _held];
private _focus = focusedCtrl _display;
if (!isNull _focus && {ctrlType _focus == 2}) exitWith {false};
private _medic = missionNamespace getVariable ["ACE_player", player];
if (isNull _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {false};
private _choices = [_display] call ACME_fnc_minigameInputBindings;
private _idx = _choices findIf {[_x,_device,_key,[_shift,_ctrl,_alt],keys _held] call ACME_fnc_minigameInputMatch};
if (_idx < 0) exitWith {false};
private _binding = _choices select _idx;
_binding params ["_action", "", "", "_double"];
_held set [_token, [true]];
_display setVariable ["ACME_InputHeld", _held];
private _run = true;
if (_double) then {
    private _taps = _display getVariable ["ACME_InputTaps", createHashMap];
    private _id = str _binding;
    private _last = _taps getOrDefault [_id, -10];
    _run = (diag_tickTime - _last) <= 0.3;
    _taps set [_id, if (_run) then {-10} else {diag_tickTime}];
    _display setVariable ["ACME_InputTaps", _taps];
};
if (!_run) exitWith {true};
switch (_action) do {
    case "nv": {
        // Use the engine's current goggles and action. Do not replace hmd, overlays, or PP.
        if (hmd _medic != "") then {
            if (currentVisionMode _medic == 1) then {
                _medic action ["NVGogglesOff", _medic];
            } else {
                _medic action ["NVGoggles", _medic];
            };
        };
    };
    case "flip": {["toggle"] call ACME_fnc_ventFlip;};
};
true
