/* B207 diagnostic build/protocol handshake; installed on server, players and headless clients. */
if (missionNamespace getVariable ["ACME_networkCompatInstalled", false]) exitWith {};
ACME_networkCompatInstalled = true;
ACME_networkCompatLocalManifest = [] call ACME_fnc_networkCompatManifest;
ACME_networkCompatLocalIssues = [ACME_networkCompatLocalManifest, ACME_networkCompatLocalManifest] call ACME_fnc_networkCompatCompare;
ACME_networkCompatLocalStatus = ["incompatible", "ok"] select (ACME_networkCompatLocalIssues isEqualTo []);
ACME_networkCompatServerManifest = [];
ACME_networkCompatServerBuild = "unverified";
ACME_networkCompatStatus = "pending";
ACME_networkCompatIssues = [];
ACME_networkCompatAttempts = 0;
ACME_networkCompatPeers = createHashMap;
ACME_networkCompatRetiredOwners = [];
ACME_networkCompatNotices = createHashMap;
ACME_networkCompatWarned = [];
ACME_networkCompatChallenge = "";
ACME_networkCompatChallengeSerial = 0;
ACME_networkCompatNonce = format ["client:%1:%2", clientOwner, diag_tickTime];
["ACME_networkCompatHello", {["hello", _this] call ACME_fnc_networkCompatReceive;}] call CBA_fnc_addEventHandler;
["ACME_networkCompatProbe", {["probe", _this] call ACME_fnc_networkCompatReceive;}] call CBA_fnc_addEventHandler;
["ACME_networkCompatReply", {["reply", _this] call ACME_fnc_networkCompatReceive;}] call CBA_fnc_addEventHandler;
if (isServer) then {
    ACME_networkCompatServerManifest = ACME_networkCompatLocalManifest;
    ACME_networkCompatServerBuild = ACME_buildBatch;
    ACME_networkCompatStatus = ACME_networkCompatLocalStatus;
    ACME_networkCompatIssues = ACME_networkCompatLocalIssues;
    ACME_networkCompatPeers set [str clientOwner, ["server", "server", "server", ACME_networkCompatStatus,
        ACME_networkCompatIssues, ACME_networkCompatLocalManifest]];
    ["local-server", ACME_networkCompatStatus, ACME_networkCompatIssues, "server installation", true] call ACME_fnc_networkCompatNotice;
    addMissionEventHandler ["PlayerConnected", {
        params ["", "", "", "", "_owner"];
        ["join", _owner] call ACME_fnc_networkCompatPeer;
    }];
    addMissionEventHandler ["PlayerDisconnected", {
        params ["", "", "", "", "_owner"];
        ["leave", _owner] call ACME_fnc_networkCompatPeer;
    }];
    // PostInit may miss initial connection events. One finite seed includes HCs and never repeats as a world scan.
    [{
        private _machines = +allPlayers;
        {_machines pushBackUnique _x;} forEach (entities "HeadlessClient_F");
        {["seed", owner _x, "", 0, if (_x isKindOf "HeadlessClient_F") then {"HC"} else {"client"}] call ACME_fnc_networkCompatPeer;} forEach _machines;
    }, [], 3] call CBA_fnc_waitAndExecute;
} else {
    [{_this call ACME_fnc_networkCompatRetry;}, [ACME_networkCompatNonce, 0], 3] call CBA_fnc_waitAndExecute;
};
