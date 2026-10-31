/* B39 compile-time override of ACM_core_fnc_resetVariables.
   Native ACM called getUp unconditionally during reset, so a unit that happened to be in a lying animation
   at initialization/respawn could play UnconsciousOutProne and visibly roll before control was returned.
   Reset is state cleanup, not a physical Get Up action: clear the lying state directly and never animate. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient) exitWith {};

_patient setVariable ["ACM_core_InstantDeath", false];
_patient setVariable ["ACM_core_KnockOut_State", false];
_patient setVariable ["ACM_core_TimeOfDeath", nil, true];
_patient setVariable ["ACM_core_WasTreated", false, true];
_patient setVariable ["ACM_core_WasWounded", false, true];
_patient setVariable ["ACM_core_CarryAssist_State", false, true];

if (isPlayer _patient) then {
    _patient setVariable ["ACM_core_TreatmentText_Providers", []];
};

_patient setVariable ["ACM_core_CriticalVitals_State", false, true];
_patient setVariable ["ACM_core_CriticalVitals_Passed", false, true];

[_patient] call ACM_core_fnc_generateTargetVitals;

// Critical B39 change: reset the bookkeeping only. Do not call ACM_core_fnc_getUp here.
_patient setVariable ["ACM_core_Lying_State", false, true];
_patient setVariable ["ACM_core_Sitting_State", false, true];

// A reset/respawn also invalidates any local provider-roll theatre left from the previous unit state.
if (local _patient) then {
    if (!isNil "ACME_fnc_aiProtectionSync") then {[_patient, "reset"] call ACME_fnc_aiProtectionSync;};
    _patient setVariable ["ACME_rollProviderActive", false];
    _patient setVariable ["ACME_rollProviderToken", ""];
};
