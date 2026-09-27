/* Inventory mutations execute only on the recipient owner. Receipts precede acknowledgement.
   A full carried container is used as fallback; never drop a returned device through a vehicle floor. */
params ["_operation", "_id", "_medic", "_patient", ["_settings", []], ["_lastPos", []], ["_lastVehicle", objNull]];
if (isNull _medic || {!local _medic} || {_id == ""}) exitWith {};
private _receipts = _medic getVariable ["ACME_vent_inventoryReceipts", createHashMap];
private _key = _id + ":" + _operation;
private _localReceipts = missionNamespace getVariable ["ACME_vent_localReceipts", createHashMap];
private _actor = getPlayerUID _medic;
if (_actor == "") then {_actor = netId _medic;};
private _localKey = _actor + ":" + _key;
private _receipt = _receipts getOrDefault [_key, _localReceipts getOrDefault [_localKey, []]];
if !(_receipt isEqualTo []) exitWith {
    ["ACME_ventCustodyAck", [_operation, _id, _medic, _receipt select 0, _receipt select 1]] call CBA_fnc_serverEvent;
};
private _ok = false;
private _device = +_settings;
if (_operation == "take") then {
    if (alive _medic && {!isNull _patient} && {alive _patient}
        && {[_medic, "ventilator"] call ACME_fnc_procedureAllowed}
        && {[_medic, _patient] call ACME_fnc_ventRecoveryNear}) then {
        private _supply = [_medic, _patient, ["ACME_Ventilator"]] call ACME_fnc_treatmentSupplyTake;
        if !(_supply isEqualTo []) then {
            private _source = if (isNull (_supply select 2)) then {_supply select 0} else {_supply select 2};
            _device = [];
            {if (!isNil {_source getVariable _x}) then {_device pushBack [_x, _source getVariable _x];};} forEach ([] call ACME_fnc_ventDeviceFields);
            // Custody retains the origin separately from patient device fields for recovery.
            _device pushBack ["ACME_supplyOrigin", [_supply select 0, _supply select 2]];
            [_supply, false] call ACME_fnc_treatmentSupplyRefund;
            _ok = true;
        };
    };
    // Failed takes are terminal. A later connect request gets a new transaction ID.
    _receipts set [_key, [_ok, _device]];
};
if (_operation == "give") then {
    if ([_medic, _patient, _lastPos, _lastVehicle] call ACME_fnc_ventRecoveryNear) then {
        private _before = [_medic, "ACME_Ventilator"] call ace_common_fnc_getCountOfItem;
        _medic addItem "ACME_Ventilator";
        private _after = [_medic, "ACME_Ventilator"] call ace_common_fnc_getCountOfItem;
        if (_after == _before) then {
            private _container = objNull;
            {if (!isNull _x) exitWith {_container = _x;};} forEach [backpackContainer _medic, vestContainer _medic, uniformContainer _medic];
            if (!isNull _container) then {_container addItemCargoGlobal ["ACME_Ventilator", 1];};
            _after = [_medic, "ACME_Ventilator"] call ace_common_fnc_getCountOfItem;
        };
        _ok = _after == (_before + 1);
        if (_ok) then {
            // The existing item model has one carried-device settings block per medic.
            // Preserve a spare's settings when the medic already holds another ventilator.
            if (_before == 0) then {
                private _fields = [] call ACME_fnc_ventDeviceFields;
                {_medic setVariable [_x, nil, true];} forEach _fields;
                {if ((_x select 0) in _fields) then {_medic setVariable [_x select 0, _x select 1, true];};} forEach _device;
                _medic setVariable ["ACME_vent_powerOn", false, true];
                _medic setVariable ["ACME_vent_hasBooted", false, true];
            };
            _medic setVariable ["ACME_vent_devicePatient", objNull, true];
            _receipts set [_key, [true, _device]];
            if (hasInterface && {_medic isEqualTo ACE_player}) then {
                ["Ventilator returned to your equipment.", 3] call ace_common_fnc_displayTextStructured;
            };
        };
    };
};
// Do not cache failed returns. They can succeed when the provider comes back or gains a container.
if (_key in _receipts) then {
    _localReceipts set [_localKey, _receipts get _key];
    missionNamespace setVariable ["ACME_vent_localReceipts", _localReceipts];
    _medic setVariable ["ACME_vent_inventoryReceipts", _receipts, true];
};
["ACME_ventCustodyAck", [_operation, _id, _medic, _ok, _device]] call CBA_fnc_serverEvent;
