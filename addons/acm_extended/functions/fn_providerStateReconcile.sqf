/* Provider-local safety net for stale controllers that can make later actions appear unavailable. */
if (!hasInterface) exitWith {0};
private _medic = call ACME_fnc_controlledProvider;
if (isNull _medic || {!local _medic}) exitWith {0};

private _repairs = 0;
private _active = missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false];

if (_active) then {
    private _session = _medic getVariable ["ACM_core_ContinuousAction_Session", []];
    private _epoch = missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", -1];
    private _lastSeen = _medic getVariable ["ACM_core_ContinuousAction_LastSeen", -1];
    private _patient = if (_session isEqualType [] && {count _session == 2}) then {_session select 0} else {objNull};
    private _invalid = !alive _medic
        || {_medic getVariable ["ACE_isUnconscious", false]}
        || {!(_session isEqualType [] && {count _session == 2})}
        || {(_session param [1, -2]) != _epoch}
        || {isNull _patient}
        || {!(_lastSeen isEqualType 0 && {finite _lastSeen})}
        || {CBA_missionTime - _lastSeen > 6};

    private _invalidAt = missionNamespace getVariable ["ACME_providerInvalidContinuousAt", -1];
    if (_invalid) then {
        if !(_invalidAt isEqualType 0 && {finite _invalidAt}) then {_invalidAt = -1;};
        if (_invalidAt < 0) then {
            missionNamespace setVariable ["ACME_providerInvalidContinuousAt", diag_tickTime];
        } else {
            if (diag_tickTime - _invalidAt >= 1) then {
                private _bvmLocal = missionNamespace getVariable ["ACM_breathing_BVM_LocalSession", []];
                private _bvmCleaned = false;
                if (!isNil "ACM_breathing_fnc_bvmCleanupLocal"
                    && {_bvmLocal isEqualType []} && {count _bvmLocal == 3}
                    && {(_bvmLocal select 0) isEqualTo _medic}
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

                    missionNamespace setVariable ["ACM_core_ContinuousAction_Active", false];
                    missionNamespace setVariable ["ACM_core_ContinuousAction_PFH", -1];
                    missionNamespace setVariable ["ACM_core_ContinuousAction_ShouldReopen", false];
                    missionNamespace setVariable ["ACM_core_ContinuousAction_IsDialog", false];
                    _medic setVariable ["ACM_core_ContinuousAction_Session", [], true];

                    "ACM_UseBVM" cutText ["", "PLAIN", 0, false];
                    "ACM_HeadTilt" cutText ["", "PLAIN", 0, false];
                    "ACM_ContinuousActionText" cutText ["", "PLAIN", 0, false];
                    [] call ace_interaction_fnc_hideMouseHint;
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
};

if (_medic getVariable ["ACME_treatmentPreflightActive", false]) then {
    private _seen = _medic getVariable ["ACME_reconcilePreflightSeen", -1];
    if !(_seen isEqualType 0 && {finite _seen}) then {_seen = -1;};
    if (_seen < 0) then {
        _medic setVariable ["ACME_reconcilePreflightSeen", diag_tickTime, false];
    } else {
        if (diag_tickTime - _seen > 4) then {
            _medic setVariable ["ACME_treatmentPreflightActive", false, false];
            _medic setVariable ["ACME_treatmentPreflightToken", "", false];
            _medic setVariable ["ACME_treatmentPreflightBypass", [], false];
            _medic setVariable ["ACME_reconcilePreflightSeen", -1, false];
            _repairs = _repairs + 1;
            diag_log "[ACME STATE RECONCILE] Cleared stale treatment preflight.";
        };
    };
} else {
    _medic setVariable ["ACME_reconcilePreflightSeen", -1, false];
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
