// Owner-authoritative casualty animation arbiter.
// Every request is serialized on the patient owner, which prevents two providers from repeatedly overwriting the
// same casualty with competing roll/special animations on a dedicated server. A short lease is enough for ordinary
// treatment transitions; modal procedures such as auscultation can hold a longer lease and release it explicitly.
params [
    ["_patient", objNull, [objNull]],
    ["_animation", "", [""]],
    ["_animPriority", 1, [0]],
    ["_source", "treatment", [""]],
    ["_provider", objNull, [objNull]],
    ["_leaseSeconds", 2.5, [0]],
    ["_lockPriority", 1, [0]],
    ["_token", "", [""]]
];
if (isNull _patient) exitWith {""};
if (_token == "") then {
    private _serial = (missionNamespace getVariable ["ACME_patientAnimSerial", 0]) + 1;
    missionNamespace setVariable ["ACME_patientAnimSerial", _serial];
    _token = format ["%1:%2:%3:%4", clientOwner, netId _patient, _serial, floor (diag_tickTime * 1000)];
};

if (!local _patient) exitWith {
    [_patient, "patientAnimRequest", [_patient, _animation, _animPriority, _source, _provider, _leaseSeconds, _lockPriority, _token]] call ACME_fnc_ownerDispatch;
    _token
};
if (!alive _patient || {!isNull objectParent _patient}) exitWith {""};
// Release can overtake a queued remote request. Keep bounded cancellation tombstones on the owner,
// so late delivery of that exact token cannot reacquire the casualty after cancel/handoff.
if (_token in (_patient getVariable ["ACME_patientAnimRetired", []])) exitWith {""};

private _now = serverTime;
private _providerId = if (isNull _provider) then {""} else {netId _provider};
private _lock = _patient getVariable ["ACME_patientAnimLock", []];
private _active = (count _lock) >= 5 && {(_lock param [4, -1]) > _now};
private _rejected = false;
if (_active) then {
    private _oldToken = _lock param [0, ""];
    private _oldSource = _lock param [1, ""];
    private _oldProvider = _lock param [2, ""];
    private _oldPriority = _lock param [3, 0];
    // Lift, temporary flattening and permanent lowering are successive stages of the same posture
    // controller. Their own pose generations cancel old callbacks; allow the new posture stage to
    // replace its older priority-1 lease, including provider -> patient-owner handoffs.
    private _postureSources = ["head-elev-lift", "head-elev-lower", "head-elev-flat"];
    private _postureHandoff = _oldPriority == 1 && {_lockPriority == 1}
        && {_oldSource in _postureSources} && {_source in _postureSources};
    private _sameOwner = (_oldToken == _token) || {(_oldSource == _source) && {_oldProvider == _providerId}} || {_postureHandoff};
    _rejected = !_sameOwner && {_oldPriority >= _lockPriority};
};
if (_rejected) exitWith {""};

_leaseSeconds = _leaseSeconds max 0.15;
private _expires = _now + _leaseSeconds;

// Moving casualty choreography shares the provider rate. The speed belongs to the accepted lease,
// never to a rejected request; a subsequent static hold restores normal speed immediately.
private _moving = _animation in ["ACME_HeadElevPatientGrab", "ACME_HeadElevPatientRelease",
    "AinjPpneMstpSnonWrflDnon_rolltofront", "AinjPpneMstpSnonWrflDnon_rolltoback"];
private _rate = if (_moving) then {call ACME_fnc_choreographyRate} else {1};
// Rate and expiry travel in the same record. A new patient owner can reinstall the finite expiry
// without depending on the old machine's private callback or a separately delivered speed flag.
_patient setVariable ["ACME_patientAnimLock", [_token, _source, _providerId, _lockPriority, _expires, _rate], true];
private _oldSpeedToken = _patient getVariable ["ACME_patientAnimSpeedToken", ""];
if (_moving || {_oldSpeedToken != ""}) then {
    _patient setVariable ["ACME_patientAnimSpeedToken", ["", _token] select _moving, true];
    _patient setAnimSpeedCoef _rate;
    ["ace_common_setAnimSpeedCoef", [_patient, _rate]] call CBA_fnc_globalEvent;
};

if (_animation != "") then {
    [_patient, _animation, _animPriority] call ACME_fnc_doAnim;
};

// Expiry is token-checked. A newer owner can replace this lease without an old timer clearing the new state.
[{
    params ["_p", "_tok"];
    if (isNull _p || {!local _p}) exitWith {};
    private _cur = _p getVariable ["ACME_patientAnimLock", []];
    if ((_cur param [0, ""]) == _tok && {(_cur param [4, -1]) <= serverTime}) then {
        // Expiry frees the lease, but a still-valid multi-stage transaction may reuse its token
        // after a sparse frame. Only explicit cancellation/completion creates a tombstone.
        [_p, _tok, false] call ACME_fnc_patientAnimRelease;
    };
}, [_patient, _token], _leaseSeconds + 0.05] call CBA_fnc_waitAndExecute;

_token
