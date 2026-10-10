#include "..\script_component.hpp"
/*
 * Author: BaerMitUmlaut
 * Plays the corresponding treatment animation.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: Treatment name <STRING>
 * 3: Is self treatment <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [cursorObject, joe, "Splint", true] call ace_medical_ai_fnc_playTreatmentAnim
 *
 * Public: No
 */

params ["_medic", "_patient", "_actionName", "_isSelfTreatment"];
TRACE_3("playTreatmentAnim",_medic,_actionName,_isSelfTreatment);

if (!isNull objectParent _medic) exitWith {};

private _config = configFile >> QACEGVAR(medical_treatment,actions) >> _actionName;

private _current = toLowerANSI animationState _medic;
private _proneProvider = stance _medic == "PRONE" || {(_current find "prone") >= 0}
    || {(_current find "ppne") >= 0 && {(_current find "pknl") < 0}};
private _configProperty = "animationMedic";
if (_isSelfTreatment) then {
    _configProperty = _configProperty + "Self";
};
if (_proneProvider) then {
    _configProperty = _configProperty + "Prone";
};

if (IS_UNCONSCIOUS(_patient) && {isNumber (_config >> "ACM_rollToBack")}) then {
    if ((getNumber (_config >> "ACM_rollToBack")) > 0) then {
        if (!isNil "ACME_fnc_patientAnimRequest") then {
            if !(_patient getVariable ["ACME_headElevated", false]) then {
                [_patient, "AinjPpneMstpSnonWrflDnon_rolltoback", 2, format ["ai-treatment:%1", toLowerANSI _actionName], _medic, 2.5, 1] call ACME_fnc_patientAnimRequest;
            };
        } else {
            [_patient, "AinjPpneMstpSnonWrflDnon_rolltoback", 2] call ACEFUNC(common,doAnimation);
        };
    };
};

if (_actionName == "CPR") exitWith {
    [_medic, "ACM_CPR"] call ACEFUNC(common,doAnimation);
};

// B263: these are modal workspace launchers, not native medic animations.
// A legacy/cached ACM action may still call the AI presentation hook on a
// modded server; no-anim warnings and goKneeling would otherwise interfere
// with the chest/thora provider ownership. The actual procedure owns theatre.
if (_actionName in [
    "ApplyChestSeal", "PerformThoracostomy", "ACME_ApplyChestSeal",
    "ACME_PerformThoracostomy", "ACME_AdjustThoracostomy",
    "ACME_InsertChestTube", "ACME_PerformNARSPEAR"
]) exitWith {};

private _anim = getText (_config >> _configProperty);
if (_anim == "") exitWith {
    // ACME-owned actions intentionally leave these fields empty. Their callback owns the
    // theatre; absence of a native prone RTM is never permission to force the provider up.
    if (!_proneProvider) then {_medic call ACEFUNC(common,goKneeling);};
    WARNING_2("no anim [%1, %2]",_actionName,_configProperty);
};

// Some inherited or ACME action configs incorrectly put a kneeling RTM in the Prone slot.
// Use BI's existing prone treatment family before weapon substitution; do not invent prone
// variants of medic1..medic5 or affect the patient roll above. CPR returned explicitly earlier.
if (_proneProvider && {(toLowerANSI _anim find "ppne") < 0}) then {
    _anim = ["AinvPpneMstpSlayW[wpn]Dnon_medicOther", "AinvPpneMstpSlayW[wpn]Dnon_medic"] select _isSelfTreatment;
};

private _wpn = switch (true) do {
    case ((currentWeapon _medic) == ""): {"non"};
    case ((currentWeapon _medic) == (primaryWeapon _medic)): {"rfl"};
    case ((currentWeapon _medic) == (handgunWeapon _medic)): {"pst"};
    default {"non"};
};
_anim = [_anim, "[wpn]", _wpn] call CBA_fnc_replace;

[_medic, _anim] call ACEFUNC(common,doAnimation);
