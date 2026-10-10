/* Three hello attempts at 3/10/25 seconds, then one terminal timeout at 45 seconds. No recurring worker. */
params ["_nonce", ["_attempt", 0]];
if (isServer || {_nonce != (missionNamespace getVariable ["ACME_networkCompatNonce", ""])}) exitWith {};
if ((missionNamespace getVariable ["ACME_networkCompatStatus", "pending"]) in ["ok", "incompatible", "unavailable"]) exitWith {};
if (_attempt >= 3) exitWith {
    ACME_networkCompatStatus = "unavailable";
    ACME_networkCompatIssues = ["No server handshake reply within 45 seconds; missing/older handshake or unreachable server (build not verified)"];
    [_nonce, ACME_networkCompatStatus, ACME_networkCompatIssues, "server verification", true] call ACME_fnc_networkCompatNotice;
};
ACME_networkCompatAttempts = _attempt + 1;
["ACME_networkCompatHello", [clientOwner, _nonce,
    missionNamespace getVariable ["ACME_networkCompatChallenge", ""],
    missionNamespace getVariable ["ACME_networkCompatLocalManifest", []]]] call CBA_fnc_serverEvent;
[{_this call ACME_fnc_networkCompatRetry;}, [_nonce, _attempt + 1], [7, 15, 20] select _attempt] call CBA_fnc_waitAndExecute;
