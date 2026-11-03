/* Retire both an in-progress charge and its completed, patient-bound authorization. */
params ["_o"];
if (isNull _o) exitWith {};
_o setVariable ["acme_tempusls_charging", [], true];
_o setVariable ["acme_tempusls_charge", [], true];
_o setVariable ["acme_tempusls_armed", false, true];
