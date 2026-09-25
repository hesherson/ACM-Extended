/* First contact keeps the weapon-preserving kneel. After an actual intervention on this
 * patient, auto-reopened menus may use ACM's continuous crouch. Every pose belongs to
 * one display and generation, including its close/missed-Unload recovery. */
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_display", displayNull, [displayNull]]];
if !(missionNamespace getVariable ["ACME_menuPoseEnabled", true]) exitWith {false};
if (isNull _medic || {!local _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {false};
if (isNull _patient || {_patient isEqualTo _medic} || {!(_patient isKindOf "CAManBase")}) exitWith {false};
if ([_medic] call ACME_fnc_animBlocked || {!isNull objectParent _patient} || {_medic call ace_common_fnc_isSwimming}) exitWith {false};
if (isNull _display) then {_display = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];};
if (isNull _display) exitWith {false};
private _oldState = _medic getVariable ["ACME_menuPose", []];
private _oldGeneric = (_oldState isNotEqualTo [] && {(_oldState select 0) == (_medic getVariable ["ACME_menuPoseGenericEpoch", -1])})
    || {(toLowerANSI animationState _medic) in ["acm_genericcontinuous", "acm_pronecontinuous"]};
[_medic, true] call ACME_fnc_menuPoseStop;
// A menu reopened during a carrier/head/roll sequence must not replace that animation.
if ([_medic] call ACME_fnc_providerStanceOwned) exitWith {false};
[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
private _epoch = (_medic getVariable ["ACME_menuPoseEpoch", 0]) + 1;
_medic setVariable ["ACME_menuPoseEpoch", _epoch];
_medic setVariable ["ACME_menuPose", [_epoch, _display, _patient]];
_display setVariable ["ACME_menuPoseOwner", [_medic, _epoch]];
private _afterTreatment = (_medic getVariable ["ACME_menuPoseAfterTreatment", objNull]) isEqualTo _patient;
if (!_afterTreatment) then {_medic setVariable ["ACME_menuPoseAfterTreatment", objNull];};
_medic setVariable ["ACME_menuPoseGenericEpoch", [-1, _epoch] select _afterTreatment];

// Display Unload is the fast path. This also covers display destruction, controlled-unit
// changes and a rejected handoff that silently retired the menu before acquiring a pose.
[{
    params ["_args", "_id"];
    _args params ["_medic", "_patient", "_display", "_epoch", "_bound"];
    if (isNull _medic || {(_medic getVariable ["ACME_menuPoseEpoch", -1]) != _epoch}
        || {(_medic getVariable ["ACME_menuPoseReleasedEpoch", -1]) == _epoch}) exitWith {
        [_id] call CBA_fnc_removePerFrameHandler;
    };
    private _state = _medic getVariable ["ACME_menuPose", []];
    private _retired = _state isEqualTo [];
    private _invalid = isNull _display || {!local _medic} || {!alive _medic}
        || {_medic getVariable ["ACE_isUnconscious", false]}
        || {_bound && {!(_medic isEqualTo ACE_player)}}
        || {[_medic] call ACME_fnc_animBlocked}
        || {isNull _patient} || {(_medic distance _patient) > ace_medical_gui_maxDistance};
    // Once a real successor has acquired the provider, its own cleanup is responsible.
    // Do not leave an old menu watchdog polling underneath a whole clinical procedure.
    if (_retired && {[_medic, true] call ACME_fnc_providerStanceOwned}) exitWith {
        [_id] call CBA_fnc_removePerFrameHandler;
    };
    if (_retired || {_invalid}) then {
        [_medic, false, _epoch] call ACME_fnc_menuPoseStop;
    };
}, 0.1, [_medic, _patient, _display, _epoch, hasInterface && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player}]] call CBA_fnc_addPerFrameHandler;

_medic setUnitPos "MIDDLE";
if (!_afterTreatment) exitWith {
    // Preserve B155's original first-contact crouch and the weapon in hand.
    if (_oldGeneric) then {
        _medic setAnimSpeedCoef 1;
        ["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
    };
    if (_oldGeneric || {stance _medic != "CROUCH"}) then {
        private _kneel = ["AmovPknlMstpSnonWnonDnon", "AmovPknlMstpSlowWrflDnon", "AmovPknlMstpSrasWlnrDnon",
            "AmovPknlMstpSlowWpstDnon", "AmovPknlMstpSoptWbinDnon"]
            select ((["", primaryWeapon _medic, secondaryWeapon _medic, handgunWeapon _medic, binocular _medic] find currentWeapon _medic) max 0);
        [_medic, _kneel, [0, 1] select _oldGeneric] call ACME_fnc_doAnim;
    };
    true
};

private _rate = [] call ACME_fnc_choreographyRate;
_medic setAnimSpeedCoef _rate;
["ace_common_setAnimSpeedCoef", [_medic, _rate]] call CBA_fnc_globalEvent;
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
    if (_transition != "") then {[_medic, _transition, 1] call ACME_fnc_doAnim;};
    [{
        params ["_medic", "_patient", "_display", "_epoch", "_bound"];
        if (isNull _display || {isNull _medic} || {!local _medic} || {!alive _medic}
            || {_medic getVariable ["ACE_isUnconscious", false]} || {[_medic] call ACME_fnc_animBlocked}
            || {_bound && {!(_medic isEqualTo ACE_player)}}
            || {(_medic getVariable ["ACME_menuPose", []]) isNotEqualTo [_epoch, _display, _patient]}) exitWith {};
        [_medic, "ACM_GenericContinuous", 1] call ACME_fnc_doAnim;
    }, [_medic, _patient, _display, _epoch, _bound], (if (_transition == "") then {0} else {(if ((_transition find "AmovPerc") == 0) then {0.65} else {1.116}) / _rate})] call CBA_fnc_waitAndExecute;
}, [_medic, _patient, _display, _epoch, _transition, _rate, _bound], _settle] call CBA_fnc_waitAndExecute;
true
