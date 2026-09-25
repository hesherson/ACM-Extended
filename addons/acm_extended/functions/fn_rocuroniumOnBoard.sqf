/* B121: native effective units incorporate dose/onset. Hardcore rapid IV delivery may transiently accelerate
   establishment of block by at most ~18%; dose remains the dominant variable. */
params ["_patient"];
if (isNull _patient) exitWith {0};
private _base = ([_patient,"Rocuronium_IV",false] call ACME_fnc_medicationCountCompat)
    + ([_patient,"Rocuronium",false] call ACME_fnc_medicationCountCompat);
if !(missionNamespace getVariable ["ACME_hcEff_medications",false]) exitWith {_base};
private _rapid = (_patient getVariable ["ACME_hcMed_rapidRocuronium",0]) max 0;
_base * (1 + 0.18*(_rapid/(0.5+_rapid)))
