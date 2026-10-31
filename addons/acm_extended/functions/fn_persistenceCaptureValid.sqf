/* Revalidate an owner's returned pair immediately before committing a server
 * save. Coolant/warm timers may advance; every static equipment fact must match.
 * The mission retains its external gameplay/input freeze until barrier end. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_persistenceCaptureValid;}; _ok};
params ["_unit","_capture"];
if (isNull _unit || {!local _unit} || {!(_capture isEqualType [])} || {count _capture != 2} || {isNil {_capture select 0}} || {isNil {_capture select 1}}) exitWith {false};
_unit setVariable ["ACME_persistenceCaptureProof",[],true];
private _saved = _capture select 1;
if !(_saved isEqualType createHashMap) exitWith {false};
private _lease = _unit getVariable ["ACME_persistenceLease",""];
if (_lease == "" || {!(_unit getVariable ["ACME_persistenceFrozen",false])}
    || {(_saved getOrDefault ["ACME_checkpointLease_v1",""]) isNotEqualTo _lease}) exitWith {false};
private _expected = [_saved] call ACME_fnc_persistenceFingerprint;
if (_expected == "") exitWith {false};
private _current = [_unit] call ACME_fnc_persistenceSnapshot;
if (_current isEqualTo [] || {(_current select 0) isNotEqualTo (_capture select 0)}) exitWith {false};
private _actual = [_current select 1] call ACME_fnc_persistenceFingerprint;
if (_actual == "" || {_actual != _expected}) exitWith {false};
_unit setVariable ["ACME_persistenceCaptureProof",[_lease,_expected],true];
true
