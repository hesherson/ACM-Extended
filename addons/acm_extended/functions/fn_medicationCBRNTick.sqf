#include "\x\ACM\addons\circulation\script_component.hpp"
/* B13: native CBRN equations, time-normalized to their old mean 25-second interval.
   Unlike the old PFHs, an early zero effective dose cannot permanently terminate treatment.
   The vitals caller owns locality; clinicalTickDelta prevents ownership/persistence catch-up.
   These remain game-specific chemical-buildup effects, not clinical toxin pharmacology. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
if (((_patient getVariable ["ace_medical_medications", []]) findIf {(_x param [0, ""]) in ["Atropine","Atropine_IV","Atropine_L","Atropine_IV_L","Dimercaprol"]}) < 0) exitWith {};
private _dt = [_patient, "medicationCBRN", 0, 2] call ACME_fnc_clinicalTickDelta;
if (_dt <= 0) exitWith {};
private _arrestFactor = [1, 0.5] select (IN_CRDC_ARRST(_patient));
private _atropine = 0;
{_atropine = _atropine + ([_patient, _x, false] call ACME_fnc_medicationCountCompat);} forEach ["Atropine","Atropine_IV","Atropine_L","Atropine_IV_L"];
if (_atropine >= 3) then {
    private _buildup = _patient getVariable [QGVAR_BUILDUP(Chemical_Sarin), 0];
    private _reduce = 2 * (_atropine / 3) * _arrestFactor * (_dt / 25);
    _patient setVariable [QGVAR_BUILDUP(Chemical_Sarin), (_buildup - _reduce) max 0, true];
    if (_atropine >= 4 && {HAS_AIRWAY_SPASM(_patient)} && {_buildup <= 1 || {random 1 < (1 - (0.7 ^ (_dt / 25)))}}) then {
        _patient setVariable [QEGVAR(CBRN,AirwaySpasm), false, true];
    };
};
private _dimercaprol = [_patient, "Dimercaprol", false] call ACME_fnc_medicationCountCompat;
if (_dimercaprol >= 0.5) then {
    private _buildup = _patient getVariable [QGVAR_BUILDUP(Chemical_Lewisite), 0];
    private _reduce = 8 * (_dimercaprol min 2) * _arrestFactor * (_dt / 25);
    _patient setVariable [QGVAR_BUILDUP(Chemical_Lewisite), (_buildup - _reduce) max 0, true];
};
