/* Only deployed devices are scanned. Corpses remain registered after allUnits excludes them.
   In-session UID recovery covers reconnect/respawn. The server ledger is not a cross-mission save service. */
if (!isServer) exitWith {};
private _records = missionNamespace getVariable ["ACME_vent_custody", createHashMap];
private _now = CBA_missionTime;
{
    private _id = _x;
    private _r = _records get _id;
    private _patient = _r get "patient";
    private _phase = _r get "phase";
    private _deleted = _r getOrDefault ["deleted", false];
    if (!isNull _patient && {!_deleted}) then {
        _r set ["lastPos", getPosASL _patient];
        _r set ["lastVehicle", objectParent _patient];
        if (_phase != "taking") then {
            private _state = [];
            {if (!isNil {_patient getVariable _x}) then {_state pushBack [_x, _patient getVariable _x];};} forEach ([] call ACME_fnc_ventDeviceFields);
            _r set ["settings", _state];
        };
    };
    private _gone = isNull _patient || {_deleted};
    // An automatically recovered vehicle-sourced device returns to that exact cargo.
    // Explicit removal still transfers custody to the provider who removes it.
    private _origin = _r getOrDefault ["supplyOrigin", []];
    private _originVehicle = _origin param [1, objNull];
    if (_phase == "attached" && {_gone} && {!isNull _originVehicle}) then {
        _originVehicle addItemCargoGlobal ["ACME_Ventilator", 1];
        {_originVehicle setVariable [_x select 0, _x select 1, true];} forEach (_r get "settings");
        _r set ["phase", "finalizing"];
        _phase = "finalizing";
    };
    if (_phase == "attached" && {_gone}) then {
        private _supplier = _r getOrDefault ["supplier", objNull];
        private _uid = _r getOrDefault ["supplierUID", ""];
        // A deleted AI donor has no entity or UID to receive the item. Keep the original
        // origin record, but recover through the captured operator near the last device position.
        if (isNull _supplier && {_uid == ""}) then {
            _supplier = _r getOrDefault ["recoveryOperator", objNull];
            _uid = _r getOrDefault ["recoveryOperatorUID", ""];
        };
        if ((isNull _supplier || {!alive _supplier} || {_uid != "" && {getPlayerUID _supplier != _uid}}) && {_uid != ""}) then {
            if (_now >= (_r getOrDefault ["nextResolve", 0])) then {
                _r set ["nextResolve", _now + 2];
                private _found = (allPlayers select {alive _x && {getPlayerUID _x == _uid}}) param [0, objNull];
                if (!isNull _found) then {_supplier = _found; _r set ["supplier", _found];};
            };
        };
        if (!(_r getOrDefault ["stopped", false]) && {!isNull _patient}) then {
            _r set ["stopped", true];
            ["ACME_ventPatientClear", [_patient, _id, false], _patient] call CBA_fnc_targetEvent;
        };
        if ([_supplier, _patient, _r get "lastPos", _r get "lastVehicle"] call ACME_fnc_ventRecoveryNear) then {
            _r set ["recipient", _supplier];
            _r set ["recipientUID", _uid];
            _r set ["phase", "returning"];
            _r set ["lastSent", -100];
            if (!isNull _patient) then {_patient setVariable ["ACME_vent_recovering", true, true];};
            _phase = "returning";
        };
    };
    if (_phase == "finalizing") then {
        if (isNull _patient || {_deleted} || {(_patient getVariable ["ACME_vent_custodyId", ""]) != _id}) then {
            _records deleteAt _id;
        } else {
            if (_now - (_r get "lastSent") >= 2) then {
                _r set ["lastSent", _now];
                ["ACME_ventPatientClear", [_patient, _id, true], _patient] call CBA_fnc_targetEvent;
            };
        };
        continue;
    };
    if (_now - (_r get "lastSent") < 2) then {continue;};
    if (_phase == "taking") then {
        _r set ["lastSent", _now];
        private _supplier = _r get "supplier";
        if (!isNull _supplier) then {["ACME_ventInventory", ["take", _id, _supplier, _patient], _supplier] call CBA_fnc_targetEvent;};
    };
    if (_phase == "returning") then {
        private _recipient = _r getOrDefault ["recipient", objNull];
        private _uid = _r getOrDefault ["recipientUID", ""];
        private _receipt = if (isNull _recipient) then {[]} else {(_recipient getVariable ["ACME_vent_inventoryReceipts", createHashMap]) getOrDefault [_id + ":give", []]};
        if (!(_receipt isEqualTo []) && {_receipt select 0}) then {
            _r set ["phase", "finalizing"]; _r set ["lastSent", -100];
            continue;
        };
        // A reconnect can resume an undelivered return. Receipts survive normal owner changes and respawn.
        if ((isNull _recipient || {!alive _recipient}) && {_uid != ""}) then {
            private _new = (allPlayers select {alive _x && {getPlayerUID _x == _uid}}) param [0, objNull];
            if (!isNull _new) then {_recipient = _new; _r set ["recipient", _new];};
        };
        if (!isNull _recipient && {[_recipient, _patient, _r get "lastPos", _r get "lastVehicle"] call ACME_fnc_ventRecoveryNear}) then {
            _r set ["lastSent", _now];
            ["ACME_ventInventory", ["give", _id, _recipient, _patient, _r get "settings", _r get "lastPos", _r get "lastVehicle"], _recipient] call CBA_fnc_targetEvent;
        };
    };
} forEach (keys _records);
if (count _records == 0) then {
    private _pfh = missionNamespace getVariable ["ACME_vent_custodyPFH", -1];
    if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler; missionNamespace setVariable ["ACME_vent_custodyPFH", -1];};
};
