/* ACM chest-seal owner callback, adapted by ACM Extended.
   A chest seal may also be used to close an open thoracostomy incision when no chest tube remains. */
params ["_medic", "_patient"];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    ["ACM_breathing_applyChestSealLocal", _this, _patient] call CBA_fnc_targetEvent;
};

[_patient] call ACME_fnc_ptxEnsure;

// Treat a chest seal as an alternate definitive closure for an open finger-thoracostomy tract.
// Use the same owner-authoritative cleanup as suturing so the two closure methods cannot diverge.
private _thoracostomyOpen = (_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) > 0;
private _tubeInstalled = (_patient getVariable ["ACME_thora_tube_left", false])
    || {_patient getVariable ["ACME_thora_tube_right", false]};

// Ordinary traumatic wound sealing remains available while surgical closure
// waits for controlled, settled PTX. It must not close an unstable drain.
if (_thoracostomyOpen && {!_tubeInstalled} && {[_patient] call ACME_fnc_ptxCanClose}) then {
    [_medic, _patient] call ACM_breathing_fnc_Thoracostomy_closeLocal;
};

// Preserve the physical chest-seal intervention even after the incision has been closed.
_patient setVariable ["ACM_breathing_ChestSeal_State", true, true];
[_patient, "seal"] call ACME_fnc_ptxTreat;
[_patient] call ACM_breathing_fnc_updateLungState;
