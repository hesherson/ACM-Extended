// Network-visible seizure gesture presentation.
// The owner still owns physiology and sequencing. Each gesture transition is replayed on every interface client,
// while the owner machine also executes it so its GestureDone EH advances the authoritative sequence.
params [
    ["_patient", objNull, [objNull]],
    ["_session", [], [[]]],
    ["_gesture", "", [""]],
    ["_active", true, [false]]
];
if (isNull _patient) exitWith {false};

// Machines that neither render the casualty nor own it have no reason to touch the gesture layer.
if (!hasInterface && {!local _patient}) exitWith {false};

private _observerSession = _patient getVariable ["ACME_seizure_observerSession", []];

if (!_active) exitWith {
    if (_session isEqualTo [] || {_observerSession isEqualTo _session} || {local _patient}) then {
        if (((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") == 0) then {
            _patient switchGesture "GestureEmpty";
        };
        _patient setVariable ["ACME_seizure_observerSession", [], false];
    };
    true
};

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

if (_session isEqualTo [] || {_gesture == ""}) exitWith {false};
_patient setVariable ["ACME_seizure_observerSession", +_session, false];
_patient switchGesture [_gesture, 0, 1, false];
true
