/* B393: server side of the ACME Persistence module (fn_persistModuleInit.sqf). [mode, args...]
 *  "load"     read the mission's saved store (missionProfileNamespace), restore the donor registry, start putting
 *             the saved ACME state back on the world's ACME objects and recreate the saved placed devices
 *  "start"    autosave, saves on leave and at the end, events from the clients and from Zeus
 *  "receive"  [unit, medicalJson, itemMetadataPairs, acmeItems]: a client's capture of its player. An empty json
 *             or metadata, or acmeItems false, keeps what was saved for that part (busy or not yet restored)
 *  "request"  [unit]: a client asks for its player's saved state (answers with ACME_persistApply, [] if none)
 *  "died"     [unit, uid] / "forget" [uid]: a player who died is not brought back hurt
 *  "save"     write the store; "saveSoon" one save a moment later (several leaving players: one save)
 *  "report"   [curator, what]: send the save summary to a Zeus (ACME_persistReport)
 *  "clear"    forget everything saved for this mission (Zeus)
 *  "note"     [text]: one debug line in the server RPT (also the clients' notes, ACME_persistNote)
 * The store is [1, [player records], [world rows], donor registry snapshot, saved at (UTC seconds), placed devices,
 * device object index, device counter]; builds without the last three read it unchanged and drop them.
 *  - a player record is [uid, name, medical json, item metadata pairs, ACME item classes (one entry per item, at
 *    most 512), saved at];
 *  - a world row is [class, posASL, fridge snapshot, cooler box snapshot, inventory snapshot, loose blood snapshot];
 *  - placed devices are ACME_fnc_equipmentWorldSnapshot's [2, rows] ([] = none saved); the index is
 *    [[acme-obj id, class, posASL], ...] for the litters, mounts and other objects those rows refer to;
 *  - the counter is the last number given to an "acme-dev-<n>" device ID. */
