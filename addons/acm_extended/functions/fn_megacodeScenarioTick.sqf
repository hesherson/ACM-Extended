// the server-side stepper for a running megacode scenario. each pass checks the elapsed time against the next
// stage and, when due, applies the vitals, rhythm and pathology of that stage to the manikin and announces it on
// the panel of the operator. when the stages run out the pfh retires, and the arrest, keeper and fatal clock take
// over.
// the pfh args are [_d].
params ["_args", "_pfhId"];
_args params ["_d"];

if (isNull _d || {!local _d}) exitWith { [_pfhId] call CBA_fnc_removePerFrameHandler; };
if !(_d getVariable ["ACME_MC_scenActive", false]) exitWith {
    [_pfhId] call CBA_fnc_removePerFrameHandler;
    _d setVariable ["ACME_MC_scenPFH", -1, false];
};

private _stages = _d getVariable ["ACME_MC_scenStages", []];
private _idx = _d getVariable ["ACME_MC_scenIdx", 0];
if (_idx >= count _stages) exitWith {
    [_d, "ACME_MC_scenActive", false] call ACME_fnc_setVarNet;
    [_pfhId] call CBA_fnc_removePerFrameHandler;
    _d setVariable ["ACME_MC_scenPFH", -1, false];
};

private _elapsed = CBA_missionTime - (_d getVariable ["ACME_MC_scenStart", CBA_missionTime]);
private _stage = _stages select _idx;
_stage params ["_at", "_label", "_hr", "_spo2", "_sbp", "_dbp", "_rr", "_etco2", "_rk", "_extra"];
if (_elapsed < _at) exitWith {};

// apply the vitals, where 0 or above means set and -1 keeps the current value. it sets the targets, so the keeper
// ramps them in.
if (_hr    >= 0) then { _d setVariable ["ACME_MC_HRTgt", _hr, true];       [_d, [["heartRate", _hr]], true] call ACM_core_fnc_setTargetVitalsState; };
if (_spo2  >= 0) then { _d setVariable ["ACME_MC_SpO2Tgt", _spo2, true];   [_d, [["oxygenSaturation", _spo2]], true] call ACM_core_fnc_setTargetVitalsState; [_d, [["spo2", _spo2, true]]] call ACM_core_fnc_setAceMedicalState; };
if (_sbp   >= 0) then { _d setVariable ["ACME_MC_SBPTgt", _sbp, true]; };
if (_dbp   >= 0) then { _d setVariable ["ACME_MC_DBPTgt", _dbp, true]; };
if (_rr    >= 0) then { _d setVariable ["ACME_MC_RRTgt", _rr, true];       [_d, [["respirationRate", _rr]], true] call ACM_core_fnc_setTargetVitalsState; [_d, [["respirationRate", _rr]], true] call ACM_breathing_fnc_setRuntimeState; };
if (_etco2 >= 0) then { _d setVariable ["ACME_MC_EtCO2Tgt", _etco2, true]; };

// apply the rhythm.
if (_rk != "") then {
    // the key maps to [displayrhythm, defaulthr, pulseless, acmcode, isarrest].
    private _map = createHashMapFromArray [
        ["sinus",["sinus",78,false,0,false]], ["stach",["sinus",130,false,0,false]], ["sbrady",["sinus",45,false,0,false]],
        ["afib",["afib",84,false,103,false]], ["vt",["vt",180,false,4,false]],
        ["torsades",["torsades",0,true,102,true]], ["vfib",["vfib",0,true,2,true]],
        ["asystole",["asystole",0,true,1,true]], ["pea",["sinus",0,true,5,true]]
    ];
    (_map getOrDefault [_rk, ["sinus",-1,false,0,false]]) params ["_disp","_dhr","_pl","_acm","_arr"];
    [_d, "ACME_MC_rhythm", _disp] call ACME_fnc_setVarNet;
    [_d, "ACME_MC_pulseless", _pl] call ACME_fnc_setVarNet;
    [_d, _acm, true, true] call ACME_fnc_rhythmActiveCommit;
    [_d, "ACME_MC_rhythmKey", _rk] call ACME_fnc_setVarNet;
    if (_arr) then {
        [_d, _acm, true] call ACME_fnc_megacodeArrest;
    } else {
        if (_d getVariable ["ace_medical_inCardiacArrest", false]) then { [_d, 0, false] call ACME_fnc_megacodeArrest; };
        [_d, _acm] call ACME_fnc_rhythmSet;
        if (_dhr >= 0 && {_hr < 0}) then { _d setVariable ["ACME_MC_HRTgt", _dhr, true]; [_d, [["heartRate", _dhr]], true] call ACM_core_fnc_setTargetVitalsState; };
    };
};

// apply the situational extra.
switch (toLower _extra) do {
    case "pneumo":     { [_d, "pneumo"] call ACME_fnc_megacodeChestInjury; };
    case "tpneumo":    { [_d, "tpneumo"] call ACME_fnc_megacodeChestInjury; };
    case "hemothorax": { [_d, "hemothorax"] call ACME_fnc_megacodeChestInjury; };
    case "junc_legs":  { [_d, "leftleg"] call ACME_fnc_junctionalInflict; [_d, "rightleg"] call ACME_fnc_junctionalInflict; };
    case "junc_arms":  { [_d, "leftarm"] call ACME_fnc_junctionalInflict; [_d, "rightarm"] call ACME_fnc_junctionalInflict; };
    case "hypoxia":    { _d setVariable ["ACME_MC_airway", "collapse", true]; [_d, [["collapse", 3]], true] call ACM_airway_fnc_setAirwayState; if (!(_d getVariable ["ACE_isUnconscious", false])) then { [_d, true] call ace_medical_status_fnc_setUnconsciousState; }; };
    case "fever":      { _d setVariable ["ACME_MC_Temp", 39.6, true]; [_d, [["bodyTemperature", 39.6, true]]] call ACM_core_fnc_setAceMedicalState; };
    case "icp_rise":   { _d setVariable ["ACME_MC_ICP", 26, true]; };
    case "cushing":    { _d setVariable ["ACME_MC_ICP", 42, true]; };
    case "herniation": {
        [_d, "ACME_MC_herniation", true] call ACME_fnc_setVarNet;
        [_d, "ACME_MC_ICP", 55] call ACME_fnc_setVarNet;
        [_d, "ACME_MC_GCS", 3] call ACME_fnc_setVarNet;
        if (!(_d getVariable ["ACE_isUnconscious", false])) then { [_d, true] call ace_medical_status_fnc_setUnconsciousState; };
    };
};

_d setVariable ["ACME_MC_scenIdx", _idx + 1, false];

// announce the stage on the panel of the operator.
private _op = _d getVariable ["ACME_MC_scenOp", objNull];
if (!isNull _op) then {
    [format ["Scenario: %1", _label], 3] remoteExec ["ace_common_fnc_displayTextStructured", _op];
    [[format ["-> %1", _label], "#c39bff"]] remoteExec ["ACME_fnc_megacodeLog", _op];
};
