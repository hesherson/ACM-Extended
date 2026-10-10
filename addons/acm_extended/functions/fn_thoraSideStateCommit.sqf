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
private _wasTube = _field == "tube" && {_patient getVariable [_name, false]};
if (_hasValue) then {
    _patient setVariable [_name, _this select 3, true];
} else {
    _patient setVariable [_name, nil, true];
};
// Removing an installed tube must retire the native aggregate on the PATIENT
// OWNER; setting the per-side flag from the provider UI alone did not. This
// leaves an open surgical tract at state 1, but no longer advertises an in-situ
// tube to ACM's suction and respiration model. A contralateral tube survives.
if (_wasTube && {_hasValue} && {!(_this select 3)}) then {
    // Pulling the tube leaves an exposed incision, not a definitive finger
    // thoracostomy being actively held open. The old "finger" tract made
    // ptxContext continue advertising a 5.0-capacity pleural outlet forever.
    private _tractKey = format ["ACME_thora_open_%1", _side];
    if ((_patient getVariable [_tractKey, ""]) == "finger") then {
        _patient setVariable [_tractKey, "split", true];
    };
    private _leftTube = _patient getVariable ["ACME_thora_tube_left", false];
    private _rightTube = _patient getVariable ["ACME_thora_tube_right", false];
    if (!_leftTube && {!_rightTube}) then {
        private _hasTract = (_patient getVariable ["ACME_thora_open_left", ""]) != ""
            || {(_patient getVariable ["ACME_thora_open_right", ""]) != ""};
        private _native = if (_hasTract) then {1} else {0};
        [_patient, [["thoracostomyState", _native]], true] call ACM_breathing_fnc_setRuntimeState;
        if (alive _patient) then {
            [_patient, "tubeRemoved"] call ACME_fnc_ptxTreat;
            [_patient] call ACM_breathing_fnc_updateLungState;
        };
    };
};
