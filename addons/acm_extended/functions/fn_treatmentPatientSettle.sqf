// Last-chance supine settle after an ordinary treatment ends.
// This is intentionally narrow: it runs only on a downed casualty whose animated torso is actually side-on, and
// only when no CPR/BVM/recovery/head-elevation/special-pose owner is active. It never creates ACM's logical lying
// state and never touches a conscious casualty who is standing/crouching normally.
params [["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]], ["_classname", "", [""]]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient, "treatmentPatientSettle", [_patient, _medic, _classname]] call ACME_fnc_ownerDispatch;};
if (!alive _patient || {!isNull objectParent _patient}) exitWith {};
private _independentlyConscious = !(_patient getVariable ["ACE_isUnconscious", false])
    && {!(_patient getVariable ["ace_medical_unconscious", false])}
    && {!(_patient getVariable ["ACME_obtunded", false])}
    && {(stance _patient) in ["STAND", "CROUCH", "PRONE"]};
if (_independentlyConscious) exitWith {};
if (_patient getVariable ["ACME_headElevated", false] || {_patient getVariable ["ACME_headElev_Suspended", false]}) exitWith {};
if (_patient getVariable ["ACM_airway_RecoveryPosition_State", false]) exitWith {};
if ((_patient getVariable ["ACME_lido_seizureState", ""]) == "active") exitWith {};
if ((_patient getVariable ["ACME_CS_rollToken", ""]) != "") exitWith {};
if ([_patient] call ACM_core_fnc_cprActive) exitWith {};
if (alive (_patient getVariable ["ACM_breathing_BVM_Medic", objNull])) exitWith {};

private _lock = _patient getVariable ["ACME_patientAnimLock", []];
if ((count _lock) >= 5 && {(_lock param [4, -1]) > serverTime}) exitWith {};

private _lyingRaw = _patient getVariable ["ACM_core_Lying_State", false];
private _lying = if (_lyingRaw isEqualType true) then {_lyingRaw} else {_lyingRaw > 0};
private _downed = (_patient getVariable ["ACE_isUnconscious", false])
    || {_patient getVariable ["ace_medical_unconscious", false]}
    || {_patient getVariable ["ACME_obtunded", false]}
    || {_lying};
if (!_downed) exitWith {};

private _as = toLowerANSI animationState _patient;
if (_as in ["acm_lyingstate", "acm_recoveryposition", "acm_cpr", "acm_cpr_stop", "acm_genericcontinuous", "acm_pronecontinuous"]) exitWith {};

// Animated shoulder/head/pelvis geometry gives us a cheap side-on detector. Supine and prone both have a strong
// vertical chest-normal component; the accidental ragdoll-on-the-side state is near zero.
private _pel = _patient modelToWorldVisual (_patient selectionPosition "pelvis");
private _hed = _patient modelToWorldVisual (_patient selectionPosition "head");
private _ls = _patient modelToWorldVisual (_patient selectionPosition "leftshoulder");
private _rs = _patient modelToWorldVisual (_patient selectionPosition "rightshoulder");
private _normal = (_hed vectorDiff _pel) vectorCrossProduct (_rs vectorDiff _ls);
private _mag = vectorMagnitude _normal;
if (_mag <= 0.0001) exitWith {};
private _sideRatio = abs ((_normal param [2, 0]) / _mag);
if (_sideRatio > 0.18) exitWith {};

private _tok = [_patient, "AinjPpneMstpSnonWrflDnon_rolltoback", 1, "fallback-supine", _medic, 2.25, 0] call ACME_fnc_patientAnimRequest;
if (_tok == "") exitWith {};

// If the engine still leaves the downed body side-on after the authored roll, finish on the normal face-up resting
// state. This is a repair only; it is skipped if another special animation owner has replaced the lease.
[{
    params ["_p", "_tok", "_med"];
    if (isNull _p || {!local _p} || {!alive _p} || {!isNull objectParent _p}) exitWith {};
    private _lock = _p getVariable ["ACME_patientAnimLock", []];
    if ((_lock param [0, ""]) != _tok) exitWith {};
    private _pel = _p modelToWorldVisual (_p selectionPosition "pelvis");
    private _hed = _p modelToWorldVisual (_p selectionPosition "head");
    private _ls = _p modelToWorldVisual (_p selectionPosition "leftshoulder");
    private _rs = _p modelToWorldVisual (_p selectionPosition "rightshoulder");
    private _n = (_hed vectorDiff _pel) vectorCrossProduct (_rs vectorDiff _ls);
    private _m = vectorMagnitude _n;
    if (_m > 0.0001 && {abs ((_n param [2,0]) / _m) <= 0.18}) then {
        private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"];
        [_p, _faceUp, 2, "fallback-supine", _med, 0.6, 0, _tok] call ACME_fnc_patientAnimRequest;
    };
}, [_patient, _tok, _medic], 1.9] call CBA_fnc_waitAndExecute;
