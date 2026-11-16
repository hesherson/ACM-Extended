// Coalesce loadout bursts without ageing inventory a second time.
if (!isServer || {!(["enabled"] call ACME_fnc_bloodTiming)}
    || {missionNamespace getVariable ["ACME_coldChainNudgePending", false]}) exitWith {};
ACME_coldChainNudgePending = true;
[{
    ACME_coldChainNudgePending = false;
    [0] call ACME_fnc_bloodColdChainTick;
}, [], 0.5] call CBA_fnc_waitAndExecute;
