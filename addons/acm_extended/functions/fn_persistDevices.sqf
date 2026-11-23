/* B393: placed medical devices for the ACME Persistence module (Tempus Pro and LS monitors, Accuvac, ventilator:
 * ACME_eqDevices, kinds pro/ls/accu/vent), through acme_equipment's world adapter (B310). Server only. [mode, args]
 *  "capture"  -> [payload, objectIndex], or [] when the devices cannot be saved now (busy, pending setup, an
 *             object without a durable ID): the caller then keeps the previous save. First gives every device and
 *             every object a device refers to (patient, paired Pro, mount, USB Pro, ventilator supplier, supply
 *             vehicle, recovery operator) a durable ID: "acme-dev-<n>" (counter ACME_persistDeviceCounter, saved
 *             with the store), "acme-player-<uid>", or "acme-obj-<class>-<x>_<y>_<z>"; an ID another system bound
 *             is kept. The index lists [id, class, posASL] of the acme-obj objects, to find them again.
 *  "restore"  [payload, objectIndex]: once, at mission start (after the donor registry, before players join):
 *             waits up to 30 s for the indexed objects and for the server journals to be idle, then "import".
 *  "import"   [payload, objectIndex]: one import per mission (ACME_fnc_equipmentWorldRestore). References that do
 *             not resolve here detach (a monitor without its patient, a device off its mount); a ventilator whose
 *             patient is not here is left out (B310: never an unfunded ventilator). If the import is still
 *             refused, the devices come back bare (no patient, pairing or mount, no ventilators).
 * Status in ACME_persistDeviceStatus: ["none"] | ["waiting"] | ["restored", n, ventilatorsLeftOut, detached] |
 * ["failed", n]. */
