// Owner-local visible seizure driver. Physiology, unconsciousness and recovery remain in the shared state machine.
// BI Spasm3-6 use isolated ACME aliases at 1.05 times each clip's native cycles/second.
params ["_patient", ["_on",true]];
if (isNull _patient || {!local _patient}) exitWith {};

// Seizure PHYSIOLOGY continues in vehicles, but body-spasm animation must not. If the casualty enters a seat during
// an active episode, tear down only the visual driver. The active seizure state remains, and the next owner tick
// starts a fresh visual session automatically after they leave the vehicle.
if (_on && {!isNull objectParent _patient}) exitWith {
    if (_patient getVariable ["ACME_seizure_motionActive",false]) then {
        [_patient,false] call ACME_fnc_seizureMotion;
    } else {
        if !(_patient getVariable ["ACME_seizure_vehicleVisualSuppressed",false]) then {
            _patient setVariable ["ACME_seizure_vehicleVisualSuppressed",true,false];
            ["ACME_seizureGestureSync", [_patient, [], "", false]] call CBA_fnc_globalEvent;
        };
    };
    true
};
if (_on && {_patient getVariable ["ACME_seizure_vehicleVisualSuppressed",false]}) then {
    _patient setVariable ["ACME_seizure_vehicleVisualSuppressed",false,false];
};

private _legacyPFH = _patient getVariable ["ACME_seizure_motionPFH",-1];
if (_legacyPFH isEqualType 0 && {_legacyPFH >= 0}) then {
    [_legacyPFH] call CBA_fnc_removePerFrameHandler;
    _patient setVariable ["ACME_seizure_motionPFH",-1];
};

private _enabled = _on && {alive _patient}
    && {!(_patient getVariable ["ACME_roc_paralyzed", false])}
    && {missionNamespace getVariable ["ACME_seizure_animEnabled",true]}
    && {(missionNamespace getVariable ["ACME_seizure_motionEnabled",1]) != 0};
if (!_enabled) exitWith {
    private _endingSession = +(_patient getVariable ["ACME_seizure_motionSession",[]]);
    _patient setVariable ["ACME_seizure_motionActive",false];
    // Invalidate delayed onset, ragdoll handoff, retry and GestureDone callbacks together.
    _patient setVariable ["ACME_seizure_motionSession",[]];
    _patient setVariable ["ACME_seizure_motionRetryPending",false];
    _patient setVariable ["ACME_seizure_motionAdvancePending",false];
    private _eh = _patient getVariable ["ACME_seizure_motionGestureEH",-1];
    if (_eh isEqualType 0 && {_eh >= 0}) then {_patient removeEventHandler ["GestureDone",_eh];};
    _patient setVariable ["ACME_seizure_motionGestureEH",-1];
    if (((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") == 0) then {
        // GestureNo is a head shake. GestureEmpty actually clears the masked animation layer.
        _patient switchGesture "GestureEmpty";
    };
    ["ACME_seizureGestureSync", [_patient, _endingSession, "", false]] call CBA_fnc_globalEvent;
    _patient setVariable ["ACME_seizure_motionCurrentGesture",""];
};

private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _session = _patient getVariable ["ACME_seizure_motionSession",[]];
if (_patient getVariable ["ACME_seizure_motionActive",false]
    && {(_session param [0,-1]) != _epoch}) then {
    [_patient,false] call ACME_fnc_seizureMotion;
};
// Idempotent recovery also covers an onset that was interrupted before any gesture could start.
if (_patient getVariable ["ACME_seizure_motionActive",false]) exitWith {
    if (CBA_missionTime >= (_patient getVariable ["ACME_seizure_motionReadyAt",0])
        && {!(_patient getVariable ["ACME_seizure_motionAdvancePending",false])}
        && {!(_patient getVariable ["ACME_seizure_motionRetryPending",false])}
        && {((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") != 0}) then {
        [_patient,_session] call ACME_fnc_seizureGestureAdvance;
    };
};

private _serial = (missionNamespace getVariable ["ACME_seizure_motionSerial",0]) + 1;
missionNamespace setVariable ["ACME_seizure_motionSerial",_serial];
_session = [_epoch,clientOwner,_serial];
_patient setVariable ["ACME_seizure_motionSession",_session];
_patient setVariable ["ACME_seizure_motionActive",true];
_patient setVariable ["ACME_seizure_motionRetryPending",false];
_patient setVariable ["ACME_seizure_motionAdvancePending",false];
_patient setVariable ["ACME_seizure_motionCurrentGesture",""];

private _oldEH = _patient getVariable ["ACME_seizure_motionGestureEH",-1];
if (_oldEH isEqualType 0 && {_oldEH >= 0}) then {_patient removeEventHandler ["GestureDone",_oldEH];};
private _eh = _patient addEventHandler ["GestureDone",{
    params ["_unit","_gesture"];
    if (!local _unit || {!(_unit getVariable ["ACME_seizure_motionActive",false])}) exitWith {};
    private _current = _unit getVariable ["ACME_seizure_motionCurrentGesture",""];
    if (_current == "" || {(toLowerANSI _gesture) != (toLowerANSI _current)}) exitWith {};
    if (_unit getVariable ["ACME_seizure_motionAdvancePending",false]) exitWith {};
    _unit setVariable ["ACME_seizure_motionAdvancePending",true];
    [{
        params ["_p","_session"];
        if (isNull _p || {!local _p}
            || {!((_p getVariable ["ACME_seizure_motionSession",[]]) isEqualTo _session)}
            || {(_session param [0,-1]) != ([_p] call ACME_fnc_clinicalEpoch)}) exitWith {};
        _p setVariable ["ACME_seizure_motionAdvancePending",false];
        [_p,_session] call ACME_fnc_seizureGestureAdvance;
    },[_unit,_unit getVariable ["ACME_seizure_motionSession",[]]]] call CBA_fnc_execNextFrame;
}];
_patient setVariable ["ACME_seizure_motionGestureEH",_eh];

// Give the onset collapse time to settle. An already-down casualty retains its base pose throughout.
private _settle = (missionNamespace getVariable ["ACME_seizure_settleDur",1.5]) max 0;
_patient setVariable ["ACME_seizure_motionReadyAt",CBA_missionTime + _settle];
[{
    params ["_p","_session"];
    if (isNull _p || {!local _p}
        || {!((_p getVariable ["ACME_seizure_motionSession",[]]) isEqualTo _session)}) exitWith {};
    [_p,_session] call ACME_fnc_seizureGestureAdvance;
},[_patient,_session],_settle] call CBA_fnc_waitAndExecute;
true