params [["_mode", "", [""]], ["_a", []], ["_b", []], ["_c", []], ["_d", []]];
if (!isServer) exitWith {};
private _cfg = missionNamespace getVariable ["ACME_persist", createHashMap];
if (count _cfg == 0 && {_mode != "enableDefault"}) exitWith {};
private _utc = {
    // seconds since 1970 from systemTimeUTC (days from the civil date: no year-length rounding)
    systemTimeUTC params ["_y", "_m", "_d", "_h", "_mi", "_s"];
    _y = _y - ([0, 1] select (_m <= 2));
    private _era = floor (_y / 400);
    private _yoe = _y - _era * 400;
    private _doy = floor ((153 * (_m + ([9, -3] select (_m > 2))) + 2) / 5) + _d - 1;
    private _doe = _yoe * 365 + floor (_yoe / 4) - floor (_yoe / 100) + _doy;
    ((_era * 146097 + _doe - 719468) * 86400) + _h * 3600 + _mi * 60 + _s
};
private _maxPlayers = 256;   // player records kept (oldest dropped first)
switch (_mode) do {
    case "enableDefault": {
        // Zeus "save now" in a mission without the Eden module: persistence with the default settings, started
        // mid-mission. Nothing saved before is put back on the players or objects already here (that would roll
        // the running mission back); players who join later get theirs as usual.
        if (!isNil "ACME_persist") exitWith {};
        private _logic = (createGroup [sideLogic, true]) createUnit ["Logic", [0, 0, 0], [], 0, "NONE"];
        _logic setVariable ["ACME_persistLate", true];
        [_logic, [], true] call ACME_fnc_persistModuleInit;
        deleteVehicle _logic;
    };
    case "load": {
        private _data = missionProfileNamespace getVariable [_cfg get "key", []];
        ACME_persistPlayers = createHashMap;
        ACME_persistUnits = createHashMap;
        ACME_persistWorldRows = [];
        ACME_persistFresh = [];
        ACME_persistDevices = [];
        ACME_persistDeviceIndex = [];
        ACME_persistBusy = [];
        ACME_persistSavedAt = 0;
        ACME_persistLateUids = [];
        if (isNil "ACME_persistDeviceCounter") then {ACME_persistDeviceCounter = 0;};
        private _offline = 0;
        if (_data isEqualType [] && {count _data >= 5} && {(_data select 0) isEqualTo 1}) then {
            {
                if (_x isEqualType [] && {count _x >= 6} && {(_x select 0) isEqualType ""} && {(_x select 0) != ""}) then {
                    private _record = +_x;
                    if !((_record select 2) isEqualType "") then {_record set [2, ""];};
                    if !((_record select 3) isEqualType []) then {_record set [3, []];};
                    if !((_record select 4) isEqualType [] && {(_record select 4) isEqualTypeAll ""}) then {_record set [4, []];};
                    if !((_record select 5) isEqualType 0) then {_record set [5, 0];};
                    ACME_persistPlayers set [_record select 0, _record select [0, 6]];
                };
            } forEach ([[], _data select 1] select ((_data select 1) isEqualType []));
            if ((_data select 2) isEqualType []) then {
                ACME_persistWorldRows = (+(_data select 2)) select {
                    _x isEqualType [] && {count _x >= 2} && {(_x select 0) isEqualType ""} && {(_x select 1) isEqualType []} && {count (_x select 1) == 3}
                };
            };
            if ((_data select 3) isEqualType []) then {ACME_persistFresh = +(_data select 3);};
            if ((_data select 4) isEqualType 0 && {finite (_data select 4)}) then {ACME_persistSavedAt = _data select 4;};
            private _devices = _data param [5, []];
            if (_devices isEqualType [] && {_devices isNotEqualTo []} && {[_devices] call ACME_fnc_equipmentWorldSchema}) then {
                ACME_persistDevices = +_devices;
                private _index = _data param [6, []];
                if (_index isEqualType []) then {
                    ACME_persistDeviceIndex = (+_index) select {
                        _x isEqualType [] && {count _x == 3} && {(_x select 0) isEqualType ""} && {(_x select 1) isEqualType ""}
                        && {(_x select 2) isEqualType []} && {count (_x select 2) == 3} && {(_x select 2) isEqualTypeAll 0}
                    };
                };
            };
            private _counter = _data param [7, 0];
            if (_counter isEqualType 0 && {finite _counter} && {_counter >= 0}) then {ACME_persistDeviceCounter = ACME_persistDeviceCounter max floor _counter;};
            if ((_cfg get "ageOffline") && {ACME_persistSavedAt > 0}) then {_offline = ((call _utc) - ACME_persistSavedAt) max 0 min 1e9;};
        };
        // device IDs are never given twice, even when the saved counter was lost
        {
            private _id = _x select 0;
            if ((_id find "acme-dev-") == 0) then {ACME_persistDeviceCounter = ACME_persistDeviceCounter max (parseNumber (_id select [9]));};
        } forEach (ACME_persistDevices param [1, []]);
        ACME_persistOffline = _offline;
        ACME_persistDeviceStatus = ["none"];
        if (_cfg getOrDefault ["late", false]) then {
            // started mid-mission (Zeus): the players already here keep their current state
            ACME_persistLateUids = (allPlayers apply {getPlayerUID _x}) select {_x != ""};
        } else {
            // donor registry first: donor bags must find their donors (refused if the mission already has a registry)
            if ((_cfg get "world") && {(ACME_persistFresh param [1, []]) isNotEqualTo []}) then {[ACME_persistFresh, _offline] call ACME_fnc_freshBloodRestore;};
            if ((_cfg get "world") && {ACME_persistWorldRows isNotEqualTo []}) then {["restoreWorld"] call ACME_fnc_persistServer;};
            // placed devices after the donor registry, once, before players join (their patients come back detached)
            if ((_cfg getOrDefault ["devices", true]) && {(ACME_persistDevices param [1, []]) isNotEqualTo []}) then {
                ["restore", ACME_persistDevices, ACME_persistDeviceIndex] call ACME_fnc_persistDevices;
            };
        };
        if (call ACME_fnc_debugEnabled) then {
            diag_log format ["[ACME PERSIST] loaded %1: %2 players, %3 world rows, %4 devices, offline %5 s", _cfg get "key", count ACME_persistPlayers, count ACME_persistWorldRows, count (ACME_persistDevices param [1, []]), _offline];
        };
    };
    case "restoreWorld": {
        // The objects come back from the mission or from another persistence system, maybe some time after start:
        // look for each saved object (same class, within 1.5 m) every 5 s for 5 minutes. Until then a save keeps
        // the saved row of an object not yet found or not yet put back ("captureWorld").
        ACME_persistWorldPending = ACME_persistWorldRows apply {[_x, false]};
        ACME_persistWorldUsed = [];
        ACME_persistWorldRestoreOpen = true;
        [{
            params ["_args", "_id"];
            _args params ["_until"];
            private _offline = missionNamespace getVariable ["ACME_persistOffline", 0];
            private _pending = missionNamespace getVariable ["ACME_persistWorldPending", []];
            {
                _x params ["_row", "_done"];
                if (!_done) then {
                    _row params ["_type", "_pos", ["_fridge", []], ["_box", []], ["_inv", []], ["_blood", []]];
                    private _obj = ((nearestObjects [ASLToAGL _pos, [_type], 1.5, true]) select {typeOf _x == _type && {!(_x in ACME_persistWorldUsed)}}) param [0, objNull];
                    if (!isNull _obj && {local _obj}) then {
                        private _ok = true;
                        if (_fridge isNotEqualTo []) then {
                            _ok = (_obj getVariable ["ACME_bloodFridge", false]) && {[_obj, _fridge, 0, _offline] call ACME_fnc_bloodFridgeRestore};
                        };
                        if (_ok && {_box isNotEqualTo []}) then {_ok = [_obj, _box, _offline] call ACME_fnc_coolerRestore;};
                        if (_ok && {_inv isNotEqualTo []} && {(_inv param [1, []]) isNotEqualTo []}) then {_ok = [_obj, _inv, createHashMap, _offline] call ACME_fnc_inventoryRestore;};
                        if (_ok && {_blood isNotEqualTo []} && {(_blood param [1, []]) isNotEqualTo []}) then {_ok = [_obj, _blood, _offline] call ACME_fnc_bloodExposureRestore;};
                        if (_ok) then {
                            _x set [1, true];
                            ACME_persistWorldUsed pushBack _obj;
                            ["note", format ["%1 at %2", _type, _pos]] call ACME_fnc_persistServer;
                        };
                    };
                };
            } forEach _pending;
            if (CBA_missionTime > _until || {(_pending findIf {!(_x select 1)}) < 0}) then {
                ACME_persistWorldRestoreOpen = false;
                [_id] call CBA_fnc_removePerFrameHandler;
            };
        }, 5, [CBA_missionTime + 300]] call CBA_fnc_addPerFrameHandler;
    };
    case "start": {
        if (!isNil "ACME_persistServerStarted") exitWith {};
        ACME_persistServerStarted = true;
        ["ACME_persistRecord", {["receive"] + _this call ACME_fnc_persistServer}] call CBA_fnc_addEventHandler;
        ["ACME_persistRequest", {["request"] + _this call ACME_fnc_persistServer}] call CBA_fnc_addEventHandler;
        ["ACME_persistDied", {["died"] + _this call ACME_fnc_persistServer}] call CBA_fnc_addEventHandler;
        ["ACME_persistNote", {["note", _this param [0, ""]] call ACME_fnc_persistServer}] call CBA_fnc_addEventHandler;
        // Zeus: run from the server's own frame, never inside a client's event (the device adapters refuse that)
        ["ACME_persistSaveNow", {
            [{["save"] call ACME_fnc_persistServer; ["report", _this, "saved"] call ACME_fnc_persistServer;}, _this param [0, objNull]] call CBA_fnc_execNextFrame;
        }] call CBA_fnc_addEventHandler;
        ["ACME_persistStatusRequest", {
            [{["report", _this, "status"] call ACME_fnc_persistServer;}, _this param [0, objNull]] call CBA_fnc_execNextFrame;
        }] call CBA_fnc_addEventHandler;
        ["ACME_persistClear", {
            [{["clear"] call ACME_fnc_persistServer; ["report", _this, "cleared"] call ACME_fnc_persistServer;}, _this param [0, objNull]] call CBA_fnc_execNextFrame;
        }] call CBA_fnc_addEventHandler;
        [{["save"] call ACME_fnc_persistServer}, _cfg get "interval"] call CBA_fnc_addPerFrameHandler;
        addMissionEventHandler ["HandleDisconnect", {
            ["saveSoon"] call ACME_fnc_persistServer;
            false
        }];
        addMissionEventHandler ["EntityKilled", {
            params ["_unit"];
            // only the unit that player is actually in: a Zeus remote-controlling an AI reports his UID on it too
            private _uid = getPlayerUID _unit;
            if (_uid != "" && {((missionNamespace getVariable ["ACME_persistUnits", createHashMap]) getOrDefault [_uid, objNull]) isEqualTo _unit}) then {
                ["forget", _uid] call ACME_fnc_persistServer;
            };
        }];
        addMissionEventHandler ["MPEnded", {["save"] call ACME_fnc_persistServer}];
        addMissionEventHandler ["Ended", {["save"] call ACME_fnc_persistServer}];
    };
    case "receive": {
        private _unit = _a;
        if (!(_unit isEqualType objNull) || {isNull _unit} || {!alive _unit}) exitWith {};
        if (isRemoteExecuted && {remoteExecutedOwner != owner _unit}) exitWith {};
        private _uid = getPlayerUID _unit;
        if (_uid == "") exitWith {};
        ACME_persistUnits set [_uid, _unit];
        private _record = ACME_persistPlayers getOrDefault [_uid, [_uid, name _unit, "", [], [], 0]];
        _record set [1, name _unit];
        if (_b isEqualType "" && {_b != ""}) then {_record set [2, _b];};
        if (_c isEqualType [] && {_c isNotEqualTo []} && {(_c findIf {!(_x isEqualType [] && {count _x == 2} && {(_x select 0) isEqualType ""})}) < 0}) then {_record set [3, _c];};
        if (_d isEqualType []) then {_record set [4, (_d select {_x isEqualType ""}) select [0, 512]];};
        _record set [5, call _utc];
        ACME_persistPlayers set [_uid, _record];
    };
    case "request": {
        private _unit = _a;
        if (!(_unit isEqualType objNull) || {isNull _unit}) exitWith {};
        private _uid = getPlayerUID _unit;
        if (_uid == "") exitWith {["ACME_persistApply", [[]], _unit] call CBA_fnc_targetEvent;};
        ACME_persistUnits set [_uid, _unit];
        // his durable ID here (devices and clinical references decode on the server too)
        [_unit, "acme-player-" + _uid] call ACME_fnc_persistBind;
        private _late = ACME_persistLateUids find _uid;
        private _record = if (_late >= 0) then {ACME_persistLateUids deleteAt _late; []} else {+(ACME_persistPlayers getOrDefault [_uid, []])};
        ["ACME_persistApply", [_record], _unit] call CBA_fnc_targetEvent;
    };
    case "died": {
        // from the player's own machine: his unit died (also before his saved state was put back on him)
        private _unit = _a;
        // (no owner check: the corpse may already belong to the server when this arrives)
        if (!(_unit isEqualType objNull) || {!(_b isEqualType "")} || {_b == ""}) exitWith {};
        private _known = ACME_persistUnits getOrDefault [_b, objNull];
        if (isNull _known || {_known isEqualTo _unit} || {!alive _known}) then {["forget", _b] call ACME_fnc_persistServer;};
    };
    case "forget": {
        if (_a isEqualType "" && {_a != ""}) then {ACME_persistPlayers deleteAt _a;};
    };
    case "saveSoon": {
        if (missionNamespace getVariable ["ACME_persistSaveQueued", false]) exitWith {};
        ACME_persistSaveQueued = true;
        [{ACME_persistSaveQueued = false; ["save"] call ACME_fnc_persistServer;}, [], 2] call CBA_fnc_waitAndExecute;
    };
    case "save": {
        private _busy = [];
        if (_cfg get "world") then {
            ACME_persistWorldRows = ["captureWorld"] call ACME_fnc_persistServer;
            private _kept = missionNamespace getVariable ["ACME_persistWorldBusy", 0];
            if (_kept > 0) then {_busy pushBack format ["%1 fridge/cooler/container part%2", _kept, ["s", ""] select (_kept == 1)];};
            private _fresh = [] call ACME_fnc_freshBloodSnapshot;
            if (_fresh isEqualType [] && {_fresh isNotEqualTo []}) then {ACME_persistFresh = _fresh;} else {_busy pushBack "donor registry";};
        };
        if (_cfg getOrDefault ["devices", true]) then {
            private _status = (missionNamespace getVariable ["ACME_persistDeviceStatus", ["none"]]) select 0;
            private _capture = ["capture"] call ACME_fnc_persistDevices;
            if (_capture isEqualTo []) then {_busy pushBack "placed devices";} else {
                // while the saved devices are being put back, or when they could not be and nothing new was placed
                // since, an empty live world does not replace them
                private _empty = ((_capture select 0) select 1) isEqualTo [];
                if !(_status == "waiting" || {_status == "failed" && {_empty}}) then {
                    ACME_persistDevices = [_capture select 0, []] select _empty;
                    ACME_persistDeviceIndex = _capture select 1;
                };
            };
        };
        if (count ACME_persistPlayers > _maxPlayers) then {
            // the oldest records go first (the store stays bounded on a long-running server)
            private _order = (values ACME_persistPlayers) apply {[_x select 5, _x select 0]};
            _order sort false;
            {ACME_persistPlayers deleteAt (_x select 1);} forEach (_order select [_maxPlayers]);
        };
        private _now = call _utc;
        missionProfileNamespace setVariable [_cfg get "key",
            [1, +(values ACME_persistPlayers), +ACME_persistWorldRows, +ACME_persistFresh, _now,
             +ACME_persistDevices, +ACME_persistDeviceIndex, ACME_persistDeviceCounter]];
        saveMissionProfileNamespace;
        ACME_persistBusy = _busy;
        ACME_persistSavedAt = _now;
        if (call ACME_fnc_debugEnabled) then {
            diag_log format ["[ACME PERSIST] saved %1: %2 players, %3 world rows, %4 devices, busy (kept previous) %5", _cfg get "key", count ACME_persistPlayers, count ACME_persistWorldRows, count (ACME_persistDevices param [1, []]), _busy];
        };
    };
    case "captureWorld": {
        // every ACME object with saveable state; a part that is busy right now keeps what was saved for it before,
        // and so does an object the start-of-mission restore has not found or put back yet
        private _boxClasses = ["ACME_BloodCoolerBox_CSWB1U", "ACME_BloodCoolerBox_CSWB2U", "ACME_BloodCoolerBox_CSWB4U"];
        private _holders = (allMissionObjects "All") select {
            private _t = toLowerANSI typeOf _x;
            ((_t find "acme_") == 0 || {_x getVariable ["ACME_bloodFridge", false]})
            && {_t != "acme_removedcarriercargo"}
            && {(_x getVariable ["ACME_eq_kind", ""]) == ""}
            && {!(_x isKindOf "CAManBase")}
            && {alive _x || {_x getVariable ["ACME_bloodFridge", false]}}
            && {(_x getVariable ["ACME_bloodFridge", false]) || {(typeOf _x) in _boxClasses} || {maxLoad _x > 0}}
        };
        private _old = +ACME_persistWorldRows;
        private _pendingLeft = [];
        if (missionNamespace getVariable ["ACME_persistWorldRestoreOpen", false]) then {
            _pendingLeft = ((missionNamespace getVariable ["ACME_persistWorldPending", []]) select {!(_x select 1)}) apply {+(_x select 0)};
        };
        private _used = missionNamespace getVariable ["ACME_persistWorldUsed", []];
        private _rows = [];
        private _kept = 0;
        {
            private _obj = _x;
            private _type = typeOf _obj;
            private _pos = getPosASL _obj;
            if (_pendingLeft isNotEqualTo [] && {!(_obj in _used)}) then {
                private _i = _pendingLeft findIf {(_x select 0) == _type && {((_x select 1) vectorDistance _pos) < 1.5}};
                if (_i >= 0) then {_rows pushBack (_pendingLeft deleteAt _i); _obj = objNull;};
            };
            if (isNull _obj) then {continue;};
            private _prev = (_old select {(_x select 0) == _type && {((_x select 1) vectorDistance _pos) < 1.5}}) param [0, []];
            private _isFridge = _obj getVariable ["ACME_bloodFridge", false];
            private _isBox = _type in _boxClasses;
            private _fridge = if (_isFridge) then {[_obj] call ACME_fnc_bloodFridgeSnapshot} else {[]};
            private _box = if (_isBox) then {[_obj, "box"] call ACME_fnc_coolerSnapshot} else {[]};
            // a container not local here (a player is moving it) cannot be read now: busy, not empty
            private _inv = if (maxLoad _obj > 0) then {if (local _obj) then {[_obj] call ACME_fnc_inventorySnapshot} else {[]}} else {[1, []]};
            private _blood = if (maxLoad _obj > 0) then {[_obj] call ACME_fnc_bloodExposureSnapshot} else {[1, []]};
            if (_fridge isEqualTo [] && {_isFridge}) then {_fridge = _prev param [2, []]; _kept = _kept + 1;};
            if (_box isEqualTo [] && {_isBox}) then {_box = _prev param [3, []]; _kept = _kept + 1;};
            if (_inv isEqualTo []) then {_inv = _prev param [4, [1, []]]; _kept = _kept + 1;};
            if (_blood isEqualTo []) then {_blood = _prev param [5, [1, []]]; _kept = _kept + 1;};
            if (_fridge isNotEqualTo [] || {_box isNotEqualTo []} || {(_inv param [1, []]) isNotEqualTo []} || {(_blood param [1, []]) isNotEqualTo []}) then {
                _rows pushBack [_type, _pos, _fridge, _box, _inv, _blood];
            };
        } forEach _holders;
        // saved objects that have not come back yet (another persistence system may still be placing them)
        _rows append _pendingLeft;
        ACME_persistWorldBusy = _kept;
        _rows
    };
    case "report": {
        // [curator, "saved" | "status" | "cleared"]: a short summary for the Zeus who asked
        private _to = _a;
        if (!(_to isEqualType objNull) || {isNull _to}) exitWith {};
        private _rows = missionNamespace getVariable ["ACME_persistWorldRows", []];
        private _fridges = {(_x param [2, []]) isNotEqualTo []} count _rows;
        private _boxes = {(_x param [3, []]) isNotEqualTo []} count _rows;
        private _containers = {((_x param [2, []]) isEqualTo []) && {(_x param [3, []]) isEqualTo []}} count _rows;
        private _devices = count ((missionNamespace getVariable ["ACME_persistDevices", []]) param [1, []]);
        private _status = missionNamespace getVariable ["ACME_persistDeviceStatus", ["none"]];
        private _deviceText = "Placed devices: off";
        if (_cfg getOrDefault ["devices", true]) then {
            private _s = switch (_status select 0) do {
                case "waiting": {", being put back"};
                case "failed": {", could not be put back this mission"};
                case "restored": {
                    private _t = format [", %1 put back at start", _status param [1, 0]];
                    if ((_status param [2, 0]) > 0) then {_t = _t + format [" (%1 ventilator(s) left out: patient not here)", _status select 2];};
                    _t
                };
                default {""};
            };
            _deviceText = format ["Placed devices: %1%2", _devices, _s];
        };
        private _what = switch (_b) do {case "saved": {"saved"}; case "cleared": {"saved state forgotten"}; default {"status"};};
        private _lines = [
            format ["ACME persistence: %1", _what],
            format ["Players saved: %1", count (missionNamespace getVariable ["ACME_persistPlayers", createHashMap])],
            format ["Blood fridges: %1   Cooler boxes: %2   Containers: %3", _fridges, _boxes, _containers],
            _deviceText,
            format ["Donor registry: %1", ["no", "yes"] select (((missionNamespace getVariable ["ACME_persistFresh", []]) param [1, []]) isNotEqualTo [])]
        ];
        private _busy = missionNamespace getVariable ["ACME_persistBusy", []];
        if (_busy isNotEqualTo [] && {_b != "cleared"}) then {_lines pushBack ("Busy, kept the previous save: " + (_busy joinString ", "));};
        private _at = missionNamespace getVariable ["ACME_persistSavedAt", 0];
        if (_b == "status") then {
            _lines pushBack (if (_at > 0) then {format ["Last save: %1 s ago (save name %2)", round (((call _utc) - _at) max 0), _cfg get "key"]} else {"Not saved yet"});
        };
        ["ACME_persistReport", [_lines], _to] call CBA_fnc_targetEvent;
    };
    case "clear": {
        ACME_persistPlayers = createHashMap;
        ACME_persistWorldRows = [];
        ACME_persistFresh = [];
        ACME_persistDevices = [];
        ACME_persistDeviceIndex = [];
        ACME_persistBusy = [];
        ACME_persistSavedAt = 0;
        // nothing saved before is put back any more (a pending start-of-mission restore stops)
        ACME_persistWorldPending = [];
        ACME_persistWorldRestoreOpen = false;
        if (((missionNamespace getVariable ["ACME_persistDeviceStatus", ["none"]]) select 0) == "waiting") then {ACME_persistDeviceStatus = ["none"];};
        missionProfileNamespace setVariable [_cfg get "key", nil];
        saveMissionProfileNamespace;
    };
    case "note": {
        if (call ACME_fnc_debugEnabled) then {diag_log format ["[ACME PERSIST] restored %1", _a];};
    };
};
