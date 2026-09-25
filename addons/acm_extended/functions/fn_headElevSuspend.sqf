// Temporarily lay an elevated casualty flat for a treatment while preserving the logical Semi-Fowler placement.
// B122 rule: a carrier that is serving as the Semi-Fowler support NEVER returns to the patient's chest during a
// temporary suspension. It is parked beyond the head until the maneuver ends, then the same carrier is re-seated
// behind the upper back when elevation resumes. Only actually lowering/canceling Semi-Fowler restores that support
// carrier as worn gear. Backpack-supported chest-access vest removal is handled independently by chestAccess leases.
params [
    ["_patient", objNull, [objNull]],
    ["_keepVestOut", false, [false]],
    ["_frontNormalized", false, [false]]
];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    [_patient, "headElevSuspend", [_patient, _keepVestOut, _frontNormalized]] call ACME_fnc_ownerDispatch;
};
if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease;};
// Manual Semi-Fowler uses a provider-owned support hold when no backpack/carrier can prop the casualty.
// A temporary chest/airway maneuver must release that provider hold but preserve the logical Semi-Fowler episode,
// then run the same authored lay-flat suspension as every other supported patient. Fully cancelling elevation here
// made auscultation race the still-running Lower Head animation and prevented the posture from resuming afterward.
if !((_patient getVariable ["ACME_headElev_hold", []]) isEqualTo []) then {
    [_patient] call ACME_fnc_headElevHoldClear;
};
if !(_patient getVariable ["ACME_headElevated", false]) exitWith {};

// Even temporary lowering starts from anterior-up. An already-correct Semi-Fowler patient is untouched; any stale
// posterior orientation is normalized first so ACME_HeadElevPatientRelease is never played from the stomach.
private _actualBeforeSuspend = [_patient, _patient getVariable ["ACME_CS_facing","front"]]
    call ACME_fnc_chestSealActualSide;
private _needFrontFirst = !_frontNormalized && {_actualBeforeSuspend != "front"};

if (_needFrontFirst) exitWith {
    private _delay = 0.08;

    if ([_patient] call ACME_fnc_chestSealCanPhysicalRoll) then {
        [_patient,"front",false,objNull,true] call ACME_fnc_chestSealRoll;
        private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime",1.85];
        if !(_rollTime isEqualType 0 && {finite _rollTime}) then {_rollTime = 1.85;};
        _delay = (_rollTime max 0.1) + 0.08;
    } else {
        private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"];
        _patient setVariable ["ACME_CS_facing","front",true];
        ["ace_common_switchMove",[_patient,_faceUp]] call CBA_fnc_globalEvent;
    };

    [{
        params ["_p","_keep"];
        if (!isNull _p && {local _p} && {alive _p}) then {
            _p setVariable ["ACME_CS_facing","front",true];
            [_p,_keep,true] call ACME_fnc_headElevSuspend;
        };
    }, [_patient,_keepVestOut], _delay] call CBA_fnc_waitAndExecute;
};

_patient setVariable ["ACME_CS_facing","front",true];

private _parkSupport = {
    params ["_p"];
    private _prop = _p getVariable ["ACME_headElev_propObj", objNull];
    if (isNull _prop) exitWith {};

    private _park = _prop getVariable ["ACME_chestFixedPark", []];
    if !(_park isEqualType [] && {count _park == 3}) then {
        private _pel = _p modelToWorldVisual (_p selectionPosition "pelvis");
        private _hed = _p modelToWorldVisual (_p selectionPosition "head");
        private _dx = (_hed select 0) - (_pel select 0);
        private _dy = (_hed select 1) - (_pel select 1);
        private _mag = sqrt ((_dx * _dx) + (_dy * _dy));
        if (_mag < 0.05) then {
            private _dir = getDir _p;
            _dx = sin _dir;
            _dy = cos _dir;
            _mag = 1;
        };
        private _axis = [_dx / _mag, _dy / _mag, 0];
        private _gap = missionNamespace getVariable ["ACME_headElev_propGroundGap", 0.45];
        private _px = (_hed select 0) + ((_axis select 0) * _gap);
        private _py = (_hed select 1) + ((_axis select 1) * _gap);
        _park = [[_px, _py, 0.02], _axis, surfaceNormal [_px, _py]];
        _prop setVariable ["ACME_chestFixedPark", +_park, false];
    };

    _park params ["_pos","_axis","_up"];
    detach _prop;
    _prop disableCollisionWith _p;
    _p disableCollisionWith _prop;
    [_prop, _pos, _axis, _up, missionNamespace getVariable ["ACME_headElev_propEaseTime", 0.24]]
        call ACME_fnc_propEaseTo;
};

