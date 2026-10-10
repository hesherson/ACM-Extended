/* Recover the machine's actual continuous controller, then reconcile local-player preflight/claims. */
private _repairs = 0;
private _active = missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false];
private _controller = missionNamespace getVariable ["ACM_core_ContinuousAction_Controller", []];
private _epoch = missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1];
private _recorded = _controller isEqualType [] && {count _controller == 6}
    && {(_controller param [2, -2]) == _epoch}
    && {(_controller select 3) isEqualType {}}
    && {(_controller select 4) isEqualType []};
private _provider = if (_recorded) then {_controller select 0} else {
    if (hasInterface && {!isNil "ACE_player"}) then {ACE_player} else {objNull}
};
// B253: B252 continuous workers carry their provider-locality generation as the
// final worker argument. A callback may stop ticking during an away/back transfer;
// recover its reservation even if the old heartbeat is not yet six seconds old.
// Legacy 17-field controllers have no generation and keep the existing safeguards.
private _localityGeneration = if (_recorded && {count (_controller select 4) >= 18}) then {
    (_controller select 4) param [17, -1, [0]]
} else {-1};

if (_active) then {
    private _session = if (isNull _provider) then {[]} else {_provider getVariable ["ACM_core_ContinuousAction_Session", []]};
    private _lastSeen = if (isNull _provider) then {-1} else {_provider getVariable ["ACM_core_ContinuousAction_LastSeen", -1]};
    private _patient = if (_session isEqualType [] && {count _session == 2}) then {_session select 0} else {objNull};
    private _invalid = isNull _provider
        || {!local _provider}
        || {!alive _provider}
        || {_provider getVariable ["ACE_isUnconscious", false]}
        || {!(_session isEqualType [] && {count _session == 2})}
        || {(_session param [1, -2]) != _epoch}
        || {isNull _patient}
        || {!(_lastSeen isEqualType 0 && {finite _lastSeen})}
        || {CBA_missionTime - _lastSeen > 6}
        || {_localityGeneration >= 0
            && {(_provider getVariable ["ACME_providerLocalityEpoch", 0]) != _localityGeneration}};

    // A previous controller's recovery deadline must not carry into a new actor/generation.
    private _identity = [_provider, _epoch];
    if ((missionNamespace getVariable ["ACME_providerInvalidContinuousOwner", []]) isNotEqualTo _identity) then {
        missionNamespace setVariable ["ACME_providerInvalidContinuousOwner", _identity];
        missionNamespace setVariable ["ACME_providerInvalidContinuousAt", -1];
    };
    private _invalidAt = missionNamespace getVariable ["ACME_providerInvalidContinuousAt", -1];
    if (_invalid) then {
        if !(_invalidAt isEqualType 0 && {finite _invalidAt}) then {_invalidAt = -1;};
        if (_invalidAt < 0) then {
            missionNamespace setVariable ["ACME_providerInvalidContinuousAt", diag_tickTime];
        } else {
            if (diag_tickTime - _invalidAt >= 1) then {
                if (_recorded) then {
                    // Run the original worker's normal cancellation branch. It releases the exact clinical
                    // reservation, UI/input hooks and inventory before a successor can take the global gate.
                    [_provider, [["active", false]], false] call ACM_core_fnc_setContinuousActionState;
                    [_controller select 4, _controller select 5] call (_controller select 3);
                } else {
                    // Compatibility for an interrupted legacy controller with no recorded cancellation worker.
                    // All current native and stethoscope controllers publish the record before OnStart.
                    private _bvmLocal = missionNamespace getVariable ["ACM_breathing_BVM_LocalSession", []];
                    private _bvmCleaned = false;
                    if (!isNil "ACM_breathing_fnc_bvmCleanupLocal"
                        && {_bvmLocal isEqualType []} && {count _bvmLocal == 3}
                        && {(_bvmLocal select 0) isEqualTo _provider}
                        && {(_bvmLocal select 2) == _epoch}) then {
                        _bvmCleaned = _bvmLocal call ACM_breathing_fnc_bvmCleanupLocal;
                    };
                    if (!_bvmCleaned) then {
                        private _pfh = missionNamespace getVariable ["ACM_core_ContinuousAction_PFH", -1];
                        if (_pfh isEqualType 0 && {_pfh >= 0}) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
                        {
                            private _id = missionNamespace getVariable [_x, -1];
                            if (!(_id isEqualTo -1) && {!(_id isEqualTo "")}) then {
                                [_id, "keydown"] call CBA_fnc_removeKeyHandler;
                            };
                            missionNamespace setVariable [_x, -1];
                        } forEach [
                            "ACM_core_ContinuousAction_Cancel_EscapeID",
                            "ACM_core_ContinuousAction_OpenMedicalMenu_ID"
                        ];
                        [_provider, [["active", false], ["pfh", -1], ["shouldReopen", false],
                            ["isDialog", false], ["session", []]], true] call ACM_core_fnc_setContinuousActionState;
                        if (hasInterface) then {
                            "ACM_UseBVM" cutText ["", "PLAIN", 0, false];
                            "ACM_HeadTilt" cutText ["", "PLAIN", 0, false];
                            "ACM_ContinuousActionText" cutText ["", "PLAIN", 0, false];
                            [] call ace_interaction_fnc_hideMouseHint;
                        };
                    };
                    [_provider, [["controller", []]], false] call ACM_core_fnc_setContinuousActionState;
                };
                missionNamespace setVariable ["ACME_providerInvalidContinuousAt", -1];
                _repairs = _repairs + 1;
                diag_log "[ACME STATE RECONCILE] Cleared stale provider ContinuousAction controller.";
            };
        };
    } else {
        missionNamespace setVariable ["ACME_providerInvalidContinuousAt", -1];
    };
} else {
    missionNamespace setVariable ["ACME_providerInvalidContinuousAt", -1];
    // BVM's explicit cleanup may already have retired the PFH and clinical lease.
    // Drop its remaining reference without invoking that cancellation a second time.
    if (_recorded && {(missionNamespace getVariable ["ACM_core_ContinuousAction_PFH", -1]) < 0}) then {
        [_provider, [["controller", []]], false] call ACM_core_fnc_setContinuousActionState;
    };
};

