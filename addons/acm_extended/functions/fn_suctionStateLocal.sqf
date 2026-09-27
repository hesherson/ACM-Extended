/* B13: patient-owned, expiring operator leases. OFF from one provider cannot stop another.
   All times are mission time; a stale packet cannot restart a closed lease. */
params ["_patient", "_medic", "_epoch", "_token", "_sequence", "_mode", ["_position", []], ["_device", -1]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient, "suctionState", _this] call ACME_fnc_ownerDispatch;};
if (isNull _medic || {_token == ""} || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};
if !(_mode in ["off","closed","hand","salad","manual"]) exitWith {};
private _sequences = _patient getVariable ["ACME_suctionSequence", []];
private _si = _sequences findIf {(_x select 0) == _token};
if (_si >= 0 && {_sequence <= ((_sequences select _si) select 1) || {(_sequences select _si) param [2, false]}}) exitWith {};
if (_si < 0) then {_si = _sequences pushBack [_token, -1, false];};
_sequences set [_si, [_token, _sequence, _mode == "closed"]];
if (count _sequences > 64) then {_sequences deleteAt 0;};
_patient setVariable ["ACME_suctionSequence", _sequences, true];
private _sessions = (_patient getVariable ["ACME_suctionSessions", []]) select {(_x select 0) != _token};
private _valid = alive _patient && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])};
_valid = _valid && {_medic distance _patient <= 5 || {!isNull objectParent _medic && {objectParent _medic == objectParent _patient}}};
if (_mode in ["hand","salad"]) then {
    _valid = _valid && {_device == 1} && {([_medic, _patient, "ACM_ACCUVAC"] call ACME_fnc_treatmentSupplyCount) > 0};
};
if (_mode == "manual") then {
    private _proof = _medic getVariable ["ACME_suctionManualSession", []];
    _valid = _valid && {_device == 0} && {(_proof param [0, objNull]) == _patient} && {(_proof param [1, ""]) == _token};
};
private _positionOK = _position isEqualType [] && {count _position == 2}
    && {(_position findIf {!(_x isEqualType 0) || {!finite _x} || {_x < -1} || {_x > 2}}) < 0};
if (_valid && {_mode in ["hand","salad","manual"]} && {_positionOK}) then {
    _sessions pushBack [_token, _medic, CBA_missionTime + 1.5, _mode, _epoch, _sequence, _position, _device];
};
_patient setVariable ["ACME_suctionSessions", _sessions, true];
if (_mode == "closed") then {
    private _totals = (_patient getVariable ["ACME_suctionTotals", []]) select {(_x select 0) == _token};
    if !(_totals isEqualTo []) then {
        private _ml = (_totals select 0) select 1;
        if (_ml > 0) then {[_patient, "activity", "%1 suctioned %2 mL from the airway", [[_medic, false, true] call ace_common_fnc_getName, round _ml]] call ace_medical_treatment_fnc_addToLog;};
    };
};
[_patient] call ACME_fnc_ownerRegister;
