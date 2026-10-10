/*
 * Phase 23 runtime ownership: TBI/CPP and Cheyne-Stokes runtime tick registration.
 *
 * Extracted intact from ACME_fnc_postInit. The helper is invoked synchronously at the
 * original registration point so CBA handler/PFH order is unchanged.
 */

[{call ACME_fnc_tbiHandle}, 0.25, []] call CBA_fnc_addPerFrameHandler;
[{call ACME_fnc_cheyneStokesTick}, 0.10, []] call CBA_fnc_addPerFrameHandler;
if (hasInterface) then {
    [] call ACME_fnc_installRmbCancelGuard;
    ["ace_medicalMenuOpened", {
        params ["_medic", "_patient", "_display"];
        [_display] call ACME_fnc_installRmbCancelGuard;
    }] call CBA_fnc_addEventHandler;
};
