/* B70 Semi-Fowler visual application.
 * The casualty is never attached to a zero-offset helper and never teleported vertically.  The BI injured-man
 * animation contains the authored root/pose offsets; forcing an attached helper on top of it is what drove the body
 * through terrain.  Elevation therefore plays the requested patient animation once and lets its move graph settle.
 */
params [["_patient", objNull, [objNull]], ["_replayAnim", true, [true]]];
if (isNull _patient || {!alive _patient}) exitWith {};
if (!local _patient) exitWith {[_patient, "headElevTilt", [_patient, _replayAnim]] call ACME_fnc_ownerDispatch;};
if ([_patient] call ACME_fnc_animBlocked) exitWith {};

// Retire any helper left by an older build without moving the casualty back to a stale stored world position.
private _helper = _patient getVariable ["ACME_headElev_helper", objNull];
[_patient, _helper] call ACME_fnc_releasePatient;
if (!isNull _helper) then {deleteVehicle _helper;};
_patient setVariable ["ACME_headElev_helper", objNull, true];
private _m = _patient getVariable ["ACME_headElev_mass", -1];
if (_m > 0) then {_patient setMass _m; _patient setVariable ["ACME_headElev_mass", nil, true];};

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
    if (_animToken == "") exitWith {};
    [_patient, false] call ACME_fnc_headElevCollision;
    // The pin covers the whole lift motion and a short tail. The hold that follows has a speed of zero and moves
    // nothing, so the pin is not needed after that.
    [_patient, _liftTime + 0.6] call ACME_fnc_headElevPinPose;

    // The move graph carries the casualty from the grab into the hold. This check only covers the case where
    // another system took the casualty out of the grab first.
    private _poseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
    [{
        params ["_patient", "_poseToken", "_animToken"];
        if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
        if ((_patient getVariable ["ACME_headElev_poseToken", ""]) != _poseToken) exitWith {};
        if (!(_patient getVariable ["ACME_headElevated", false])) exitWith {};
        if (_patient getVariable ["ACME_headElev_Suspended", false]) exitWith {};
        if (((_patient getVariable ["ACME_patientAnimLock", []]) param [0, ""]) != _animToken) exitWith {};
        [_patient, _animToken] call ACME_fnc_patientAnimRelease;
        private _state = toLower animationState _patient;
        if (_state != "acme_headelevpatienthold") then {
            [_patient, "ACME_HeadElevPatientHold", 2] call ACME_fnc_doAnim;
        };
        [_patient, true] call ACME_fnc_headElevCollision;
    }, [_patient, _poseToken, _animToken], _liftTime + 0.5] call CBA_fnc_waitAndExecute;
};
_patient setVariable ["ACME_headElev_visualActive", true, true];
