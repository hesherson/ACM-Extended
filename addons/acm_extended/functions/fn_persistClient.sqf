/* B393: client side of the ACME Persistence module (fn_persistModuleInit.sqf). [mode, args...]
 *  "start"    once per client: ask the server for this player's saved state; capturing starts only after that
 *             answer is applied, so a fresh joiner never overwrites his own saved state with a healthy one
 *  "apply"    [record]: put the saved state back on the player: his medical state at once, the state of his ACME
 *             items once the ACME items the save lists are on him again (from his slot or from another persistence
 *             system; up to 5 minutes, then with what is there). [] = nothing saved
 *  "capture"  send this player's state to the server (every few seconds, and soon after he is hurt or treated)
 *  "soon"     one capture a moment from now (a burst of wounds or treatments: one capture)
 * Only ACME's state: the loadout itself is the slot's or another persistence system's. With the module's
 * "Give back missing ACME items" on, ACME items he had and does not have now are given back first. When another
 * persistence system loads his kit with ACME's item state in it (a CBA extended loadout), that state is kept and
 * this module does not put its own over it. */
params [["_mode", "", [""]], ["_a", []]];
if (!hasInterface) exitWith {};
private _cfg = missionNamespace getVariable ["ACME_persist", createHashMap];
if (count _cfg == 0) exitWith {};
// the ACME items a unit carries, one entry per item
private _acmeItems = {
    params ["_unit"];
    ((items _unit) + (assignedItems _unit) + (magazines _unit)) select {((toLowerANSI _x) find "acme_") == 0}
};
switch (_mode) do {
    case "start": {
        if (!isNil "ACME_persistClientStarted") exitWith {};
        ACME_persistClientStarted = true;
        ACME_persistMedReady = false;
        ACME_persistItemsReady = false;
        ACME_persistCapturing = -1;
        // a player who dies is not brought back hurt, also when he dies before his saved state is back on him
        ["CAManBase", "Killed", {
            params ["_unit"];
            if (_unit isEqualTo player) then {["ACME_persistDied", [_unit, getPlayerUID _unit]] call CBA_fnc_serverEvent;};
        }] call CBA_fnc_addClassEventHandler;
        [{!isNull player && {alive player} && {local player} && {time > 2} && {(getPlayerUID player) != ""}}, {
            ["ACME_persistRequest", [player]] call CBA_fnc_serverEvent;
            // the regular capture of this player (sends once his saved state is back on him)
            [{["capture"] call ACME_fnc_persistClient;}, (missionNamespace getVariable ["ACME_persist", createHashMap]) getOrDefault ["capture", 30]] call CBA_fnc_addPerFrameHandler;
            // and soon after he is hurt, treated, or treats someone (his ACME items change)
            ["ace_medical_woundReceived", {
                params ["_unit"];
                if (_unit isEqualTo player) then {["soon"] call ACME_fnc_persistClient;};
            }] call CBA_fnc_addEventHandler;
            ["ace_treatmentSucceded", {
                params ["_medic", "_patient"];
                if (_medic isEqualTo player || {_patient isEqualTo player}) then {["soon"] call ACME_fnc_persistClient;};
            }] call CBA_fnc_addEventHandler;
        }] call CBA_fnc_waitUntilAndExecute;
    };
    case "soon": {
        if (missionNamespace getVariable ["ACME_persistSoon", false]) exitWith {};
        ACME_persistSoon = true;
        [{ACME_persistSoon = false; ["capture"] call ACME_fnc_persistClient;}, [], 3] call CBA_fnc_waitAndExecute;
    };
    case "apply": {
        if (!isNil "ACME_persistApplying") exitWith {};   // one answer per client
        ACME_persistApplying = true;
        private _record = _a;
        private _unit = player;
        if !(_record isEqualType [] && {count _record >= 6} && {!isNull _unit} && {alive _unit}) exitWith {
            ACME_persistMedReady = true; ACME_persistItemsReady = true;
        };
        _record params ["", "", ["_json", ""], ["_meta", []], ["_items", []]];
        // his durable ID on his own machine, before anything that refers to him is decoded here
        [_unit, "acme-player-" + getPlayerUID _unit] call ACME_fnc_persistBind;
        // medical state now, not after the kit (deserializeState itself waits for ACE medical to start on him)
        private _medical = (_cfg getOrDefault ["medical", true]) && {_json isEqualType ""} && {_json != ""};
        if (_medical) then {[_unit, _json, 0] call ace_medical_fnc_deserializeState;};
        // capture his medical state only once it is on him (a capture before would save him healthy)
        [{(_this getVariable ["ace_medical_initialized", false]) || {!alive _this}}, {
            [{ACME_persistMedReady = true;}, [], 2] call CBA_fnc_waitAndExecute;
        }, _unit, 60, {ACME_persistMedReady = true;}] call CBA_fnc_waitUntilAndExecute;
        private _restore = (_cfg getOrDefault ["items", true]) && {_meta isEqualType []} && {_meta isNotEqualTo []};
        private _give = (_cfg getOrDefault ["restoreItems", false]) && {_items isEqualType []} && {_items isNotEqualTo []};
        if (!_restore && {!_give}) exitWith {
            ACME_persistItemsReady = true;
            if (_medical) then {["Your ACME medical state was restored.", 2, _unit] call ace_common_fnc_displayTextStructured;};
        };
        // what the save says he carried: lower-case class -> [count, class]
        private _expected = createHashMap;
        {
            if (_x isEqualType "") then {
                private _k = toLowerANSI _x;
                (_expected getOrDefault [_k, [0, _x]]) params ["_n", "_class"];
                _expected set [_k, [_n + 1, _class]];
            };
        } forEach ([[], _items] select (_items isEqualType []));
        private _now = diag_tickTime;
        private _state = createHashMapFromArray [
            ["unit", _unit], ["meta", [[], _meta] select _restore], ["expected", _expected], ["give", _give], ["medical", _medical],
            ["started", _now], ["deadline", _now + 300], ["stableSince", _now], ["sig", ""], ["phase", "wait"],
            ["epoch", -1], ["attempts", 0], ["watchUntil", 0], ["settledAt", -1], ["noted", false], ["count", _acmeItems]
        ];
        [{
            params ["_s", "_pfh"];
            private _unit = _s get "unit";
            private _now = diag_tickTime;
            private _finish = {
                [_pfh] call CBA_fnc_removePerFrameHandler;
                ACME_persistItemsReady = true;
            };
            // died or became another unit (respawn, team switch): the old save is not his kit any more
            if (isNull _unit || {!alive _unit} || {_unit isNotEqualTo player}) exitWith {call _finish;};
            // another persistence system loaded his kit with ACME's item state in it: that state stands
            // (ACME_persistOtherKit: fn_registerPersistenceRuntime.sqf, the unit such a loadout was last set on)
            if ((missionNamespace getVariable ["ACME_persistOtherKit", objNull]) isEqualTo _unit) exitWith {
                if (call ACME_fnc_debugEnabled) then {["ACME_persistNote", [format ["nothing over %1's ACME item state: another persistence system loaded it", name _unit]]] call CBA_fnc_serverEvent;};
                call _finish;
            };
            private _kit = _unit getVariable ["ACME_equipmentKitEpoch", 0];
            private _list = ([_unit] call (_s get "count")) apply {toLowerANSI _x};
            _list sort true;
            private _sig = str [_kit, _list];
            if (_sig != (_s get "sig")) then {_s set ["sig", _sig]; _s set ["stableSince", _now];};
            private _stable = (_now - (_s get "stableSince")) >= 3 && {(_now - (_s get "started")) >= 3};
            if ((_s get "phase") == "wait") then {
                private _have = createHashMap;
                {_have set [_x, (_have getOrDefault [_x, 0]) + 1];} forEach _list;
                private _expected = _s get "expected";
                private _missing = (keys _expected) select {(_have getOrDefault [_x, 0]) < ((_expected get _x) select 0)};
                private _go = (_now > (_s get "deadline"))
                    || {_stable && {_missing isEqualTo [] || {_s get "give"}}}
                    || {_stable && {count _expected == 0} && {(_now - (_s get "started")) >= 5}};
                if (!_go) exitWith {};
                if (_s get "give") then {
                    // what he had of ACME's and has not got now (never onto the ground: what does not fit stays out)
                    {
                        ((_s get "expected") get _x) params ["_n", "_class"];
                        for "_i" from 1 to (_n - (_have getOrDefault [_x, 0])) do {
                            if (isClass (configFile >> "CfgMagazines" >> _class)) then {_unit addMagazine _class;} else {_unit addItem _class;};
                        };
                    } forEach _missing;
                } else {
                    if (_missing isNotEqualTo [] && {!(_s get "noted")} && {call ACME_fnc_debugEnabled}) then {
                        _s set ["noted", true];
                        ["ACME_persistNote", [format ["%1's ACME item state after %2 s without all his saved ACME items (missing %3)", name _unit, round (_now - (_s get "started")), _missing apply {format ["%1 x%2", (_expected get _x) select 1, ((_expected get _x) select 0) - (_have getOrDefault [_x, 0])]}]]] call CBA_fnc_serverEvent;
                    };
                };
                if ((_s get "meta") isNotEqualTo []) then {
                    [_unit, createHashMapFromArray (_s get "meta"), 120] call ACME_fnc_persistenceRestoreExtended;
                };
                if ((_s get "attempts") == 0) then {
                    [["Your ACME items were restored.", "Your ACME medical state and items were restored."] select (_s get "medical"), 2, _unit] call ace_common_fnc_displayTextStructured;
                };
                _s set ["attempts", (_s get "attempts") + 1];
                _s set ["epoch", _unit getVariable ["ACME_equipmentKitEpoch", 0]];
                _s set ["phase", "watch"];
                _s set ["watchUntil", _now + 120];
                _s set ["settledAt", -1];
            } else {
                // his kit was replaced right after (a respawn template, another persistence system without ACME's
                // item state): once more on the new kit, at most three times
                if (_kit != (_s get "epoch") && {(_s get "attempts") < 3} && {(_s get "meta") isNotEqualTo []}) exitWith {
                    _s set ["phase", "wait"];
                    _s set ["deadline", _now + 60];
                    _s set ["give", false];
                };
                if ((_s get "settledAt") < 0 && {(_s get "meta") isEqualTo [] || {_unit getVariable ["ACME_persistenceLastRestoreOK", false]}}) then {_s set ["settledAt", _now];};
                if (_now > (_s get "watchUntil") || {(_s get "settledAt") >= 0 && {(_now - (_s get "settledAt")) >= 15}}) then {call _finish;};
            };
        }, 1, _state] call CBA_fnc_addPerFrameHandler;
    };
    case "capture": {
        private _unit = player;
        if (isNull _unit || {!alive _unit} || {!local _unit}) exitWith {};
        private _med = missionNamespace getVariable ["ACME_persistMedReady", false];
        private _kit = missionNamespace getVariable ["ACME_persistItemsReady", false];
        if (!_med && {!_kit}) exitWith {};
        // one capture in flight at a time (the item checkpoint can take a few seconds)
        private _inFlight = missionNamespace getVariable ["ACME_persistCapturing", -1];
        if (_inFlight >= 0 && {(diag_tickTime - _inFlight) < 30}) exitWith {};
        private _json = "";
        if (_med && {_cfg getOrDefault ["medical", true]}) then {
            _json = [_unit] call ace_medical_fnc_serializeState;
            if !(_json isEqualType "") then {_json = "";};
        };
        // the ACME items he carries (always: the restore waits for them); false while his own are not back yet
        private _items = false;
        if (_kit) then {_items = ([_unit] call _acmeItems) select [0, 512];};
        private _sent = false;
        if (_kit && {_cfg getOrDefault ["items", true]}) then {
            // the state of his ACME items: an owner-local checkpoint that waits until nothing is in flight
            ACME_persistCapturing = diag_tickTime;
            private _request = [_unit, {
                params ["_ok", "_extended", "_args"];
                _args params ["_unit", "_json", "_items"];
                ACME_persistCapturing = -1;
                // he died or is another unit now: this capture is not his state any more
                if (isNull _unit || {!alive _unit} || {_unit isNotEqualTo player}) exitWith {};
                private _meta = [];
                if (_ok && {_extended isEqualType []} && {count _extended == 2} && {(_extended select 1) isEqualType createHashMap}) then {
                    private _map = _extended select 1;
                    _meta = (keys _map) apply {[_x, _map get _x]};
                };
                ["ACME_persistRecord", [_unit, _json, _meta, _items]] call CBA_fnc_serverEvent;
            }, [_unit, _json, _items], 10] call ACME_fnc_persistenceLocalCheckpoint;
            _sent = _request isEqualType 0 && {_request >= 0};
            if (!_sent) then {ACME_persistCapturing = -1;};
        };
        if (!_sent) then {["ACME_persistRecord", [_unit, _json, [], _items]] call CBA_fnc_serverEvent;};
    };
};
