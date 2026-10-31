/* Opt-in, machine-local B207 validation sampler. No registration occurs until start.
 * ["start", 120, optionalLocalProvider] / ["stop"] / ["report"] / ["sample"] call ACME_fnc_networkDiagnostics.
 * Helper counters are publication/suppression REQUESTS, never packets, bytes or delivery statistics.
 * Samples contain no unit names, UIDs, patient references or claim tokens.
 */
params [
    ["_operation", "report", [""]],
    ["_limit", 120, [0]],
    ["_provider", objNull, [objNull]],
    ["_generation", -1, [0]]
];
private _state = missionNamespace getVariable ["ACME_networkDiagnostics_state", createHashMap];
private _active = _state getOrDefault ["active", false];
private _now = diag_tickTime;
private _counterNames = ["ACME_net_sent", "ACME_net_saved", "ACME_net_nonFiniteSuppressed"];
private _snapshotCounters = {
    _counterNames apply {
        private _snapshot = createHashMap;
        private _values = missionNamespace getVariable [_x, createHashMap];
        if (_values isEqualType createHashMap) then {
            {
                private _value = _values get _x;
                if (_value isEqualType 0 && {finite _value} && {_value >= 0}) then {_snapshot set [_x, _value];};
            } forEach (keys _values);
        };
        _snapshot
    }
};

