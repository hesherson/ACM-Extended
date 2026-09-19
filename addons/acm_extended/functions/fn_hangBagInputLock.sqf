// the local input lock for the full-body hang bag pose.
// it blocks locomotion and stance changes and deliberately leaves mouse movement untouched, so the head and camera of
// the player can freelook while the body remains fixed with the raised arm animation.
params [["_medic", objNull, [objNull]], ["_enable", false, [false]]];
if (!hasInterface || {isNull _medic}) exitWith {};
if (_enable && {!(_medic isEqualTo ACE_player)}) exitWith {};
if (!_enable && {!((uiNamespace getVariable ["ACME_HangInputMedic", objNull]) isEqualTo _medic)}) exitWith {};

private _oldDisplay = uiNamespace getVariable ["ACME_HangInputDisplay", displayNull];
private _oldKeyEH = uiNamespace getVariable ["ACME_HangInputKeyEH", -1];
private _oldMouseEH = uiNamespace getVariable ["ACME_HangInputMouseEH", -1];

if (!_enable) exitWith {
    uiNamespace setVariable ["ACME_HangInputMedic", objNull];
    if (!isNull _oldDisplay && {_oldKeyEH >= 0}) then {
        _oldDisplay displayRemoveEventHandler ["KeyDown", _oldKeyEH];
    };
    if (!isNull _oldDisplay && {_oldMouseEH >= 0}) then {
        _oldDisplay displayRemoveEventHandler ["MouseButtonDown", _oldMouseEH];
    };
    uiNamespace setVariable ["ACME_HangInputDisplay", displayNull];
    uiNamespace setVariable ["ACME_HangInputKeyEH", -1];
    uiNamespace setVariable ["ACME_HangInputMouseEH", -1];
    uiNamespace setVariable ["ACME_HangBlockedKeys", []];
};

private _display = findDisplay 46;
if (isNull _display) exitWith {};

if (!isNull _oldDisplay && {_oldKeyEH >= 0}) then {
    _oldDisplay displayRemoveEventHandler ["KeyDown", _oldKeyEH];
};
if (!isNull _oldDisplay && {_oldMouseEH >= 0}) then {
    _oldDisplay displayRemoveEventHandler ["MouseButtonDown", _oldMouseEH];
};

// resolve the actual keybinds of the user rather than assuming wasd or the default stance keys.
private _blockedActions = [
    "MoveForward", "MoveBack", "MoveLeft", "MoveRight",
    "MoveFastForward", "MoveSlowForward", "Evasive", "Turbo", "TurboToggle",
    "TurnLeft", "TurnRight", "Stand", "Crouch", "Prone",
    "AdjustUp", "AdjustDown", "AdjustLeft", "AdjustRight",
    "LeanLeft", "LeanRight", "LeanLeftToggle", "LeanRightToggle", "GetOver",
    "Fire", "Throw", "ReloadMagazine", "SwitchWeapon", "NextWeapon", "PrevWeapon",
    "Handgun", "PrimaryWeapon", "SecondaryWeapon", "Binocular"
];
private _blockedKeys = [];
{
    {
        _x params [["_main", []], ["_combo", []], ["_doubleTap", false]];
        if (_main isEqualType [] && {(count _main) >= 2}) then {
            _main params [["_code", -1], ["_device", ""]];
            if (_device == "KEYBOARD" && {_code isEqualType 0} && {_code >= 0}) then {
                _blockedKeys pushBackUnique _code;
            };
        };
    } forEach (actionKeysEx _x);
} forEach _blockedActions;
uiNamespace setVariable ["ACME_HangBlockedKeys", _blockedKeys];

private _keyEH = _display displayAddEventHandler ["KeyDown", {
    params ["_display", "_key", "_shift", "_ctrl", "_alt"];
    private _unit = ACE_player;
    private _locked = !isNull _unit && {alive _unit} && {_unit getVariable ["ACME_hang_Active", false]};
    if (!_locked) exitWith {false};
    _key in (uiNamespace getVariable ["ACME_HangBlockedKeys", []])
}];

// the RMB consume: while a bag is held, the right mouse button, button 1, lowers the bag, canceling, and is
// swallowed so it never reaches the aim and optic action of the engine. the medic must not raise their weapon.
// lmb and MMB pass through.
// returning true from MouseButtonDown blocks the default handling. we trigger the cancel one frame later so the
// handler returns cleanly first, because calling hangBagStop directly from inside the eh can fight the same
// display. B127 carries the episode fingerprint across that deferred frame so a click from a just-ended bag cannot
// lower a new bag started before the callback executes.
private _mouseEH = _display displayAddEventHandler ["MouseButtonDown", {
    params ["_display", "_button"];
    private _unit = ACE_player;
    private _locked = !isNull _unit && {alive _unit} && {_unit getVariable ["ACME_hang_Active", false]};
    if (!_locked) exitWith {false};
    if (_button isEqualTo 1) then {
        private _episodeStart = _unit getVariable ["ACME_hang_Start", -1];
        [{
            params ["_episodeStart"];
            private _unit = ACE_player;
            if (isNull _unit) exitWith {};
            if ((_unit getVariable ["ACME_hang_Start", -2]) != _episodeStart) exitWith {};
            if (_unit getVariable ["ACME_hang_Active", false]) then { [false] call ACME_fnc_hangBagStop; };
        }, [_episodeStart]] call CBA_fnc_execNextFrame;
        true  // swallow the RMB so the weapon does not aim
    } else {
        false
    };
}];

uiNamespace setVariable ["ACME_HangInputMedic", _medic];
uiNamespace setVariable ["ACME_HangInputDisplay", _display];
uiNamespace setVariable ["ACME_HangInputKeyEH", _keyEH];
uiNamespace setVariable ["ACME_HangInputMouseEH", _mouseEH];
