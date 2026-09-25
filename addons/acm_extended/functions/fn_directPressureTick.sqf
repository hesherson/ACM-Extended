// Shared Direct Pressure per-frame worker. Direct Pressure itself never owns ACM's global continuous-action gate.
// Deliberate movement now releases the hold entirely. Ordinary compatible treatments may replace only the provider
// animation; true ACM maneuvers temporarily suspend the pose/clinical marker and can resume after the maneuver.
// This keeps the menu responsive without letting a stale pressure loop swallow the provider's movement input.
params ["_args", "_pfhId"];
_args params ["_medic", "_patient", "_bodyPart", "_mode"];

// B127 session ownership. The PFH id stored on the provider is the Direct Pressure episode identity. A callback
// which survived removal from an older episode must never observe a later ACME_DP_Active=true and begin operating on
// its old patient/body part again. Fingerprint the patient/part/mode as a second guard in case a CBA PFH id is ever
// recycled during a long session.
if (isNull _medic
    || {(_medic getVariable ["ACME_DP_PFH", -1]) != _pfhId}
    || {!((_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient)}
    || {(_medic getVariable ["ACME_DP_Part", ""]) != _bodyPart}
    || {(_medic getVariable ["ACME_DP_Mode", ""]) != _mode}) exitWith {
    [_pfhId] call CBA_fnc_removePerFrameHandler;
};

if !(_medic getVariable ["ACME_DP_Active", false]) exitWith {[_pfhId] call CBA_fnc_removePerFrameHandler;};
if !(missionNamespace getVariable ["ACME_sys_dp", true]) exitWith {
    [false, _medic, false] call ACME_fnc_directPressureStop;
    [_pfhId] call CBA_fnc_removePerFrameHandler;
};

private _stop = "";
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious", false]}) then {_stop = "down";};
if (_stop == "" && {isNull _patient}) then {_stop = "patient";};

private _leash = if (_mode == "torso") then {
    missionNamespace getVariable ["ACME_DP_torsoLeashDist", 3.2]
} else {
    missionNamespace getVariable ["ACME_DP_leashDist", 2.7]
};
private _medicVehicle = objectParent _medic;
private _patientVehicle = objectParent _patient;
if (_stop == "" && {_medicVehicle isNotEqualTo _patientVehicle}) then {_stop = "far";};
if (_stop == "" && {(_medic distance _patient) > _leash}) then {_stop = "far";};

if (_stop != "") exitWith {
    if (_stop == "far") then {["Direct pressure released.", 2, _medic] call ace_common_fnc_displayTextStructured;};
    [true, _medic, false] call ACME_fnc_directPressureStop;
    [_pfhId] call CBA_fnc_removePerFrameHandler;
};

// Movement is an explicit release request, not a temporary pressure yield. Check it before the pose controller so
// the looping hold cannot consume the first movement frames and then quietly reapply itself when the key is released.
// inputAction respects remapped movement keys/controllers, unlike hard-coded DIK handlers.
private _moveInput = (inputAction "MoveForward") + (inputAction "MoveBack")
                   + (inputAction "MoveLeft") + (inputAction "MoveRight")
                   + (inputAction "TurnLeft") + (inputAction "TurnRight")
                   + (inputAction "MoveFastForward") + (inputAction "MoveSlowForward")
                   + (inputAction "Evasive");
private _moving = _moveInput > 0.01;
if (_moving) exitWith {
    [true, _medic, false] call ACME_fnc_directPressureStop;
    [_pfhId] call CBA_fnc_removePerFrameHandler;
};

// Higher-priority interventions win BEFORE Direct Pressure gets any chance to reassert its decorative hold.
// This includes chest-access preparation and head-position/provider choreography, not just an already-active
// continuous action. DP remains clinically alive and resumes later; it never cancels or overwrites the maneuver.
private _nativeCpr = [_patient] call ACM_core_fnc_cprActive;
private _nativeBvm = [_patient] call ACM_core_fnc_bvmActive;
private _handoff = _medic getVariable ["ACME_chestAccessManeuverHandoff", []];
private _providerHandoffActive = ((_handoff param [0, objNull, [objNull]]) isEqualTo _patient)
    && {(_handoff param [1, -1, [0]]) > CBA_missionTime};
private _ownerHandoffUntil = _patient getVariable ["ACME_chestAccess_maneuverHandoffUntil", -1];
private _ownerHandoffActive = (_ownerHandoffUntil isEqualType 0) && {serverTime < _ownerHandoffUntil};
private _maneuverActive = (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])
    || {_nativeCpr} || {_nativeBvm} || {_providerHandoffActive} || {_ownerHandoffActive};
