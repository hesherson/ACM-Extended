/* Follow ACM's continuous-action crouch while another patient's medical menu owns the provider.
 * Keep the display and generation with the request so a late callback cannot animate a newer action. */
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_display", displayNull, [displayNull]]];
if !(missionNamespace getVariable ["ACME_menuPoseEnabled", true]) exitWith {false};
if (isNull _medic || {!local _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {false};
if (isNull _patient || {_patient isEqualTo _medic} || {!(_patient isKindOf "CAManBase")}) exitWith {false};
if ([_medic] call ACME_fnc_animBlocked || {!isNull objectParent _patient} || {_medic call ace_common_fnc_isSwimming}) exitWith {false};
if (isNull _display) then {_display = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];};
if (isNull _display) exitWith {false};
[_medic, true] call ACME_fnc_menuPoseStop;
// A menu reopened during a carrier/head/roll sequence must not replace that animation.
if ([_medic] call ACME_fnc_providerStanceOwned) exitWith {false};
[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
private _epoch = (_medic getVariable ["ACME_menuPoseEpoch", 0]) + 1;
_medic setVariable ["ACME_menuPoseEpoch", _epoch];
_medic setVariable ["ACME_menuPose", [_epoch, _display, _patient]];
_display setVariable ["ACME_menuPoseOwner", [_medic, _epoch]];
private _rate = [] call ACME_fnc_choreographyRate;
_medic setAnimSpeedCoef _rate;
["ace_common_setAnimSpeedCoef", [_medic, _rate]] call CBA_fnc_globalEvent;
_medic setUnitPos "MIDDLE";
private _settle = [_medic] call ACME_fnc_medicAnimationPrep;
private _transition = switch (stance _medic) do {
    case "STAND": {"AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"};
    case "PRONE": {"AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"};
    default {""};
};
private _bound = hasInterface && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player};
[{
    params ["_medic", "_patient", "_display", "_epoch", "_transition", "_rate", "_bound"];
    if (isNull _display || {isNull _medic} || {!local _medic} || {!alive _medic}
        || {_medic getVariable ["ACE_isUnconscious", false]} || {[_medic] call ACME_fnc_animBlocked}
        || {_bound && {!(_medic isEqualTo ACE_player)}}
        || {(_medic getVariable ["ACME_menuPose", []]) isNotEqualTo [_epoch, _display, _patient]}) exitWith {};
    if (_transition != "") then {[_medic, _transition, 2] call ACME_fnc_doAnim;};
    [{
        params ["_medic", "_patient", "_display", "_epoch", "_bound"];
        if (isNull _display || {isNull _medic} || {!local _medic} || {!alive _medic}
            || {_medic getVariable ["ACE_isUnconscious", false]} || {[_medic] call ACME_fnc_animBlocked}
            || {_bound && {!(_medic isEqualTo ACE_player)}}
            || {(_medic getVariable ["ACME_menuPose", []]) isNotEqualTo [_epoch, _display, _patient]}) exitWith {};
        [_medic, "ACM_GenericContinuous", 2] call ACME_fnc_doAnim;
    }, [_medic, _patient, _display, _epoch, _bound], (if (_transition == "") then {0} else {(if ((_transition find "AmovPerc") == 0) then {0.65} else {1.116}) / _rate})] call CBA_fnc_waitAndExecute;
}, [_medic, _patient, _display, _epoch, _transition, _rate, _bound], _settle] call CBA_fnc_waitAndExecute;
true
