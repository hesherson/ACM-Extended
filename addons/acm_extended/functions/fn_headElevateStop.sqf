// B71 lower Semi-Fowler to flat using the authored patient release in tandem with the provider sequence.
params [
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_quiet", false, [false]],
    ["_frontNormalized", false, [false]],
    ["_preserveSupportForChest", false, [false]],
    ["_providerReady", false, [false]],
    ["_cprEpoch", -1, [0]],
    ["_cprOwner", -1, [0]]
];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    [_patient, "headElevStop", [_medic, _patient, _quiet, _frontNormalized, _preserveSupportForChest, _providerReady, _cprEpoch, _cprOwner]] call ACME_fnc_ownerDispatch;
};
if (canSuspend) exitWith {isNil {[_medic, _patient, _quiet, _frontNormalized, _preserveSupportForChest, _providerReady, _cprEpoch, _cprOwner] call ACME_fnc_headElevateStop;};};
// Only the server can resolve a remote unit's owner. Patient-owner clients validate the replicated episode;
// local providers use clientOwner, including the valid local zero identity outside multiplayer.
private _validCPROwner = {
    params ["_medic", "_providerOwner"];
    if (!finite _providerOwner || {_providerOwner < 0} || {_providerOwner != floor _providerOwner}
        || {_providerOwner == 0 && {isMultiplayer}}) exitWith {false};
    if (local _medic) exitWith {_providerOwner == clientOwner};
    isMultiplayer && {!isServer || {_providerOwner == owner _medic}}
};
// A queued automatic lower belongs only to the CPR episode that requested it. Cancellation, replacement and
// provider ownership transfer retire that request before it can move the patient or steal chest custody.
if (_cprEpoch >= 0 && {isNull _medic || {!alive _medic}
    || {!([_medic] call ace_common_fnc_isAwake)} || {!([_medic, _cprOwner] call _validCPROwner)}
    || {(_medic getVariable ["ACM_circulation_CPR_Epoch", -1]) != _cprEpoch}
    || {!((_patient getVariable ["ACM_circulation_CPR_session", []]) isEqualTo [_medic, _cprEpoch])}}) exitWith {};
// A cancelled CPR entry may have already cleared the logical elevation while its accepted release is still
// running. A replacement episode must wait for that exact motion to retire before an "already flat" ACK.
private _pendingLowerLock = _patient getVariable ["ACME_patientAnimLock", []];
if (_cprEpoch >= 0 && {!(_patient getVariable ["ACME_headElevated", false])}
    && {(_pendingLowerLock param [1, ""]) == "head-elev-lower"}) exitWith {};
private _cprLowerAck = _patient getVariable ["ACME_cprLowerReady", []];
if (_cprEpoch >= 0 && {(_cprLowerAck param [0, objNull]) isEqualTo _medic}
    && {(_cprLowerAck param [1, -1]) == _cprEpoch}) exitWith {};
private _lowerStateEpoch = (_patient getVariable ["ACME_headElev_startEpoch", 0]) + 1;
_patient setVariable ["ACME_headElev_startEpoch", _lowerStateEpoch, false];
private _publishCPRLower = {
    params ["_delay"];
    if (_cprEpoch >= 0) then {
        _patient setVariable ["ACME_cprLowerReady", [_medic, _cprEpoch, if (_delay < 0) then {_delay} else {serverTime + _delay}], true];
    };
};
private _cprLowerDelay = 0;
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
    _patient setVariable ["ACME_chestAccess_vestLoadoutKitEpoch",
        _patient getVariable ["ACME_headElev_vestLoadoutKitEpoch", _patient getVariable ["ACME_equipmentKitEpoch", 0]], true];
    _patient setVariable ["ACME_chestAccess_vestProp", _headSupportProp, true];
    // Transfer custody of the SAME live container; never recreate its pre-removal supplies.
    if (_patient getVariable ["ACME_headElev_vestLoadoutLive", false]) then {
        private _cargo = _patient getVariable ["ACME_carrierCargo", objNull];
        if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierSavedVar", "ACME_chestAccess_vestLoadout", true];};
        _patient setVariable ["ACME_chestAccess_vestLoadoutLive", true, true];
        _patient setVariable ["ACME_chestAccess_vestLoadoutSettled", false, true];
        _patient setVariable ["ACME_headElev_vestLoadoutLive", false, true];
    };
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
if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease; [0] call _publishCPRLower;};
if !(_patient getVariable ["ACME_headElevated", false]) exitWith {
    [_patient] call ACME_fnc_headElevVestRestore;
    [_patient] call ACME_fnc_chestAccessVestRestore;
    [0] call _publishCPRLower;
};

// An active Semi-Fowler placement is already anterior-up by construction. Lowering must never classify the
// transient release geometry as prone and start a second body roll. The release animation itself returns the
// casualty directly to the stable face-up rest.
_patient setVariable ["ACME_CS_facing","front",true];

