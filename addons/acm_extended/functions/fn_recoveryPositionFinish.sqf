/* The exact treatment callback owns this recovery episode; stale callbacks cannot stop its successor. */
params ["_args", ["_success", false]];
_args params ["_medic", "_patient", "_part", "_classname"];
if ((toLowerANSI _classname) != "recoveryposition") exitWith {};
private _token = _args param [7, ""];
private _record = _medic getVariable ["ACME_recoveryAction", []];
if (_token == "" || {(_record param [0, ""]) != _token}) exitWith {};
_record params ["", "", "_epoch", "_rollToken", "_dispatched"];
private _valid = _success && {[_args, 5, 5] call ACME_fnc_recoveryPositionProgress} && {_record param [4, false]};
[_medic, _patient, _valid, !_valid, ["cancel", "commit"] select _valid, _token] call ACM_airway_fnc_setRecoveryPosition;
_medic setVariable ["ACME_recoveryAction", []];
// Native treatment success must not clip a late-starting Flip. Its existing controller owns the
// full held sample and finite cleanup; only cancellation actively retires this exact provider episode.
if (!_valid && {(_medic getVariable ["ACME_rollProviderToken", ""]) == _rollToken} && {_rollToken != ""}) then {
    private _pfh = _medic getVariable ["ACME_rollProviderPFH", -1];
    if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
    _medic setVariable ["ACME_rollProviderPFH", -1];
    _medic setVariable ["ACME_rollProviderToken", ""];
    _medic setVariable ["ACME_rollProviderActive", false];
    [_medic, "roll", _epoch] call ACME_fnc_treatmentPoseStop;
};
