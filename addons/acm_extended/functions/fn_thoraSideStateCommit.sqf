/* Phase 84: authoritative writer for durable per-side thoracostomy procedural state.
 * An omitted/nil value clears the field without ever referencing an undefined local.
 */
params ["_patient", "_side", "_field"];
if (isNull _patient) exitWith {};
// Durable thoracostomy state is patient-owner authoritative. Provider-side UI may request a commit, but it never
// writes another machine's casualty directly.
if (!local _patient) exitWith {
    [_patient, "thoraSideState", +_this] call ACME_fnc_ownerDispatch;
};
_side = toLower _side;
_field = toLower _field;
if !(_side in ["left","right"]) exitWith {};
private _allowed = ["incision","incisionscore","prep","infection","open","ribtarget","site","tube","sealed","closed"];
if !(_field in _allowed) exitWith {};
private _name = format ["ACME_thora_%1_%2", _field, _side];
private _hasValue = (count _this > 3) && {!isNil {_this select 3}};
private _proposalEpoch = _this param [4, -1];
if (_field == "ribtarget" && {_hasValue} && {_proposalEpoch >= 0}
    && {_proposalEpoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};
// The randomized anatomy belongs to the casualty. Concurrent viewers may propose an initial target,
// but only the first owner-side proposal establishes it. Explicit reset clears must still pass through.
if (_field == "ribtarget" && {_hasValue} && {count (_patient getVariable [_name, []]) == 4}) exitWith {};
if (_hasValue) then {
    _patient setVariable [_name, _this select 3, true];
} else {
    _patient setVariable [_name, nil, true];
};
