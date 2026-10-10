// limb and torso direct pressure: the free-movement holding pose. it is called every active tick.
// the medic can still use the medical menu and other treatments. while stationary and looking at the patient they
// adopt the connected direct-pressure hold. any competing treatment, movement, or look-away immediately retires the
// held-animation reassert worker. Movement only releases the pose, not the clinical Direct Pressure state, so the
// animation reapplies only after two quiet seconds facing the patient; the pressure session remains active.
params ["_medic", "_patient"];
if (isNull _medic || {!local _medic}) exitWith {};
private _exit = _medic getVariable ["ACME_DP_Exit", []];
if (_exit isNotEqualTo [] && {(_exit param [2, -1]) != (_medic getVariable ["ACME_providerLocalityEpoch", 0])
    || {(CBA_missionTime - (_exit param [4, -99])) > ((_exit param [6, 0]) + 2)}}) then {
    _medic setVariable ["ACME_DP_Exit", [], false];
};
private _inPose = _medic getVariable ["ACME_DP_InPose", false];
private _heldPose = _medic getVariable ["ACME_DP_Pose", "ACME_DirectPressureHold"];
private _heldProne = _medic getVariable ["ACME_DP_PoseProne", false];
// A provider may choose prone while this persistent hold is running. Update both the
// requested state and the comparison target before any reassert can pull them up.
if (!_heldProne && {([_medic, "ACME_DirectPressureHold"] call ACME_fnc_providerAnimation) == "ACM_ProneContinuous"}) then {
    _heldProne = true;
    _heldPose = [_medic, "ACME_DirectPressureHold", true] call ACME_fnc_providerAnimation;
    _medic setVariable ["ACME_DP_Pose", _heldPose];
    _medic setVariable ["ACME_DP_PoseProne", true];
};
if ([_medic, _patient] call ACME_fnc_directPressurePoseBusy) exitWith {
    [_medic] call ACME_fnc_directPressurePoseRetire;
};

// there is no pose in a vehicle.
if (!isNull objectParent _medic) exitWith {
    [_medic] call ACME_fnc_directPressurePoseRetire;
    if (_inPose) then {
        _medic setVariable ["ACME_DP_InPose", false];
    };
};

private _now = CBA_missionTime;

// the movement intent: the movement keys or actual displacement since the last tick. inputAction respects remapped
// keyboard/controller bindings, so the escape behavior does not depend on W/A/S/D specifically.
private _moveInput = (inputAction "MoveForward") + (inputAction "MoveBack")
                   + (inputAction "MoveLeft") + (inputAction "MoveRight")
                   + (inputAction "TurnLeft") + (inputAction "TurnRight")
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
    private _actual = toLower animationState _medic;
    private _ownsVisibleHold = _inPose || {_actual == toLower _heldPose};
    [_medic] call ACME_fnc_directPressurePoseRetire;
    if (_ownsVisibleHold) then {[_medic, _heldProne] call ACME_fnc_directPressurePoseExit;};
    _medic setVariable ["ACME_DP_IdleStart", _now];
} else {
    if ((_medic getVariable ["ACME_DP_Exit", []]) isNotEqualTo []) exitWith {};
    if (!_inPose) then {
        private _idleStart = _medic getVariable ["ACME_DP_IdleStart", _now];
        if ((_now - _idleStart) >= (missionNamespace getVariable ["ACME_DP_idleToPose", 2])) then {
            [_medic, _patient] call ACME_fnc_directPressurePoseEnter;
        };
    } else {
        private _actual = toLower animationState _medic;
        private _lastAssert = _medic getVariable ["ACME_DP_LastPoseAssert", 0];
        if (_actual != toLower _heldPose && {(_now - _lastAssert) >= 0.6} && {!([_medic] call ACME_fnc_animBlocked)}) then {
            // Recheck real empty hands before recovering a replaced hold, never mask a selected weapon with Wnon.
            [_medic] call ACME_fnc_directPressurePoseRetire;
            [_medic, _patient] call ACME_fnc_directPressurePoseEnter;
        };
    };
};
