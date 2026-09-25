#include "..\script_component.hpp"
#include "..\UseBVM_defines.hpp"
/*
 * Author: Blue
 * Use BVM on patient.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: Use Oxygen <BOOL>
 * 3: Using Portable Oxygen <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorObject, false, false] call ACM_breathing_fnc_useBVM;
 *
 * Public: No
 */

params ["_medic", "_patient", ["_useOxygen", false], ["_portableOxygen", false]];

if (isNull _medic || {isNull _patient} || {!local _medic} || {!alive _medic}
    || {!([_medic] call ACEFUNC(common,isAwake))}
    || {missionNamespace getVariable [QEGVAR(core,ContinuousAction_Active), false]}
    || {!([_medic, _patient, true] call FUNC(canUseBVM))}) exitWith {};
private _reserved = _patient getVariable [QGVAR(BVM_Medic), objNull];
if ([_reserved, _patient] call FUNC(bvmSessionValid)) exitWith {
    [LLSTRING(BVM_Already), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
};

// Recover a dead, disconnected or abandoned provider reservation before a new start.
private _oldSession = _patient getVariable [QGVAR(BVM_session), []];
[_reserved, _patient, _oldSession param [1, -1]] call FUNC(bvmRelease);

// A provider-supported Semi-Fowler has no prop and cannot survive the supporting provider yielding to BVM.
// Supported backpack/carrier Semi-Fowler is compatible with BVM and is intentionally left elevated.
if ((_patient getVariable ["ACME_headElevated", false])
    && {_patient getVariable ["ACME_headElev_manualUnsupported", false]}) then {
    [_patient, "headElevStop", [_medic, _patient, false, false]] call ACME_fnc_ownerDispatch;
};

// BVM outranks Direct Pressure for provider animation and clinical hand use, but it must not destroy the
// persistent pressure episode. Yield the same-provider/same-patient hold before BVM takes ownership; the DP PFH
// keeps the episode alive without its marker/pose and resumes it only after the real native BVM/CPR lifetime ends.
private _dpSamePatient = (_medic getVariable ["ACME_DP_Active", false])
    && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient};
