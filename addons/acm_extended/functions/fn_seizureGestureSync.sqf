// Network-visible seizure gesture presentation.
// The owner still owns physiology and sequencing. Each gesture transition is replayed on every interface client,
// while the owner machine also executes it so its GestureDone EH advances the authoritative sequence.
params [
    ["_patient", objNull, [objNull]],
    ["_session", [], [[]]],
    ["_gesture", "", [""]],
    ["_active", true, [false]],
    ["_pulse", 0, [0]],
    ["_duration", 0, [0]]
];
if (isNull _patient) exitWith {false};

// Machines that neither render the casualty nor own it have no reason to touch the gesture layer.
if (!hasInterface && {!local _patient}) exitWith {false};

private _observerSession = _patient getVariable ["ACME_seizure_observerSession", []];

if (!_active) exitWith {
    if (_session isEqualTo [] && {alive _patient} && {isNull objectParent _patient}
        && {!(_patient getVariable ["ACME_roc_paralyzed",false])}) exitWith {false};
    if (_session isNotEqualTo []) then {
        private _retired = +(_patient getVariable ["ACME_seizure_observerRetired",[]]);
        _retired pushBackUnique _session;
        if (count _retired > 8) then {_retired deleteAt 0;};
        _patient setVariable ["ACME_seizure_observerRetired",_retired,false];
    };
    if (_session isEqualTo [] || {_observerSession isEqualTo _session}) then {
        if (((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") == 0) then {
            _patient switchGesture "GestureEmpty";
        };
        _patient setVariable ["ACME_seizure_observerSession", [], false];
    };
    true
};

if (_session in (_patient getVariable ["ACME_seizure_observerRetired",[]])) exitWith {false};
if ((_observerSession param [0,-1]) == (_session param [0,-2])
    && {(_observerSession param [1,-1]) == (_session param [1,-2])}
    && {(_observerSession param [2,-1]) > (_session param [2,-2])}) exitWith {false};

// A delayed start may not revive a dead/reset casualty or a now-paralyzed motor layer.
// owner is authoritative on the server. A client-owned casualty's session is authored with clientOwner;
// clients cannot validate remote presentation by comparing that ID with their non-authoritative owner result.
private _sessionOwner = _session param [1, -1];
private _ownerMatches = if (isServer) then {
    _sessionOwner == owner _patient
} else {
    !local _patient || {_sessionOwner == clientOwner}
};
if (!alive _patient
    || {_session isEqualTo []}
    || {(_session param [0,-1]) != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!_ownerMatches}
    || {local _patient && {!(_session isEqualTo (_patient getVariable ["ACME_seizure_motionSession", []]))}}) exitWith {false};
if (_patient getVariable ["ACME_roc_paralyzed", false]) exitWith {
    if (((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") == 0) then {
        _patient switchGesture "GestureEmpty";
    };
    _patient setVariable ["ACME_seizure_observerSession", [], false];
    false
};

// Never render seizure body motion in a vehicle. Physiology remains active and the owner restarts visuals after exit.
if (!isNull objectParent _patient) exitWith {
    if (((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") == 0) then {
        _patient switchGesture "GestureEmpty";
    };
    _patient setVariable ["ACME_seizure_observerSession", [], false];
    false
};

// Reject retired/unknown gestures from a delayed packet or mismatched older build.
if !(_gesture in ["ACME_SeizureSpasm0", "ACME_SeizureSpasm4", "ACME_SeizureSpasm5", "ACME_SeizureSpasm6"]) exitWith {false};
if (_observerSession isEqualTo _session && {_pulse > 0}
    && {_pulse <= (_patient getVariable ["ACME_seizure_observerPulse",-1])}) exitWith {false};
_patient setVariable ["ACME_seizure_observerSession", +_session, false];
_patient setVariable ["ACME_seizure_observerPulse",_pulse,false];
_patient setVariable ["ACME_seizure_observerUntil",if (_duration > 0) then {CBA_missionTime + _duration} else {-1},false];
_patient switchGesture [_gesture, 0, 1, false];
if (_duration > 0) then {
    [{
        params ["_patient","_session","_pulse"];
        if (isNull _patient
            || {!((_patient getVariable ["ACME_seizure_observerSession",[]]) isEqualTo _session)}
            || {(_patient getVariable ["ACME_seizure_observerPulse",-1]) != _pulse}) exitWith {};
        // Blend out the masked gesture. Never change the underlying recovery/Semi-Fowler/lying move.
        if (((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") == 0) then {
            _patient switchGesture ["GestureEmpty",0,0.15,false];
            // Bound the blend-out even if a modded gesture graph never reaches its empty state.
            [{
                params ["_patient","_session","_pulse"];
                if (isNull _patient
                    || {!((_patient getVariable ["ACME_seizure_observerSession",[]]) isEqualTo _session)}
                    || {(_patient getVariable ["ACME_seizure_observerPulse",-1]) != _pulse}) exitWith {};
                private _current = toLowerANSI (gestureState _patient);
                if (_current in ["gestureempty","", "<none>"] || {(_current find "acme_seizurespasm") == 0}) then {
                    _patient switchGesture ["GestureEmpty",0,1,false];
                };
            },[_patient,_session,_pulse],0.06] call CBA_fnc_waitAndExecute;
        };
    },[_patient,_session,_pulse],(_duration max 0.04) min 0.35] call CBA_fnc_waitAndExecute;
};
true
