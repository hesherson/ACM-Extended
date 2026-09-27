#include "..\script_component.hpp"
#include "..\HeadTilt_defines.hpp"
/*
 * Author: Blue
 * Perform head tilt-chin lift maneuver on patient
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorTarget] call ACM_airway_fnc_beginHeadTiltChinLift;
 *
 * Public: No
 */

params ["_medic", "_patient"];

// Revalidate the short native launcher at callback time. Rejected entries must never
// install input handlers or publish a reservation for a continuous controller that did not start.
if (isNull _medic || {isNull _patient} || {!local _medic} || {!alive _medic}
    || {IS_UNCONSCIOUS(_medic)}) exitWith {false};
if ((_patient getVariable [QGVAR(AirwayItem_Oral), ""]) == "SGA"
    || {_patient getVariable [QGVAR(SurgicalAirway_InProgress), false]}
    || {_patient getVariable [QGVAR(SurgicalAirway_State), false]}
    || {_patient getVariable ["ACME_ETT_Inserted", false]}
    || {_patient getVariable [QGVAR(RecoveryPosition_State), false]}
    || {_patient call ACEFUNC(common,isBeingDragged)}
    || {_patient call ACEFUNC(common,isBeingCarried)}) exitWith {};

if (_patient getVariable [QGVAR(HeadTilt_State), false]) exitWith {
    [LLSTRING(HeadTiltChinLift_Already), 2, _medic] call ACEFUNC(common,displayTextStructured);
};

[[_medic, _patient, "head"], { // On Start
    params ["_medic", "_patient", "_bodyPart"];

    "ACM_HeadTilt" cutRsc ["RscHeadTilt", "PLAIN", 0, false];

    // B127: the mouse cancel belongs to the continuous-action generation which accepted this maneuver. Remove any
    // stranded old handler first, then make the new one harmless as soon as another continuous action takes over.
    private _oldID = missionNamespace getVariable [QGVAR(HeadTiltCancel_MouseID), -1];
    if (!(_oldID isEqualTo -1) && {!(_oldID isEqualTo "")}) then {[_oldID, "keydown"] call CBA_fnc_removeKeyHandler;};
    private _epoch = missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1];
    GVAR(HeadTiltTarget) = _patient;
    GVAR(HeadTiltEpoch) = _epoch;
    private _cancelCode = compile format [
        "if ((missionNamespace getVariable ['ACM_core_ContinuousAction_Epoch', -2]) == %1) then {missionNamespace setVariable ['ACM_core_ContinuousAction_Active', false];}; false",
        _epoch
    ];
    GVAR(HeadTiltCancel_MouseID) = [0xF0, [false, false, false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

    // showMouseHint's first slot is LMB.  Install a display-level mouse fallback as well as CBA's 0xF0 mapping;
    // this survives input-layout/mod conflicts that can otherwise leave the hint visible but non-functional.
    private _oldDisplayEH = missionNamespace getVariable [QGVAR(HeadTiltCancel_DisplayEH), -1];
    private _mainDisplay = findDisplay 46;
    if (!isNull _mainDisplay && {_oldDisplayEH >= 0}) then {_mainDisplay displayRemoveEventHandler ["MouseButtonDown", _oldDisplayEH];};
    GVAR(HeadTiltCancel_DisplayEH) = -1;
    if (!isNull _mainDisplay) then {
        GVAR(HeadTiltCancel_DisplayEH) = _mainDisplay displayAddEventHandler ["MouseButtonDown", {
            params ["", "_button"];
            if (_button != 0) exitWith {false};
            private _p = missionNamespace getVariable ["ACM_airway_HeadTiltTarget", objNull];
            private _ownerEpoch = missionNamespace getVariable ["ACM_airway_HeadTiltEpoch", -2];
            private _activeEpoch = missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1];
            if (_ownerEpoch == _activeEpoch && {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}) then {
                missionNamespace setVariable ["ACM_core_ContinuousAction_Active", false];
            };
            false
        }];
    };

    [ACELLSTRING(common,Cancel), "", ""] call ACEFUNC(interaction,showMouseHint);
    [_patient, "activity", LSTRING(HeadTiltChinLift_ActionLog), [[_medic, false, true] call ACEFUNC(common,getName)]] call ACEFUNC(medical_treatment,addToLog);
    [LLSTRING(HeadTiltChinLift_ActionHint), 2, _medic] call ACEFUNC(common,displayTextStructured);

    private _display = uiNamespace getVariable ["ACM_HeadTilt", displayNull];
    private _ctrlText = _display displayCtrl IDC_HEADTILT_TEXT;

    _ctrlText ctrlSetText ([_patient, false, true] call ACEFUNC(common,getName));

    _patient setVariable ["ACM_airway_HeadTilt_State_Session", [_medic, _epoch], true];
    _patient setVariable [QGVAR(HeadTilt_State), true, true];
    ["ACM_core_continuousHoldTrack", [_medic, _patient, _epoch, "ACM_airway_HeadTilt_State"]] call CBA_fnc_serverEvent;
}, { // On cancel
    params ["_medic", "_patient", "_bodyPart"];

    // Release the exact continuous-action generation that created this hold. A newer action may already have
    // incremented the shared epoch by the time this callback runs; using the current epoch would leave the old
    // HeadTilt_State reservation stuck on the patient.
    private _ownedEpoch = missionNamespace getVariable [QGVAR(HeadTiltEpoch), -1];

    private _id = missionNamespace getVariable [QGVAR(HeadTiltCancel_MouseID), -1];
    if (!(_id isEqualTo -1) && {!(_id isEqualTo "")}) then {[_id, "keydown"] call CBA_fnc_removeKeyHandler;};
    GVAR(HeadTiltCancel_MouseID) = -1;
    private _mainDisplay = findDisplay 46;
    private _displayEH = missionNamespace getVariable [QGVAR(HeadTiltCancel_DisplayEH), -1];
    if (!isNull _mainDisplay && {_displayEH >= 0}) then {_mainDisplay displayRemoveEventHandler ["MouseButtonDown", _displayEH];};
    GVAR(HeadTiltCancel_DisplayEH) = -1;
    GVAR(HeadTiltTarget) = objNull;
    GVAR(HeadTiltEpoch) = -1;

    ["", "", ""] call ACEFUNC(interaction,showMouseHint);

    "ACM_HeadTilt" cutText ["","PLAIN", 0, false];

    [LLSTRING(HeadTiltChinLift_ActionCancelled), 1.5, _medic] call ACEFUNC(common,displayTextStructured);

    [_medic, _patient, _ownedEpoch, "ACM_airway_HeadTilt_State"] call EFUNC(core,continuousHoldRelease);
}, { // PerFrame
    params ["_medic", "_patient", "_bodyPart"];

    if !((_patient getVariable ["ACM_airway_HeadTilt_State_Session", []]) isEqualTo [_medic, EGVAR(core,ContinuousAction_Epoch)]) exitWith {
        missionNamespace setVariable ["ACM_core_ContinuousAction_Active", false];
    };

    if (_patient getVariable [QGVAR(AirwayItem_Oral), ""] == "SGA" || _patient getVariable [QGVAR(SurgicalAirway_InProgress), false] || _patient getVariable [QGVAR(SurgicalAirway_State), false] || _patient getVariable ["ACME_ETT_Inserted", false] || _patient getVariable [QGVAR(RecoveryPosition_State), false] || _patient call ACEFUNC(common,isBeingDragged) || _patient call ACEFUNC(common,isBeingCarried)) then {
        EGVAR(core,ContinuousAction_Active) = false;
    };
}, false, -1, false, true] call EFUNC(core,beginContinuousAction)