// A second action can join an already-flat casualty. Never replay the release; just keep every removed carrier
// parked outside the chest workspace.
if (_patient getVariable ["ACME_headElev_Suspended", false]) exitWith {
    [_patient] call _parkSupport;
    [_patient] call ACME_fnc_chestAccessVestPark;
};

_patient setVariable ["ACME_headElev_Suspended", true, true];
_patient setVariable ["ACME_headElev_visualActive", false, true];
// Legacy/public flag retained for older readers. B122 no longer uses it to decide whether the support vest is
// re-worn during a suspension: support gear stays out for every temporary flat maneuver.
if (_keepVestOut) then {_patient setVariable ["ACME_headElev_suspendKeepVestOut", true, true];};

private _lowerTime = missionNamespace getVariable ["ACME_headElev_lowerAnimTime", 1.4];
if (!(_lowerTime isEqualType 0) || {_lowerTime < 0.2}) then {_lowerTime = 1.4;};
_patient setVariable ["ACME_headElev_suspendReadyAt", CBA_missionTime + _lowerTime, false];

private _suspendVest = [];
if (_patient getVariable ["ACME_headElev_vestRemoved", false]) then {
    _suspendVest = +(_patient getVariable ["ACME_headElev_vestLoadout", []]);
};
_patient setVariable ["ACME_headElev_suspendVestLoadout", _suspendVest, false];

private _patientAnimToken = "";
private _animLock = _patient getVariable ["ACME_patientAnimLock", []];
private _lockSource = _animLock param [1, ""];
private _lockPriority = _animLock param [3, 0];
private _lockUntil = _animLock param [4, -1];
private _interventionOwnsPatient = (_lockUntil isEqualType 0) && {_lockUntil > serverTime}
    && {_lockPriority >= 2}
    && {!(_lockSource in ["head-elev-lower","head-elev-flat"])};

if (isNull objectParent _patient && {!_interventionOwnsPatient}) then {
    [_patient, false] call ACME_fnc_headElevCollision;
    // Semi-Fowler yields to any already-owned intervention animation. Priority 1 lets chest/airway/treatment
    // patient choreography win instead of a late suspension request canceling the intervention.
    _patientAnimToken = [_patient, "ACME_HeadElevPatientRelease", 2, "head-elev-lower", objNull, _lowerTime + 0.3, 1] call ACME_fnc_patientAnimRequest;
    if (_patientAnimToken != "") then {
        [_patient, _lowerTime] call ACME_fnc_headElevPinPose;
    };
};
private _poseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
// Chest-seal preparation must observe this callback's actual completion, not
// just the nominal lower deadline. A new suspension cannot inherit an old
// callback when the supported placement itself has kept the same pose token.
private _suspendSerial = 1 + (_patient getVariable ["ACME_headElev_suspendSerial", 0]);
_patient setVariable ["ACME_headElev_suspendSerial", _suspendSerial, false];
private _suspendToken = format ["%1:%2", _poseToken, _suspendSerial];
_patient setVariable ["ACME_headElev_suspendPending", _suspendToken, false];
[{
    params ["_patient", "_poseToken", "_patientAnimToken", "_parkSupport", "_suspendToken"];
    if (isNull _patient) exitWith {};
    if ((_patient getVariable ["ACME_headElev_suspendPending", ""]) != _suspendToken) exitWith {};
    if (!local _patient || {!alive _patient}
        || {(_patient getVariable ["ACME_headElev_poseToken", ""]) != _poseToken}
        || {!(_patient getVariable ["ACME_headElev_Suspended", false])}) exitWith {
        _patient setVariable ["ACME_headElev_suspendPending", "", false];
    };
    // A resumed/replaced placement owns its collision recovery, not this retired suspension.
    [_patient, true] call ACME_fnc_headElevCollision;

    // This is the central B122 behavior: no temporary treatment re-vests the support carrier while the logical
    // elevated-head state still exists. It stays beyond the head until resume or a true Lower Head action.
    [_patient] call _parkSupport;
    [_patient] call ACME_fnc_chestAccessVestPark;

    private _rest = [_patient] call ACME_fnc_headElevRestAnim;
    if (isNull objectParent _patient && {_rest != ""} && {_patientAnimToken != ""}) then {
        [_patient, _rest, 2, "head-elev-flat", objNull, 0.8, 1, _patientAnimToken] call ACME_fnc_patientAnimRequest;
    };
    _patient setVariable ["ACME_headElev_suspendPending", "", false];
}, [_patient, _poseToken, _patientAnimToken, _parkSupport, _suspendToken], _lowerTime] call CBA_fnc_waitAndExecute;
