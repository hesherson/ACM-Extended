// limb and torso direct pressure: the free-movement holding pose. it is called every active tick.
// the medic can still use the medical menu and other treatments. while stationary and looking at the patient they
// adopt the connected direct-pressure hold. any competing treatment, movement, or look-away immediately retires the
// held-animation reassert worker. Movement only releases the pose, not the clinical Direct Pressure state, so the
// animation can reapply after the provider stops moving and settles again.
params ["_medic", "_patient"];
private _inPose = _medic getVariable ["ACME_DP_InPose", false];
private _poseToken = _medic getVariable ["ACME_DP_PoseToken", 0];

// ACE can still be finishing the treatment callback for a fraction of a second after Direct Pressure starts.
// During that entry grace, do not interpret ACE's own end-animation bookkeeping as a competing treatment or it
// immediately tears down the hold we just requested.
private _entryGrace = CBA_missionTime < (_medic getVariable ["ACME_DP_PoseGraceUntil", 0]);

// A plain open medical menu is NOT a competing treatment. Stop Direct Pressure has to remain usable while the
// provider visibly keeps pressure on the wound. Yield only when another treatment actually owns the provider pose.
private _treating = !_entryGrace && {
    (_medic getVariable ["ACME_DP_TreatmentBusy", false])
    || {(_medic getVariable ["ACME_treatmentPreflightActive", false])}
    || {(_medic getVariable ["ACME_chestAccessPreflightActive", false])}
    || {(_medic getVariable ["ACME_chestAccessProvider", []]) isNotEqualTo []}
    || {_medic getVariable ["ACME_headElev_seqActive", false]}
    || {(_medic getVariable ["ace_medical_treatment_endInAnim", ""]) != ""}
    || {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}
    || {[_patient] call ACM_core_fnc_cprActive}
    || {[_patient] call ACM_core_fnc_bvmActive}
};
if (_treating) exitWith {
    // Kill ACME_fnc_doAnimHeld's reassert generation before the tourniquet/bandage/other treatment takes over.
    // Do not force an unarmed crouch here. The incoming treatment owns the next pose and forcing Wnon first is what
    // produced the visible weapon-out/weapon-away flicker between back-to-back actions.
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    _medic setVariable ["ACME_DP_InPose", false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime];
};

// there is no pose in a vehicle.
if (!isNull objectParent _medic) exitWith {
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    if (_inPose) then {
        _medic setVariable ["ACME_DP_InPose", false];
    };
};

private _now = CBA_missionTime;

// the movement intent: the movement keys or actual displacement since the last tick. inputAction respects remapped
// keyboard/controller bindings, so the escape behavior does not depend on W/A/S/D specifically.
private _moveInput = (inputAction "MoveForward") + (inputAction "MoveBack")
                   + (inputAction "MoveLeft") + (inputAction "MoveRight")
                   + (inputAction "MoveFastForward") + (inputAction "MoveSlowForward")
                   + (inputAction "Evasive");
private _lastPos = _medic getVariable ["ACME_DP_LastPos", getPosASL _medic];
private _cur = getPosASL _medic;
_medic setVariable ["ACME_DP_LastPos", _cur];
private _moving = (_moveInput > 0) || {(_cur distance _lastPos) > 0.04};

// looking toward the patient, on horizontal facing, pitch-independent.
private _dv = (getPosVisual _patient) vectorDiff (getPosVisual _medic);
private _dv2 = [_dv select 0, _dv select 1, 0];
private _lk = eyeDirection _medic;
private _lk2 = [_lk select 0, _lk select 1, 0];
private _looking = if (_dv2 isEqualTo [0,0,0] || {_lk2 isEqualTo [0,0,0]}) then { true } else {
    ((vectorNormalized _dv2) vectorDotProduct (vectorNormalized _lk2)) > (missionNamespace getVariable ["ACME_DP_lookDot", 0.4])
};

if (_moving || {!_looking}) then {
    // Movement/look-away is an absolute POSE escape, not a Direct Pressure cancellation. Retire every pending held
    // reassert first. When actual movement exists, do not inject an intermediate unarmed animation at all: the
    // player's own movement state gets first chance to supersede the hold, preserving the selected weapon state.
    _medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];
    private _actual = toLower animationState _medic;
    private _ownsVisibleHold = _inPose || {_actual == "acme_directpressurehold"};
    if (_ownsVisibleHold && {!([_medic] call ACME_fnc_animBlocked)}) then {
        _medic setUnitPos "AUTO";

        if (!_moving) then {
            // Looking away while stationary has no movement state to take over, so use the normal neutral exit.
            [_medic, "AmovPknlMstpSnonWnonDnon", 1] call ACME_fnc_doAnim;
        };

        // Narrow engine-state repair. A movement command must never be swallowed by a stale looping DP state. If the
        // engine is STILL physically in the DP hold after movement/treatment has had a chance to win, use priority 2
        // once to break only that stale state. B127 token-checks the callback so an exit scheduled by an old hold can
        // never break a newer Direct Pressure episode or a treatment which replaced it.
        [{
            params ["_m", "_tok"];
            if (isNull _m || {!local _m} || {!alive _m} || {!isNull objectParent _m}) exitWith {};
            if ((_m getVariable ["ACME_DP_PoseToken", -1]) != _tok) exitWith {};
            if !(_m getVariable ["ACME_DP_Active", false]) exitWith {};
            if ((toLower animationState _m) != "acme_directpressurehold") exitWith {};
            _m setUnitPos "AUTO";
            [_m, "AmovPknlMstpSnonWnonDnon", 2] call ACME_fnc_doAnim;
        }, [_medic, _poseToken], 0.08] call CBA_fnc_waitAndExecute;
    };
    _medic setVariable ["ACME_DP_InPose", false];
    _medic setVariable ["ACME_DP_IdleStart", _now];
} else {
    if (!_inPose) then {
        private _idleStart = _medic getVariable ["ACME_DP_IdleStart", _now];
        if ((_now - _idleStart) >= (missionNamespace getVariable ["ACME_DP_idleToPose", 0.8])) then {
            // Resume the ACME-owned pose directly. No weapon preflight, holster request, or weapon restore is issued.
            [_medic, "ACME_DirectPressureHold", 1.1, 1] call ACME_fnc_doAnimHeld;
            _medic setVariable ["ACME_DP_InPose", true];
            _medic setVariable ["ACME_DP_LastPoseAssert", _now];
        };
    } else {
        // ACE or another animation layer can replace a looping hold after our initial request. ACME_DP_InPose is
        // intent, not proof that the engine is still showing the pose, so reassert it at a low rate while the medic
        // remains stationary, facing the patient, and no real competing treatment owns the animation.
        private _actual = toLower (animationState _medic);
        private _lastAssert = _medic getVariable ["ACME_DP_LastPoseAssert", 0];
        if (_actual != "acme_directpressurehold" && {(_now - _lastAssert) >= 0.6} && {!([_medic] call ACME_fnc_animBlocked)}) then {
            [_medic, "ACME_DirectPressureHold", 1.1, 1] call ACME_fnc_doAnimHeld;
            _medic setVariable ["ACME_DP_LastPoseAssert", _now];
        };
    };
};
