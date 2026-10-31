/* One RPT entry per status signature; at most one visible terminal warning per endpoint/connection. */
params ["_key", "_status", ["_issues", []], ["_label", "this machine"], ["_visible", false]];
private _notices = missionNamespace getVariable ["ACME_networkCompatNotices", createHashMap];
private _signature = str [_status, _issues];
if ((_notices getOrDefault [_key, ""]) == _signature) exitWith {};
_notices set [_key, _signature];
missionNamespace setVariable ["ACME_networkCompatNotices", _notices];
diag_log format ["[ACME NETWORK COMPAT] %1: %2 | %3", _label, _status, _issues joinString " | "];
private _warned = missionNamespace getVariable ["ACME_networkCompatWarned", []];
if (_visible && {hasInterface} && {_status in ["incompatible", "unavailable"]} && {!(_key in _warned)}) then {
    _warned pushBack _key;
    missionNamespace setVariable ["ACME_networkCompatWarned", _warned];
    private _summary = if (_status == "unavailable") then {
        "Server build could not be verified: no compatible handshake reply. Check the complete server/client installation."
    } else {format ["Build/component mismatch: %1", _issues param [0, "see RPT"]]};
    [format ["ACM Extended: %1 Update every fork PBO on server, clients and headless clients; restart Arma. Medical actions remain enabled. See NETWORK COMPAT in the RPT/debug status.", _summary], 12]
        call ace_common_fnc_displayTextStructured;
};
