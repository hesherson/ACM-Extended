/* Store both linked records on the same physical carrier; reference fields are rebound only on receipt. */
params ["_owner"];
if (isNull _owner || {!local _owner}) exitWith {false};
private _meds = _owner getVariable ["ACME_infusion_PreparedBags",[]];
private _sets=(_owner getVariable ["ACME_preparedIVSets",[]]) apply {
    [_x,_owner] call ACME_fnc_bloodUseSeed
};
_owner setVariable ["ACME_preparedIVSets",_sets,true];
private _payloads = _sets apply {
    private _set = +_x;
    private _id = _set select 0;
    private _mi = _meds findIf {(_x param [0,""]) == _id};
    [_id,_set,if (_mi >= 0) then {+(_meds select _mi)} else {[]}]
};
[_owner,"prepared",_payloads] call ACME_fnc_inventoryLedgerCommit
