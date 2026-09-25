/* Debit cardiac-strength source through the shared partial-vial ledger. */
params ["_medic", "_ml"];
if (isNull _medic || {!local _medic} || {!(_ml isEqualType 0)} || {!finite _ml} || {_ml <= 0} || {_ml > 10}) exitWith {false};
private _holder = [_medic] call ACME_fnc_vialHolder;
if (isNull _holder || {([_holder, "EpinephrineCardiac"] call ACME_fnc_infusionVialVolume) + 0.00001 < _ml}) exitWith {false};
[_holder, "EpinephrineCardiac", _ml, _medic] call ACME_fnc_vialTake
