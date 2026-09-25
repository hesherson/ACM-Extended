/* Reserve one physical treatment ITEM through ACE's native supply policy.
   removeItem has global arguments/effects, as used by native ACM cric via ACE.
   The vehicle is captured before debit so dismounting never changes the refund donor.
   Return [] on failure, otherwise [unit, classname, sourceVehicle, receiptId].
   Settle a receipt once with treatmentSupplyRefund: true refunds, false commits. */
params ["_medic", "_patient", "_items", ["_personalOnly", false]];
if (isNull _medic || {!local _medic} || {!(_items isEqualType [])} || {_items isEqualTo []}) exitWith {[]};
private _receipt = [];
isNil {
    private _sources = [];
    {
        private _vehicle = objectParent _x;
        _sources pushBack [_x, _vehicle, itemCargo _vehicle];
    } forEach ([_medic, _patient] call ACME_fnc_treatmentSupplyOrder);
    private _used = [objNull, "", false];
    if (_personalOnly) then {
        // Already-materialized used/cooled bags must keep their own volume/cold provenance.
        // This branch is always provider-local and intentionally excludes vehicle cargo.
        {
            private _before = [_medic, _x] call ace_common_fnc_getCountOfItem;
            if (_before > 0) exitWith {
                _medic removeItem _x;
                if (([_medic, _x] call ace_common_fnc_getCountOfItem) < _before) then {_used = [_medic, _x, true];};
            };
        } forEach _items;
    } else {
        _used = [_medic, _patient, _items] call ace_medical_treatment_fnc_useItem;
    };
    _used params [["_donor", objNull], ["_item", ""]];
    if (!isNull _donor && {_item != ""}) then {
        private _vehicle = objNull;
        private _index = _sources findIf {(_x select 0) isEqualTo _donor};
        if (_index >= 0) then {
            private _source = _sources select _index;
            if (!_personalOnly && {_item in (_source select 2)}) then {_vehicle = _source select 1;};
        };
        private _serial = (missionNamespace getVariable ["ACME_supplyReceiptSerial", 0]) + 1;
        missionNamespace setVariable ["ACME_supplyReceiptSerial", _serial];
        private _id = format ["%1:%2", clientOwner, _serial];
        _receipt = [_donor, _item, _vehicle, _id];
        private _pending = missionNamespace getVariable ["ACME_supplyReceipts", createHashMap];
        _pending set [_id, +_receipt];
        missionNamespace setVariable ["ACME_supplyReceipts", _pending];
    };
    true
};
_receipt
