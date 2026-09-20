// Burping has no timer. UI peel cycles prevent repeated effects within one lift.
// Only the patient owner may apply the treatment; old cooldown records are ignored.
params ["_patient", ["_requireLocal", false]];
!isNull _patient && {!_requireLocal || {local _patient}}
