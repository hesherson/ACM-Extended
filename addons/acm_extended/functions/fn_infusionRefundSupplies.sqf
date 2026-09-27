/* Call only after the pending request is marked acknowledged. */
params [["_receipt", [], [[]]], ["_refund", true]];
if (_receipt isEqualTo []) exitWith {};
if (count _receipt == 4) exitWith {
    _receipt params ["_medic","_items","_source","_id"];
    private _pending = missionNamespace getVariable ["ACME_medicationSourceReceipts",createHashMap];
    if !((_pending getOrDefault [_id,[]]) isEqualTo _receipt) exitWith {};
    // Consume the captured authorization before refunding, including on a replay
    // of a copied receipt. This never depends on the current player or selector.
    _pending deleteAt _id;
    {[_x,_refund] call ACME_fnc_treatmentSupplyRefund;} forEach _items;
    if (_refund) then {
        _source params ["_holder","_taken"];
        // The source owner waits for any newer drawer's lease before adding the
        // captured delta to the current ledger. Never overwrite that drawer's map.
        [_holder,"vialRefund",[_id,_taken]] call ACME_fnc_ownerDispatch;
    };
};
if (!_refund) exitWith {};
_receipt params ["_medic", ["_items", []], ["_solution", []]];
if (isNull _medic || {!local _medic}) exitWith {};
{[_medic, _x] call ace_common_fnc_addToInventory;} forEach _items;
if (count _solution == 2) then {
    _solution params ["_med", "_ml"];
    [_medic, _med, _ml, _medic] call ACME_fnc_vialRefund;
};