// Input preflight and Direct Pressure pending requests below belong to the controlled interface actor only.
if (!hasInterface || {isNil "ACE_player"} || {isNull ACE_player}) exitWith {_repairs};
private _medic = ACE_player;
if (!local _medic) exitWith {_repairs};

if (_medic getVariable ["ACME_treatmentPreflightActive", false]) then {
    private _token = _medic getVariable ["ACME_treatmentPreflightToken", ""];
    private _startedAt = _medic getVariable ["ACME_treatmentPreflightStartedAt", -1];
    private _stale = (_token == "")
        || {!(_startedAt isEqualType 0 && {finite _startedAt})}
        || {_startedAt < 0}
        || {(CBA_missionTime - _startedAt) > 4};

    if (_stale) then {
        _medic setVariable ["ACME_treatmentPreflightActive", false, false];
        _medic setVariable ["ACME_treatmentPreflightToken", "", false];
        _medic setVariable ["ACME_treatmentPreflightBypass", [], false];
        _medic setVariable ["ACME_treatmentPreflightStartedAt", -1, false];
        _repairs = _repairs + 1;
        diag_log format ["[ACME STATE RECONCILE] Cleared stale treatment preflight token=%1 age=%2.",
            _token, if (_startedAt isEqualType 0) then {CBA_missionTime - _startedAt} else {-1}];
    };
};

// A lost owner-command ACK must not leave the Direct Pressure action permanently disabled for this medic.
private _dpPending = _medic getVariable ["ACME_DP_ClaimPending", []];
if (_dpPending isEqualType [] && {count _dpPending >= 4}) then {
    private _requestedAt = _medic getVariable ["ACME_DP_ClaimRequestedAt", -1];
    if (!(_requestedAt isEqualType 0 && {finite _requestedAt}) || {_requestedAt < 0} || {(diag_tickTime - _requestedAt) > 4}) then {
        _dpPending params ["_patient", "_part", "_token", "_epoch"];
        if (!isNull _patient && {_token != ""}) then {
            [_patient, "directPressureClaim", ["release", [_medic, _part, _token, _epoch, clientOwner]]] call ACME_fnc_ownerDispatch;
        };
        _medic setVariable ["ACME_DP_ClaimPending", [], false];
        _medic setVariable ["ACME_DP_ClaimRequestedAt", -1, false];
        _repairs = _repairs + 1;
        // This runs only when retiring the pending slot, never every reconciliation tick.
        diag_log format ["[ACME STATE RECONCILE] Cleared stale Direct Pressure claim request. token=%1 epoch=%2 patient=%3 age=%4",
            _token, _epoch, netId _patient, if (_requestedAt isEqualType 0) then {diag_tickTime - _requestedAt} else {-1}];
    };
};

if !(_medic getVariable ["ACME_DP_Active", false]) then {
    if ((_medic getVariable ["ACME_DP_TreatmentBusy", false])
        || {_medic getVariable ["ACME_DP_Paused", false]}
        || {(_medic getVariable ["ACME_DP_PauseTreatmentClass", ""]) != ""}) then {
        _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
        _medic setVariable ["ACME_DP_Paused", false, false];
        _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
        _repairs = _repairs + 1;
    };
};

_repairs
