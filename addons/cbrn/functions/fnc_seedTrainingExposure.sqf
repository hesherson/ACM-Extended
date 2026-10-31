#include "..\script_component.hpp"
/* Native-owned initial absorbed dose for an already evacuated training casualty.
 * No hazard zone is spawned: PPE prevents new exposure, not an absorbed dose.
 * The existing CBRN worker owns elimination and treatment response afterward.
 */
params ["_patient", "_hazard", "_buildup"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {false};
if !(_hazard in ["Chemical_CS", "Chemical_Chlorine", "Chemical_Sarin"]) exitWith {false};
_buildup = (_buildup max 0) min 95;
_patient setVariable [format ["ACM_CBRN_%1_Buildup", toLower _hazard], _buildup, true];
_patient setVariable [format ["ACM_CBRN_%1_WasExposed", toLower _hazard], true, true];
// Resolving CS still presents minor irritation after the mask was fitted.
// Native ongoing CS effects require active exposure and correctly stop outside it.
if (_hazard == "Chemical_CS") then {[_patient,0.2] call ACEFUNC(medical,adjustPainLevel);};
[_patient, _hazard] call FUNC(initHazardUnit);
[_patient, true] call FUNC(updateExposureEffects);
true
