"""Run production compatibility manifests, comparisons and finite CBA lifecycles.

Config metadata, server/client identity, CBA delivery and UI are engine fixtures.
Packets and scheduled callbacks are delivered explicitly, including stale replies.
The VM lacks finite; its engine predicate is adapted for these finite fixtures.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import adapt, execute, read


def adapted(source):
    source = re.sub(r'\bfinite (_\w+)', r'(\1 isEqualType 0)', source)
    for old, new in (("isServer", "_server"), ("hasInterface", "_interface"),
                     ("clientOwner", "_clientId"), ("diag_tickTime", "_clock"),
                     ("allPlayers", "_playerObjects")):
        source = re.sub(r"\b" + old + r"\b", new, source)
    source = source.replace('entities "HeadlessClient_F"', '[]')
    source = source.replace('private _cfg = configFile >> "CfgPatches" >> _x;', 'private _cfg = _x;')
    source = source.replace('isClass _cfg', '!(_cfg in _missingComponents)')
    source = source.replace('getText (_cfg >> "acmeBuildBatch")', '["build", _cfg] call _configRead')
    source = source.replace('getNumber (_cfg >> "acmeNetworkProtocol")', '1')
    source = source.replace('getText (_cfg >> "acmeComponent")', '["identity", _cfg] call _configRead')
    source = re.sub(r'(_\w+) getOrDefault \[(_\w+), (\[\]|"")\]', r'[\1, \2, \3] call _getDefault', source)
    # Mission EH registration is an engine boundary; callbacks themselves remain real code.
    tokens = lex(source); pairs = matching(tokens); edits = []
    for i, token in enumerate(tokens[:-1]):
        if token.value == "addMissionEventHandler" and tokens[i + 1].value == "[":
            end = tokens[pairs[i + 1]].offset + 1
            edits.append((token.offset, end, source[tokens[i + 1].offset:end] + " call _missionEH"))
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    return adapt(source)


def setup(server=False, interface=True, client=11, initialize=True):
    code = f'private _server={str(server).lower()}; private _interface={str(interface).lower()}; private _clientId={client};\n'
    code += r'''
        private _clock = 10; private _jobs = []; private _messages = [];
        private _visibleNotices = []; private _registered = []; private _missionHandlers = [];
        private _playerObjects = []; private _missingComponents = []; private _staleComponents = [];
        private _getDefault = {params ["_map", "_key", "_default"]; if (_key in _map) then {_map get _key} else {_default}};
        private _configRead = {
            params ["_field", "_component"];
            if (_field == "identity") exitWith {toLower (_component select [4, 100])};
            if (_component in _staleComponents) then {"B206"} else {"B207"}
        };
        ACME_infusion_version = "1.2.4.1"; ACME_buildBatch = "B207"; ACME_networkProtocol = 1;
        CBA_fnc_waitAndExecute = {_jobs pushBack _this;};
        CBA_fnc_serverEvent = {_messages pushBack ["server", _this];};
        CBA_fnc_ownerEvent = {_messages pushBack ["owner", _this];};
        CBA_fnc_addEventHandler = {_registered pushBack _this;};
        ace_common_fnc_displayTextStructured = {_visibleNotices pushBack _this;};
        private _missionEH = {_missionHandlers pushBack _this; count _missionHandlers};
        private _drain = {
            private _steps = 0;
            while {count _jobs > 0 && {_steps < 30}} do {
                private _job = _jobs deleteAt 0;
                _clock = _clock + (_job select 2);
                (_job select 1) call (_job select 0);
                _steps = _steps + 1;
            };
            [_steps < 30, "unbounded callback/retry chain"] call _check;
        };
    '''
    for name in ("networkCompatManifest", "networkCompatCompare", "networkCompatNotice", "networkCompatRetry", "networkCompatPeer", "networkCompatReceive", "networkCompatInit"):
        code += 'ACME_fnc_' + name + '={' + adapted(read(name)) + '};\n'
    code += r'''
        private _savedServer = _server; private _savedInterface = _interface;
        _server = true;
        private _serverManifest = [] call ACME_fnc_networkCompatManifest;
        _server = false; _interface = true;
        private _clientManifest = [] call ACME_fnc_networkCompatManifest;
        _interface = false;
        private _hcManifest = [] call ACME_fnc_networkCompatManifest;
        _server = _savedServer; _interface = _savedInterface;
    '''
    if initialize:
        code += '[] call ACME_fnc_networkCompatInit;\n'
    return code


def test_manifest_reads_all_fourteen_components_and_headless_role():
    execute(setup(interface=False, initialize=False) + r'''
        _staleComponents = ["ACM_core"]; _missingComponents = ["ACM_itemtext"];
        private _m = [] call ACME_fnc_networkCompatManifest;
        [(_m select 4) == "HC" && {count (_m select 5) == 14}, "HC or component manifest omitted"] call _check;
        private _issues = [_m, _m] call ACME_fnc_networkCompatCompare;
        [count _issues == 2, "partial installation was not identified"] call _check;
        [(_issues findIf {(_x find "ACM_core") >= 0}) >= 0, "stale PBO not identified"] call _check;
        [(_issues findIf {(_x find "ACM_itemtext") >= 0}) >= 0, "missing PBO not identified"] call _check;
    ''')


def test_matching_server_client_and_headless_manifests_compare_without_role_mismatch():
    execute(setup(initialize=False) + r'''
        [([_serverManifest, _clientManifest] call ACME_fnc_networkCompatCompare) isEqualTo [], "matching player rejected"] call _check;
        [([_serverManifest, _hcManifest] call ACME_fnc_networkCompatCompare) isEqualTo [], "matching HC rejected"] call _check;
    ''')


@pytest.mark.parametrize("mutation", [
    '_clientManifest set [2,"B206"];',
    '_clientManifest set [3,2];',
    '_clientManifest set [3,1.5];',
    '_clientManifest set [3,"1"];',
    '_clientManifest set [1,"1.2.3.1"];',
    '((_clientManifest select 5) select 0) set [4,"core"];',
    '(_clientManifest select 5) deleteAt 1;',
    '_clientManifest = [99];',
])
def test_build_protocol_public_version_identity_and_malformed_differences_are_explicit(mutation):
    execute(setup(initialize=False) + mutation + r'''
        [count ([_serverManifest, _clientManifest] call ACME_fnc_networkCompatCompare) > 0, "mismatch accepted"] call _check;
    ''')


def test_server_records_matching_headless_peer_and_targets_reply_only_to_that_machine():
    execute(setup(server=True, interface=False, client=2) + r'''
        ["join", 11, "", 0, "HC"] call ACME_fnc_networkCompatPeer;
        private _challenge = (ACME_networkCompatPeers get "11") select 0;
        ["hello", [11, "hc-session", _challenge, _hcManifest]] call ACME_fnc_networkCompatReceive;
        private _row = ACME_networkCompatPeers get "11";
        [(_row select 2) == "HC" && {(_row select 3) == "ok"}, "HC handshake was skipped"] call _check;
        [((_messages select 0) select 1) select 2 == 11, "server reply addressed wrong machine"] call _check;
        private _before = count _messages; call _drain;
        [count _messages == _before, "acknowledged peer kept receiving probes"] call _check;
        [ACME_networkCompatStatus == "ok", "peer overwrote server local status"] call _check;
    ''')


def test_server_local_mixed_installation_remains_incompatible_after_peer_reply():
    execute(setup(server=True, interface=False, client=2, initialize=False) + r'''
        _staleComponents = ["ACM_core"];
        [] call ACME_fnc_networkCompatInit;
        ["join", 11] call ACME_fnc_networkCompatPeer;
        private _challenge = (ACME_networkCompatPeers get "11") select 0;
        ["hello", [11, "current-client", _challenge, _clientManifest]] call ACME_fnc_networkCompatReceive;
        [ACME_networkCompatStatus == "incompatible", "peer cleared mixed server installation status"] call _check;
        [ACME_networkCompatIssues isEqualTo ACME_networkCompatLocalIssues, "peer replaced server's own issues"] call _check;
        [count ACME_networkCompatIssues == 1, "server missing its stale component diagnostic"] call _check;
    ''')


def test_malformed_machine_identifiers_and_noninteger_protocol_are_rejected():
    execute(setup(server=True, interface=False, client=2) + r'''
        ["join", 11.5] call ACME_fnc_networkCompatPeer;
        ["hello", [11.5, "bad-owner", "", _clientManifest]] call ACME_fnc_networkCompatReceive;
        [!("11.5" in ACME_networkCompatPeers) && {_messages isEqualTo []}, "fractional machine identifier accepted"] call _check;
        _clientManifest set [3, 1.5];
        [count ([_clientManifest, _clientManifest] call ACME_fnc_networkCompatCompare) == 1, "self-matching invalid protocol accepted"] call _check;
        _server = false; _clientId = 11;
        { ["probe", [_x]] call ACME_fnc_networkCompatReceive; } forEach ["server:11x:1", "server:11.0:1", "server:11:1.5", "server:11:1x"];
        [_messages isEqualTo [] && {ACME_networkCompatChallenge == ""}, "malformed challenge accepted"] call _check;
    ''')


def test_client_accepts_only_current_nonce_and_challenge_then_stops_retrying():
    execute(setup() + r'''
        ["probe", ["server:11:2"]] call ACME_fnc_networkCompatReceive;
        ["reply", ["other-client", "server:11:2", _serverManifest]] call ACME_fnc_networkCompatReceive;
        [ACME_networkCompatStatus == "pending", "another client's reply was accepted"] call _check;
        ["reply", [ACME_networkCompatNonce, "server:11:1", _serverManifest]] call ACME_fnc_networkCompatReceive;
        [ACME_networkCompatStatus == "pending", "old connection reply was accepted"] call _check;
        ["reply", [ACME_networkCompatNonce, "server:11:2", _serverManifest]] call ACME_fnc_networkCompatReceive;
        [ACME_networkCompatStatus == "ok" && {ACME_networkCompatServerBuild == "B207"}, "valid server reply rejected"] call _check;
        private _before = count _messages;
        for "_i" from 1 to 20 do {["probe", ["server:11:2"]] call ACME_fnc_networkCompatReceive;};
        call _drain;
        [count _messages == _before, "successful handshake kept sending traffic"] call _check;
    ''')


def test_no_server_has_three_attempts_one_terminal_warning_and_no_recurring_jobs():
    execute(setup() + r'''
        [] call ACME_fnc_networkCompatInit;
        [count _registered == 3 && {count _jobs == 1}, "init duplicated handlers or retry chain"] call _check;
        call _drain;
        [ACME_networkCompatStatus == "unavailable", "silent server was called compatible"] call _check;
        [count _messages == 3 && {ACME_networkCompatAttempts == 3}, "server retries were not bounded to three"] call _check;
        [count _visibleNotices == 1 && {_jobs isEqualTo []}, "timeout repeated warnings or kept scheduling"] call _check;
        [ACME_networkCompatNonce, 3] call ACME_fnc_networkCompatRetry;
        [count _messages == 3 && {count _visibleNotices == 1}, "terminal callback restarted traffic"] call _check;
    ''')


def test_missing_peer_times_out_once_and_late_reply_can_resolve_unverified_status():
    execute(setup(server=True, interface=False, client=2) + r'''
        ["join", 11] call ACME_fnc_networkCompatPeer;
        private _challenge = (ACME_networkCompatPeers get "11") select 0;
        call _drain;
        [count _messages == 3, "missing peer probes not bounded"] call _check;
        [((ACME_networkCompatPeers get "11") select 3) == "unavailable", "missing peer not marked unverified"] call _check;
        ["hello", [11, "late-jip", _challenge, _clientManifest]] call ACME_fnc_networkCompatReceive;
        [((ACME_networkCompatPeers get "11") select 3) == "ok", "slow JIP could not recover after timeout"] call _check;
        [count _messages == 4 && {_jobs isEqualTo []}, "late reply started recurring work"] call _check;
    ''')


def test_disconnect_and_reconnect_invalidate_old_callbacks_packets_and_remove_old_row():
    execute(setup(server=True, interface=False, client=2) + r'''
        ["join", 11] call ACME_fnc_networkCompatPeer;
        private _old = (ACME_networkCompatPeers get "11") select 0;
        ["hello", [11, "old-client", _old, _clientManifest]] call ACME_fnc_networkCompatReceive;
        ["leave", 11] call ACME_fnc_networkCompatPeer;
        [!("11" in ACME_networkCompatPeers), "disconnected full manifest retained"] call _check;
        [!(("peer:" + _old) in ACME_networkCompatNotices), "disconnected notice row retained"] call _check;
        ["hello", [11, "old-client", _old, _clientManifest]] call ACME_fnc_networkCompatReceive;
        [!("11" in ACME_networkCompatPeers), "late hello resurrected disconnected peer"] call _check;
        ["join", 11] call ACME_fnc_networkCompatPeer;
        private _new = (ACME_networkCompatPeers get "11") select 0;
        ["probe", 11, _old, 3] call ACME_fnc_networkCompatPeer;
        ["hello", [11, "old-client", _old, _clientManifest]] call ACME_fnc_networkCompatReceive;
        [((ACME_networkCompatPeers get "11") select 3) == "pending", "old callback corrupted replacement connection"] call _check;
        ["hello", [11, "new-client", _new, _clientManifest]] call ACME_fnc_networkCompatReceive;
        [((ACME_networkCompatPeers get "11") select 1) == "new-client", "new reconnect not acknowledged"] call _check;
        for "_id" from 12 to 100 do {["leave", _id] call ACME_fnc_networkCompatPeer;};
        [count ACME_networkCompatRetiredOwners <= 64, "disconnect tombstones grew without bound"] call _check;
    ''')


def test_duplicate_or_old_probes_do_not_create_more_retry_chains():
    execute(setup(interface=False) + r'''
        ["probe", ["server:11:3"]] call ACME_fnc_networkCompatReceive;
        for "_i" from 1 to 20 do {["probe", ["server:11:3"]] call ACME_fnc_networkCompatReceive;};
        ["probe", ["server:11:2"]] call ACME_fnc_networkCompatReceive;
        ["probe", ["server:12:4"]] call ACME_fnc_networkCompatReceive;
        [count _messages == 1 && {count _jobs == 1}, "duplicate/foreign probes created a retry storm"] call _check;
        [ACME_networkCompatChallenge == "server:11:3", "stale probe replaced current connection"] call _check;
        ["reply", [ACME_networkCompatNonce, "server:11:3", _serverManifest]] call ACME_fnc_networkCompatReceive;
        [ACME_networkCompatStatus == "ok" && {_visibleNotices isEqualTo []}, "HC handshake required UI"] call _check;
    ''')


def test_old_challenged_hello_cannot_recreate_peer_after_tombstone_eviction():
    execute(setup(server=True, interface=False, client=2) + r'''
        ["join", 11] call ACME_fnc_networkCompatPeer;
        private _old = (ACME_networkCompatPeers get "11") select 0;
        ["leave", 11] call ACME_fnc_networkCompatPeer;
        for "_id" from 12 to 76 do {["leave", _id] call ACME_fnc_networkCompatPeer;};
        [!(11 in ACME_networkCompatRetiredOwners), "fixture did not evict old tombstone"] call _check;
        private _before = count _jobs;
        ["hello", [11, "old-client", _old, _clientManifest]] call ACME_fnc_networkCompatReceive;
        [!("11" in ACME_networkCompatPeers) && {count _jobs == _before} && {_messages isEqualTo []}, "obsolete hello created phantom peer or work"] call _check;
        ["hello", [11, "fresh-client", "", _clientManifest]] call ACME_fnc_networkCompatReceive;
        ["11" in ACME_networkCompatPeers && {count _jobs == _before + 1} && {count _messages == 1}, "initial hello could not discover a fresh peer"] call _check;
    ''')


def test_incompatibility_is_visible_once_and_does_not_mutate_treatment_state():
    execute(setup() + r'''
        _patient setVariable ["ACME_DP_Active", true];
        ["probe", ["server:11:1"]] call ACME_fnc_networkCompatReceive;
        _serverManifest set [2, "B206"];
        for "_i" from 1 to 3 do {
            ["reply", [ACME_networkCompatNonce, "server:11:1", _serverManifest]] call ACME_fnc_networkCompatReceive;
        };
        [ACME_networkCompatStatus == "incompatible" && {count _visibleNotices == 1}, "mismatch not visible once"] call _check;
        [_patient getVariable "ACME_DP_Active", "handshake changed medical actions"] call _check;
        private _before = count _messages; call _drain;
        [count _messages == _before, "incompatible result kept retrying"] call _check;
    ''')
