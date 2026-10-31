// Commit one discovered chest seal and own exactly one bounded medic3 placement animation.
// Placement uses the shared accelerated choreography rate. The Flip button may pre-empt this episode immediately.
params ["_idx"];
private _holes = uiNamespace getVariable ["ACME_CS_Holes", []];
if (_idx < 0 || {_idx >= count _holes}) exitWith {};
private _hole = _holes select _idx;
if (_hole select 4) exitWith {};
private _key = [_hole] call ACME_fnc_chestSealKey;
if !(["seal", _key, "ACM_ChestSeal"] call ACME_fnc_chestSealRequest) exitWith {};
(_holes select _idx) set [4, true];
uiNamespace setVariable ["ACME_CS_Holes", _holes];
uiNamespace setVariable ["ACME_CS_Held", false];

private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
uiNamespace setVariable ["ACME_CS_SealsLeft",
    [_medic, _patient, "ACM_ChestSeal"] call ACME_fnc_treatmentSupplyCount];

// AinvPknlMstpSnonWnonDnon_medic3 is reserved ONLY for physically applying a seal.
// Any previous placement worker is retired before the new seal owns its 2.65 s window.
if (!isNull _medic && {local _medic}) then {
    private _oldPFH = uiNamespace getVariable ["ACME_CS_ApplyPFH", -1];
    if (_oldPFH isEqualType 0 && {_oldPFH >= 0}) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};

    private _serial = (uiNamespace getVariable ["ACME_CS_ApplyAnimSerial", 0]) + 1;
    uiNamespace setVariable ["ACME_CS_ApplyAnimSerial", _serial];
    uiNamespace setVariable ["ACME_CS_ApplyPFH", -1];

    private _duration = missionNamespace getVariable ["ACME_CS_applyAnimSeconds", 2.65];
    if !(_duration isEqualType 0 && {finite _duration} && {_duration > 0.1} && {_duration < 10}) then {_duration = 2.65;};
    private _endsAt = diag_tickTime + _duration;
    uiNamespace setVariable ["ACME_CS_ApplyGestureUntil", _endsAt];

    // Retire whatever chest-procedure pose is currently visible as a handoff. This explicitly kills an old
    // NCD provider episode as well as the hands-on-chest workspace before seal placement takes ownership.
    private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
    private _poseMode = _pose param [1, ""];
    private _poseEpoch = _pose param [0, -1];
    if (_poseEpoch >= 0 && {_poseMode in ["chestSealWorkspace","chestSeal","ncdSeat","roll","chestAccess"]}) then {
        [_medic, _poseMode, _poseEpoch, true] call ACME_fnc_treatmentPoseStop;
    };

    _medic setVariable ["ACME_CS_providerHoldEpoch", -1, false];
    uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch", -1];

    // The chest workspace is already visibly empty-handed. Clear only Arma's logical weapon selection before
    // handing into medic3, then use the SAME normal priority-1 pose path as the rest of the chest choreography.
    // This avoids the priority-2/switchMove fallback which can visibly pull the selected weapon back into the hands.
    if (missionNamespace getVariable ["ACME_interventionAnimations", true]) then {
        if (currentWeapon _medic != "") then {_medic selectWeapon "";};
        _medic setVariable ["ACME_medicAnimationPrep", ["empty_hands_ready", CBA_missionTime, ""], false];
    };
    private _placeEpoch = [_medic, "chestSeal", _duration, _patient] call ACME_fnc_treatmentPoseStart;

    if (_placeEpoch >= 0) then {
        // B178 one-shot placement ownership: treatmentPoseStart issues the selected medic3/medicUp3 exactly once.
        // Do not run an independent watchdog that reissues the finite RTM when Arma naturally transitions out.
        uiNamespace setVariable ["ACME_CS_ApplyPFH", -1];

        // One bounded timer owns the placement lifetime. It is generation/epoch guarded, so Flip/close/reopen or
        // any newer treatment can pre-empt medic3 immediately and this callback becomes a no-op.
        [{
            params ["_m", "_p", "_epoch", "_serial"];
            if ((uiNamespace getVariable ["ACME_CS_ApplyAnimSerial", -1]) != _serial) exitWith {};
            private _pfh = uiNamespace getVariable ["ACME_CS_ApplyPFH", -1];
            if (_pfh isEqualType 0 && {_pfh >= 0}) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
            uiNamespace setVariable ["ACME_CS_ApplyPFH", -1];
            uiNamespace setVariable ["ACME_CS_ApplyGestureUntil", 0];

            if (isNull _m || {!local _m} || {!alive _m}) exitWith {};
            private _state = _m getVariable ["ACME_treatmentPoseState", []];
            if ((_state param [0, -2]) != _epoch || {(_state param [1, ""]) != "chestSeal"}) exitWith {};

            // End this one placement episode. Ambulatory patients do not replay the workspace medicUp motion
            // after each seal: return naturally to crouch and leave the panel open. Downed patients retain the
            // persistent hands-on-chest workspace.
            private _restoreWorkspace = !([_p] call ACME_fnc_patientUpright);
            [_m, "chestSeal", _epoch, _restoreWorkspace] call ACME_fnc_treatmentPoseStop;

            private _display = uiNamespace getVariable ["ACME_CS_DLG", displayNull];
            if (isNull _display
                || {!((uiNamespace getVariable ["ACME_CS_Medic", objNull]) isEqualTo _m)}
                || {!((uiNamespace getVariable ["ACME_CS_Patient", objNull]) isEqualTo _p)}) exitWith {};

            if (_restoreWorkspace) then {
                private _holdEpoch = [_m, _p] call ACME_fnc_chestSealProviderHoldStart;
                _m setVariable ["ACME_CS_providerHoldEpoch", _holdEpoch, false];
                uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch", _holdEpoch];
            } else {
                _m setVariable ["ACME_CS_providerHoldEpoch", -1, false];
                uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch", -1];
            };
        }, [_medic, _patient, _placeEpoch, _serial], _duration] call CBA_fnc_waitAndExecute;
    } else {
        uiNamespace setVariable ["ACME_CS_ApplyGestureUntil", 0];
    };
};

[] call ACME_fnc_chestSealRefreshSlot;
[] call ACME_fnc_chestSealRender;
[] call ACME_fnc_chestSealPrompt;
