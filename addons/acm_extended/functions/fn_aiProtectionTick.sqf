/* Called by the existing owner lifecycle sweep. Work is limited to registered patients, never allUnits/groups. */
if !(missionNamespace getVariable ["ACME_aiProtection_ready", false]) then {[] call ACME_fnc_aiProtectionInit;};
{
    [_x] call ACME_fnc_aiProtectionSync;
} forEach +(missionNamespace getVariable ["ACME_aiProtection_candidates", []]);
