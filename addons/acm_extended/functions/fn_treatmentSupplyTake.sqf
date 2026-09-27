/* Reserve one physical treatment ITEM through ACE's supply policy, extended for EFAK virtual kit contents.
   Without EFAK, the native ACE useItem path is unchanged. With EFAK, the same patient/medic/vehicle ordering is
   reproduced per source and only then extended to a kit-contained item.
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
        // Used/cooled bags carry provenance outside the ordinary inventory model. Keep this branch
        // provider-local and loose-inventory-only exactly as before.
        {
            private _before = [_medic, _x] call ace_common_fnc_getCountOfItem;
            if (_before > 0) exitWith {
                _medic removeItem _x;
                if (([_medic, _x] call ace_common_fnc_getCountOfItem) < _before) then {
                    _used = [_medic, _x, true];
                };
            };
        } forEach _items;
    } else {
        private _efakAvailable =
            !isNil "efak_medical_fnc_countItem"
            && {!isNil "efak_medical_fnc_takeItem"};

        if (!_efakAvailable) then {
            // Keep stock 1.2.4 behavior bit-for-bit when EFAK is not loaded.
            _used = [_medic, _patient, _items] call ace_medical_treatment_fnc_useItem;
        } else {
            // Match ACE's Zeus treatment shortcut: report the requested item without changing inventory.
            if (_medic isEqualTo player && {!isNull findDisplay 312}) then {
                _used = [_medic, _items select 0, false];
            } else {
                scopeName "ACME_EFAK_SUPPLY";
                {
                    private _unit = _x;
                    private _unitVehicle = objectParent _unit;
                    private _unitItems = [_unit, 0] call ace_common_fnc_uniqueItems;
                    private _unitMagazines = [_unit, 2] call ace_common_fnc_uniqueItems;
                    private _vehicleItems = itemCargo _unitVehicle;
                    private _vehicleMagazines = magazineCargo _unitVehicle;

                    {
                        private _candidate = _x;
                        switch (true) do {
                            case (_candidate in _vehicleItems): {
                                _unitVehicle addItemCargoGlobal [_candidate, -1];
                                _used = [_unit, _candidate, false];
                                breakOut "ACME_EFAK_SUPPLY";
                            };
                            case (_candidate in _vehicleMagazines): {
                                [_unitVehicle, _candidate] call ace_common_fnc_adjustMagazineAmmo;
                                _used = [_unit, _candidate, false];
                                breakOut "ACME_EFAK_SUPPLY";
                            };
                            case (_candidate in _unitItems): {
                                _unit removeItem _candidate;
                                _used = [_unit, _candidate, true];
                                breakOut "ACME_EFAK_SUPPLY";
                            };
                            case (_candidate in _unitMagazines): {
                                private _magsStart = count magazines _unit;
                                [_unit, _candidate] call ace_common_fnc_adjustMagazineAmmo;
                                _used = [_unit, _candidate, (count magazines _unit) < _magsStart];
                                breakOut "ACME_EFAK_SUPPLY";
                            };
                            default {
                                // Loose inventory was already checked above, so a successful EFAK take here
                                // represents virtual contents packed inside this donor's IFAK/AFAK/MFAK.
                                if (
                                    _unit isKindOf "CAManBase"
                                    && {([_unit, _candidate] call efak_medical_fnc_countItem) > 0}
                                    && {[_unit, _candidate] call efak_medical_fnc_takeItem}
                                ) then {
                                    _used = [_unit, _candidate, false];
                                    breakOut "ACME_EFAK_SUPPLY";
                                };
                            };
                        };
                    } forEach _items;
                } forEach ([_medic, _patient] call ACME_fnc_treatmentSupplyOrder);
            };
        };
    };

    _used params [["_donor", objNull], ["_item", ""]];
    if (!isNull _donor && {_item != ""}) then {
        private _vehicle = objNull;
        private _index = _sources findIf {(_x select 0) isEqualTo _donor};
        if (_index >= 0) then {
            private _source = _sources select _index;
            if (!_personalOnly && {_item in (_source select 2)}) then {
                _vehicle = _source select 1;
            };
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
