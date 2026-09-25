/* Death cleanup for an elevated casualty.
 * If the casualty dies while elevated, play the exact same patient release/lay-flat animation used by the normal
 * Lower Head action, then tear down elevation state. Provider animation is never started here. */
private _patient = if (_this isEqualType []) then {_this param [0, objNull, [objNull]]} else {_this};
if (!(_patient isEqualType objNull) || {isNull _patient}) exitWith {};
if (!local _patient) exitWith {[_patient, "headElevDeath", [_patient]] call ACME_fnc_ownerDispatch;};
if (canSuspend) exitWith {isNil {[_patient] call ACME_fnc_headElevDeathRelease;};};

private _wasElevated = (_patient getVariable ["ACME_headElevated", false])
    && {_patient getVariable ["ACME_headElev_visualActive", true]};
private _inVehicle = !isNull objectParent _patient;
private _releaseTime = missionNamespace getVariable ["ACME_headElev_lowerAnimTime", 1.4];

[_patient] call ACME_fnc_headElevHoldClear;
_patient setVariable ["ACME_headElev_treatments", createHashMap, true];
_patient setVariable ["ACME_headElevated", false, true];
_patient setVariable ["ACME_headElev_pendingLift", [], true];
_patient setVariable ["ACME_headElev_manualUnsupported", false, true];
_patient setVariable ["ACME_headElev_Suspended", false, true];
_patient setVariable ["ACME_headElev_ResumePending", false, true];
_patient setVariable ["ACME_headElev_TransportPending", nil, true];
_patient setVariable ["ACME_headElev_poseToken", "", true];
_patient setVariable ["ACME_headElev_visualActive", false, true];
_patient setVariable ["ACME_headElev_suspendVestLoadout", [], false];
_patient setVariable ["ACME_headElev_suspendReadyAt", -1, false];

private _pfh = _patient getVariable ["ACME_headElev_pfh", -1];
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
_patient setVariable ["ACME_headElev_pfh", -1];
private _eh = _patient getVariable ["ACME_headElev_killEH", -1];
if (_eh >= 0) then {_patient removeEventHandler ["Killed", _eh];};
_patient setVariable ["ACME_headElev_killEH", -1];

private _helper = _patient getVariable ["ACME_headElev_helper", objNull];
[_patient, _helper] call ACME_fnc_releasePatient;
if (!isNull _helper) then {deleteVehicle _helper;};
_patient setVariable ["ACME_headElev_helper", objNull, true];

private _prop = _patient getVariable ["ACME_headElev_propObj", objNull];
if (!isNull _prop) then {detach _prop; deleteVehicle _prop;};
_patient setVariable ["ACME_headElev_propObj", objNull, true];

// Match the living lay-flat path exactly: collision/mass is relaxed during the root-motion release. Corpse
// animations are allowed by ace_common_fnc_doAnimation; ACME_fnc_doAnim only blocks units inside vehicles.
if (_wasElevated && {!_inVehicle}) then {
    [_patient, false] call ACME_fnc_headElevCollision;
    [_patient, "ACME_HeadElevPatientRelease", 2] call ACME_fnc_doAnim;
    [{
        params ["_p"];
        if (isNull _p || {!local _p}) exitWith {};
        [_p, true] call ACME_fnc_headElevCollision;
    }, [_patient], _releaseTime] call CBA_fnc_waitAndExecute;
} else {
    [_patient, true] call ACME_fnc_headElevCollision;
};

[_patient] call ACME_fnc_headElevVestRestore;
[_patient, true] call ACME_fnc_chestAccessVestRestore;
_patient setVariable ["ACME_headElev_preserveFaceDown", nil, true];
_patient setVariable ["ACME_headElev_baseAnim", nil, true];
