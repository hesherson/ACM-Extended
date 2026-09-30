/* B70 Semi-Fowler visual application.
 * The casualty is never attached to a zero-offset helper and never teleported vertically.  The BI injured-man
 * animation contains the authored root/pose offsets; forcing an attached helper on top of it is what drove the body
 * through terrain.  Elevation therefore plays the requested patient animation once and lets its move graph settle.
 */
params [["_patient", objNull, [objNull]], ["_replayAnim", true, [true]]];
if (isNull _patient || {!alive _patient}) exitWith {false};
if (!local _patient) exitWith {
    [_patient, "headElevTilt", [_patient, _replayAnim]] call ACME_fnc_ownerDispatch;
    true
};
if ([_patient] call ACME_fnc_animBlocked) exitWith {false};

// Retire any helper left by an older build without moving the casualty back to a stale stored world position.
private _helper = _patient getVariable ["ACME_headElev_helper", objNull];
[_patient, _helper] call ACME_fnc_releasePatient;
if (!isNull _helper) then {deleteVehicle _helper;};
_patient setVariable ["ACME_headElev_helper", objNull, true];
private _m = _patient getVariable ["ACME_headElev_mass", -1];
// Legacy cleanup must use the same deferred, global restore as ordinary motion completion. A local setMass
// followed by clearing the saved value strands observers at low mass and defeats the next-frame safety window.
// An existing moving lease keeps its collision ownership if the replacement lift is rejected below.
private _motionToken = _patient getVariable ["ACME_patientAnimSpeedToken", ""];
private _motionLock = _patient getVariable ["ACME_patientAnimLock", []];
private _motionOwnsCollision = _motionToken != "" && {(_motionLock param [0, ""]) == _motionToken}
    && {(_motionLock param [4, -1]) > serverTime};
if (_m > 0 && {!_motionOwnsCollision}) then {[_patient, true] call ACME_fnc_headElevCollision;};

private _visualAccepted = true;
if (_replayAnim && {isNull objectParent _patient}) then {
    // ACM can report ACM_LyingState for one frame while the grab enters. Give the animation guard a short grace.
    // Priority 2 is the ACE pickup method: playMoveNow first, then switchMove when the move graph has no edge from
    // the current pose. An ACE unconscious pose has no edge into the grab, so the fallback is required.
    _patient setVariable ["ACME_headElev_animGraceUntil", CBA_missionTime + 2.5, false];
    // The casualty carries no physics weight while the body moves. A provider standing over them is otherwise
    // pushed by the body, hard enough to throw them and kill them.
    private _liftTime = missionNamespace getVariable ["ACME_headElev_liftAnimTime", 1.2 / (call ACME_fnc_choreographyRate)];
    if (!(_liftTime isEqualType 0) || {_liftTime <= 0}) then {_liftTime = 1.2 / (call ACME_fnc_choreographyRate);};
    private _animToken = [_patient, "ACME_HeadElevPatientGrab", 2, "head-elev-lift", objNull, _liftTime + 0.6, 1]
        call ACME_fnc_patientAnimRequest;
    if (_animToken == "") exitWith {_visualAccepted = false;};
    [_patient, false] call ACME_fnc_headElevCollision;
    // The pin covers the whole lift motion and a short tail. The hold that follows has a speed of zero and moves
    // nothing, so the pin is not needed after that.
    [_patient, _liftTime + 0.6] call ACME_fnc_headElevPinPose;

    // The move graph carries the casualty from the grab into the hold. This check only covers the case where
    // another system took the casualty out of the grab first.
    private _poseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
    if (_patient getVariable ["ACME_headElev_vestRemoved", false]) then {
        // Seat the saved support carrier after this actual lift, never during provider preparation. A manually
        // removed carrier may already have a persistent world prop; reuse that exact object instead of spawning a
        // duplicate, then clear its fixed chest-access park before attaching it behind the upper back.
        [{
            params ["_patient", "_vestClass", "_poseToken"];
            if (isNull _patient || {!local _patient} || {!alive _patient}
                || {!(_patient getVariable ["ACME_headElevated", false])}
                || {(_patient getVariable ["ACME_headElev_poseToken", ""]) != _poseToken}
                || {!(_patient getVariable ["ACME_headElev_vestRemoved", false])}
                || {!isNull objectParent _patient}) exitWith {};

            private _prop = _patient getVariable ["ACME_headElev_propObj", objNull];
            if (isNull _prop) then {
                private _model = getText (configFile >> "CfgWeapons" >> _vestClass >> "model");
                if (_model != "") then {_prop = createSimpleObject [_model, [0,0,0], false];};
                if (isNull _prop) then {
                    _prop = createVehicle ["GroundWeaponHolder", getPosATL _patient, [], 0, "CAN_COLLIDE"];
                    _prop addItemCargoGlobal [_vestClass, 1];
                };
                _patient setVariable ["ACME_headElev_propObj", _prop, true];
            };

            if (!isNull _prop) then {_prop setVariable ["ACME_chestFixedPark", nil, false];};
            [_patient] call ACME_fnc_headElevPropApply;
        }, [_patient, _patient getVariable ["ACME_headElev_propVest", ""], _poseToken], _liftTime + 0.1] call CBA_fnc_waitAndExecute;
    };
    [{
        params ["_patient", "_poseToken", "_animToken"];
        if (isNull _patient || {!local _patient}) exitWith {};
        private _lock = _patient getVariable ["ACME_patientAnimLock", []];
        private _ownsAnim = (_lock param [0, ""]) == _animToken;
        if (!_ownsAnim) exitWith {};

        // Always retire our own lift lease, even when Lower Head/cancellation cleared the logical placement while
        // the grab was still running. B165 returned before this release and could strand the patient animation lock
        // and collision-disabled state, which in turn made later medical actions appear dead.
        [_patient, _animToken] call ACME_fnc_patientAnimRelease;

        private _currentPose = _patient getVariable ["ACME_headElev_poseToken", ""];
        private _replacementPlacement = _currentPose != "" && {_currentPose != _poseToken};
        if (!_replacementPlacement) then {
            [_patient, true] call ACME_fnc_headElevCollision;
        };

        if (!alive _patient || {_replacementPlacement}
            || {!(_patient getVariable ["ACME_headElevated", false])}
            || {_patient getVariable ["ACME_headElev_Suspended", false]}) exitWith {};

        private _state = toLowerANSI animationState _patient;
        if (_state != "acme_headelevpatienthold") then {
            [_patient, "ACME_HeadElevPatientHold", 2] call ACME_fnc_doAnim;
        };
    }, [_patient, _poseToken, _animToken], _liftTime + 0.5] call CBA_fnc_waitAndExecute;
};
if (!_visualAccepted) exitWith {
    _patient setVariable ["ACME_headElev_visualActive", false, true];
    false
};
_patient setVariable ["ACME_headElev_visualActive", true, true];
true
