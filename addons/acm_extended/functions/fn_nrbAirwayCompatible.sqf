// NRB compatibility is intentionally narrow.
// A non-rebreather may coexist with no adjunct, an OPA and/or an NPA.
// Advanced airways (i-gel/SGA, ETT, surgical airway) occupy or bypass the mask interface and require BVM/vent support.
params [["_patient", objNull, [objNull]]];
if (isNull _patient) exitWith {false};

private _oral = toUpperANSI (_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]);
private _ett = _patient getVariable ["ACME_ETT_Inserted", false];
private _surgical = _patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false];

(_oral in ["", "OPA"]) && {!_ett} && {!_surgical} && {!(_patient getVariable ["ACME_vent_nivMask", false])}
