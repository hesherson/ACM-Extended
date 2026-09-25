// B71 lower Semi-Fowler to flat using the authored patient release in tandem with the provider sequence.
params [
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_quiet", false, [false]],
    ["_frontNormalized", false, [false]],
    ["_preserveSupportForChest", false, [false]],
    ["_providerReady", false, [false]]
];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    [_patient, "headElevStop", [_medic, _patient, _quiet, _frontNormalized, _preserveSupportForChest, _providerReady]] call ACME_fnc_ownerDispatch;
};
if (canSuspend) exitWith {isNil {[_medic, _patient, _quiet, _frontNormalized, _preserveSupportForChest, _providerReady] call ACME_fnc_headElevateStop;};};
private _wasVisual = _patient getVariable ["ACME_headElev_visualActive", true];
private _wasSuspended = _patient getVariable ["ACME_headElev_Suspended", false];
private _wasManualUnsupported = _patient getVariable ["ACME_headElev_manualUnsupported", false];

// If CPR/chest access permanently replaces a plate-carrier-supported Semi-Fowler, transfer that exact removed
// carrier into chest-access custody instead of putting it back on during CPR. The existing chest-access release
// path then restores it once CPR/BVM and their handoff window are genuinely over.
private _headSupportSaved = +(_patient getVariable ["ACME_headElev_vestLoadout", []]);
private _headSupportProp = _patient getVariable ["ACME_headElev_propObj", objNull];
private _headSupportRemoved = _patient getVariable ["ACME_headElev_vestRemoved", false]
    && {(count _headSupportSaved) == 2};
private _chestLeasesNow = _patient getVariable ["ACME_chestAccess_leases", createHashMap];
private _handoffUntilNow = _patient getVariable ["ACME_chestAccess_maneuverHandoffUntil", -1];
private _chestOwnsAfterCancel = _preserveSupportForChest
    || {(count _chestLeasesNow) > 0}
    || {[_patient] call ACME_fnc_chestAccessManeuverActive}
    || {(_handoffUntilNow isEqualType 0) && {serverTime < _handoffUntilNow}};

if (_headSupportRemoved && {_chestOwnsAfterCancel}
    && {(count (_patient getVariable ["ACME_chestAccess_vestLoadout", []])) != 2}) then {
    _patient setVariable ["ACME_chestAccess_vestLoadout", +_headSupportSaved, true];
    _patient setVariable ["ACME_chestAccess_vestProp", _headSupportProp, true];
    if (!isNull _headSupportProp) then {
        _headSupportProp setVariable ["ACME_chestFixedPark", _headSupportProp getVariable ["ACME_chestFixedPark", []], false];
    };

    _patient setVariable ["ACME_headElev_vestRemoved", false, true];
    _patient setVariable ["ACME_headElev_vestLoadout", [], true];
    _patient setVariable ["ACME_headElev_propVest", "", true];
    _patient setVariable ["ACME_headElev_propVestItems", [], true];
    _patient setVariable ["ACME_headElev_propObj", objNull, true];
};

[_patient] call ACME_fnc_headElevHoldClear;
_patient setVariable ["ACME_headElev_treatments", createHashMap, true];
if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease;};
if !(_patient getVariable ["ACME_headElevated", false]) exitWith {
    [_patient] call ACME_fnc_headElevVestRestore;
    [_patient] call ACME_fnc_chestAccessVestRestore;
};

// Lowering Semi-Fowler also starts from the back. If something externally left the casualty posterior-up, roll
// front/supine first and only then play ACME_HeadElevPatientRelease.
private _actualBeforeLower = [_patient, _patient getVariable ["ACME_CS_facing","front"]]
    call ACME_fnc_chestSealActualSide;
private _needFrontFirst = !_frontNormalized && {_actualBeforeLower != "front"};

if (_needFrontFirst) exitWith {
    private _delay = 0.08;

    if ([_patient] call ACME_fnc_chestSealCanPhysicalRoll) then {
        [_patient,"front",false,_medic,true] call ACME_fnc_chestSealRoll;
        private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime", 1.85 / (call ACME_fnc_choreographyRate)];
        if !(_rollTime isEqualType 0 && {finite _rollTime}) then {_rollTime = 1.85 / (call ACME_fnc_choreographyRate);};
        _delay = (_rollTime max 0.1) + 0.08;
    } else {
        private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"];
        _patient setVariable ["ACME_CS_facing","front",true];
        ["ace_common_switchMove",[_patient,_faceUp]] call CBA_fnc_globalEvent;
    };

    // The roll belongs to this placement. A later elevation or a completed lower
    // must not be retired by this old retry, even when the patient is local again.
    private _poseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
    [{
        params ["_m","_p","_quiet","_poseToken","_preserveSupportForChest"];
        if (isNull _p || {!local _p}) exitWith {};
        if ((_p getVariable ["ACME_headElev_poseToken", ""]) != _poseToken) exitWith {};
        _p setVariable ["ACME_CS_facing","front",true];
        [_m,_p,_quiet,true,_preserveSupportForChest] call ACME_fnc_headElevateStop;
    }, [_medic,_patient,_quiet,_poseToken,_preserveSupportForChest], _delay] call CBA_fnc_waitAndExecute;
};

// An explicit supported Lower Head waits for the medic's actual reach. Automatic suspension,
// manual-hold release and CPR still use their existing patient-only handoff.
if (!_providerReady && {!_quiet} && {!_wasSuspended} && {!_wasManualUnsupported}
    && {!isNull _medic} && {!([_medic] call ACME_fnc_animBlocked)}
    && {!([_patient] call ACME_fnc_animBlocked)}) exitWith {
    [_medic, "lower", _patient, _patient getVariable ["ACME_headElev_poseToken", ""]] call ACME_fnc_headElevMedicSeq;
};