switch (toLowerANSI _operation) do {
    case "start": {
        // Repeated start must not replace the worker, erase samples, or lose the original counting flag.
        if (_active) exitWith {["report"] call ACME_fnc_networkDiagnostics};
        if !(finite _limit) then {_limit = 120;};
        _limit = (floor _limit max 1) min 600;
        if (isNull _provider && {hasInterface}) then {_provider = missionNamespace getVariable ["ACE_player", objNull];};
        if (!isNull _provider && {!local _provider}) then {_provider = objNull;};
        private _serial = 1 + (_state getOrDefault ["generation", 0]);
        private _role = if (isServer) then {if (hasInterface) then {"listen_server"} else {"dedicated_server"}}
            else {if (hasInterface) then {"player_client"} else {"headless_client"}};
        _state = createHashMapFromArray [
            ["active", true], ["generation", _serial], ["limit", _limit], ["interval", 1],
            ["startedAt", _now], ["stoppedAt", -1], ["nextAt", _now + 1], ["lastAt", _now],
            ["stopReason", ""], ["samples", []], ["provider", _provider],
            ["countWasDefined", !isNil {missionNamespace getVariable "ACME_net_count"}],
            ["countWasEnabled", missionNamespace getVariable ["ACME_net_count", false]],
            ["previousCounters", call _snapshotCounters],
            ["machine", [_role, clientOwner, missionNamespace getVariable ["ACME_infusion_version", "unknown"],
                missionNamespace getVariable ["ACME_buildBatch", "unknown"],
                missionNamespace getVariable ["ACME_networkAuditRevision", "unknown"]]]
        ];
        missionNamespace setVariable ["ACME_networkDiagnostics_state", _state];
        missionNamespace setVariable ["ACME_net_count", true];
        private _handle = [{
            params ["_args"];
            _args params ["_serial"];
            ["sample", 120, objNull, _serial] call ACME_fnc_networkDiagnostics;
        }, 1, [_serial]] call CBA_fnc_addPerFrameHandler;
        _state set ["handle", _handle];
        ["report"] call ACME_fnc_networkDiagnostics
    };
    case "stop": {
        if (_active) then {
            private _handle = _state getOrDefault ["handle", -1];
            if (_handle >= 0) then {[_handle] call CBA_fnc_removePerFrameHandler;};
            _state set ["active", false];
            _state set ["handle", -1];
            _state set ["stoppedAt", _now];
            _state set ["provider", objNull];
            if ((_state getOrDefault ["stopReason", ""]) == "") then {_state set ["stopReason", "manual"];};
            // Preserve an independently enabled counter session; never reset its accumulated maps.
            if (_state getOrDefault ["countWasDefined", false]) then {
                missionNamespace setVariable ["ACME_net_count", _state getOrDefault ["countWasEnabled", false]];
            } else {missionNamespace setVariable ["ACME_net_count", nil];};
            _state set ["previousCounters", []];
        };
        ["report"] call ACME_fnc_networkDiagnostics
    };
    case "sample": {
        if (!_active || {_generation >= 0 && {_generation != (_state getOrDefault ["generation", -1])}}
            || {_now < (_state getOrDefault ["nextAt", _now + 1])}) exitWith {[]};
        // Manual samples obey the same one-second minimum as the PFH. Sparse frames produce one real sample,
        // never a synthetic catch-up burst. Auto-stop releases the sole worker at the configured cap.
        _state set ["nextAt", _now + 1];
        private _current = call _snapshotCounters;
        private _previous = _state get "previousCounters";
        private _deltas = [];
        private _fieldDeltas = [];
        for "_i" from 0 to 2 do {
            private _new = _current select _i;
            private _old = _previous select _i;
            private _delta = 0;
            private _reset = false;
            private _fields = createHashMap;
            {
                private _value = _new get _x;
                private _prior = _old getOrDefault [_x, 0];
                private _fieldReset = _value < _prior;
                private _fieldDelta = if (_fieldReset) then {_value} else {_value - _prior};
                if (_fieldReset) then {_reset = true;};
                _delta = _delta + _fieldDelta;
                if (_fieldDelta > 0 || {_fieldReset}) then {_fields set [_x, [_fieldDelta, _fieldReset]];};
            } forEach (keys _new);
            {
                if !(_x in _new) then {
                    _reset = true;
                    _fields set [_x, [0, true]];
                };
            } forEach (keys _old);
            _deltas pushBack [_delta, _reset];
            _fieldDeltas pushBack _fields;
        };
        _state set ["previousCounters", _current];

        private _registries = [
            "ACME_clinical_ownedUnits", "ACME_clinical_activePatients", "ACME_circ_activePatients",
            "ACME_coag_activePatients", "ACME_infusion_activePatients", "ACME_tbi_activePatients",
            "ACME_nrb_activePatients", "ACME_hpmk_activePatients", "ACME_cs_activePatients",
            "ACME_autoBP_patients", "ACME_rhythm_activePatients", "ACME_vent_serverPatients", "ACME_hpmk_serverPatients",
            "ACME_preox_activePatients", "ACME_aspiration_activePatients", "ACME_shock_activePatients",
            "ACME_rhythmThreshold_activePatients"
        ] apply {
            private _list = missionNamespace getVariable [_x, []];
            [_x, if (_list isEqualType []) then {count _list} else {-1}]
        };
        private _fps = diag_fps;
        if !(finite _fps && {_fps > 0}) then {_fps = -1;};
        private _frameDelta = diag_deltaTime;
        if !(finite _frameDelta && {_frameDelta >= 0}) then {_frameDelta = -1;};
        private _dp = ["not_local", -1, false];
        private _hang = ["not_local", -1, -1, -1];
        private _medic = _state getOrDefault ["provider", objNull];
        if (!isNull _medic && {local _medic}) then {
            private _pending = _medic getVariable ["ACME_DP_ClaimPending", []];
            private _dpPending = _pending isEqualType [] && {count _pending >= 4};
            private _dpActive = _medic getVariable ["ACME_DP_Active", false];
            private _dpAt = _medic getVariable ["ACME_DP_ClaimRequestedAt", -1];
            private _dpAge = if (_dpPending && {_dpAt isEqualType 0} && {finite _dpAt} && {_dpAt >= 0}) then {(_now - _dpAt) max 0} else {-1};
            _dp = [if (_dpPending) then {"pending"} else {if (_dpActive) then {"active"} else {"idle"}}, _dpAge, _dpActive];
            private _hangActive = _medic getVariable ["ACME_hang_Active", false];
            private _claimed = _medic getVariable ["ACME_hang_Claimed", false];
            private _sequence = _medic getVariable ["ACME_hang_ClaimSequence", -1];
            private _ackSequence = _medic getVariable ["ACME_hang_ClaimAckSequence", -1];
            private _hangPending = _hangActive && {!_claimed || {_sequence > _ackSequence}};
            private _hangAt = _medic getVariable ["ACME_hang_ClaimRequestedAt", -1];
            private _hangAge = if (_hangPending && {_hangAt isEqualType 0} && {finite _hangAt} && {_hangAt >= 0}) then {(serverTime - _hangAt) max 0} else {-1};
            _hang = [if (!_hangActive) then {"idle"} else {if (!_claimed) then {"pending"} else {if (_hangPending) then {"renewing"} else {"active"}}},
                _hangAge, _sequence, _ackSequence];
        };
        private _compatibility = [
            missionNamespace getVariable ["ACME_networkCompatLocalStatus", "unavailable"],
            missionNamespace getVariable ["ACME_networkCompatStatus", "unavailable"],
            missionNamespace getVariable ["ACME_networkCompatServerBuild", "unverified"],
            missionNamespace getVariable ["ACME_networkCompatAttempts", 0],
            count (missionNamespace getVariable ["ACME_networkCompatLocalIssues", []]),
            count (missionNamespace getVariable ["ACME_networkCompatIssues", []]),
            count (missionNamespace getVariable ["ACME_networkCompatPeers", createHashMap])
        ];
        private _sample = createHashMapFromArray [
            ["at", _now], ["elapsed", _now - (_state get "lastAt")], ["fps", _fps], ["frameDelta", _frameDelta],
            ["helperRequestDeltas", _deltas], ["helperRequestFields", _fieldDeltas],
            ["counterEnabled", missionNamespace getVariable ["ACME_net_count", false]],
            ["registrySizes", _registries], ["directPressure", _dp], ["hangBag", _hang], ["compatibility", _compatibility]
        ];
        _state set ["lastAt", _now];
        private _samples = _state get "samples";
        _samples pushBack _sample;
        if (count _samples >= (_state get "limit")) then {
            _state set ["stopReason", "sample_limit"];
            ["stop"] call ACME_fnc_networkDiagnostics;
        };
        _sample
    };
    case "report": {
        createHashMapFromArray [
            ["active", _active], ["interval", 1], ["limit", _state getOrDefault ["limit", 120]],
            ["startedAt", _state getOrDefault ["startedAt", -1]], ["stoppedAt", _state getOrDefault ["stoppedAt", -1]],
            ["stopReason", _state getOrDefault ["stopReason", "not_started"]], ["machine", +(_state getOrDefault ["machine", []])],
            ["counterMeaning", "helper requests only; NOT wire packets, bytes, delivery or total network traffic"],
            ["fieldDeltaMeaning", "per counter map: variable -> [request delta, counter reset]"],
            ["counterOrder", ["publicationRequests", "suppressedRequests", "nonFiniteRejected"]],
            ["samples", +(_state getOrDefault ["samples", []])]
        ]
    };
    default {createHashMapFromArray [["error", "Use start, stop, report or sample"]]};
}