params [["_mode", "", [""]], ["_a", []], ["_b", []]];
if (!isServer) exitWith {[]};
private _null = ["0:0", "", ""];
switch (_mode) do {
    case "capture": {
        if (isNil "ACME_persistDeviceCounter") then {ACME_persistDeviceCounter = 0;};
        private _devices = (missionNamespace getVariable ["ACME_eqDevices", []]) select {!isNull _x};
        // no device placed and none being set up: nothing to wait for (busy treatment journals elsewhere would
        // otherwise keep devices saved before that were picked up since)
        if (_devices isEqualTo [] && {count (missionNamespace getVariable ["ACME_eqPending", createHashMap]) == 0}) exitWith {[[2, []], []]};
        private _ok = true;
        // [object, isDevice] -> true when it has a durable ID
        private _assign = {
            params ["_o", ["_device", false]];
            if (isNull _o) exitWith {true};
            private _have = _o getVariable ["ACME_persistenceId", ""];
            if (_have isEqualType "" && {_have != ""} && {count _have <= 256}) exitWith {
                // ours: keep this machine's binding on it (restore decodes through it); another system's: theirs
                if ((_have find "acme-") == 0) then {[_o, _have] call ACME_fnc_persistBind; true} else {true}
            };
            if (_device) exitWith {
                private _done = false;
                for "_i" from 1 to 32 do {
                    ACME_persistDeviceCounter = ACME_persistDeviceCounter + 1;
                    if ([_o, format ["acme-dev-%1", ACME_persistDeviceCounter]] call ACME_fnc_persistBind) exitWith {_done = true;};
                };
                _done
            };
            if (isPlayer _o && {(getPlayerUID _o) != ""}) exitWith {[_o, "acme-player-" + getPlayerUID _o] call ACME_fnc_persistBind};
            private _p = getPosASL _o;
            private _base = format ["acme-obj-%1-%2_%3_%4", typeOf _o, round (_p select 0), round (_p select 1), round (_p select 2)];
            private _done = false;
            for "_i" from 1 to 9 do {
                if ([_o, [_base, format ["%1-%2", _base, _i]] select (_i > 1)] call ACME_fnc_persistBind) exitWith {_done = true;};
            };
            _done
        };
        // devices first, so a paired or USB Pro is named as a device, not as an object
        {if !([_x, true] call _assign) then {_ok = false;};} forEach _devices;
        {
            private _o = _x;
            private _kind = _o getVariable ["ACME_eq_kind", ""];
            private _patient = _o getVariable ["ACME_eq_patient", objNull];
            if (_kind in ["pro", "ls"]) then {
                private _prefix = ["acme_tempus", "acme_tempusls"] select (_kind == "ls");
                _patient = _o getVariable [_prefix + "_pat", objNull];
            };
            private _refs = [_patient, _o getVariable ["ACME_eq_mount", objNull]];
            if (_kind == "ls") then {_refs append [_o getVariable ["acme_tempusls_link", objNull], _o getVariable ["ACME_eq_usb", objNull]];};
            if (_kind == "vent" && {!isNull _patient}) then {
                private _r = (missionNamespace getVariable ["ACME_vent_custody", createHashMap]) getOrDefault [_patient getVariable ["ACME_vent_custodyId", ""], createHashMap];
                if (_r isEqualType createHashMap) then {
                    _refs append [_r getOrDefault ["supplier", objNull], (_r getOrDefault ["supplyOrigin", []]) param [1, objNull], _r getOrDefault ["recoveryOperator", objNull]];
                };
            };
            {if (_x isEqualType objNull && {!(_x in _devices)} && {!([_x] call _assign)}) then {_ok = false;};} forEach _refs;
        } forEach _devices;
        if (!_ok) exitWith {[]};
        private _save = call ACME_fnc_equipmentWorldSnapshot;
        if !(_save isEqualType [] && {count _save == 2}) exitWith {[]};
        private _bindings = missionNamespace getVariable ["ACME_clinicalObjectBindings", createHashMap];
        private _index = [];
        private _seen = [];
        {
            _x params ["", "", "", "", "", "", "_patient", "", "_link", "_custody", ["_mount", _null], ["_usb", _null]];
            private _refs = [_patient, _link, _mount, _usb];
            if (count _custody == 5) then {_refs append [_custody select 0, _custody select 2, _custody select 3];};
            {
                private _id = _x select 2;
                if ((_id find "acme-obj-") == 0 && {!(_id in _seen)}) then {
                    _seen pushBack _id;
                    private _obj = _bindings getOrDefault [_id, objNull];
                    if (!isNull _obj) then {_index pushBack [_id, typeOf _obj, getPosASL _obj];};
                };
            } forEach _refs;
        } forEach (_save select 1);
        [_save, _index]
    };
    case "resolve": {
        // [objectIndex] -> how many of the indexed objects are bound here now. A litter, mount or vehicle is found
        // again by class within 2 m of where it was saved; never a unit (an AI patient is not the one saved).
        private _found = 0;
        private _bindings = missionNamespace getVariable ["ACME_clinicalObjectBindings", createHashMap];
        {
            _x params ["_id", "_class", "_pos"];
            private _have = _bindings getOrDefault [_id, objNull];
            if (!isNull _have && {(_have getVariable ["ACME_persistenceId", ""]) isEqualTo _id}) then {_found = _found + 1; continue;};
            if (_class isKindOf "CAManBase") then {continue;};
            private _candidates = (nearestObjects [ASLToAGL _pos, [_class], 2, true]) select {
                typeOf _x == _class && {alive _x} && {(_x getVariable ["ACME_persistenceId", ""]) in ["", _id]}
            };
            {
                if ([_x, _id] call ACME_fnc_persistBind) exitWith {_found = _found + 1;};
            } forEach _candidates;
        } forEach _a;
        _found
    };
    case "restore": {
        if !(_a isEqualType [] && {count _a == 2} && {((_a select 1) isEqualType [])}) exitWith {ACME_persistDeviceStatus = ["none"];};
        ACME_persistDeviceStatus = ["waiting"];
        [{
            params ["_args", "_id"];
            _args params ["_payload", "_index", "_soft", "_hard"];
            if (((missionNamespace getVariable ["ACME_persistDeviceStatus", ["none"]]) select 0) != "waiting") exitWith {
                [_id] call CBA_fnc_removePerFrameHandler;   // cleared by Zeus meanwhile
            };
            if (time <= 0) exitWith {};
            private _all = (["resolve", _index] call ACME_fnc_persistDevices) >= count _index;
            private _idle = call ACME_fnc_persistenceJournalsReady;
            if ((_idle && {_all || {CBA_missionTime > _soft}}) || {CBA_missionTime > _hard}) then {
                [_id] call CBA_fnc_removePerFrameHandler;
                ["import", _payload, _index] call ACME_fnc_persistDevices;
            };
        }, 1, [+_a, +_b, CBA_missionTime + 30, CBA_missionTime + 90]] call CBA_fnc_addPerFrameHandler;
    };
    case "import": {
        ["resolve", _b] call ACME_fnc_persistDevices;
        private _version = _a select 0;
        private _rows = +(_a select 1);
        private _bindings = missionNamespace getVariable ["ACME_clinicalObjectBindings", createHashMap];
        private _custodies = missionNamespace getVariable ["ACME_vent_custody", createHashMap];
        private _decode = {
            params ["_ref"];
            if ((_ref select 2) == "") exitWith {objNull};
            private _o = ["decode", _ref] call ACME_fnc_clinicalObjectRef;
            if (isNil "_o" || {!(_o isEqualType objNull)}) then {objNull} else {_o}
        };
        // 1) rows whose device ID is taken here, and ventilators without their (restored, still ventilated) patient
        private _kept = [];
        private _slots = [];
        private _ventsOut = 0;
        private _detached = 0;
        {
            private _row = _x;
            _row params ["_rowId", "_kind", "", "", "", "", "_pref"];
            if (!isNull (_bindings getOrDefault [_rowId, objNull])) then {continue;};
            private _patient = [_pref] call _decode;
            private _usable = !isNull _patient && {_patient isKindOf "CAManBase"} && {alive _patient}
                && {isNull (_patient getVariable ["ACME_eq_" + _kind, objNull])} && {!([_pref select 2, _kind] in _slots)};
            if (_kind == "vent") then {
                if !(_usable && {_patient getVariable ["ACME_vent_onPatient", false]} && {!(_patient getVariable ["ACME_vent_recovering", false])}
                    && {!((_patient getVariable ["ACME_vent_custodyId", ""]) in _custodies)} && {!(("world:" + _rowId) in _custodies)}) then {
                    _ventsOut = _ventsOut + 1;
                    continue;
                };
            } else {
                if (!_usable && {(_pref select 2) != ""}) then {_row set [6, +_null]; _detached = _detached + 1;};
            };
            if (((_row select 6) select 2) != "") then {_slots pushBack [(_row select 6) select 2, _kind];};
            _kept pushBack _row;
        } forEach _rows;
        // 2) pairings, mounts, USB and ventilator custody that do not resolve here detach
        private _proIds = (_kept select {(_x select 1) == "pro"}) apply {_x select 0};
        private _mounts = [];
        private _usbs = [];
        {
            private _row = _x;
            private _kind = _row select 1;
            private _link = _row select 8;
            if ((_link select 2) != "" && {!((_link select 2) in _proIds)}) then {
                private _o = [_link] call _decode;
                if (isNull _o || {!(_o isKindOf "ACME_TempusPro")}) then {_row set [8, +_null]; _detached = _detached + 1;};
            };
            if (count _row >= 12) then {
                private _mount = _row select 10;
                if ((_mount select 2) != "") then {
                    private _o = [_mount] call _decode;
                    if (isNull _o || {(_mount select 2) in _mounts} || {getText (configOf _o >> "ACME_eq_mountKind") != _kind}
                        || {!isNull (_o getVariable ["ACME_eq_device", objNull])}) then {
                        _row set [10, +_null]; _detached = _detached + 1;
                    } else {_mounts pushBack (_mount select 2);};
                };
                private _usb = _row select 11;
                if ((_usb select 2) != "") then {
                    private _usbId = _usb select 2;
                    private _inRows = _usbId in _proIds;
                    private _o = if (_inRows) then {objNull} else {[_usb] call _decode};
                    private _linkId = (_row select 8) select 2;
                    if (_usbId in _usbs || {_linkId != "" && {_linkId != _usbId}}
                        || {!_inRows && {isNull _o || {!(_o isKindOf "ACME_TempusPro")} || {!isNull (_o getVariable ["ACME_eq_usbLs", objNull])}}}) then {
                        _row set [11, +_null]; _detached = _detached + 1;
                    } else {_usbs pushBack _usbId;};
                };
            };
            if (_kind == "vent") then {
                private _custody = _row select 9;
                {
                    private _ref = _custody select _x;
                    if ((_ref select 2) != "" && {isNull ([_ref] call _decode)}) then {_custody set [_x, +_null];};
                } forEach [0, 2, 3];
            };
        } forEach _kept;
        private _payload = [_version, _kept];
        private _result = [false, []];
        if ([_payload] call ACME_fnc_equipmentWorldSchema) then {_result = [_payload] call ACME_fnc_equipmentWorldRestore;};
        if !(_result param [0, false]) then {
            // 3) still refused: the devices alone, where they stood
            private _bare = (_kept select {(_x select 1) != "vent"}) apply {
                private _r = +_x;
                _r set [6, +_null]; _r set [8, +_null];
                if (count _r >= 12) then {_r set [10, +_null]; _r set [11, +_null];};
                _r
            };
            _ventsOut = _ventsOut + ({(_x select 1) == "vent"} count _kept);
            _detached = count _kept;
            _payload = [_version, _bare];
            if ([_payload] call ACME_fnc_equipmentWorldSchema) then {_result = [_payload] call ACME_fnc_equipmentWorldRestore;};
        };
        if (_result param [0, false]) then {
            ACME_persistDeviceStatus = ["restored", count (_result select 1), _ventsOut, _detached];
            ["note", format ["%1 placed devices (%2 ventilators left out, %3 references detached)", count (_result select 1), _ventsOut, _detached]] call ACME_fnc_persistServer;
        } else {
            ACME_persistDeviceStatus = ["failed", count _rows];
            ["note", format ["no placed devices: the equipment adapter refused all %1 saved (live devices already in the mission, or its journals busy); the save keeps them", count _rows]] call ACME_fnc_persistServer;
        };
        ACME_persistDeviceStatus
    };
    default {[]};
};