private _manualPause = _medic getVariable ["ACME_DP_Paused", false];
private _pauseClass = _medic getVariable ["ACME_DP_PauseTreatmentClass", ""];
private _chestPrep = _medic getVariable ["ACME_chestAccessPreflightActive", false]
    || {(_medic getVariable ["ACME_chestAccessProvider", []]) isNotEqualTo []};
private _headProvider = _medic getVariable ["ACME_headElev_seqActive", false];
private _treatmentBusy = _medic getVariable ["ACME_DP_TreatmentBusy", false]
    || {_medic getVariable ["ACME_treatmentPreflightActive", false]};

private _maneuverClasses = ["cpr", "usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"];
// CPR's launcher treatment ends long before compressions do. Keep the DP pause through the real native role and
// the bounded CPR <-> BVM transfer window; clear it only after both roles and both handoff clocks have ended.
if (!_maneuverActive && {_pauseClass in _maneuverClasses}) then {
    _medic setVariable ["ACME_DP_Paused", false, false];
    _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
    _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _manualPause = false;
    _pauseClass = "";
    _treatmentBusy = _medic getVariable ["ACME_treatmentPreflightActive", false];
};
private _mustYieldClinical = _maneuverActive || {_manualPause} || {_chestPrep} || {_headProvider} || {_treatmentBusy};
private _yieldedClinical = _medic getVariable ["ACME_DP_ClinicalYield", false];

if (_mustYieldClinical) exitWith {
    // Kill only DP's own visual generation. Never inject a neutral pose; the incoming intervention owns animation.
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    _medic setVariable ["ACME_DP_InPose", false, false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
    if (!_yieldedClinical) then {
        [_patient, "directPressureMarker", [_medic, _bodyPart, false]] call ACME_fnc_ownerDispatch;
        _medic setVariable ["ACME_DP_ClinicalYield", true];
        _medic setVariable ["ACME_DP_ClinicalYieldStart", CBA_missionTime];
    };
};

// Only a provider with no higher-priority intervention may adopt/reassert the visible Direct Pressure pose.
if (_mode in ["torso", "limb"]) then {[_medic, _patient] call ACME_fnc_directPressurePose;};

// Reapply the synchronized pressure marker once the incompatible activity ends. Shift both clot timers by the exact
// yielded duration so time spent walking, assessing, or performing another maneuver never counts as pressure time.
if (_yieldedClinical) then {
    private _yieldStart = _medic getVariable ["ACME_DP_ClinicalYieldStart", CBA_missionTime];
    private _yieldDuration = (CBA_missionTime - _yieldStart) max 0;
    _medic setVariable ["ACME_DP_Start", (_medic getVariable ["ACME_DP_Start", CBA_missionTime]) + _yieldDuration];
    _medic setVariable ["ACME_DP_NextClot", (_medic getVariable ["ACME_DP_NextClot", CBA_missionTime]) + _yieldDuration];
    _medic setVariable ["ACME_DP_ClinicalYield", false];
    _medic setVariable ["ACME_DP_ClinicalYieldStart", 0];
    [_patient, "directPressureMarker", [_medic, _bodyPart, true]] call ACME_fnc_ownerDispatch;
};

private _held = CBA_missionTime - (_medic getVariable ["ACME_DP_Start", CBA_missionTime]);
if (_held < 15) exitWith {};
if (CBA_missionTime < (_medic getVariable ["ACME_DP_NextClot", 0])) exitWith {};
_medic setVariable ["ACME_DP_NextClot", CBA_missionTime + 2];

// Wound arrays belong to the casualty owner. The provider owns only the hold timer/animation; ask the patient
// owner to perform this clot attempt against its current wound state so simultaneous damage/coagulation cannot
// race a remote client's read/modify/write.
[_patient, "directPressureClot", [_medic, _bodyPart]] call ACME_fnc_ownerDispatch;
