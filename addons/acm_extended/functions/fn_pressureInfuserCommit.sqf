/* Patient-owner commit. Receipts survive full heal so delayed retries stay idempotent.
   The pressure infuser itself is reusable and is never consumed; _isNewCuff only distinguishes first application
   from pumping an already fitted cuff. The ledger grows with actual requests and ends with the patient's entity lifetime. */
params ["_patient", "_medic", "_bagId", "_epoch", "_id", "_issued", "_isNewCuff", ["_allowDrug", false]];
if (isNull _patient || {!local _patient} || {isNull _medic}) exitWith {};
private _receipts = _patient getVariable ["ACME_piReceipts", createHashMap];
private _old = _receipts getOrDefault [_id, []];
if !(_old isEqualTo []) exitWith {
    ["ACME_piAck", [_id, _old select 0, _old select 1, _old select 2], _medic] call CBA_fnc_targetEvent;
};
private _ok = false;
private _refund = false;
private _message = "Pressure cuff request rejected: the patient or bag changed.";
private _found = [];
// _issued is retained in the wire format for compatibility only. It originates on the provider client and must
// never be compared with the casualty owner's CBA_missionTime. Epoch, stable bag identity, live bag contents,
// medic distance and idempotent receipts already make delayed/retried requests safe.
if (alive _patient && {alive _medic} && {(_medic distance _patient) <= 5}
    && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}) then {
    {
        private _i = _y findIf {(_x param [8, ""]) == _bagId};
        if (_i >= 0) exitWith { _found = _y select _i; };
    } forEach (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);
    if !(_found isEqualTo []) then {
        private _hasDrug = ((_patient getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _bagId}) >= 0;
        private _type = _found param [0, ""];
        private _eligible = _type in ["Blood", "FreshBlood", "Saline", "Plasma", "PlasmaLyte"] || {(toLowerANSI _type) in keys (missionNamespace getVariable ["ACME_infusion_premixedByType", createHashMap])};
        if (_hasDrug != _allowDrug) then {_message = "The bag changed section. Select it in the correct list.";};
        if (_hasDrug == _allowDrug && {_eligible} && {(_found param [1, 0]) > 0.5}) then {
            private _cuffs = _patient getVariable ["ACME_piCuffs", createHashMap];
            private _already = _bagId in _cuffs;
            if (_already || {_isNewCuff && {([_medic, _patient, "ACME_PressureInfuser"] call ACME_fnc_treatmentSupplyCount) > 0}}) then {
                _cuffs set [_bagId, [CBA_missionTime, 1.0]];
                [_patient, "cuffs", _cuffs] call ACME_fnc_pressureInfuserStateCommit;
                _ok = true;
                _message = if (_already) then {"Cuff pumped back up to pressure."} else {"Pressure infuser applied to the selected bag."};
            };
        };
    };
};
_receipts set [_id, [_ok, _refund, _message]];
[_patient, "receipts", _receipts] call ACME_fnc_pressureInfuserStateCommit;
["ACME_piAck", [_id, _ok, _refund, _message], _medic] call CBA_fnc_targetEvent;
