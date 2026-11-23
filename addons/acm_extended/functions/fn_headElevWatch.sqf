/* Bind local handlers from replicated elevation state. No periodic global scan. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {};
if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease;};
if !(_patient getVariable ["ACME_headElevated", false]) exitWith {};
if ((_patient getVariable ["ACME_headElev_killEH", -1]) < 0) then {
    private _eh = _patient addEventHandler ["Killed", {[_this select 0] call ACME_fnc_headElevDeathRelease;}];
    _patient setVariable ["ACME_headElev_killEH", _eh];
};
if ((_patient getVariable ["ACME_headElev_pfh", -1]) >= 0) exitWith {};
private _pfh = [{
    params ["_args", "_handle"];
    _args params ["_patient"];
    if (isNull _patient || {!local _patient}) exitWith {[_handle] call CBA_fnc_removePerFrameHandler;};
    if ((_patient getVariable ["ACME_headElev_pfh", -1]) != _handle) exitWith {[_handle] call CBA_fnc_removePerFrameHandler;};
    if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease;};
    if !(_patient getVariable ["ACME_headElevated", false]) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        _patient setVariable ["ACME_headElev_pfh", -1];
    };
    // B166 has no provider-ready handshake. Patient lift starts immediately on the patient owner.
    private _hold = _patient getVariable ["ACME_headElev_hold", []];
    private _releaseHold = false;
    if !(_hold isEqualTo []) then {
        _hold params ["_medic", "_token", "_started"];
        _releaseHold = isNull _medic || {!isPlayer _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
            || {objectParent _medic != objectParent _patient}
            || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])
                && {vehicle _medic != vehicle _patient}};
        if (CBA_missionTime - _started > 4) then {
            _releaseHold = _releaseHold || {!((_medic getVariable ["ACME_headElev_holding", []]) isEqualTo [_patient, _token])};
        };
    };
    if (_releaseHold) exitWith {[objNull, _patient] call ACME_fnc_headElevateStop;};
    private _suspended = _patient getVariable ["ACME_headElev_Suspended", false];
    // B393: a provider who left, died or went down in the middle of a treatment never ends his lease; it no longer
    // holds the casualty flat (the takeover does the same after an owner change).
    if (_suspended) then {
        private _leases = _patient getVariable ["ACME_headElev_treatments", createHashMap];
        if (_leases isEqualType createHashMap && {count _leases > 0}) then {
            private _gone = (keys _leases) select {
                private _m = (_leases get _x) param [0, objNull];
                isNull _m || {!alive _m} || {_m getVariable ["ACE_isUnconscious", false]}
            };
            if (_gone isNotEqualTo []) then {
                {_leases deleteAt _x;} forEach _gone;
                _patient setVariable ["ACME_headElev_treatments", _leases, true];
                if (count _leases == 0) then {
                    _patient setVariable ["ACME_headElev_ResumePending", true, true];
                    [{_this call ACME_fnc_headElevTryResume;}, [_patient, _patient getVariable ["ACME_headElev_poseToken", ""]], 0.75] call CBA_fnc_waitAndExecute;
                };
            };
        };
    };
    if (!_suspended && {(_patient call ace_common_fnc_isBeingDragged) || {_patient call ace_common_fnc_isBeingCarried}}) then {
        ["ACME_headElev_transportDown", [_patient], _patient] call CBA_fnc_targetEvent;
    };
}, 0.5, [_patient]] call CBA_fnc_addPerFrameHandler;
_patient setVariable ["ACME_headElev_pfh", _pfh];
