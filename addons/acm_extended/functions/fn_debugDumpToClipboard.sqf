/*
 * Patient-focused ACME diagnostic dump for the pause menu.
 * Writes a readable clinical summary first, then a bounded raw-variable section for every ACM/ACME/ACE-medical
 * variable carried by the selected patient. This makes state drift/locality issues inspectable without requiring
 * the on-screen overlay to render hundreds of variables.
 */
private _out = {
    params ["_line"];
    diag_log text _line;
    "ace" callExtension ["clipboard:append", [_line + endl]];
};

private _playerRef = if (!isNil "ACE_player" && {!isNull ACE_player}) then {ACE_player} else {player};
private _patient = missionNamespace getVariable ["ACME_debug_target", objNull];
if (!isNull _patient && {!(_patient isKindOf "CAManBase")}) then {_patient = objNull;};
if (isNull _patient) then {
    private _last = missionNamespace getVariable ["ACME_debug_lastTreatmentTarget", objNull];
    if (!isNull _last && {_last isKindOf "CAManBase"}) then {_patient = _last;};
};
if (isNull _patient) then {_patient = _playerRef;};

private _ver = getText (configFile >> "CfgPatches" >> "ACM_Extended" >> "version");
if (_ver == "") then {_ver = missionNamespace getVariable ["ACME_infusion_version", "?"];};
private _build = missionNamespace getVariable ["ACME_buildBatch", "?"];
private _normalBlood = missionNamespace getVariable ["ACME_hypo_bloodNormal", 6];
private _circVol = _patient getVariable ["ace_medical_bloodVolume", _normalBlood];
private _extBleedDbg = if (!isNil "ace_medical_status_fnc_getBloodLoss") then {(([_patient] call ace_medical_status_fnc_getBloodLoss) max 0) * 60000} else {0};
private _juncBleedDbg = ((_patient getVariable ["ACME_junctionalBleedLPS", 0]) max 0) * 60000;
private _intBleedDbg = if (!isNil "ACM_circulation_fnc_getInternalBleedingRate") then {(([_patient] call ACM_circulation_fnc_getInternalBleedingRate) max 0) * 60000} else {0};
private _hemoBleedDbg = if (!isNil "ACM_circulation_fnc_getHemothoraxBleedingRate") then {(([_patient] call ACM_circulation_fnc_getHemothoraxBleedingRate) max 0) * 60000} else {0};
private _capBleedDbg = if (!isNil "ACM_circulation_fnc_getCapillaryDamageBleedingRate") then {(([_patient] call ACM_circulation_fnc_getCapillaryDamageBleedingRate) max 0) * 60000} else {0};
private _bloodComp = _patient getVariable ["ACM_circulation_Blood_Volume", _normalBlood];
private _plasmaComp = _patient getVariable ["ACM_circulation_Plasma_Volume", 0];
private _salineComp = _patient getVariable ["ACM_circulation_Saline_Volume", 0];
private _overloadComp = _patient getVariable ["ACM_circulation_Overload_Volume", 0];
private _effVol = ((_bloodComp + (_plasmaComp * 0.3) - _overloadComp) min _normalBlood) max 0;
private _hr = if (alive _patient) then {_patient getVariable ["ace_medical_heartRate", 0]} else {0};
private _rr = _patient getVariable ["ACM_breathing_RespirationRate", 0];
private _spo2 = _patient getVariable ["ace_medical_spo2", 0];
private _pain = _patient getVariable ["ace_medical_pain", 0];
private _sys = 0;
private _dia = 0;
if (!isNil "ace_medical_status_fnc_getBloodPressure") then {
    private _bp = [_patient] call ace_medical_status_fnc_getBloodPressure;
    if (_bp isEqualType [] && {count _bp >= 2}) then {_dia = _bp select 0; _sys = _bp select 1;};
};
private _map = if (_sys > 0) then {(_sys + 2 * _dia) / 3} else {_patient getVariable ["ACM_circulation_MAP", 0]};
private _etco2 = if (!isNil "ACM_breathing_fnc_getEtCO2") then {[_patient] call ACM_breathing_fnc_getEtCO2} else {-1};

[format ["~~~~~~~~~ACM Extended Debug v%1 %2~~~~~~~~~", _ver, _build]] call _out;
[format ["Time=%1 CBA=%2 tick=%3 fps=%4", time toFixed 1, CBA_missionTime toFixed 1, diag_tickTime toFixed 1, diag_fps toFixed 1]] call _out;
[format ["Patient=%1 type=%2 netId=%3 owner=%4 local=%5 alive=%6", name _patient, typeOf _patient, netId _patient, owner _patient, local _patient, alive _patient]] call _out;
[""] call _out;

