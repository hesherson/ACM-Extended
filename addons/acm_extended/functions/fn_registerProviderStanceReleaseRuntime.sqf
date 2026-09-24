// B72 provider stance release. ACME starts ordinary on-foot treatments from empty-hands crouch, but setUnitPos is
// only an entry guard, never a permanent player lock. Once ACE reports success/failure, release AUTO after the
// native crouched end-animation handoff. Do not interfere with head-lift or another ACME-owned finite pose.
//
// Direct Pressure integration: another treatment owns the provider animation the instant ACE says it started.
// Retire DP's held-animation generation at that boundary so a tourniquet, bandage, IV action, etc. can never be
// overwritten by the short ACME_DirectPressureHold reassert worker. Limb/head DP remains clinically active and
// simply yields its pose to movement/treatments; torso DP is the exclusive maneuver and movement hard-releases it.
["ace_treatmentStarted", {
    params ["_medic", "_patient", "_bodyPart", ["_classname", ""]];
    if (hasInterface && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player}
        && {uiNamespace getVariable ["ACME_PulseCheckActive", false]}) then {
        uiNamespace setVariable ["ACME_PulseCheckCancel", true];
        "ACM_FeelPulse" cutText ["","PLAIN",0,false];
    };
    if (isNull _medic || {!local _medic} || {!(_medic getVariable ["ACME_DP_Active", false])}) exitWith {};
    if (_classname == "ACME_DirectPressure") exitWith {};
    if !((_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient) exitWith {};

    // A normal treatment owns provider animation until ACE reports success/failure. DP remains clinically active,
    // but its visual hold becomes completely passive so it cannot overwrite the intervention animation.
    _medic setVariable ["ACME_DP_TreatmentBusy", true, false];
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    _medic setVariable ["ACME_DP_InPose", false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime];
    _medic setVariable ["ACME_DP_LastPoseAssert", 0];
}] call CBA_fnc_addEventHandler;

