/* B14: onset-aware IM/IV contributions in native reference-equivalent mcg.
   The supplied buccal product is counted in lozenges, not mg: its contribution is a
   separate bounded game coefficient, NOT an assumed 800 mcg inventory strength.
   This augments a hypnotic; it is never an independent induction agent. */
params [["_patient",objNull,[objNull]]];
if (isNull _patient || {isNil "ace_medical_status_fnc_getMedicationCount"}) exitWith {0};
private _equivMcg = 0;
{
    private _v = [_patient,_x,false] call ACME_fnc_medicationCountCompat;
    if (_v isEqualType 0 && {finite _v}) then {_equivMcg = _equivMcg + (_v max 0) * 83;};
} forEach ["Fentanyl_IV","Fentanyl"];
private _min = missionNamespace getVariable ["ACME_fent_minBluntMcg",50];
private _full = (missionNamespace getVariable ["ACME_fent_fullBluntMcg",200]) max (_min + 1);
private _injectable = linearConversion [_min,_full,_equivMcg,0,1,true];
private _buccal = [_patient,"Fentanyl_BUC",false] call ACME_fnc_medicationCountCompat;
(_injectable + ((_buccal max 0) * 0.5)) min 1
