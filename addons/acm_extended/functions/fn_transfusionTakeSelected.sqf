/* B226: the bag chosen from the inventory pane belongs to THAT source, not ACE's automatic
 * patient-first search. Administration sets still use the ordinary shared-equipment policy.
 * Return a standard single-settlement receipt, including exact dropped-carrier/vehicle cargo. */
params ["_medic", "_patient", "_class", ["_mode", 0], ["_vehicle", objNull]];
if (isNull _medic || {!local _medic} || {!alive _medic} || {_class == ""} || {!(_mode in [0,1,2])}) exitWith {[]};
private _donor = if (_mode == 1) then {_patient} else {_medic};
if (isNull _donor || {_mode == 1 && {_medic distance _donor > 5}}) exitWith {[]};
if (_mode == 2 && {isNull _vehicle || {objectParent _medic isNotEqualTo _vehicle}}) exitWith {[]};
private _receipt = [];
isNil {
    private _cargo = objNull;
    private _taken = false;
    if (_mode == 2) then {
        if (_class in itemCargo _vehicle) then {
            _vehicle addItemCargoGlobal [_class, -1];
            _cargo = _vehicle;
            _taken = true;
        };
    } else {
        private _carrier = [_donor, [_class]] call ACME_fnc_carrierSupplyTake;
        if (!isNull (_carrier param [0, objNull])) then {
            _cargo = _carrier param [3, objNull];
            _taken = true;
        } else {
            _taken = [_donor, _class] call ACME_fnc_itemTake;
        };
    };
    if (_taken) then {
        private _serial = (missionNamespace getVariable ["ACME_supplyReceiptSerial", 0]) + 1;
        missionNamespace setVariable ["ACME_supplyReceiptSerial", _serial];
        _receipt = [_donor, _class, _cargo, format ["%1:%2", clientOwner, _serial]];
        private _pending = missionNamespace getVariable ["ACME_supplyReceipts", createHashMap];
        _pending set [_receipt select 3, +_receipt];
        missionNamespace setVariable ["ACME_supplyReceipts", _pending];
    };
    true
};
_receipt