// Supported Lower Head starts provider and patient motion on the same frame. Provider theatre does not gate
// patient state or the lay-flat animation. Automatic suspension and manual-held Semi-Fowler keep their own paths.
if (!_providerReady && {!_quiet} && {!_wasSuspended} && {!_wasManualUnsupported}
    && {!isNull _medic} && {!([_medic] call ACME_fnc_animBlocked)}
    && {!([_patient] call ACME_fnc_animBlocked)}) then {
    [_medic, "lower"] call ACME_fnc_headElevMedicSeq;
};

// If Lower Head is requested while the lift tail still owns the patient, retire that exact lease synchronously.
// The lay-flat release can then acquire the casualty immediately instead of silently losing to our own old lock.
private _activePatientLock = _patient getVariable ["ACME_patientAnimLock", []];
if ((count _activePatientLock) >= 5
    && {(_activePatientLock param [1, ""]) == "head-elev-lift"}
    && {(_activePatientLock param [4, -1]) > serverTime}) then {
    private _liftToken = _activePatientLock param [0, ""];
    if (_liftToken != "") then {[_patient, _liftToken] call ACME_fnc_patientAnimRelease;};
    [_patient, true] call ACME_fnc_headElevCollision;
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
if (!_quiet && {!isNull _medic} && {!isNil "ace_medical_treatment_fnc_addToLog"}) then {
    private _providerName = [_medic, false, true] call ace_common_fnc_getName;
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
// Preserve the shared original mass until the deferred global restore actually executes. A subsequent accepted
// lower invalidates that restore; a competing live moving lease still owns collision if our lower is rejected.
private _motionToken = _patient getVariable ["ACME_patientAnimSpeedToken", ""];
private _motionLock = _patient getVariable ["ACME_patientAnimLock", []];
private _motionOwnsCollision = _motionToken != "" && {(_motionLock param [0, ""]) == _motionToken}
    && {(_motionLock param [4, -1]) > serverTime};
if (_mass > 0 && {!_motionOwnsCollision}) then {[_patient, true] call ACME_fnc_headElevCollision;};


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
        _cprLowerDelay = -2; // Accepted, awaiting the owner-side animation completion below.
        [_patient, false] call ACME_fnc_headElevCollision;
        [_patient, _lowerTime] call ACME_fnc_headElevPinPose;
    } else {
        // No accepted animation means no proof that a living, visibly elevated casualty was laid flat.
        // Leave the requesting CPR controller to cancel at its bounded entry deadline.
        _cprLowerDelay = -1;
    };
    // Manual/unsupported Semi-Fowler owns its provider exit through fn_headElevHoldStart. Starting the ordinary
    // Lower Head provider sequence here would make two animation controllers fight over the same medic.
    // The supported provider sequence already owns its reach/exit; never start it again here.
    private _rest = [_patient] call ACME_fnc_headElevRestAnim;
    [{
        params ["_patient", "_rest", "_animToken", "_medic", "_cprEpoch", "_cprOwner", "_lowerStateEpoch", "_validCPROwner"];
        if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
        if (_patient getVariable ["ACME_headElevated", false]) exitWith {};
        // B238: manual lowering has the same lifecycle boundary as an automatic CPR lower.
        if ((_patient getVariable ["ACME_headElev_startEpoch", 0]) != _lowerStateEpoch) exitWith {};
        if ((_patient getVariable ["ACME_headElev_poseToken", ""]) != "") exitWith {};
        private _ownsAnim = _animToken != "" && {((_patient getVariable ["ACME_patientAnimLock", []]) param [0, ""]) == _animToken};
        if ((_cprEpoch >= 0 || {_animToken != ""}) && {!_ownsAnim}) exitWith {};
        // Retire this completion before gear/presentation writes. A repeated delivery cannot restore twice.
        _patient setVariable ["ACME_headElev_startEpoch", _lowerStateEpoch + 1, false];
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
        // A pending request becomes ready only after this owner has finished the accepted release. Expired,
        // replaced or migrated animation ownership cannot authorize compressions on a provider's local timer.
        if (_cprEpoch >= 0 && {_ownsAnim} && {!isNull _medic} && {alive _medic}
            && {[_medic] call ace_common_fnc_isAwake} && {[_medic, _cprOwner] call _validCPROwner}
            && {(_medic getVariable ["ACM_circulation_CPR_Epoch", -1]) == _cprEpoch}
            && {(_patient getVariable ["ACM_circulation_CPR_session", []]) isEqualTo [_medic, _cprEpoch]}) then {
            _patient setVariable ["ACME_cprLowerReady", [_medic, _cprEpoch, serverTime], true];
        };
    }, [_patient, _rest, _animToken, _medic, _cprEpoch, _cprOwner, _lowerStateEpoch, _validCPROwner], _lowerTime] call CBA_fnc_waitAndExecute;
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

[_cprLowerDelay] call _publishCPRLower;
