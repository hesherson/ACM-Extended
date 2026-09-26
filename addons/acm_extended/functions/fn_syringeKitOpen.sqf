// open the custom syringe kit bench dialog.
// the config onload calls fn_syringekitonload, and we also nudge it on the next frame as a fallback for environments
// where the engine does not fire onload. the onload is idempotent, guarded on the display.
private _medic = call ACME_fnc_controlledProvider;
if (isNull _medic || {!local _medic}) exitWith {};
uiNamespace setVariable ["ACME_SK_Medic", _medic];
uiNamespace setVariable ["ACME_SK_InitDisplay", displayNull];
createDialog "ACME_SyringeKit_Dialog";
[{ call ACME_fnc_syringeKitOnLoad; }, [], 0.05] call CBA_fnc_waitAndExecute;
