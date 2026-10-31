/* B222: patient eligibility for mask CPAP, shared by menu, server and patient owner.
   No mandatory/apneic rescue through a mask. This is a gameplay gate, not clinical advice. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {false};
if (!([_patient] call ace_common_fnc_isAwake)
    || {_patient getVariable ["ace_medical_inCardiacArrest", false]}
    || {_patient getVariable ["ACME_roc_paralyzed", false]}
    || {_patient getVariable ["ACME_nrb_on", false]}
    || {_patient getVariable ["ACM_airway_RecoveryPosition_State", false]}
    || {_patient getVariable ["ACME_ETT_Inserted", false]}
    || {(_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "SGA"}
    || {_patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false]}) exitWith {false};
private _rr = _patient getVariable ["ACME_resp_neuralRR",
    _patient getVariable ["ACM_breathing_RespirationRate", 0]];
(_rr isEqualType 0) && {finite _rr} && {_rr > 0}
