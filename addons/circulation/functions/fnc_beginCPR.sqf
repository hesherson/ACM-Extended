#include "..\script_component.hpp"
/*
 * Author: Blue
 * Begin CPR
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorTarget] call ACM_circulation_fnc_beginCPR;
 *
 * Public: No
 */

params ["_medic", "_patient"];

if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {};
private _reserved = _patient getVariable [QGVAR(CPR_Medic), objNull];
if ([_reserved, _patient] call FUNC(cprSessionValid)) exitWith {
    [LLSTRING(CPR_Already), 2, _medic] call ACEFUNC(common,displayTextStructured);
};

private _oldSession = _patient getVariable [QGVAR(CPR_session), []];
[_reserved, _patient, _oldSession param [1, -1]] call FUNC(cprRelease);

// CPR outranks Direct Pressure for provider animation and clinical hand use without destroying the persistent
// pressure episode. This local guard also covers direct/scripted CPR starts that bypass the ACE treatment bridge.
private _dpSamePatient = (_medic getVariable ["ACME_DP_Active", false])
    && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient};
if (_dpSamePatient) then {
    _medic setVariable ["ACME_DP_Paused", true, false];
    _medic setVariable ["ACME_DP_PauseTreatmentClass", "cpr", false];
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    _medic setVariable ["ACME_DP_InPose", false, false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
};

// Recover this client's interrupted controller before replacing its captured session.
private _localSession = missionNamespace getVariable [QGVAR(CPR_LocalSession), []];
if !(_localSession isEqualTo []) then {_localSession call FUNC(cprCleanupLocal);};

// B128 CPR lifetime ownership. CPR predates ACM's generic continuous-action controller, so it needs its own episode
// token. The old implementation used client-global CPRTarget/loopCPR state from delayed callbacks and installed a
// new AnimDone handler every time compressions resumed. Old handlers could therefore wake up during a later CPR
// episode and repeatedly switchMove the provider back into ACM_CPR. One provider now owns one immutable epoch.
// Keep the sequence on the provider too, so a new owner cannot reuse an old epoch.
private _epoch = 1 + ((missionNamespace getVariable [QGVAR(CPR_Epoch), 0]) max (_medic getVariable [QGVAR(CPR_Sequence), 0]));
_medic setVariable [QGVAR(CPR_Sequence), _epoch, true];
GVAR(CPR_Epoch) = _epoch;
_medic setVariable [QGVAR(CPR_Epoch), _epoch, true];
_medic setVariable [QGVAR(CPR_Patient), _patient, true];
_medic setVariable [QGVAR(CPR_StartedEpoch), -1, false];
_medic setVariable [QGVAR(CPR_Loop), false, false];
_medic setVariable [QGVAR(CPR_Cancel), false];
_medic setVariable [QGVAR(CPR_lastSeen), CBA_missionTime, true];
_patient setVariable [QGVAR(CPR_session), [_medic, _epoch], true];
GVAR(CPR_LocalSession) = [_medic, _patient, _epoch];
[QGVAR(cprTrack), [_medic, _patient, _epoch]] call CBA_fnc_serverEvent;

// 1.2.3: a successful CPR start completes any BVM -> CPR chest-access handoff.
// The shared carrier lease itself stays owned by the treatment lifecycle until both maneuvers have ended.
private _chestHandoff = _medic getVariable ["ACME_chestAccessManeuverHandoff", []];
if ((_chestHandoff param [0, objNull, [objNull]]) isEqualTo _patient) then {
    _medic setVariable ["ACME_chestAccessManeuverHandoff", [], false];
};

// Synchronously retire input/EH leftovers before installing new handlers. Never leave an old F0/F1/F2 or
// AnimDone callback around to operate on the new CPRTarget.
{
    private _oldID = missionNamespace getVariable [_x, -1];
    if (!(_oldID isEqualTo -1) && {!(_oldID isEqualTo "")}) then {[_oldID, "keydown"] call CBA_fnc_removeKeyHandler;};
} forEach [
    "ACM_circulation_CPRCancel_EscapeID",
    "ACM_circulation_CPRCancel_MouseID",
    "ACM_circulation_CPRToggle_MouseID",
    "ACM_circulation_CPRSwap_MouseID"
];
private _oldAnimEH = _medic getVariable [QGVAR(CPR_AnimEH), -1];
if (_oldAnimEH >= 0) then {_medic removeEventHandler ["AnimDone", _oldAnimEH];};
_medic setVariable [QGVAR(CPR_AnimEH), -1, false];

private _fnc_doCPRAnimation = {
    params ["_medic", "_epoch"];
    if (isNull _medic
        || {(_medic getVariable [QGVAR(CPR_Epoch), -1]) != _epoch}
        || {!(_medic getVariable [QGVAR(CPR_Loop), false])}) exitWith {};
    [QACEGVAR(common,switchMove), [_medic, "ACM_CPR"]] call CBA_fnc_globalEvent;
};

_patient setVariable [QACEGVAR(medical,CPR_provider), _medic, true];
_patient setVariable [QGVAR(CPR_Medic), _medic, true];
_medic setVariable [QGVAR(isPerformingCPR), true, true];

GVAR(CPRTarget) = _patient;
GVAR(CPRActive) = true;
GVAR(BVMActive) = false;
GVAR(MedicHasBVM) = false;
GVAR(MedicHasBVMType) = "";
GVAR(SwapToBVM) = false;

private _uniqueItems = [_medic, 0] call ACEFUNC(common,uniqueItems);
private _itemIndex = _uniqueItems findIf {_x == "ACM_BVM"};
if (_itemIndex < 0) then {
    _itemIndex = _uniqueItems findIf {_x == "ACM_PocketBVM"};
    GVAR(MedicHasBVMType) = "ACM_PocketBVM";
} else {
    GVAR(MedicHasBVMType) = "ACM_BVM";
};
GVAR(MedicHasBVM) = _itemIndex >= 0;
if !(GVAR(MedicHasBVM)) then {GVAR(MedicHasBVMType) = "";};

// Every input callback carries the literal CPR epoch. It resolves the casualty from the provider's episode variable,
// never from the mutable client-global CPRTarget used by the presentation layer.
private _cancelCode = compile format [
    "private _m = ACE_player; if (isNull _m || {(_m getVariable ['ACM_circulation_CPR_Epoch', -2]) != %1}) exitWith {false}; _m setVariable ['ACM_circulation_CPR_Loop', false]; _m setVariable ['ACM_circulation_CPR_Cancel', true]; false",
    _epoch
];
GVAR(CPRCancel_EscapeID) = [0x01, [false, false, false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;
GVAR(CPRCancel_MouseID) = [0xF0, [false, false, false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

private _toggleCode = compile format [
    "private _m = ACE_player; if (isNull _m || {(_m getVariable ['ACM_circulation_CPR_Epoch', -2]) != %1}) exitWith {false}; private _p = _m getVariable ['ACM_circulation_CPR_Patient', objNull]; if (isNull _p) exitWith {false}; private _owner = _p getVariable ['ace_medical_CPR_provider', objNull]; if (isNull _owner) then {_p setVariable ['ace_medical_CPR_provider', _m, true];} else {if (_owner isEqualTo _m) then {_p setVariable ['ace_medical_CPR_provider', objNull, true];};}; false",
    _epoch
];
GVAR(CPRToggle_MouseID) = [0xF1, [false, false, false], _toggleCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

private _swapCode = compile format [
    "private _m = ACE_player; if (isNull _m || {(_m getVariable ['ACM_circulation_CPR_Epoch', -2]) != %1}) exitWith {false}; private _p = _m getVariable ['ACM_circulation_CPR_Patient', objNull]; if (isNull _p) exitWith {false}; if (isNull (_p getVariable ['ace_medical_CPR_provider', objNull]) && {isNull (_p getVariable ['ACM_breathing_BVM_Medic', objNull])} && {missionNamespace getVariable ['ACM_circulation_MedicHasBVM', false]}) then {missionNamespace setVariable ['ACM_circulation_SwapToBVM', true];}; false",
    _epoch
];
GVAR(CPRSwap_MouseID) = [0xF2, [false, false, false], _swapCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

ACEGVAR(medical_gui,pendingReopen) = false;
if (dialog) then {closeDialog 0;};

// A finite assessment can still own a zero-speed hold when the next maneuver starts.
// Retire that owner before this action takes over, including its observer/JIP freeze.
if (!isNil "ACME_fnc_treatmentPoseStop") then {[_medic] call ACME_fnc_treatmentPoseStop;};
[QACEGVAR(common,setAnimSpeedCoef), [_medic, 1]] call CBA_fnc_globalEvent;

private _notInVehicle = isNull objectParent _medic;
private _initialAnimation = animationState _medic;
private _startDelay = 2;
GVAR(loopCPR) = false;

if (_notInVehicle) then {
    [_medic, "AinvPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_medic", 1] call ACEFUNC(common,doAnimation);
    GVAR(loopCPR) = true;
    _medic setVariable [QGVAR(CPR_Loop), true, false];
} else {
    if (currentWeapon _medic != "") then {[_medic] call ACEFUNC(weaponselect,putWeaponAway);};
};

if (_initialAnimation in ["amovpercmstpsnonwnondnon", "amovpknlmstpsnonwnondnon_gear", "amovpknlmstpsnonwnondnon"]) then {
    _startDelay = 1.8;
};

private _readyAt = CBA_missionTime + _startDelay;
private _CPRStartTime = _readyAt + 0.2;

// Start the watchdog immediately, not after a blind wait. Escape/F0 during the entry animation therefore tears the
// session down on the next frame and can never leave a two-second delayed callback that later starts an old CPR.
private _controller = [{
    params ["_args", "_idPFH"];
    _args params ["_medic", "_patient", "_notInVehicle", "_readyAt", "_CPRStartTime", "_fnc_doCPRAnimation", "_epoch"];

    // A newer CPR episode owns the provider. The newer start synchronously removed these old input hooks, so the old
    // PFH retires itself only. It must not remove possibly reused handler ids or mutate any current client globals.
    if !((missionNamespace getVariable [QGVAR(CPR_LocalSession), []]) isEqualTo [_medic, _patient, _epoch]) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    private _patientCondition = isNull _patient || {(!(IS_UNCONSCIOUS(_patient)) && alive _patient)};
    private _medicCondition = isNull _medic || {!(alive _medic)} || {IS_UNCONSCIOUS(_medic)} || {!local _medic};
    private _vehicleCondition = (objectParent _medic isNotEqualTo objectParent _patient);
    private _enteredVehicle = _notInVehicle && {!isNull objectParent _medic};
    private _distanceCondition = (!isNull _patient) && {(_patient distance2D _medic) > ACEGVAR(medical_gui,maxDistance)};
    private _ownsCPR = !isNull _patient
        && {(_patient getVariable [QGVAR(CPR_session), []]) isEqualTo [_medic, _epoch]}
        && {(_patient getVariable [QGVAR(CPR_Medic), objNull]) isEqualTo _medic};
    private _swapToBVM = GVAR(SwapToBVM);

    if (_patientCondition || _medicCondition || !_ownsCPR || _swapToBVM || dialog
        || {_medic getVariable [QGVAR(CPR_Cancel), false]}
        || {_enteredVehicle} || {(!_notInVehicle && _vehicleCondition) || {(_notInVehicle && _distanceCondition)}}) exitWith {
        private _started = (_medic getVariable [QGVAR(CPR_StartedEpoch), -1]) == _epoch;

        // Preserve the open-chest lease across the synchronous CPR -> BVM swap. The token is bounded so a failed
        // replacement cannot strand the carrier off the casualty.
        if (_swapToBVM && {!isNull _medic} && {!isNull _patient}) then {
            _medic setVariable ["ACME_chestAccessManeuverHandoff", [_patient, CBA_missionTime + 1.00], false];
            [_patient, "chestAccessManeuverHandoff", [1.00]] call ACME_fnc_ownerDispatch;
        };

        if !([_medic, _patient, _epoch] call FUNC(cprCleanupLocal)) exitWith {};

        if (_notInVehicle && {!_medicCondition} && {_medic isEqualTo ACE_player} && {isNull objectParent _medic}) then {
            [QACEGVAR(common,setAnimSpeedCoef), [_medic, 1]] call CBA_fnc_globalEvent;
            _medic setUnitPos "AUTO";
            // Play the release, then queue a controllable native idle. medicEnd alone can stop at its last frame.
            [_medic, "AinvPknlMstpSnonWnonDnon_medicEnd", 2] call ACEFUNC(common,doAnimation);
            [_medic, "AmovPknlMstpSnonWnonDnon", 0] call ACEFUNC(common,doAnimation);
        };

        if (_started && {!isNull _patient}) then {
            private _CPRTime = (CBA_missionTime - _CPRStartTime) max 0;
            private _time = [_CPRTime, "MM:SS"] call BIS_fnc_secondsToString;
            [_patient, "activity", LLSTRING(CPR_ActionLog_Stopped), [[_medic, false, true] call ACEFUNC(common,getName), _time]] call ACEFUNC(medical_treatment,addToLog);
            _patient setVariable [QGVAR(CPR_StoppedTotal), _CPRTime, true];
            _patient setVariable [QGVAR(CPR_StoppedTime), CBA_missionTime, true];
        };

        // A dead/replaced provider must not close or reopen the new player's interface.
        if (_medicCondition || {!(_medic isEqualTo ACE_player)}) exitWith {};
        closeDialog 0;
        if (_swapToBVM && {!_medicCondition} && {!isNull _patient}) then {
            [LLSTRING(CPR_SwappedToBVM), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
            [_medic, _patient, false] call EFUNC(breathing,useBVM);
        } else {
            if (_started) then {[LLSTRING(CPR_Stopped), 1.5, _medic] call ACEFUNC(common,displayTextStructured);};
            if (!_medicCondition && {!isNull _patient}) then {[QEGVAR(core,openMedicalMenu), _patient] call CBA_fnc_localEvent;};
        };
    };

    // Keep paused sessions alive too. The server expires a controller that stops running.
    if (CBA_missionTime - (_medic getVariable [QGVAR(CPR_lastSeen), -100]) >= 2) then {
        _medic setVariable [QGVAR(CPR_lastSeen), CBA_missionTime, true];
    };

    // Entry completes once. Install exactly one AnimDone loop owner for this episode. Resuming compressions later only
    // requests ACM_CPR again; it never registers another event handler.
    if ((_medic getVariable [QGVAR(CPR_StartedEpoch), -1]) != _epoch) then {
        if (CBA_missionTime < _readyAt) exitWith {};

        if (currentWeapon _medic != "") then {[_medic] call ACEFUNC(weaponselect,putWeaponAway);};
        [LLSTRING(CPR_Stop), LLSTRING(CPR_Pause), ""] call ACEFUNC(interaction,showMouseHint);
        [_patient, "activity", LLSTRING(CPR_ActionLog_Started), [[_medic, false, true] call ACEFUNC(common,getName)]] call ACEFUNC(medical_treatment,addToLog);
        if (EGVAR(breathing,SwapToCPR)) then {
            EGVAR(breathing,SwapToCPR) = false;
        } else {
            [LLSTRING(CPR_Started), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
        };

        private _animEH = _medic addEventHandler ["AnimDone", {
            params ["_medic", "_anim"];
            private _registered = _medic getVariable [QGVAR(CPR_AnimEH), -1];
            if (_registered != _thisEventHandler) exitWith {
                _medic removeEventHandler [_thisEvent, _thisEventHandler];
            };
            if !(_medic getVariable [QGVAR(CPR_Loop), false]) exitWith {};
            private _patient = _medic getVariable [QGVAR(CPR_Patient), objNull];
            if (isNull _patient || {!alive _medic}
                || {!((_patient getVariable [QGVAR(CPR_Medic), objNull]) isEqualTo _medic)}) exitWith {};
            [QACEGVAR(common,switchMove), [_medic, "ACM_CPR"]] call CBA_fnc_globalEvent;
        }];
        _medic setVariable [QGVAR(CPR_AnimEH), _animEH, false];
        _medic setVariable [QGVAR(CPR_StartedEpoch), _epoch, false];

        [QGVAR(handleCPR), [_patient, _CPRStartTime], _patient] call CBA_fnc_targetEvent;
        if (_notInVehicle) then {[_medic, _epoch] call _fnc_doCPRAnimation;};
    };

    // The ventilator intentionally publishes through ACM's BVM provider channel so native gas-exchange code sees
    // mechanical ventilation. That provider may appear/disappear as delivered minute ventilation crosses its
    // validity threshold. A BVM/ventilation-state change is not a CPR pause/resume event: only a real change in
    // cprActive may announce "Continued CPR"/"CPR paused" or restart/stop the compression animation.
    private _cprNow = [_patient] call EFUNC(core,cprActive);
    private _bvmNow = [_patient] call EFUNC(core,bvmActive);
    private _cprWasActive = GVAR(CPRActive);
    private _bvmWasActive = GVAR(BVMActive);
    private _cprChanged = _cprNow isNotEqualTo _cprWasActive;
    private _bvmChanged = _bvmNow isNotEqualTo _bvmWasActive;

    if (_cprChanged || _bvmChanged) then {
        private _uniqueItems = [_medic, 0] call ACEFUNC(common,uniqueItems);
        private _itemIndex = _uniqueItems findIf {_x == "ACM_BVM"};
        if (_itemIndex < 0) then {
            _itemIndex = _uniqueItems findIf {_x == "ACM_PocketBVM"};
            GVAR(MedicHasBVMType) = "ACM_PocketBVM";
        } else {
            GVAR(MedicHasBVMType) = "ACM_BVM";
        };
        GVAR(MedicHasBVM) = _itemIndex >= 0;
        if !(GVAR(MedicHasBVM)) then {GVAR(MedicHasBVMType) = "";};

        if ((_patient getVariable [QEGVAR(airway,AirwayItem_Oral), ""]) == "SGA") then {
            GVAR(BVMActive) = _bvmNow;
            if (_cprNow) then {
                if (_cprChanged) then {
                    [LLSTRING(CPR_Continued), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
                };
                [LLSTRING(CPR_Stop), LLSTRING(CPR_Pause), ""] call ACEFUNC(interaction,showMouseHint);
                GVAR(CPRActive) = true;
                GVAR(loopCPR) = true;
                _medic setVariable [QGVAR(CPR_Loop), true, false];
                if (_cprChanged && {_notInVehicle}) then {[_medic, _epoch] call _fnc_doCPRAnimation;};
            } else {
                _medic setVariable [QGVAR(CPR_Loop), false, false];
                if (_cprChanged) then {
                    if (_notInVehicle) then {[QACEGVAR(common,switchMove), [_medic, "ACM_CPR_Stop"]] call CBA_fnc_globalEvent;};
                    [LLSTRING(CPR_Paused), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
                };
                [LLSTRING(CPR_Stop), LLSTRING(CPR_Continue), (["", LLSTRING(CPR_SwapToBVM)] select (GVAR(MedicHasBVM) && isNull (_patient getVariable [QEGVAR(breathing,BVM_Medic), objNull])))] call ACEFUNC(interaction,showMouseHint);
                GVAR(CPRActive) = false;
                GVAR(loopCPR) = false;
                _medic setVariable [QGVAR(CPR_Loop), false, false];
            };
        } else {
            if (_bvmNow) then {
                [LLSTRING(CPR_Stop), "", ""] call ACEFUNC(interaction,showMouseHint);
                GVAR(BVMActive) = true;
                GVAR(CPRActive) = _cprNow;
                GVAR(loopCPR) = GVAR(CPRActive);
                _medic setVariable [QGVAR(CPR_Loop), GVAR(CPRActive), false];
            } else {
                GVAR(BVMActive) = false;
                if (_cprNow) then {
                    if (_cprChanged) then {
                        [LLSTRING(CPR_Continued), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
                    };
                    [LLSTRING(CPR_Stop), LLSTRING(CPR_Pause), ""] call ACEFUNC(interaction,showMouseHint);
                    GVAR(CPRActive) = true;
                    GVAR(loopCPR) = true;
                    _medic setVariable [QGVAR(CPR_Loop), true, false];
                    if (_cprChanged && {_notInVehicle}) then {[_medic, _epoch] call _fnc_doCPRAnimation;};
                } else {
                    _medic setVariable [QGVAR(CPR_Loop), false, false];
                    if (_cprChanged) then {
                        if (_notInVehicle) then {[QACEGVAR(common,switchMove), [_medic, "ACM_CPR_Stop"]] call CBA_fnc_globalEvent;};
                        [LLSTRING(CPR_Paused), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
                    };
                    [LLSTRING(CPR_Stop), LLSTRING(CPR_Continue), (["", LLSTRING(CPR_SwapToBVM)] select (GVAR(MedicHasBVM) && isNull (_patient getVariable [QEGVAR(breathing,BVM_Medic), objNull])))] call ACEFUNC(interaction,showMouseHint);
                    GVAR(CPRActive) = false;
                    GVAR(loopCPR) = false;
                    _medic setVariable [QGVAR(CPR_Loop), false, false];
                };
            };
        };
        _medic setVariable [QGVAR(isPerformingCPR), GVAR(CPRActive), true];
    };
}, 0, [_medic, _patient, _notInVehicle, _readyAt, _CPRStartTime, _fnc_doCPRAnimation, _epoch]] call CBA_fnc_addPerFrameHandler;

GVAR(CPR_ControllerPFH) = _controller;