if (_dpSamePatient) then {
    _medic setVariable ["ACME_DP_Paused", true, false];
    _medic setVariable ["ACME_DP_PauseTreatmentClass", "usebvm", false];
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    _medic setVariable ["ACME_DP_InPose", false, false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
};

[[_medic, _patient, "head", [_useOxygen, _portableOxygen]], { // On Start
    params ["_medic", "_patient", "_bodyPart", "_extraArgs"];
    _extraArgs params ["_useOxygen", "_portableOxygen"];

    private _epoch = missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1];
    _extraArgs set [2, _epoch];
    GVAR(BVM_LocalSession) = [_medic, _patient, _epoch];

    // 1.2.3: a successful BVM start completes any CPR -> BVM chest-access handoff.
    private _chestHandoff = _medic getVariable ["ACME_chestAccessManeuverHandoff", []];
    if ((_chestHandoff param [0, objNull, [objNull]]) isEqualTo _patient) then {
        _medic setVariable ["ACME_chestAccessManeuverHandoff", [], false];
    };

    _medic setVariable [QGVAR(BVM_patient), _patient, true];
    _medic setVariable [QGVAR(BVM_epoch), _epoch, true];
    _patient setVariable [QGVAR(BVM_session), [_medic, _epoch], true];
    [QGVAR(bvmTrack), [_medic, _patient, _epoch]] call CBA_fnc_serverEvent;

    "ACM_UseBVM" cutRsc ["RscUseBVM", "PLAIN", 0, false];

    _patient setVariable [QGVAR(BVM_Medic), _medic, true];

    GVAR(BVMTarget) = _patient;
    GVAR(BVMActive) = false;
    GVAR(CPRActive) = false;

    GVAR(SwapToCPR) = false;

    GVAR(BVM_OxygenActive) = _useOxygen;
    GVAR(BVM_PortableOxygen) = _portableOxygen;

    _patient setVariable [QGVAR(BVM_ConnectedOxygen), _useOxygen, true];

    GVAR(BVM_BreathCount) = 0;

    GVAR(BVMTarget_Intubated) = ((_patient getVariable [QEGVAR(airway,AirwayItem_Oral), ""]) == "SGA");

    // B127: BVM used to install these handlers before beginContinuousAction had accepted the session. A rejected
    // start therefore leaked live mouse handlers, and an old BVM handler could later clear the global continuous
    // action gate while CPR, head tilt or another maneuver was running. Install them only from On Start, after the
    // controller has assigned this session's epoch, and make every handler generation-aware.
    {
        private _oldID = missionNamespace getVariable [_x, -1];
        if (!(_oldID isEqualTo -1) && {!(_oldID isEqualTo "")}) then {[_oldID, "keydown"] call CBA_fnc_removeKeyHandler;};
    } forEach [
        "ACM_breathing_BVMCancel_MouseID",
        "ACM_breathing_BVMToggle_MouseID",
        "ACM_breathing_BVMSwap_MouseID"
    ];

    private _cancelCode = compile format [
        "if ((missionNamespace getVariable ['ACM_core_ContinuousAction_Epoch', -2]) != %1) exitWith {false}; missionNamespace setVariable ['ACM_core_ContinuousAction_Active', false]; false",
        _epoch
    ];
    GVAR(BVMCancel_MouseID) = [0xF0, [false, false, false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

    private _toggleCode = compile format [
        "if ((missionNamespace getVariable ['ACM_core_ContinuousAction_Epoch', -2]) != %1) exitWith {false}; private _t = missionNamespace getVariable ['ACM_breathing_BVMTarget', objNull]; if (isNull _t) exitWith {false}; if ((_t getVariable ['ACM_breathing_BVM_provider', objNull]) isEqualTo objNull) then {_t setVariable ['ACM_breathing_BVM_provider', ACE_player, true];} else {_t setVariable ['ACM_breathing_BVM_provider', objNull, true];}; false",
        _epoch
    ];
    GVAR(BVMToggle_MouseID) = [0xF1, [false, false, false], _toggleCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

    private _swapCode = compile format [
        "if ((missionNamespace getVariable ['ACM_core_ContinuousAction_Epoch', -2]) != %1) exitWith {false}; private _t = missionNamespace getVariable ['ACM_breathing_BVMTarget', objNull]; if (isNull _t) exitWith {false}; if (isNull (_t getVariable ['ACM_breathing_BVM_provider', objNull]) && {isNull (_t getVariable ['ACM_circulation_CPR_Medic', objNull])}) then {missionNamespace setVariable ['ACM_breathing_SwapToCPR', true]; missionNamespace setVariable ['ACM_core_ContinuousAction_Active', false];}; false",
        _epoch
    ];
    GVAR(BVMSwap_MouseID) = [0xF2, [false, false, false], _swapCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

    private _display = uiNamespace getVariable ["ACM_UseBVM", displayNull];
    private _ctrlTopText = _display displayCtrl IDC_USEBVM_TOPTEXT;
    private _ctrlText = _display displayCtrl IDC_USEBVM_TEXT;

    // A BVM session remains an active ventilation session during CPR. The old non-SGA branch deliberately did
    // not register BVM_provider when CPR was running, creating a visual "assist" state that delivered no breaths.
    // Keep compressor and ventilator ownership independent instead.
    private _assisting = [_patient] call EFUNC(core,cprActive);
    GVAR(CPRActive) = _assisting;
    _patient setVariable [QGVAR(BVM_provider), _medic, true];
    GVAR(BVMActive) = true;
    [LLSTRING(BVM_Stop), LLSTRING(BVM_Pause), ""] call ACEFUNC(interaction,showMouseHint);

    if (_assisting) then {
        if !(GVAR(BVM_OxygenActive)) then {
            _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM_Assist);
        } else {
            _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM_AssistOxygen);
        };
    } else {
        if (GVAR(BVM_OxygenActive)) then {
            _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM_Oxygen);
        } else {
            _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM);
        };
    };

    _medic setVariable [QGVAR(isUsingBVM), ([_patient] call EFUNC(core,bvmActive)), true];

    _ctrlText ctrlSetText ([_patient, false, true] call ACEFUNC(common,getName));

    GVAR(BVM_NextBreath) = (CBA_missionTime + 2);
    GVAR(BVM_BreathCount) = 0;

    if (GVAR(BVMActive)) then {
        [_patient, "activity", LSTRING(BVM_ActionLog_Start), [[_medic, false, true] call ACEFUNC(common,getName)]] call ACEFUNC(medical_treatment,addToLog);
    };

    if (EGVAR(circulation,SwapToBVM)) then {
        EGVAR(circulation,SwapToBVM) = false;
    } else {
        [LLSTRING(BVM_Started), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
    };
}, { // On cancel
    params ["_medic", "_patient", "_bodyPart", "_extraArgs"];
    _extraArgs params ["_useOxygen", "_portableOxygen"];

    private _epoch = _extraArgs param [2, -1];
    private _swapToCPR = missionNamespace getVariable [QGVAR(SwapToCPR), false];

    // Preserve the open-chest lease across the deliberate 0.1 s BVM -> CPR handoff. The bounded token lets the
    // existing lease watchdog restore the carrier if CPR fails to take ownership.
    if (_swapToCPR && {!isNull _medic} && {!isNull _patient}) then {
        // A supported Semi-Fowler BVM -> CPR swap has to lower the casualty once before compressions begin.
        // Keep the existing chest-access lease alive through that authored 1.4 s release so the carrier is not
        // restored and immediately removed again during the handoff.
        private _handoffSec = if (_patient getVariable ["ACME_headElevated", false]) then {2.50} else {1.00};
        _medic setVariable ["ACME_chestAccessManeuverHandoff", [_patient, CBA_missionTime + _handoffSec], false];
        [_patient, "chestAccessManeuverHandoff", [_handoffSec]] call ACME_fnc_ownerDispatch;
    };

    if !([_medic, _patient, _epoch] call FUNC(bvmCleanupLocal)) exitWith {};
    // Death/respawn/locality loss releases ownership without reopening menus on the replacement player.
    if (isNull _medic || {isNull _patient} || {!local _medic} || {!alive _medic}
        || {!(_medic isEqualTo ACE_player)} || {!([_medic] call ACEFUNC(common,isAwake))}) exitWith {};

    [_patient, "activity", LLSTRING(BVM_ActionLog_Stop), [[_medic, false, true] call ACEFUNC(common,getName), GVAR(BVM_BreathCount)]] call ACEFUNC(medical_treatment,addToLog);

    closeDialog 0;

    if (_swapToCPR) then {
        EGVAR(core,ContinuousAction_ForceOpenMenu) = false;
        // B128: this handoff used to fire unconditionally 0.1 s after BVM teardown. If another continuous action
        // started in that gap, the old BVM callback could inject CPR into the new maneuver. Carry the generation
        // which actually owned this BVM and abandon the handoff if anything newer has taken the controller.
        [{
            params ["_medic", "_patient", "_epoch"];
            if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -2]) != _epoch
                || {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}
                || {isNull _medic} || {isNull _patient}) exitWith {};
            [LLSTRING(BVM_SwappedToCPR), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
            [_medic, _patient] call EFUNC(circulation,beginCPR);
        }, [_medic, _patient, _epoch], 0.1] call CBA_fnc_waitAndExecute;
    } else {
        [LLSTRING(BVM_Stopped), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
        [QEGVAR(core,openMedicalMenu), _patient] call CBA_fnc_localEvent;
    };

    GVAR(BVMTarget) = objNull;
}, { // PerFrame
    params ["_medic", "_patient", "_bodyPart", "_extraArgs"];
    _extraArgs params ["_useOxygen", "_portableOxygen"];

    private _updateMouseHint = false;
    private _updateText = false;

    if ((([_patient] call EFUNC(core,cprActive)) isNotEqualTo GVAR(CPRActive))
        || {([_patient] call EFUNC(core,bvmActive)) isNotEqualTo GVAR(BVMActive)}) then {
        _updateMouseHint = true;
        _updateText = true;
    };

    if ((_patient getVariable [QGVAR(BVM_ConnectedOxygen), false]) isNotEqualTo GVAR(BVM_OxygenActive)) then {
        GVAR(BVM_OxygenActive) = (_patient getVariable [QGVAR(BVM_ConnectedOxygen), false]);
        _updateText = true;
    };

    if (_updateMouseHint) then {
        // Re-evaluate the two independent roles. CPR never suppresses a valid BVM provider and BVM never suppresses
        // a valid compressor; the hint only controls this provider's BVM pause/resume state.
        GVAR(CPRActive) = [_patient] call EFUNC(core,cprActive);
        if ([_patient] call EFUNC(core,bvmActive)) then { // Active BVM
            [LLSTRING(BVM_Continued), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
            [LLSTRING(BVM_Stop), LLSTRING(BVM_Pause), ""] call ACEFUNC(interaction,showMouseHint);
            GVAR(BVMActive) = true;
        } else { // Paused BVM
            [LLSTRING(BVM_Paused), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
            [LLSTRING(BVM_Stop), LLSTRING(BVM_Continue), (["", LLSTRING(BVM_SwapToCPR)] select (isNull (_patient getVariable [QEGVAR(circulation,CPR_Medic), objNull])))] call ACEFUNC(interaction,showMouseHint);
            GVAR(BVMActive) = false;
        };
        _medic setVariable [QGVAR(isUsingBVM), ([_patient] call EFUNC(core,bvmActive)), true];
    };

    if (_updateText) then {
        private _display = uiNamespace getVariable ["ACM_UseBVM", displayNull];
        private _ctrlTopText = _display displayCtrl IDC_USEBVM_TOPTEXT;

        if ([_patient] call EFUNC(core,cprActive)) then {
            if !(_patient getVariable [QGVAR(BVM_ConnectedOxygen), false]) then {
                _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM_Assist);
            } else {
                _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM_AssistOxygen);
            };
        } else {
            if !(_patient getVariable [QGVAR(BVM_ConnectedOxygen), false]) then {
                _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM);
            } else {
                _ctrlTopText ctrlSetText LLSTRING(BVM_UsingBVM_Oxygen);
            };
        };
    };

    if (alive (_patient getVariable [QGVAR(BVM_provider), objNull])) then {
        if !([_medic, _patient, true] call FUNC(canUseBVM)) exitWith {
            EGVAR(core,ContinuousAction_Active) = false;
        };

        if (GVAR(BVM_NextBreath) < CBA_missionTime) then {
            GVAR(BVM_NextBreath) = CBA_missionTime + 6;
            playSound3D [QPATHTO_R(sound\bvm_squeeze.wav), _patient, false, getPosASL _patient, 12, 1, 12]; // 1.227s
            GVAR(BVM_BreathCount) = GVAR(BVM_BreathCount) + 1;
            if (GVAR(BVM_BreathCount) > 1 && (GET_AIRWAYSTATE(_patient) > 0)) then {
                // Oxygen physiology consumes these timestamps on the casualty owner. Never stamp them with the
                // provider client's mission clock; one owner-routed event per delivered breath is sufficient.
                [_patient, "bvmBreath", [_patient getVariable [QGVAR(BVM_ConnectedOxygen), false]]] call ACME_fnc_ownerDispatch;
            };

            if (GVAR(BVM_PortableOxygen)) then {
                private _success = [_medic] call FUNC(useOxygenTankReserve);
                if !(_success) then {
                    [LLSTRING(BVM_UsingBVM_OxygenTankDepleted), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
                    _patient setVariable [QGVAR(BVM_ConnectedOxygen), false, true];
                    GVAR(BVM_PortableOxygen) = false;
                };
            };
        };
    };
}] call EFUNC(core,beginContinuousAction);