["------Vitals / Volume------"] call _out;
[format ["HR=%1 BP=%2/%3 MAP=%4 RR=%5 SpO2=%6 EtCO2=%7 Pain=%8", round _hr, round _sys, round _dia, round _map, round _rr, round _spo2, round _etco2, _pain toFixed 3]] call _out;
[format ["Circulating=%1L Effective=%2L BloodComp=%3L Plasma=%4L Crystalloid=%5L Overload=%6L", _circVol toFixed 3, _effVol toFixed 3, _bloodComp toFixed 3, _plasmaComp toFixed 3, _salineComp toFixed 3, _overloadComp toFixed 3]] call _out;
[format ["Platelets=%1 Calcium=%2 Vasoconstriction=%3 Transfused=%4L HemolysisVol=%5L HemolysisSeverity=%6",
    _patient getVariable ["ACM_circulation_Platelet_Count", 3],
    _patient getVariable ["ACM_circulation_Calcium_Count", 0],
    _patient getVariable ["ACM_circulation_Vasoconstriction_State", 0],
    (_patient getVariable ["ACM_circulation_TransfusedBlood_Volume", 0]) toFixed 3,
    (_patient getVariable ["ACM_circulation_HemolyticReaction_Volume", 0]) toFixed 3,
    (_patient getVariable ["ACM_circulation_HemolyticReaction_Severity", 0]) toFixed 3
]] call _out;
[""] call _out;

["------Core / Airway------"] call _out;
[format ["Unconscious=%1 CardiacArrest=%2 InstantDeath=%3 KnockOut=%4 CriticalVitals=%5 Passed=%6 Lying=%7 Sitting=%8",
    _patient getVariable ["ACE_isUnconscious", false],
    _patient getVariable ["ace_medical_inCardiacArrest", false],
    _patient getVariable ["ACM_core_InstantDeath", false],
    _patient getVariable ["ACM_core_KnockOut_State", false],
    _patient getVariable ["ACM_core_CriticalVitals_State", false],
    _patient getVariable ["ACM_core_CriticalVitals_Passed", false],
    _patient getVariable ["ACM_core_Lying_State", false],
    _patient getVariable ["ACM_core_Sitting_State", false]
]] call _out;
private _stableWake = [_patient] call ace_medical_status_fnc_hasStableVitals;
private _forcedWake = [_patient] call ACM_core_fnc_isForcedUnconscious;
private _canWake = [_patient, false] call ACM_core_fnc_canWake;
private _sedLoadDbg = [_patient] call ACME_fnc_sedationOnBoard;
private _sedActiveDbg = [_patient] call ACME_fnc_sedationActive;
[format ["WakeGate Stable=%1 Forced=%2 CanWake=%3 SedLoad=%4 SedActive=%5 RocParalyzed=%6 RepairCount=%7 LastRepair=%8",
    _stableWake,
    _forcedWake,
    _canWake,
    _sedLoadDbg toFixed 3,
    _sedActiveDbg,
    _patient getVariable ["ACME_roc_paralyzed", false],
    _patient getVariable ["ACME_consciousRepairCount", 0],
    _patient getVariable ["ACME_consciousRepairLast", []]
]] call _out;
[format ["AirwayReflex=%1 Collapse=%2 VomitObs=%3 BloodObs=%4 Recovery=%5 HeadTilt=%6 OPA=%7 NPA=%8",
    _patient getVariable ["ACM_airway_AirwayReflex_State", true],
    _patient getVariable ["ACM_airway_AirwayCollapse_State", 0],
    _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0],
    _patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0],
    _patient getVariable ["ACM_airway_RecoveryPosition_State", false],
    _patient getVariable ["ACM_airway_HeadTilt_State", false],
    _patient getVariable ["ACM_airway_AirwayItem_Oral", ""],
    _patient getVariable ["ACM_airway_AirwayItem_Nasal", ""]
]] call _out;
[format ["SurgicalAirway=%1 InProgress=%2 Tube=%3 Cuff=%4 Strap=%5",
    _patient getVariable ["ACM_airway_SurgicalAirway_State", false],
    _patient getVariable ["ACM_airway_SurgicalAirway_InProgress", false],
    _patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false],
    _patient getVariable ["ACM_airway_SurgicalAirway_CuffInflated", false],
    _patient getVariable ["ACM_airway_SurgicalAirway_StrapSecure", false]
]] call _out;
[""] call _out;

["------Breathing / Chest------"] call _out;
[format ["ChestInjury=%1 PTX=%2 TensionPTX=%3 HardcorePTX=%4 HemoState=%5 HemoFluid=%6L ChestSeal=%7 Thoracostomy=%8",
    _patient getVariable ["ACM_breathing_ChestInjury_State", false],
    _patient getVariable ["ACM_breathing_Pneumothorax_State", 0],
    _patient getVariable ["ACM_breathing_TensionPneumothorax_State", false],
    _patient getVariable ["ACM_breathing_Hardcore_Pneumothorax", false],
    _patient getVariable ["ACM_breathing_Hemothorax_State", 0],
    (_patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0]) toFixed 3,
    _patient getVariable ["ACM_breathing_ChestSeal_State", false],
    _patient getVariable ["ACM_breathing_Thoracostomy_State", -1]
]] call _out;
[format ["LungState=%1 BVM=%2 BVM_O2=%3",
    _patient getVariable ["ACM_breathing_Stethoscope_LungState", [0,0]],
    _patient getVariable ["ACM_breathing_isUsingBVM", false],
    _patient getVariable ["ACM_breathing_BVM_ConnectedOxygen", false]
]] call _out;
[format ["ThoraSide L=[open:%1 tube:%2 seal:%3 closed:%4] R=[open:%5 tube:%6 seal:%7 closed:%8]",
    _patient getVariable ["ACME_thora_open_left", ""],
    _patient getVariable ["ACME_thora_tube_left", false],
    _patient getVariable ["ACME_thora_sealed_left", false],
    _patient getVariable ["ACME_thora_closed_left", false],
    _patient getVariable ["ACME_thora_open_right", ""],
    _patient getVariable ["ACME_thora_tube_right", false],
    _patient getVariable ["ACME_thora_sealed_right", false],
    _patient getVariable ["ACME_thora_closed_right", false]
]] call _out;
[""] call _out;

