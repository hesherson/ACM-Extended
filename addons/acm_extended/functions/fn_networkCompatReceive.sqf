/* Handshake-only events. Never dispatch medical actions or alter treatment permissions. */
params ["_op", ["_args", []]];
switch (_op) do {
    case "probe": {
        if (isServer) exitWith {};
        _args params [["_challenge", "", [""]]];
        if (_challenge == "" || {count _challenge > 100}) exitWith {};
        private _parts = _challenge splitString ":";
        if (count _parts != 3 || {(_parts select 0) != "server"} || {(_parts select 1) != str clientOwner}) exitWith {};
        private _serial = parseNumber (_parts select 2);
        if (!finite _serial || {_serial <= 0} || {_serial != floor _serial} || {str _serial != (_parts select 2)}
            || {_serial < (missionNamespace getVariable ["ACME_networkCompatChallengeSerial", 0])}) exitWith {};
        private _nonce = missionNamespace getVariable ["ACME_networkCompatNonce", ""];
        if (_nonce == "") exitWith {};
        private _sameChallenge = _challenge == (missionNamespace getVariable ["ACME_networkCompatChallenge", ""]);
        if (_sameChallenge && {(missionNamespace getVariable ["ACME_networkCompatStatus", "pending"]) in ["ok", "incompatible"]}) exitWith {};
        if (_sameChallenge && {(diag_tickTime - (missionNamespace getVariable ["ACME_networkCompatProbeReplyAt", -10])) < 2}) exitWith {};
        // Probe retries resend the same transaction; they never create another retry chain.
        ACME_networkCompatChallenge = _challenge;
        ACME_networkCompatChallengeSerial = _serial;
        ACME_networkCompatProbeReplyAt = diag_tickTime;
        ["ACME_networkCompatHello", [clientOwner, _nonce, _challenge,
            missionNamespace getVariable ["ACME_networkCompatLocalManifest", []]]] call CBA_fnc_serverEvent;
    };
    case "hello": {
        if (!isServer) exitWith {};
        _args params [["_owner", -1, [0]], ["_nonce", "", [""]], ["_challenge", "", [""]], ["_manifest", [], [[]]]];
        if (!finite _owner || {_owner <= 2} || {_owner != floor _owner}
            || {_nonce == ""} || {count _nonce > 100} || {count _manifest > 6}) exitWith {};
        if (_owner in (missionNamespace getVariable ["ACME_networkCompatRetiredOwners", []])) exitWith {};
        private _peers = missionNamespace getVariable ["ACME_networkCompatPeers", createHashMap];
        private _key = str _owner;
        private _row = _peers getOrDefault [_key, []];
        // Only an initial hello can discover a peer; an obsolete challenged packet cannot recreate one.
        if (_row isEqualTo [] && {_challenge != ""}) exitWith {};
        if (_row isEqualTo []) then {
            ["seed", _owner] call ACME_fnc_networkCompatPeer;
            _peers = missionNamespace getVariable ["ACME_networkCompatPeers", createHashMap];
            _row = _peers getOrDefault [_key, []];
        };
        if (_row isEqualTo [] || {(_row select 3) == "disconnected"}) exitWith {};
        if (_challenge != (_row select 0)) exitWith {
            // A fresh client hello can precede PlayerConnected delivery or miss the first server probe.
            if (_challenge == "") then {["ACME_networkCompatProbe", [_row select 0], _owner] call CBA_fnc_ownerEvent;};
        };
        if ((_row select 1) != "" && {(_row select 1) != _nonce}) exitWith {};
        private _serverManifest = missionNamespace getVariable ["ACME_networkCompatLocalManifest", []];
        private _issues = [_serverManifest, _manifest] call ACME_fnc_networkCompatCompare;
        if !((_manifest param [4, "unknown", [""]]) in ["client", "HC"]) then {_issues pushBack "Peer role must be client or HC";};
        private _status = ["incompatible", "ok"] select (_issues isEqualTo []);
        _row set [1, _nonce];
        _row set [2, _manifest param [4, "unknown", [""]]];
        _row set [3, _status];
        _row set [4, _issues];
        _row set [5, _manifest];
        _peers set [_key, _row];
        ACME_networkCompatPeers = _peers;
        ["peer:" + _challenge, _status, _issues, format ["machine %1 %2", _owner, _row select 2]] call ACME_fnc_networkCompatNotice;
        ["ACME_networkCompatReply", [_nonce, _challenge, _serverManifest], _owner] call CBA_fnc_ownerEvent;
    };
    case "reply": {
        if (isServer) exitWith {};
        _args params [["_nonce", "", [""]], ["_challenge", "", [""]], ["_serverManifest", [], [[]]]];
        if (_nonce == "" || {_nonce != (missionNamespace getVariable ["ACME_networkCompatNonce", ""])}
            || {_challenge == ""} || {_challenge != (missionNamespace getVariable ["ACME_networkCompatChallenge", ""])}) exitWith {};
        private _localManifest = missionNamespace getVariable ["ACME_networkCompatLocalManifest", []];
        private _issues = [_serverManifest, _localManifest] call ACME_fnc_networkCompatCompare;
        if ((_serverManifest param [4, "unknown", [""]]) != "server") then {_issues pushBack "Reply did not identify a server manifest";};
        ACME_networkCompatServerManifest = _serverManifest;
        ACME_networkCompatServerBuild = _serverManifest param [2, "unverified", [""]];
        ACME_networkCompatStatus = ["incompatible", "ok"] select (_issues isEqualTo []);
        ACME_networkCompatIssues = _issues;
        [_nonce, ACME_networkCompatStatus, _issues, "server verification", true] call ACME_fnc_networkCompatNotice;
    };
};
