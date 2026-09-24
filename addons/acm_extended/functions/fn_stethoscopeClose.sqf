// Unload is the final authority for this display instance.
// It must release audio, patient positioning, the continuous-action reservation and the provider's frozen pose.
// The normal controller PFH still performs the same cancellation path; every operation below is token-scoped and
// therefore safe when both paths run on adjacent frames.
disableSerialization;
params ["_display"];
if (isNull _display) exitWith {};

private _tickPFH = _display getVariable ["ACME_stethTickPFH", -1];
if (_tickPFH isEqualType 0 && {_tickPFH >= 0}) then {[_tickPFH] call CBA_fnc_removePerFrameHandler;};
_display setVariable ["ACME_stethTickPFH", -1];

// Capture before clearing: Unload must still abort the flip that was active.
private _flipWasActive = _display getVariable ["ACME_stethFlipActive", false];
private _flipPFH = _display getVariable ["ACME_stethFlipPFH", -1];
if (_flipPFH isEqualType 0 && {_flipPFH >= 0}) then {[_flipPFH] call CBA_fnc_removePerFrameHandler;};
_display setVariable ["ACME_stethFlipPFH", -1];
_display setVariable ["ACME_stethFlipToken", ""];
_display setVariable ["ACME_stethFlipActive", false];

{
    _x params ["_emitter","_sound"];
    if (!isNull _sound) then {deleteVehicle _sound;};
    if (!isNull _emitter) then {deleteVehicle _emitter;};
} forEach (_display getVariable ["ACME_stethChannels",[]]);
_display setVariable ["ACME_stethChannels",[]];
_display setVariable ["ACME_stethPressed",false];

private _medic = _display getVariable ["ACME_stethMedic",objNull];
private _patient = _display getVariable ["ACME_stethPatient",objNull];

// An Unload during an ACTIVE Flip is an immediate abort. Do not cancel unrelated patient/provider roll
// controllers merely because the auscultation display is closing normally.
if (_flipWasActive) then {
    if (!isNull _medic && {local _medic}) then {
        [_medic,"stethoscopeFlip"] call ACME_fnc_rollProviderCancel;
    };
    if (!isNull _patient) then {
        // Closing auscultation always settles a live Flip anterior-up / lying on the back.
        [_patient,"front"] call ACME_fnc_patientRollCancel;
    };
};
private _poseEpoch = _display getVariable ["ACME_stethPoseEpoch",-1];
private _continuousEpoch = _display getVariable ["ACME_continuousEpoch",-1];

// Release this provider's casualty animation lease immediately. The normal onCancel path sees the cleared lease
// and becomes a no-op, so a missed PFH frame can never leave the patient pinned by a dead stethoscope session.
private _restoreDispatched = false;
if (!isNull _medic) then {
    private _lease = _medic getVariable ["ACME_stethPatientAnimLease",[]];
    if ((count _lease) >= 2) then {
        private _leasePatient = _lease param [0,objNull];
        private _leaseToken = _lease param [1,""];
        if (!isNull _leasePatient && {_leaseToken != ""}) then {
            [_leasePatient,_leaseToken] call ACME_fnc_patientAnimRelease;
        };
    };
    _medic setVariable ["ACME_stethPatientAnimLease",[],false];

    // UseStethoscope removes the carrier before the modal scope opens. The scope display is the real lifetime
    // boundary, so release that exact lease here even if the generic controller was superseded.
    private _chestLease = _medic getVariable ["ACME_chestAccess_treatment", []];
    if ((_chestLease param [0, objNull]) isEqualTo _patient
        && {toLowerANSI (_chestLease param [1, ""]) == "usestethoscope"}) then {
        private _leaseId = _chestLease param [2, ""];
        _medic setVariable ["ACME_chestAccess_treatment", []];
        if (!isNull _patient && {_leaseId != ""}) then {
            _restoreDispatched = true;
            [_patient, _medic, _leaseId, false, "usestethoscope"] call ACME_fnc_chestAccessVestEvent;
        };
    };
};

// Even a no-carrier/no-preflight stethoscope session may have physically flipped the patient posteriorly.
// Route through the common chest restore path anyway: it now normalizes front/supine before doing anything else,
// including the no-custody branch.
if (!isNull _patient && {!_restoreDispatched}) then {
    [_patient,false,_medic,"access",false] call ACME_fnc_chestAccessVestRestore;
};

// Retire only the continuous-action generation that created this display. This is the critical fallback for
// abnormal dialog teardown: a dead stethoscope display must never leave ACM_core_ContinuousAction_Active stuck true.
if (_continuousEpoch >= 0
    && {(missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch",-2]) == _continuousEpoch}) then {
    ACM_core_ContinuousAction_Active = false;
    ACM_core_ContinuousAction_IsDialog = false;
    if (!isNull _medic
        && {(_medic getVariable ["ACM_core_ContinuousAction_Session", []]) isEqualTo [_patient, _continuousEpoch]}) then {
        _medic setVariable ["ACM_core_ContinuousAction_Session", [], true];
    };
};

// Release only this stethoscope pose as a handoff. The requested exit is not the generic treatment blend:
// play the exact Semi-Fowler provider Putdown/inventory pair and finish in the normal unarmed crouch.
if (!isNull _medic && {_poseEpoch >= 0}
    && {(_medic getVariable ["ACME_treatmentPoseEpoch",-2]) == _poseEpoch}) then {
    [_medic,"stethoscope",_poseEpoch,true] call ACME_fnc_treatmentPoseStop;

    if (local _medic && {getAnimSpeedCoef _medic == 0}) then {
        _medic setAnimSpeedCoef 1;
    };
};

// A superseded display must not start its exit over a newer continuous action.
// Use the scope generation here: an active Flip legitimately owns a newer roll pose epoch.
if (_continuousEpoch >= 0
    && {(missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch",-2]) == _continuousEpoch}
    && {!isNull _medic} && {local _medic} && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious",false])}
    && {isNull objectParent _medic}
    && {!(_medic getVariable ["ACME_headElev_seqActive",false])}) then {
    [_medic,"lower"] call ACME_fnc_headElevMedicSeq;
};

if ((uiNamespace getVariable ["ACM_breathing_Stethoscope_DLG",displayNull]) isEqualTo _display) then {
    uiNamespace setVariable ["ACM_breathing_Stethoscope_DLG",displayNull];
};
[-1] call ace_hearing_fnc_updateHearingProtection;
