if (missionNamespace getVariable ["ACME_NA2_chestInstalled", false]) exitWith {};
ACME_NA2_chestInstalled = true;
ACME_CS_pending = createHashMap;
ACME_CS_sessions = createHashMap;
ACME_CS_editResults = createHashMap;
["ACME_CS_session", { if (isServer) then { isNil { _this call ACME_fnc_chestSealSession; }; }; }] call CBA_fnc_addEventHandler;
["ACME_CS_edit", { if (isServer) then { isNil { _this call ACME_fnc_chestSealEdit; }; }; }] call CBA_fnc_addEventHandler;
["ACME_CS_reset", { if (isServer) then { isNil { _this call ACME_fnc_chestSealReset; }; }; }] call CBA_fnc_addEventHandler;
["ACME_CS_ack", { _this call ACME_fnc_chestSealAck; }] call CBA_fnc_addEventHandler;
["ACME_CS_ackSeen", {
    if (!isServer) exitWith {};
    params ["_id", "_client"];
    private _result = ACME_CS_editResults getOrDefault [_id, []];
    if (count _result >= 6 && {(_result select 4) == _client}) then { _result set [5, true]; };
}] call CBA_fnc_addEventHandler;
["ACME_CS_snapshot", { _this call ACME_fnc_chestSealSyncUI; }] call CBA_fnc_addEventHandler;
["ACME_CS_roster", {
    params ["_patient", "_viewers"];
    if (!hasInterface || {isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}
        || {(uiNamespace getVariable ["ACME_CS_Patient", objNull]) != _patient}) exitWith {};
    private _old = uiNamespace getVariable ["ACME_CS_presenceTargets", []];
    uiNamespace setVariable ["ACME_CS_presenceTargets", _viewers];
    private _new = _viewers - _old - [uiNamespace getVariable ["ACME_CS_presenceViewer", player]];
    private _last = uiNamespace getVariable ["ACME_CS_presencePacket", []];
    if (count _new > 0 && {count _last >= 6}
        && {diag_tickTime - (uiNamespace getVariable ["ACME_CS_presenceLastT", -1]) <= (missionNamespace getVariable ["ACME_CS_presenceStale", 0.5])}) then {
        // A stationary provider's current gesture is sent on join without requiring movement.
        ["ACME_CS_presence", _last, _new] call CBA_fnc_targetEvent;
    };
}] call CBA_fnc_addEventHandler;
if (hasInterface) then {
    [{
        private _now = diag_tickTime;
        if (!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])) then {
            if (_now >= (uiNamespace getVariable ["ACME_CS_sessionNextPing", 0])) then {
                uiNamespace setVariable ["ACME_CS_sessionNextPing", _now + 5];
                ["ACME_CS_session", [uiNamespace getVariable ["ACME_CS_Patient", objNull],
                    uiNamespace getVariable ["ACME_CS_presenceViewer", player], "ping"]] call CBA_fnc_serverEvent;
            };
        };
        {
            private _entry = ACME_CS_pending get _x;
            if (_now - (_entry select 2) >= 2) then {
                _entry set [2, _now];
                // Same ID/payload retries are idempotent. B72 intentionally has no cross-machine mission-clock
                // expiry: the server returns the cached outcome or evaluates the still-current epoch/revision.
                ["ACME_CS_edit", _entry select 0] call CBA_fnc_serverEvent;
            };
        } forEach (keys ACME_CS_pending);
    }, 1, []] call CBA_fnc_addPerFrameHandler;
};
if (isServer) then {
    [{
        private _players = allPlayers;
        private _owners = _players apply {owner _x};
        {
            private _key = _x;
            (ACME_CS_sessions get _key) params ["_patient", "_members"];
            private _keep = _members select {
                !isNull (_x select 0) && {alive (_x select 0)} && {(_x select 0) in _players}
                    && {!((_x select 0) getVariable ["ACE_isUnconscious", false])}
                    && {CBA_missionTime - (_x select 1) <= 15}
            };
            // A provider can disappear without an onUnload (death, respawn or disconnect).
            // Release that viewer only. Patient death does not evict the remaining providers.
            {
                private _token = _x param [2, ""];
                if (_token != "") then {[_patient, "chestSealPatientEnd", [_patient, _token]] call ACME_fnc_ownerDispatch;};
            } forEach (_members - _keep);
            if (isNull _patient || {count _keep == 0}) then { ACME_CS_sessions deleteAt _key; }
            else {
                if (count _keep != count _members) then {
                    ACME_CS_sessions set [_key, [_patient, _keep]];
                    private _viewers = _keep apply {_x select 0};
                    ["ACME_CS_roster", [_patient, _viewers], _viewers] call CBA_fnc_targetEvent;
                };
                // A newly acquired penetrating wound becomes shared while the UI remains open.
                if (count (_patient getVariable ["ACME_CS_penetratingWounds", []]) > (_patient getVariable ["ACME_CS_processedPenetratingCount", 0])) then {
                    [_patient] call ACME_fnc_chestSealGenHoles;
                };
            };
        } forEach (keys ACME_CS_sessions);
        {
            private _r = ACME_CS_editResults get _x;
            private _age = CBA_missionTime - (_r select 0);
            // Never turn an accepted but unacknowledged action into a refund after timeout.
            // Keep connected unconfirmed outcomes until the client has actually seen them.
            if ((_age > 60 && {_r select 5}) || {_age > 120 && {!((_r select 4) in _owners)}}) then {
                ACME_CS_editResults deleteAt _x;
            };
        } forEach (keys ACME_CS_editResults);
    }, 1, []] call CBA_fnc_addPerFrameHandler;
};
