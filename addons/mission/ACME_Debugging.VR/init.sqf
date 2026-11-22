if (isMultiplayer) exitWith {};

[] spawn {
    waitUntil {sleep 0.1; !isNull player};
    missionNamespace setVariable ["ACME_debug_forceOverlay", true];
    [] call ACMEQA_fnc_setupServer;
    [player, false] call ACMEQA_fnc_setupPlayer;
};
