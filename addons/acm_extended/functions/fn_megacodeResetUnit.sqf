// Reset a Megacode dummy to a clean baseline where the dummy is local.
params ["_d"];
if (isNull _d || {!local _d}) exitWith {};
if (!alive _d) exitWith {[_d] call ACME_fnc_megacodeRespawn;};

[_d] call ACME_fnc_megacodeClearWounds;
{
    _x params ["_v","_dv"];
    _d setVariable [_v,_dv,true];
} forEach [
    ["ACME_MC_HR",78],["ACME_MC_SpO2",98],["ACME_MC_SBP",122],["ACME_MC_DBP",78],
    ["ACME_MC_RR",14],["ACME_MC_EtCO2",38],["ACME_MC_Temp",37.0],
    ["ACME_MC_HRTgt",78],["ACME_MC_SpO2Tgt",98],["ACME_MC_SBPTgt",122],["ACME_MC_DBPTgt",78],
    ["ACME_MC_RRTgt",14],["ACME_MC_EtCO2Tgt",38],
    ["ACME_MC_rhythm","sinus"],["ACME_MC_rhythmKey","sinus"],["ACME_MC_pulseless",false],["ACME_MC_airway","patent"],
    ["ACME_MC_ICP",10],["ACME_MC_GCS",15],["ACME_MC_herniation",false],["ACME_MC_seizure",false],
    ["ACME_MC_posturing","none"],["ACME_MC_pupils","equal"],["ACME_MC_airwayObstruct",false],
    ["ACME_MC_pneumoLeft",false],["ACME_MC_pneumoRight",false]
];
[_d,[["heartRate",78],["respirationRate",14],["oxygenSaturation",98]],true] call ACM_core_fnc_setTargetVitalsState;
[_d,0] call ACME_fnc_rhythmSet;
[_d,0,true,false] call ACME_fnc_rhythmActiveCommit;
[_d,[["blood",0],["vomit",0],["collapse",0]],true] call ACM_airway_fnc_setAirwayState;
[_d,"ncd"] call ACME_fnc_megacodeChestInjury;
if (_d getVariable ["ace_medical_inCardiacArrest",false]) then {[_d,0,false] call ACME_fnc_megacodeArrest;};
if (_d getVariable ["ACE_isUnconscious",false]) then {[_d,false] call ace_medical_status_fnc_setUnconsciousState;};

_d setVariable ["ACME_MC_arrestElapsed",0,false];
_d setVariable ["ACME_MC_arrestLast",CBA_missionTime,false];
_d setVariable ["ACME_MC_dying",false,true];
_d setVariable ["ACME_AED_ElectricalRateRhythm",-999,false];
_d setVariable ["ACME_AED_ElectricalRateLastUpdate",-1,false];
_d setVariable ["ACME_AED_ClockRhythm",-999,false];
[_d, [["aedPadsLastBeep", CBA_missionTime]], false] call ACM_circulation_fnc_setRuntimeState;

private _scenPFH=_d getVariable ["ACME_MC_scenPFH",-1];
if (_scenPFH>=0) then {[_scenPFH] call CBA_fnc_removePerFrameHandler;};
_d setVariable ["ACME_MC_scenPFH",-1,false];
_d setVariable ["ACME_MC_scenActive",false,true];
_d setVariable ["ACME_MC_scenName","",true];

[_d,[["aiUnconsciousness",true,true]]] call ACM_core_fnc_setAceMedicalState;
[_d,[["instantDeathImmune",true,true]]] call ACM_core_fnc_setAceMedicalState;
[_d,[["deathBlocked",true,true]]] call ACM_core_fnc_setAceMedicalState;

// Retain the episode receipt while clearing injury: this dummy reset does not advance clinicalEpoch,
// so a delayed pre-reset emesis packet must not recreate lung injury.
private _aspiration = [_d] call ACME_fnc_aspirationState;
if (_aspiration isEqualTo []) then {_aspiration = [[_d] call ACME_fnc_clinicalEpoch,"",0,0,0];};
_aspiration set [2,0];
_aspiration set [3,0];
// Batch-3 expansion states also return to a neutral baseline when those functions are present.
{
    _x params ["_key","_value","_public"];
    _d setVariable [_key,_value,_public];
} forEach [
    ["ACME_aspiration_State",_aspiration,true],
    ["ACME_laryngo_emesis",[],true],
    ["ACME_aspiration_load",0,true],
    ["ACME_aspiration_injury",0,true],
    ["ACME_aspiration_edema",0,true],
    ["ACME_aspiration_edemaActive",false,true],
    ["ACME_aspiration_shunt",0,true],
    ["ACME_aspiration_RRDrive",0,true],
    ["ACME_aspiration_SpO2Penalty",0,true],
    ["ACME_aspiration_lastRRAdj",0,false],
    ["ACME_aspiration_lastEmesisKey","",false]
];
if (!isNil "ACME_fnc_shockSetPhenotype") then {[_d,"auto",0] call ACME_fnc_shockSetPhenotype;};
[_d] call ACME_fnc_megacodeStanceLock;
