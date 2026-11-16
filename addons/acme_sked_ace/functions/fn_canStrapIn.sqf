/*
 * Medical menu: can the casualty be strapped into a laid out SKED within 3.5 m?
 * Arguments: 0: medic, 1: patient. Returns: bool.
 */
params ["_medic", "_patient"];
[_patient] call acme_sked_fnc_validCasualty && {!isNull ([_patient] call acme_sked_fnc_findLitter)}
