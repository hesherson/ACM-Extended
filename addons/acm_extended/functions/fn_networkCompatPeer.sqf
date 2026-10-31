/* Server connection lifecycle. Row: [challenge, clientNonce, role, status, issues, manifest]. */
params ["_op", "_owner", ["_challenge", ""], ["_attempt", 0], ["_role", "unknown"]];
if (!isServer || {!(_owner isEqualType 0)} || {!finite _owner} || {_owner <= 2} || {_owner != floor _owner}) exitWith {};
private _peers = missionNamespace getVariable ["ACME_networkCompatPeers", createHashMap];
private _key = str _owner;
private _row = _peers getOrDefault [_key, []];
if (_op in ["leave", "join"] && {!(_row isEqualTo [])}) then {
    private _notices = missionNamespace getVariable ["ACME_networkCompatNotices", createHashMap];
    _notices deleteAt ("peer:" + (_row select 0));
};
if (_op == "leave") exitWith {
    _peers deleteAt _key;
    // Suppress delayed old hellos after deletion without retaining identity or large manifests.
    private _retired = missionNamespace getVariable ["ACME_networkCompatRetiredOwners", []];
    _retired pushBackUnique _owner;
    if (count _retired > 64) then {_retired deleteAt 0;};
    ACME_networkCompatRetiredOwners = _retired;
};
if (_op in ["join", "seed"]) exitWith {
    if (_op == "seed" && {!(_row isEqualTo [])}) exitWith {};
    private _retired = missionNamespace getVariable ["ACME_networkCompatRetiredOwners", []];
    if (_op == "seed" && {_owner in _retired}) exitWith {};
    ACME_networkCompatRetiredOwners = _retired - [_owner];
    private _serial = (missionNamespace getVariable ["ACME_networkCompatPeerSerial", 0]) + 1;
    ACME_networkCompatPeerSerial = _serial;
    private _newChallenge = format ["server:%1:%2", _owner, _serial];
    _peers set [_key, [_newChallenge, "", _role, "pending", [], []]];
    ACME_networkCompatPeers = _peers;
    [{_this call ACME_fnc_networkCompatPeer;}, ["probe", _owner, _newChallenge, 0], 3] call CBA_fnc_waitAndExecute;
};
if (_op != "probe" || {_row isEqualTo []} || {(_row select 0) != _challenge}
    || {(_row select 3) != "pending"}) exitWith {};
if (_attempt >= 3) exitWith {
    _row set [3, "unavailable"];
    private _issues = ["No handshake within 45 seconds; peer may be missing ACME, running an older build, or still loading. Its build is unverified."];
    _row set [4, _issues];
    _peers set [_key, _row];
    ["peer:" + _challenge, "unavailable", _issues, format ["machine %1 %2", _owner, _row select 2]] call ACME_fnc_networkCompatNotice;
};
["ACME_networkCompatProbe", [_challenge], _owner] call CBA_fnc_ownerEvent;
[{_this call ACME_fnc_networkCompatPeer;}, ["probe", _owner, _challenge, _attempt + 1], [7, 15, 20] select _attempt] call CBA_fnc_waitAndExecute;
