// CfgFunctions owns these functions and has already compiled them before postInit.
// Compiling them again here attempts to overwrite final functions on every mission.
// Keep deferred runtime registration; its existing guard prevents duplicate handlers.
[{ call ACME_fnc_expansionRegisterRuntime; }, [], 0.75] call CBA_fnc_waitAndExecute;
