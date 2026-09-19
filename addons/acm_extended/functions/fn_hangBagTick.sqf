// the hang bag tick. it keeps the flow boost active, hard-locks the body translation and heading, and restores the
// raised-arm loop only if another system actually knocks it out. the locomotion and stance input is consumed
// separately, so this watchdog does not repeatedly restart the animation.
params ["_args", "_pfhId"];
_args params ["_medic", "_patient"];

// B127: the stored PFH id plus patient is the Hang Bag episode identity. An old callback must never see a later
// ACME_hang_Active=true and lower the new bag because its old patient went out of range or changed state.
if (isNull _medic) exitWith {[_pfhId] call CBA_fnc_removePerFrameHandler;};
if ((_medic getVariable ["ACME_hang_PFH", -1]) != _pfhId
    || {!((_medic getVariable ["ACME_hang_Patient", objNull]) isEqualTo _patient)}) exitWith {
    [_pfhId] call CBA_fnc_removePerFrameHandler;
};
if (!alive _medic || {!(_medic getVariable ["ACME_hang_Active", false])}) exitWith {
    [false, _medic] call ACME_fnc_hangBagStop;
    [_pfhId] call CBA_fnc_removePerFrameHandler;
};
if !(local _medic) exitWith {
    [true, _medic] call ACME_fnc_hangBagStop;
    [_pfhId] call CBA_fnc_removePerFrameHandler;
};
// the system toggle. it is the same rule as direct pressure: disabling the system lowers the bag cleanly instead of
// leaving the medic locked holding it.
if !(missionNamespace getVariable ["ACME_sys_hang", true]) exitWith {
    [false, _medic] call ACME_fnc_hangBagStop;
};

private _stop = false;
private _why = "";
if (isNull _patient) then { _stop = true; _why = "Patient gone. Bag lowered."; };
private _leash = missionNamespace getVariable ["ACME_hang_leash", 3];
if (!_stop && {(_medic distance _patient) > _leash}) then {
    _stop = true;
    _why = "Out of line range. Bag lowered.";
};
if (!_stop && {!isNull objectParent _medic || {_medic getVariable ["ACE_isUnconscious", false]} || {(stance _medic) == "PRONE"}}) then {
    _stop = true;
    _why = "Bag lowered.";
};
if (_stop) exitWith {
    if (_why != "") then { [_why, 2, _medic] call ace_common_fnc_displayTextStructured; };
    [true, _medic] call ACME_fnc_hangBagStop;
};

// auto-lower when the hung bag has finished transfusing. once flow has been seen on this line and it is gone,
// because the bag drained and was removed, or, on a y line, the blood became an [empty bag] marker and only the
// clamped saline reserve remains, play the exit animation automatically. the saw-flow latch stops us lowering on
// the first ticks before the freshly hung bag is registered.
// note that this must end the tick at the pfh top level. an exitwith nested inside the if (_hPart != "") then-block
// only exits that block, so execution would fall through to the hint re-assert below and re-create the "RMB / Esc
// - Lower IV Bag" prompt after hangBagStop hid it, which is exactly why the prompt lingered after a completed
// transfusion. set a flag and stop at the top level instead.
private _hPart = toLower (_medic getVariable ["ACME_hang_Part", ""]);
private _doneTransfusing = false;
if (_hPart != "") then {
    private _hbags = [];
    { if (toLower _x == _hPart) then { _hbags = _y; }; } forEach (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);
    private _flowing = (_hbags findIf {
        !((_x param [0, ""]) in ["ACME_Empty", "ACME_EmptySaline", "ACME_SalineY"]) && {(_x param [1, 0]) > 0.5}
    }) >= 0;
    if (_flowing) then {
        _medic setVariable ["ACME_hang_sawFlow", true];
    } else {
        if (_medic getVariable ["ACME_hang_sawFlow", false]) then { _doneTransfusing = true; };
    };
};
if (_doneTransfusing) exitWith {
    ["Transfusion complete. Bag lowered.", 2, _medic] call ace_common_fnc_displayTextStructured;
    [true, _medic] call ACME_fnc_hangBagStop;  // this hides the hint. the exitwith here means the tick will not re-assert it.
};

[_patient, "ACME_hang_flowMult", (missionNamespace getVariable ["ACME_hang_flowMult", 1.75])] call ACME_fnc_setVarNet;

// keep the cancel prompt up: recreate it if a HUD refresh cleared the control, and only while the hang is genuinely
// still active. during teardown, from a completed transfusion, RMB or esc, hangBagStop has already cleared
// ACME_hang_Active and hidden the hint, and without this guard a trailing tick would re-create the prompt and
// leave it stuck on screen after the bag has lowered.
if (hasInterface
    && {_medic getVariable ["ACME_hang_Active", false]}
    && {isNull (uiNamespace getVariable ["ACME_hang_HintCtrl", controlNull])}) then {
    [true] call ACME_fnc_hangBagHint;
};

// Input-lock key handlers already consume locomotion. Never correct player translation/heading with setPosASL,
// setDir or velocity writes here: those transforms caused the reported slow rightward slide and can fight vehicle/
// animation state. Likewise, do not continuously restart the full-body pose; repeated animation assertions can
// produce the engine jump/footstep sound loop. If another system genuinely knocks the hold pose out after the
// entry grace period, lower the bag cleanly and return control instead of wrestling the animation graph.
private _graceUntil = _medic getVariable ["ACME_hang_PoseRetryAt", 0];
if (CBA_missionTime >= _graceUntil) then {
    private _animNow = toLower animationState _medic;
    if ((_animNow find "jetscrewaidfcrouchthumbup") < 0) exitWith {
        [true, _medic] call ACME_fnc_hangBagStop;
    };
};