{
    [_x, {
        params ["_medic", "_patient", "_bodyPart", ["_classname", ""]];
        if (isNull _medic || {!local _medic} || {!alive _medic} || {!isNull objectParent _medic}) exitWith {};

        // ACE reports setup success after BVM has taken over the provider. Completing
        // that short setup must not resume pressure or reopen a menu over the maneuver.
        // Its real cancellation emits a later treatment event after releasing the controller.
        if (_medic isEqualTo ACE_player && {
            (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])
            || {!isNull _patient && {[_patient] call ACM_core_fnc_cprActive}}
            || {!isNull _patient && {[_patient] call ACM_core_fnc_bvmActive}}
        }) exitWith {};

        private _classKey = toLowerANSI _classname;
        private _headOwned = _classname in ["ACME_ElevateHead", "ACME_LowerHead"];
        // CheckPulse is intentionally a near-instant ACE treatment whose success callback opens ACME's longer-lived
        // pulse/watch minigame. ACE emits ace_treatmentSucceded only AFTER that callback returns. If the generic DP
        // completion path clears TreatmentBusy and reopens the medical menu here, it immediately destroys the pulse
        // minigame that just started. Keep DP animation-passive until fnc_feelPulse performs its real cleanup.
        private _pulseStillOwnsProvider = (_classKey == "checkpulse")
            && {uiNamespace getVariable ["ACME_PulseCheckActive", false]}
            && {(uiNamespace getVariable ["ACME_PulseCheckMedic", objNull]) isEqualTo _medic}
            && {(uiNamespace getVariable ["ACME_PulseCheckPatient", objNull]) isEqualTo _patient};

        // A completed/failed treatment gets a fresh quiet window before Direct Pressure is allowed to visibly resume.
        // Head positioning is the exception: its provider sequence continues after the ACE event, so a successful
        // active sequence keeps the clinical pause until fn_headElevMedicSeq reaches its real end state.
        if ((_medic getVariable ["ACME_DP_Active", false])
            && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}) then {
            private _pauseClass = _medic getVariable ["ACME_DP_PauseTreatmentClass", ""];
            private _headStillActive = _headOwned && {_medic getVariable ["ACME_headElev_seqActive", false]};
            if (_pauseClass != "" && {_pauseClass == _classKey} && {!_headStillActive}) then {
                _medic setVariable ["ACME_DP_Paused", false, false];
                _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
            };
            if (!_headStillActive && {!_pulseStillOwnsProvider}) then {
                _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
                _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
                _medic setVariable ["ACME_DP_InPose", false];
                _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime];
                _medic setVariable ["ACME_DP_LastPoseAssert", 0];

                // B127: timed ACE treatments can emit their completion event before ace_common_dlgProgress has been
                // destroyed. The former 0.05 s one-shot saw the still-live progress display, skipped the reopen, and
                // never tried again. Wait for the progress display to actually disappear, then reopen exactly once.
                // The Direct Pressure pose token makes the delayed callback episode-safe: stopping/restarting DP or
                // moving to another patient invalidates it before it can touch the newer UI flow.
                private _dpToken = _medic getVariable ["ACME_DP_PoseToken", -1];
                [{
                    params ["_m", "_p", "_tok"];
                    if (isNull _m || {isNull _p} || {!local _m}
                        || {!(_m getVariable ["ACME_DP_Active", false])}
                        || {!((_m getVariable ["ACME_DP_Patient", objNull]) isEqualTo _p)}
                        || {(_m getVariable ["ACME_DP_PoseToken", -2]) != _tok}) exitWith {true};
                    isNull (uiNamespace getVariable ["ace_common_dlgProgress", displayNull])
                }, {
                    params ["_m", "_p", "_tok"];
                    if (isNull _m || {isNull _p} || {!local _m}
                        || {!(_m getVariable ["ACME_DP_Active", false])}
                        || {!((_m getVariable ["ACME_DP_Patient", objNull]) isEqualTo _p)}
                        || {(_m getVariable ["ACME_DP_PoseToken", -2]) != _tok}) exitWith {};
                    // A completion callback queued by an earlier treatment can run
                    // after BVM starts. It no longer owns the provider's interface.
                    if ((missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])
                        && {_m isEqualTo ACE_player}) exitWith {};
                    private _menu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
                    private _progress = uiNamespace getVariable ["ace_common_dlgProgress", displayNull];
                    // Do not replace a purpose-built minigame/dialog which a treatment callback intentionally opened.
                    if (!isNull _progress || {dialog && {isNull _menu}}) exitWith {};
                    if (isNull _menu) then {
                        ["ACM_core_openMedicalMenu", _p] call CBA_fnc_localEvent;
                    };
                }, [_medic, _patient, _dpToken], 2, {}] call CBA_fnc_waitUntilAndExecute;
            };
        };

        if (_headOwned) exitWith {};

        [{
            params ["_m"];
            if (isNull _m || {!local _m} || {!alive _m} || {!isNull objectParent _m}) exitWith {};
            // Completion events can be followed immediately by another action or by the medical menu reopening.
            // The ended treatment no longer owns stance at this point, so a newer owner always wins.
            if ([_m] call ACME_fnc_providerStanceOwned) exitWith {};
            _m setUnitPos "AUTO";
        }, [_medic], 0.12] call CBA_fnc_waitAndExecute;
    }] call CBA_fnc_addEventHandler;
} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];

// Zone 3 posture control must distinguish a treatment animation from a genuine attempt to stand. Treatment
// events fire on the provider client, but the posture watcher runs on the casualty owner. Send only a duration;
// the casualty owner stamps the actual deadline on its own CBA_missionTime clock.
["ace_treatmentStarted", {
    params ["_medic", "_patient"];
    if (isNull _patient || {!(_patient getVariable ["ACME_AAJT_zone3", false])}) exitWith {};
    [_patient, "aajtGrace", [120]] call ACME_fnc_ownerDispatch;
}] call CBA_fnc_addEventHandler;
{
    [_x, {
        params ["_medic", "_patient"];
        if (isNull _patient || {!(_patient getVariable ["ACME_AAJT_zone3", false])}) exitWith {};
        [_patient, "aajtGrace", [0.9]] call ACME_fnc_ownerDispatch;
    }] call CBA_fnc_addEventHandler;
} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];