_patient setVariable ["ACME_CS_facing","front",true];
_patient setVariable ["ACME_headElev_poseToken", "", true];
_patient setVariable ["ACME_headElevated", false, true];
_patient setVariable ["ACME_headElev_pendingLift", [], true];
_patient setVariable ["ACME_headElev_manualUnsupported", false, true];
_patient setVariable ["ACME_headElev_Suspended", false, true];
_patient setVariable ["ACME_headElev_ResumePending", false, true];
_patient setVariable ["ACME_headElev_visualActive", false, true];
_patient setVariable ["ACME_headElev_suspendVestLoadout", [], false];
_patient setVariable ["ACME_headElev_suspendReadyAt", -1, false];
_patient setVariable ["ACME_headElev_suspendKeepVestOut", false, true];
if (!_quiet && {!isNil "ace_medical_treatment_fnc_addToLog"}) then {
    private _providerName = if (isNull _medic) then {"Provider"} else {[_medic, false, true] call ace_common_fnc_getName};
    [_patient, "activity", "%1 laid head flat", "%1 laid them supine", [_providerName]] call ACME_fnc_medLog;
};
private _pfh = _patient getVariable ["ACME_headElev_pfh", -1];
if (_pfh isEqualType 0 && {_pfh >= 0}) then {[_pfh] call CBA_fnc_removePerFrameHandler; _patient setVariable ["ACME_headElev_pfh", -1];};

// Clean any helper left from an older build, but never restore a cached world position.
private _helper = _patient getVariable ["ACME_headElev_helper", objNull];
[_patient, _helper] call ACME_fnc_releasePatient;
if (!isNull _helper) then {deleteVehicle _helper;};
_patient setVariable ["ACME_headElev_helper", objNull, true];
private _mass = _patient getVariable ["ACME_headElev_mass", -1];
if (_mass > 0) then {_patient setMass _mass; _patient setVariable ["ACME_headElev_mass", nil, true];};


// If the casualty was already physically flat from a temporary suspension, permanent cancellation only retires
// the logical Semi-Fowler episode. Replaying the release animation here is what caused CPR/BVM handoffs to keep
// "setting them down" over and over.
private _visibleLower = !_quiet && {!_wasSuspended} && {isNull objectParent _patient}
    && {_wasVisual};
if (_visibleLower) then {
    // Patient and provider start together. The carrier stays as the physical bolster until the authored release has
    // finished, then it returns to the chest. That prevents a loadout change from cutting the lay-flat animation short.
    private _lowerTime = missionNamespace getVariable ["ACME_headElev_lowerAnimTime", 1.4 / (call ACME_fnc_choreographyRate)];
    private _animToken = [_patient, "ACME_HeadElevPatientRelease", 2, "head-elev-lower", _medic, _lowerTime + 0.3, 1]
        call ACME_fnc_patientAnimRequest;
    if (_animToken != "") then {
        [_patient, false] call ACME_fnc_headElevCollision;
        [_patient, _lowerTime] call ACME_fnc_headElevPinPose;
    };
    // Manual/unsupported Semi-Fowler owns its provider exit through fn_headElevHoldStart. Starting the ordinary
    // Lower Head provider sequence here would make two animation controllers fight over the same medic.
    // The supported provider sequence already owns its reach/exit; never start it again here.
    private _rest = [_patient] call ACME_fnc_headElevRestAnim;
    [{
        params ["_patient", "_rest", "_animToken"];
        if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
        if (_patient getVariable ["ACME_headElevated", false]) exitWith {};
        private _ownsAnim = _animToken != "" && {((_patient getVariable ["ACME_patientAnimLock", []]) param [0, ""]) == _animToken};
        if (_ownsAnim) then {[_patient, _animToken] call ACME_fnc_patientAnimRelease;};
        // A newer elevation must finish its own lift before normal collision returns.
        if (_ownsAnim) then {[_patient, true] call ACME_fnc_headElevCollision;};
        // This is a true Lower Head action: the support carrier may finally return to the body. A separate
        // backpack-supported chest-access carrier still waits for its own action lease to end.
        [_patient] call ACME_fnc_headElevVestRestore;
        [_patient] call ACME_fnc_chestAccessVestRestore;
        private _propObj = _patient getVariable ["ACME_headElev_propObj", objNull];
        if (!isNull _propObj) then {detach _propObj; deleteVehicle _propObj;};
        _patient setVariable ["ACME_headElev_propObj", objNull, true];
        if (_ownsAnim && {isNull objectParent _patient} && {_rest != ""}) then {[_patient, _rest, 2] call ACME_fnc_doAnim;};
    }, [_patient, _rest, _animToken], _lowerTime] call CBA_fnc_waitAndExecute;
} else {
    [_patient, true] call ACME_fnc_headElevCollision;
    [_patient] call ACME_fnc_headElevVestRestore;
    [_patient] call ACME_fnc_chestAccessVestRestore;
    private _propObj = _patient getVariable ["ACME_headElev_propObj", objNull];
    if (!isNull _propObj) then {detach _propObj; deleteVehicle _propObj;};
    _patient setVariable ["ACME_headElev_propObj", objNull, true];
};
_patient setVariable ["ACME_headElev_preserveFaceDown", nil, true];
_patient setVariable ["ACME_headElev_baseAnim", nil, true];
