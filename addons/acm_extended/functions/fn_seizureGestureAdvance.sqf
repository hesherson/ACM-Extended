// Start a complete BI spasm directly on the gesture layer, independent of the underlying move graph.
// Never substitute a shared absolute speed or change the patient's global animation-speed coefficient.
params ["_patient",["_session",[]],["_afterHandoff",false]];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
if (_session isEqualTo []) then {_session = _patient getVariable ["ACME_seizure_motionSession",[]];};
if (_session isEqualTo []
    || {!((_patient getVariable ["ACME_seizure_motionSession",[]]) isEqualTo _session)}
    || {(_session param [0,-1]) != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!(_patient getVariable ["ACME_seizure_motionActive",false])}
    || {_patient getVariable ["ACME_roc_paralyzed", false]}
    || {! (missionNamespace getVariable ["ACME_seizure_animEnabled",true])}) exitWith {};
if (CBA_missionTime < (_patient getVariable ["ACME_seizure_motionReadyAt",0])) exitWith {};

private _retry = {
    if (_patient getVariable ["ACME_seizure_motionRetryPending",false]) exitWith {};
    _patient setVariable ["ACME_seizure_motionRetryPending",true];
    [{
        params ["_p","_session"];
        if (isNull _p || {!local _p}
            || {!((_p getVariable ["ACME_seizure_motionSession",[]]) isEqualTo _session)}
            || {(_session param [0,-1]) != ([_p] call ACME_fnc_clinicalEpoch)}) exitWith {};
        _p setVariable ["ACME_seizure_motionRetryPending",false];
        [_p,_session] call ACME_fnc_seizureGestureAdvance;
    },[_patient,_session],0.35] call CBA_fnc_waitAndExecute;
};
// Physiology continues while another procedure or movement owns the casualty.
if (!isNull objectParent _patient
    || {_patient call ace_common_fnc_isBeingDragged}
    || {_patient call ace_common_fnc_isBeingCarried}
    || {[_patient] call ACM_core_fnc_cprActive}
    || {CBA_missionTime < (_patient getVariable ["ACME_CS_rollUntil",-1])}) exitWith {call _retry;};

// A settled unconscious ragdoll can stay asleep indefinitely. Merely waiting for isAwake was why
// debug seizures appeared only after CPR/rolling woke the skeleton. End that physical state once,
// preserving the actual up-facing surface; never flatten a head-elevated patient or change heading/position.
if (!isAwake _patient && {!_afterHandoff}) exitWith {
    if (vectorMagnitude (velocity _patient) > 0.6) exitWith {call _retry;};
    private _lock = _patient getVariable ["ACME_patientAnimLock",[]];
    if ((_lock param [4,-1]) > CBA_missionTime) exitWith {call _retry;};
    private _rest = "";
    if (_patient getVariable ["ACME_headElevated",false]
        && {!(_patient getVariable ["ACME_headElev_Suspended",false])}) then {
        _rest = "ACME_HeadElevPatientHold";
    } else {
        private _side = [_patient,"front"] call ACME_fnc_chestSealActualSide;
        _rest = if (_side == "front") then {
            missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"]
        } else {
            missionNamespace getVariable ["ACME_uncon_faceDown","ace_medical_engine_uncon_anim_1"]
        };
    };
    _patient setVariable ["ACME_seizure_motionAdvancePending",true];
    _patient switchMove [_rest,0,1,false];
    [{
        params ["_p","_session"];
        if (isNull _p || {!local _p}
            || {!((_p getVariable ["ACME_seizure_motionSession",[]]) isEqualTo _session)}
            || {(_session param [0,-1]) != ([_p] call ACME_fnc_clinicalEpoch)}) exitWith {};
        _p setVariable ["ACME_seizure_motionAdvancePending",false];
        [_p,_session,true] call ACME_fnc_seizureGestureAdvance;
    },[_patient,_session]] call CBA_fnc_execNextFrame;
};
private _gestures = [
    "ACME_SeizureSpasm3",
    "ACME_SeizureSpasm4",
    "ACME_SeizureSpasm5",
    "ACME_SeizureSpasm6"
];
private _last = _patient getVariable ["ACME_seizure_motionCurrentGesture",""];
private _pool = _gestures - [_last];
if (_pool isEqualTo []) then {_pool = +_gestures;};
private _next = selectRandom _pool;
_patient setVariable ["ACME_seizure_motionAdvancePending",false];
_patient setVariable ["ACME_seizure_motionCurrentGesture",_next];
// playActionNow can be swallowed by ACM_LyingState's isolated action graph.
// switchGesture (Arma 2.18+) starts the configured gesture without replacing the supine base pose.
_patient switchGesture [_next,0,1,false];
true
