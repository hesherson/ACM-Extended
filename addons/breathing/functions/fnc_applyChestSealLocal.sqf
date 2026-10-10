/* ACM traumatic-wound chest-seal owner callback, adapted by ACM Extended.
   Surgical dressings are applied to their selected tract through aftercare. */
params ["_medic", "_patient"];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    ["ACM_breathing_applyChestSealLocal", _this, _patient] call CBA_fnc_targetEvent;
};

[_patient] call ACME_fnc_ptxEnsure;

// A vented traumatic-wound seal never sutures or removes a surgical tract.
_patient setVariable ["ACM_breathing_ChestSeal_State", true, true];
[_patient, "seal"] call ACME_fnc_ptxTreat;
[_patient] call ACM_breathing_fnc_updateLungState;
