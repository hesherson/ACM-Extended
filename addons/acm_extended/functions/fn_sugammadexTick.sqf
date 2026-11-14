/* B13: dose-specific, mass-limited reversal. No immortal blanket credit.
   Native Sugammadex_IV units = 100 mg; Rocuronium_IV units = mg/kg.
   Binding remains attached to the original rocuronium record as that record washes out.
   The 16 mg/kg / 1.2 mg/kg immediate-reversal reference is game calibration, not a TOF model. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
if !(missionNamespace getVariable ["ACME_sys_paralytic", true]) exitWith {};
[_patient] call ACME_fnc_medicationRecordIDs;
private _records = _patient getVariable ["ace_medical_medications", []];
private _now = ([true] call ACME_fnc_clinicalClock);
private _roc = _records select {(_x param [0, ""]) in ["Rocuronium", "Rocuronium_IV"] && {_now < (_x select 1) + (_x select 3)}};
private _sug = _records select {(_x param [0, ""]) == "Sugammadex_IV" && {_now < (_x select 1) + (_x select 3)}};
private _rocIDs = _roc apply {_x param [15, ""]};
private _sugIDs = _sug apply {_x param [15, ""]};
private _bindings = (_patient getVariable ["ACME_sug_bindings", []]) select {(_x select 0) in _rocIDs};
private _spent = (_patient getVariable ["ACME_sug_spent", []]) select {(_x select 0) in _sugIDs};
private _kg = (_patient getVariable ["ACM_core_BodyWeight", 80]) max 1;
private _fieldDose = (missionNamespace getVariable ["ACME_sug_fieldMgPerKg", 16]) max 0.001;
private _fullClear = (missionNamespace getVariable ["ACME_sug_fullClear", 1.2]) max 0;
private _activeMg = 0;
{
    private _donor = _x;
    private _id = _donor select 15;
    private _envelope = [_donor select 7, _now - (_donor select 1), _donor select 2, _donor select 3, _donor select 8] call ACM_circulation_fnc_getMedicationEffect;
    private _mg = (_donor select 12) * 100 * (_envelope max 0);
    _activeMg = _activeMg + _mg;
    private _idx = _spent findIf {(_x select 0) == _id};
    if (_idx < 0) then {_idx = _spent pushBack [_id, 0];};
    private _used = (_spent select _idx) select 1;
    private _available = ((_mg / _kg / _fieldDose * _fullClear) - _used) max 0;
    {
        private _target = _x;
        private _targetID = _target select 15;
        private _bidx = _bindings findIf {(_x select 0) == _targetID};
        if (_bidx < 0) then {_bidx = _bindings pushBack [_targetID, 0];};
        private _bound = (_bindings select _bidx) select 1;
        // Convert a present-mass debit to an original-record fraction. This matters late in washout.
        private _present = linearConversion [(_target select 2) + (_target select 8), _target select 3, _now - (_target select 1), 1, 0, true];
        if (_present > 0.000001 && {_available > 0}) then {
            private _unbound = (((_target select 12) - _bound) max 0) * _present;
            private _take = _available min _unbound;
            _bindings set [_bidx, [_targetID, _bound + (_take / _present)]];
            _available = (_available - _take) max 0;
            _used = _used + _take;
        };
    } forEach _roc;
    _spent set [_idx, [_id, _used]];
} forEach _sug;
// The binding ledgers change continuously while reversal is active. Keep the exact owner copy every tick but
// replicate the structured snapshots at most once per second, with immediate refresh if the record identities change.
_patient setVariable ["ACME_sug_bindings", _bindings, false];
_patient setVariable ["ACME_sug_spent", _spent, false];
private _ledgerSig = [
    _bindings apply {_x param [0, ""]},
    _spent apply {_x param [0, ""]}
];
private _ledgerLastSig = _patient getVariable ["ACME_sug_netSig", []];
private _ledgerLastAt = _patient getVariable ["ACME_sug_netAt", -1];
if (_ledgerSig isNotEqualTo _ledgerLastSig || {_ledgerLastAt < 0} || {diag_tickTime - _ledgerLastAt >= 1}) then {
    [_patient, "ACME_sug_bindings", _bindings] call ACME_fnc_setVarNet;
    [_patient, "ACME_sug_spent", _spent] call ACME_fnc_setVarNet;
    _patient setVariable ["ACME_sug_netSig", _ledgerSig, false];
    _patient setVariable ["ACME_sug_netAt", diag_tickTime, false];
};
private _rawRoc = ([_patient, "Rocuronium_IV", false] call ACME_fnc_medicationCountRaw) + ([_patient, "Rocuronium", false] call ACME_fnc_medicationCountRaw);
private _unboundRoc = [_patient] call ACME_fnc_rocuroniumOnBoard;
[_patient, "ACME_sug_mgPerKg", _activeMg / _kg, 0.05, 1] call ACME_fnc_setVarNetApprox;
[_patient, "ACME_sug_reversalEffective", (_rawRoc - _unboundRoc) max 0, 0.005, 1] call ACME_fnc_setVarNetApprox;
[_patient, "ACME_sug_fullReversal", _rawRoc > 0.001 && {_unboundRoc <= 0.001}] call ACME_fnc_setVarNet;
[_patient, "ACME_sug_boundCapacity", 0] call ACME_fnc_setVarNet; // retire B12 global credit
[_patient, "ACME_sug_ramp", 1] call ACME_fnc_setVarNet; // native envelope already applied
