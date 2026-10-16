#include "..\script_component.hpp"
/* Apply an explicit training case once, on the newly created casualty owner.
 * Random gunshot/blast damage is deliberately not added to a selected case.
 */
params ["_patient", "_preset", "_location"];
if (isNull _patient || {!local _patient} || {!alive _patient} || {count _preset != 11}) exitWith {false};
if (_patient getVariable [QGVAR(PresetApplied), false]) exitWith {false};
_patient setVariable [QGVAR(PresetApplied), true, true];
_preset params ["_id", "_title", "_severity", "_wounds", "_fractures", "_blood", "_airway", "_chest", "_tbi", "_blast", "_cbrn"];

// Reuse native ACM wound, blood and fracture construction on this same unit.
[_location, _wounds, _fractures, _blood, [0,0], [0,0,0], _patient, _severity >= 3] call FUNC(spawnCustomPatient);
// Apply the selected obstruction now; the legacy custom spawner's delayed
// chest/airway path must not reapply a case after the trainee already treats it.
if (_airway isNotEqualTo [0,0]) then {
    [_patient, [["vomit",_airway select 0],["collapse",_airway select 1]], true] call EFUNC(airway,setAirwayState);
};
_patient setVariable [QGVAR(PatientPreset), _id, true];
if (_chest isNotEqualTo []) then {
    _chest params ["_kind", "_side", ["_hemo",0], ["_fluid",0]];
    [_patient, true] call EFUNC(breathing,setChestInjuryState);
    [_patient, [["stethoscopeLungState", [[1,0],[0,1]] select _side]], true] call EFUNC(breathing,setRuntimeState);
    if (_kind in [1,2]) then {
        [_patient, 1] call ACME_fnc_ptxInjury;
        if (_kind == 2) then {
            private _state = [_patient] call ACME_fnc_ptxEnsure;
            _state set [1,4];
            _state set [2,0.8];
            _state set [4,1];
            [_patient, _state, true] call ACME_fnc_ptxPublish;
        };
    };
    if (_kind == 3) then {
        [_patient, [["hemothorax", _hemo], ["hemothoraxFluid", _fluid]], true] call EFUNC(breathing,setRuntimeState);
        [_patient, true] call EFUNC(breathing,handleHemothorax);
    };
    [_patient] call EFUNC(breathing,updateLungState);
};
if (_tbi isNotEqualTo []) then {
    [_patient, _tbi select 0, _tbi select 1] call ACME_fnc_zeusTBIApplyLocal;
};
if (_blast > 0) then {[_patient, _blast] call ACME_fnc_blastLungInflict;};
if (_cbrn isNotEqualTo []) then {
    _patient addGoggles "G_AirPurifyingRespirator_01_F";
    [_patient, _cbrn select 0, _cbrn select 1] call EFUNC(CBRN,seedTrainingExposure);
};
true