["------Circulation / Damage / Disability------"] call _out;
[format ["Rhythm=%1 ReversibleArrest=%2 ShockResistant=%3 CPR=%4 CirculationState=%5",
    _patient getVariable ["ACM_circulation_Cardiac_RhythmState", 0],
    _patient getVariable ["ACM_circulation_ReversibleCardiacArrest_State", false],
    _patient getVariable ["ACM_circulation_CardiacArrest_ShockResistant", false],
    _patient getVariable ["ACM_circulation_isPerformingCPR", false],
    _patient getVariable ["ACM_circulation_CirculationState", true]
]] call _out;
[format ["Coagulation=%1 InternalCoag=%2 Fractures=%3 Splints=%4 TourniquetTimes=%5",
    _patient getVariable ["ACM_damage_Coagulation_Active", false],
    _patient getVariable ["ACM_damage_IBCoagulation_Active", false],
    _patient getVariable ["ACM_disability_Fracture_State", [0,0,0,0,0,0]],
    _patient getVariable ["ace_medical_treatment_splints", [0,0,0,0,0,0]],
    _patient getVariable ["ACM_disability_Tourniquet_Time", [0,0,0,0,0,0]]
]] call _out;
[""] call _out;

["------ACME High-Value State------"] call _out;
private _tbiState = _patient getVariable ["ACME_tbi_State", createHashMap];
[format ["BleedSources raw mL/min: external=%1 junctional=%2 internal=%3 hemothorax=%4 capillary=%5 total=%6",
    round _extBleedDbg, round _juncBleedDbg, round _intBleedDbg, round _hemoBleedDbg, round _capBleedDbg,
    round (_extBleedDbg + _juncBleedDbg + _intBleedDbg + _hemoBleedDbg + _capBleedDbg)]] call _out;
private _tbiICP = if (_tbiState isEqualType createHashMap) then {_tbiState getOrDefault ["icp", 0]} else {0};
private _tbiCPP = _map - _tbiICP;
[format ["TBI=%1 ICP=%2 CPP=%3 HPMK=%4/%5 Obtunded=%6 Vent=%7 ETT=%8",
    _patient getVariable ["ACME_tbi_HasTBI", false],
    _tbiICP toFixed 2,
    _tbiCPP toFixed 2,
    _patient getVariable ["ACME_hpmk_on", false],
    _patient getVariable ["ACME_hpmk_state", ""],
    _patient getVariable ["ACME_obtunded", false],
    _patient getVariable ["ACME_vent_connected", false],
    _patient getVariable ["ACME_ETT_Inserted", false]
]] call _out;
private _juncStates = ["leftarm", "rightarm", "leftleg", "rightleg"] apply {[_x, _patient getVariable [format ["ACME_Junc_%1", _x], ""]]};
[format ["Junctional=%1 BleedLPS=%2 XStatSurgery=%3 XStatImpaired=%4",
    _juncStates,
    (_patient getVariable ["ACME_junctionalBleedLPS", 0]) toFixed 5,
    _patient getVariable ["ACME_XStat_needsSurgery", false],
    _patient getVariable ["ACME_XStat_impaired", false]
]] call _out;
[""] call _out;

private _valueText = {
    params ["_v"];
    if (_v isEqualType []) exitWith {
        if ((count _v) > 80) then {format ["ARRAY[count=%1]", count _v]} else {str _v}
    };
    if ((typeName _v) == "HASHMAP") exitWith {format ["HASHMAP[count=%1]", count (keys _v)]};
    private _s = str _v;
    if ((count _s) > 600) then {(_s select [0, 600]) + "..."} else {_s}
};

["------Raw Patient Medical Variables------"] call _out;
private _vars = allVariables _patient select {
    private _u = toUpper _x;
    ((_u find "ACM_") == 0) || {((_u find "ACME_") == 0)} || {((_u find "ACE_MEDICAL_") == 0)} || {_u in ["ACE_ISUNCONSCIOUS"]}
};
_vars sort true;
{
    private _v = _patient getVariable [_x, nil];
    if (!isNil "_v") then {[format ["%1 = %2", _x, [_v] call _valueText]] call _out;};
} forEach _vars;

"ace" callExtension ["clipboard:complete", []];
["ACME debug information copied to clipboard.", 2] call ace_common_fnc_displayTextStructured;
