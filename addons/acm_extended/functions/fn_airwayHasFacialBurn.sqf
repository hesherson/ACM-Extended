/* Read native head-burn wounds. No duplicate injury flag or network publication is needed.
   ACE medical_damage/fnc_woundsHandlerBase.sqf stores classComplex as 10 * classIndex + size.
   ACM damage/ACE_Medical_Injuries.hpp adds ChemicalBurn to the native injury table. */
params ["_patient"];
if (isNull _patient) exitWith { false };
// Retained mission hook: set true on the patient before grading to model a scenario facial burn.
if ((_patient getVariable ["ACME_facialBurn", false]) isEqualTo true) exitWith { true };
private _names = missionNamespace getVariable ["ace_medical_damage_woundClassNames", []];
private _burn = false;
{
    private _wounds = _patient getVariable [_x, createHashMap];
    if !(_wounds isEqualType createHashMap) then { continue; };
    {
        if !(_x isEqualType [] && {count _x >= 2}) then { continue; };
        private _id = _x select 0;
        private _amount = _x select 1;
        if !(_id isEqualType 0 && {_amount isEqualType 0} && {_amount > 0}) then { continue; };
        private _index = floor (_id / 10);
        if (_index < 0 || {_index >= count _names}) then { continue; };
        if ((_names select _index) in ["ThermalBurn", "ChemicalBurn", "Burn1", "Burn2", "Burn3"]) exitWith { _burn = true; };
    } forEach (_wounds getOrDefault ["head", []]);
    if (_burn) exitWith {};
} forEach ["ace_medical_openWounds", "ace_medical_bandagedWounds", "ace_medical_stitchedWounds"];
_burn
