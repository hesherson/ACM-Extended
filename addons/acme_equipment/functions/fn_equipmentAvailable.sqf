/* Reusable deployed suction is tied to this patient, not whoever originally carried it. */
params ["_medic","_patient"];
if (isNull _medic || {isNull _patient}) exitWith {false};
private _o=_patient getVariable ["ACME_eq_accu",objNull];
!isNull _o && {(_o getVariable ["ACME_eq_patient",objNull]) isEqualTo _patient}
    && {!isObjectHidden _o} && {isNull attachedTo _o} && {!(_o getVariable ["ACME_eq_restoreStaged",false])} && {!(_o getVariable ["ACME_eq_busy",false])} && {_o distance _patient<=4} && {_medic distance _o<=4}
