/*
 * ACME debug page 1/2: compact clinical overview.
 * Designed for a single screenshot on 16:9 while retaining the high-value state needed for bug reports.
 */
disableSerialization;

private _cleanup = {
    {
        private _c = uiNamespace getVariable [_x, controlNull];
        if (!isNull _c) then {ctrlDelete _c;};
        uiNamespace setVariable [_x, controlNull];
    } forEach ["ACME_DebugMenuCtrlL", "ACME_DebugMenuCtrlR", "ACME_DebugMenuCtrlS", "ACME_DebugMenuCtrl"];
};

if (!(call ACME_fnc_debugEnabled)) exitWith {call _cleanup;};

private _display = findDisplay 46;
if (isNull _display) then {_display = uiNamespace getVariable ["RscDisplayMission", displayNull];};
if (isNull _display) exitWith {};

private _ctrlL = uiNamespace getVariable ["ACME_DebugMenuCtrlL", controlNull];
if (!isNull _ctrlL && {!((ctrlParent _ctrlL) isEqualTo _display)}) then {ctrlDelete _ctrlL; _ctrlL = controlNull;};
private _ctrlR = uiNamespace getVariable ["ACME_DebugMenuCtrlR", controlNull];
if (!isNull _ctrlR && {!((ctrlParent _ctrlR) isEqualTo _display)}) then {ctrlDelete _ctrlR; _ctrlR = controlNull;};
private _ctrlS = uiNamespace getVariable ["ACME_DebugMenuCtrlS", controlNull];
if (!isNull _ctrlS) then {_ctrlS ctrlShow false;};
private _old = uiNamespace getVariable ["ACME_DebugMenuCtrl", controlNull];
if (!isNull _old) then {ctrlDelete _old; uiNamespace setVariable ["ACME_DebugMenuCtrl", controlNull];};

if (isNull _ctrlL) then {
    _ctrlL = _display ctrlCreate ["RscStructuredText", -1];
    _ctrlL ctrlSetBackgroundColor [0.043, 0.082, 0.188, 0.88];
    _ctrlL ctrlShow true;
    uiNamespace setVariable ["ACME_DebugMenuCtrlL", _ctrlL];
};
if (isNull _ctrlR) then {
    _ctrlR = _display ctrlCreate ["RscStructuredText", -1];
    _ctrlR ctrlSetBackgroundColor [0.043, 0.082, 0.188, 0.88];
    _ctrlR ctrlShow true;
    uiNamespace setVariable ["ACME_DebugMenuCtrlR", _ctrlR];
};
_ctrlL ctrlShow true;
_ctrlR ctrlShow true;

private _canvas = call ACME_fnc_uiCanvas;
_canvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
private _gap = 0.0035;
// B116: keep the entire clinical snapshot on one screenshot. The panel is narrower than B114 and the font
// starts smaller; only the network/engineering page is allowed to live elsewhere.
private _totalW = ((_uiW * 0.36) max 0.34) min 0.42;
private _w = (_totalW - _gap) / 2;
private _x = safeZoneXAbs + 0.002;
private _y = safeZoneY + 0.014;
private _h = (safeZoneH - 0.024) max 0.30;
_ctrlL ctrlSetPosition [_x, _y, _w, _h];
_ctrlR ctrlSetPosition [_x + _w + _gap, _y, _w, _h];
_ctrlL ctrlCommit 0;
_ctrlR ctrlCommit 0;

private _userScale = missionNamespace getVariable ["ACME_debug_scale", 1];
private _scale = (((_userScale max 0.50) min 1.15) * 0.54) max 0.39 min 0.62;

private _cTitle = "#D9A441";
private _cSect  = "#F0E7D2";
private _cLabel = "#C0B7A2";
private _cGood  = "#5FB56E";
private _cWarn  = "#D9A441";
private _cBad   = "#E04141";
private _cCrit  = "#FF5A5A";
private _cMute  = "#8A8474";

private _safe = {
    params ["_v"];
    private _s = if (_v isEqualType "") then {_v} else {str _v};
    _s = (_s splitString "&") joinString "&amp;";
    _s = (_s splitString "<") joinString "&lt;";
    _s = (_s splitString ">") joinString "&gt;";
    _s
};
private _yn = {params ["_v"]; if (_v) then {"yes"} else {"no"};};
private _ynCol = {params ["_v", ["_badWhenTrue", false]]; if (_badWhenTrue) exitWith {if (_v) then {_cBad} else {_cGood}}; if (_v) then {_cGood} else {_cMute};};
private _padRight = {
    params ["_s", "_w"];
    if !(_s isEqualType "") then {_s = str _s;};
    while {count _s < _w} do {_s = _s + " ";};
    if ((count _s) > _w) then {_s = _s select [0, _w];};
    _s
};
private _alignValue = {
    params ["_v", ["_w", 12]];
    private _s = if (_v isEqualType "") then {_v} else {str _v};
    // Match the original debug layout: right-align the integer/whole-token side so ones, tens and hundreds share
    // one vertical column. Decimal/unit suffixes then trail to the right inside a constant-width value field.
    private _integerW = (_w - 4) max 1;
    private _dot = _s find ".";
    private _integer = if (_dot > -1) then {_s select [0, _dot]} else {_s};
    private _suffix = if (_dot > -1) then {_s select [_dot]} else {""};
    while {count _integer < _integerW} do {_integer = " " + _integer;};
    private _txt = _integer + _suffix;
    while {count _txt < _w} do {_txt = _txt + " ";};
    _txt
};
private _pair = {
    params ["_a", "_av", "_ac", "_b", "_bv", "_bc"];
    private _aTxt = [_a, 7] call _padRight;
    private _bTxt = [_b, 7] call _padRight;
    private _avTxt = [([_av, 12] call _alignValue)] call _safe;
    private _bvTxt = [([_bv, 12] call _alignValue)] call _safe;
    format ["<t color='%7'>%1</t> <t color='%3'>%2</t>  <t color='%7'>%4</t> <t color='%6'>%5</t>", _aTxt, _avTxt, _ac, _bTxt, _bvTxt, _bc, _cLabel]
};
private _one = {
    params ["_a", "_av", "_ac"];
    private _aTxt = [_a, 7] call _padRight;
    private _avTxt = [([_av, 12] call _alignValue)] call _safe;
    format ["<t color='%4'>%1</t> <t color='%3'>%2</t>", _aTxt, _avTxt, _ac, _cLabel]
};
private _sect = {params ["_s"]; format ["<t color='%1'>%2</t>", _cSect, _s];};
private _arr = {params ["_name"]; private _v = missionNamespace getVariable [_name, []]; if (_v isEqualType []) then {_v} else {[]};};
private _pushUnique = {params ["_a", "_o"]; if (!isNull _o && {!(_o in _a)}) then {_a pushBack _o;}; _a};

// Same target selection contract as the full debug page.
private _patient = missionNamespace getVariable ["ACME_debug_target", objNull];
if (!isNull _patient && {!(_patient isKindOf "CAManBase")}) then {_patient = objNull;};
if (isNull _patient) then {
    private _last = missionNamespace getVariable ["ACME_debug_lastTreatmentTarget", objNull];
    if (!isNull _last && {_last isKindOf "CAManBase"}) then {_patient = _last;};
};
if (isNull _patient) then {
    private _cands = [];
    {
        { _cands = [_cands, _x] call _pushUnique; } forEach ([_x] call _arr);
    } forEach ["ACME_infusion_activePatients", "ACME_tbi_activePatients", "ACME_circ_activePatients", "ACME_autoBP_patients", "ACME_hpmk_activePatients"];
    if (_cands isEqualTo []) then {_patient = ACE_player;} else {_patient = _cands select 0;};
};

private _ver = getText (configFile >> "CfgPatches" >> "ACM_Extended" >> "version");
if (_ver == "") then {_ver = missionNamespace getVariable ["ACME_infusion_version", "?"];};
private _rc = missionNamespace getVariable ["ACME_debugRevision", ""];
if (_rc isEqualType "" && {_rc != ""}) then {_ver = format ["%1-%2", _ver, _rc];};
private _batch = missionNamespace getVariable ["ACME_buildBatch", "?"];
private _left = [];
private _right = [];
private _pName = if (isNull _patient) then {"NO PATIENT"} else {name _patient};
_left pushBack format ["<t color='%1' size='1.02'>ACME DEBUG v%2</t>  <t color='%1'>CLINICAL 1/2</t>", _cTitle, _ver];
_left pushBack format ["<t color='%1'>%2  |  %3  |  Ctrl+PgUp/PgDn</t>", _cMute, [_pName] call _safe, _batch];
_right pushBack format ["<t color='%1' size='1.02'>AT A GLANCE</t>", _cTitle];
_right pushBack format ["<t color='%1'>Page 2: NETWORK 2/2</t>", _cTitle];

if (isNull _patient) exitWith {
    _left pushBack (["Patient", "none", _cWarn] call _one);
    _ctrlL ctrlSetStructuredText parseText format ["<t size='%1' font='EtelkaMonospacePro'>%2</t>", _scale, _left joinString "<br/>"];
    _ctrlR ctrlSetStructuredText parseText format ["<t size='%1' font='EtelkaMonospacePro'>%2</t>", _scale, _right joinString "<br/>"];
};

// Core vitals.
private _hr = if (alive _patient) then {round (_patient getVariable ["ace_medical_heartRate", 0])} else {0};
private _rr = round (_patient getVariable ["ACM_breathing_RespirationRate", 0]);
private _spo2 = round (_patient getVariable ["ace_medical_spo2", 0]);
private _bp = if (!isNil "ace_medical_status_fnc_getBloodPressure") then {[_patient] call ace_medical_status_fnc_getBloodPressure} else {[0,0]};
private _dia = round (_bp param [0, 0]);
private _sys = round (_bp param [1, 0]);
private _map = if (_sys > 0) then {round ((_sys + 2 * _dia) / 3)} else {round (_patient getVariable ["ACM_circulation_MAP", 0])};
private _circState = _patient getVariable ["ACME_circ_State", createHashMap];
private _etco2 = _circState getOrDefault ["etco2Observed", -1];
private _temp = _patient getVariable ["ACME_hypo_temp", 37];
private _pain = _patient getVariable ["ace_medical_pain", 0];
private _uncon = _patient getVariable ["ACE_isUnconscious", false];
private _arrest = _patient getVariable ["ace_medical_inCardiacArrest", false];
private _crit = _patient getVariable ["ACM_core_CriticalVitals_State", false];
private _coLMin = if (!isNil "ace_medical_status_fnc_getCardiacOutput") then {([_patient] call ace_medical_status_fnc_getCardiacOutput) * 60} else {0};

private _hrC = if (_hr <= 0 || {_hr < 40} || {_hr >= 180}) then {_cBad} else {if (_hr < 60 || {_hr >= 130}) then {_cWarn} else {_cGood}};
private _bpC = if (_sys <= 0 || {_sys < 80}) then {_cBad} else {if (_sys < 90 || {_sys > 160}) then {_cWarn} else {_cGood}};
private _mapC = if (_map <= 0 || {_map < 55}) then {_cBad} else {if (_map < 65 || {_map > 110}) then {_cWarn} else {_cGood}};
private _rrC = if (_rr <= 0 || {_rr < 8} || {_rr > 30}) then {_cBad} else {if (_rr < 10 || {_rr > 24}) then {_cWarn} else {_cGood}};
private _spC = if (_spo2 <= 0 || {_spo2 < 90}) then {_cBad} else {if (_spo2 < 94) then {_cWarn} else {_cGood}};
private _tempC = if (_temp < 32 || {_temp >= 40}) then {_cBad} else {if (_temp < 35 || {_temp >= 38.5}) then {_cWarn} else {_cGood}};

_left pushBack (["VITALS"] call _sect);
_left pushBack (["HR", _hr, _hrC, "BP", format ["%1/%2", _sys, _dia], _bpC] call _pair);
_left pushBack (["MAP", _map, _mapC, "RR", _rr, _rrC] call _pair);
_left pushBack (["SpO2", format ["%1%%", _spo2], _spC, "EtCO2", if (_etco2 < 0) then {"n/a"} else {round _etco2}, if (_etco2 < 0) then {_cMute} else {if (_etco2 < 20 || {_etco2 > 55}) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Temp", format ["%1 C", _temp toFixed 1], _tempC, "Pain", format ["%1%%", round (_pain * 100)], if (_pain > 0.8) then {_cBad} else {if (_pain > 0.4) then {_cWarn} else {_cGood}}] call _pair);
private _stateTxt = if (!alive _patient) then {"DEAD"} else {if (_arrest) then {"ARREST"} else {if (_uncon) then {"UNCON"} else {if (_crit) then {"CRITICAL"} else {"awake"}}}};
private _stateCol = if (!alive _patient || {_arrest}) then {_cCrit} else {if (_uncon || {_crit}) then {_cWarn} else {_cGood}};
_left pushBack (["State", _stateTxt, _stateCol, "CO", format ["%1 L/min", _coLMin toFixed 1], if (_coLMin <= 0.01) then {_cBad} else {if (_coLMin < 3) then {_cWarn} else {_cGood}}] call _pair);

// Perfusion / hemorrhage.
private _normalBlood = missionNamespace getVariable ["ACME_hypo_bloodNormal", 6];
private _circ = _patient getVariable ["ace_medical_bloodVolume", _patient getVariable ["ACME_circulatingVolume", _normalBlood]];
private _blood = _patient getVariable ["ACM_circulation_Blood_Volume", _normalBlood];
private _plasma = _patient getVariable ["ACM_circulation_Plasma_Volume", 0];
private _cryst = _patient getVariable ["ACM_circulation_Saline_Volume", 0];
private _over = _patient getVariable ["ACM_circulation_Overload_Volume", 0];
private _eff = ((_blood + (_plasma * 0.3) - _over) min _normalBlood) max 0;
private _bleedLps = if (!isNil "ace_medical_status_fnc_getBloodLoss") then {[_patient] call ace_medical_status_fnc_getBloodLoss} else {0};
private _bleedMlMin = (_bleedLps max 0) * 60000;
private _jBleed = (_patient getVariable ["ACME_junctionalBleedLPS", 0]) * 60000;
private _intBleed = if (!isNil "ACM_circulation_fnc_getInternalBleedingRate") then {(([_patient] call ACM_circulation_fnc_getInternalBleedingRate) max 0) * 60000} else {0};
private _hemoBleed = if (!isNil "ACM_circulation_fnc_getHemothoraxBleedingRate") then {(([_patient] call ACM_circulation_fnc_getHemothoraxBleedingRate) max 0) * 60000} else {0};
private _capBleed = if (!isNil "ACM_circulation_fnc_getCapillaryDamageBleedingRate") then {(([_patient] call ACM_circulation_fnc_getCapillaryDamageBleedingRate) max 0) * 60000} else {0};
private _totalBleed = _bleedMlMin + _jBleed + _intBleed + _hemoBleed + _capBleed;
private _vaso = _patient getVariable ["ACM_circulation_Vasoconstriction_State", 0];
private _plate = _patient getVariable ["ACM_circulation_Platelet_Count", 3];
private _calcium = _patient getVariable ["ACM_circulation_Calcium_Count", 0];
private _bvCol = if (_circ < 3.6) then {_cBad} else {if (_circ < 4.4) then {_cWarn} else {_cGood}};
private _bleedCol = if (_bleedMlMin >= 500) then {_cBad} else {if (_bleedMlMin >= 100) then {_cWarn} else {_cGood}};
_left pushBack (["PERFUSION / BLEEDING"] call _sect);
_left pushBack (["Circ", format ["%1L", _circ toFixed 2], _bvCol, "Eff", format ["%1L", _eff toFixed 2], if (_eff < 3.6) then {_cBad} else {if (_eff < 4.4) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Blood", format ["%1L", _blood toFixed 2], _cLabel, "Plasma", format ["%1L", _plasma toFixed 2], _cLabel] call _pair);
_left pushBack (["Cryst", format ["%1L", _cryst toFixed 2], _cLabel, "Over", format ["%1L", _over toFixed 2], if (_over > 0.5) then {_cWarn} else {_cMute}] call _pair);
_left pushBack (["Ext", format ["%1 mL/min", round _bleedMlMin], _bleedCol, "Junc", format ["%1 mL/min", round _jBleed], if (_jBleed > 0) then {_cBad} else {_cGood}] call _pair);
_left pushBack (["Internal", format ["%1", round _intBleed], if (_intBleed > 0) then {_cBad} else {_cGood}, "Hemo", format ["%1", round _hemoBleed], if (_hemoBleed > 0) then {_cBad} else {_cGood}] call _pair);
_left pushBack (["Cap", format ["%1", round _capBleed], if (_capBleed > 0) then {_cWarn} else {_cGood}, "SrcTot", format ["%1 mL/min", round _totalBleed], if (_totalBleed >= 500) then {_cBad} else {if (_totalBleed > 0) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Vaso", _vaso toFixed 2, _cLabel, "Plate", _plate toFixed 2, if (_plate < 1.5) then {_cWarn} else {_cGood}] call _pair);
private _pressor = _circState getOrDefault ["pressorSupport", 0];
private _svr = _patient getVariable ["ace_medical_peripheralResistance", 100];
_left pushBack (["Pressor", _pressor toFixed 2, if (_pressor > 0) then {_cGood} else {_cMute}, "SVR", round _svr, _cLabel] call _pair);
_left pushBack (["Ca", _calcium toFixed 2, _cLabel, "Coag", (_circState getOrDefault ["coagMult", 1]) toFixed 2, _cLabel] call _pair);

// Airway and chest.
private _airReflex = _patient getVariable ["ACM_airway_AirwayReflex_State", true];
private _collapse = _patient getVariable ["ACM_airway_AirwayCollapse_State", 0];
private _vomit = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
private _bloodObs = _patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0];
private _opa = _patient getVariable ["ACM_airway_AirwayItem_Oral", ""];
private _npa = _patient getVariable ["ACM_airway_AirwayItem_Nasal", ""];
private _ett = _patient getVariable ["ACME_ETT_Inserted", false];
private _cuff = _patient getVariable ["ACME_ETT_CuffInflated", false];
private _cric = _patient getVariable ["ACM_airway_SurgicalAirway_State", false];
private _ptx = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
private _tptx = _patient getVariable ["ACM_breathing_TensionPneumothorax_State", false];
private _hemo = _patient getVariable ["ACM_breathing_Hemothorax_State", 0];
private _hemoFluid = _patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0];
private _seal = _patient getVariable ["ACM_breathing_ChestSeal_State", false];
private _tubeL = _patient getVariable ["ACME_thora_tube_left", false];
private _tubeR = _patient getVariable ["ACME_thora_tube_right", false];
private _tractL = _patient getVariable ["ACME_thora_open_left", ""];
private _tractR = _patient getVariable ["ACME_thora_open_right", ""];
private _sealedL = _patient getVariable ["ACME_thora_sealed_left", false];
private _sealedR = _patient getVariable ["ACME_thora_sealed_right", false];
private _closedL = (_patient getVariable ["ACME_thora_closed_left", false]) || {_sealedL && {_tractL == "sealed"} && {!_tubeL}};
private _closedR = (_patient getVariable ["ACME_thora_closed_right", false]) || {_sealedR && {_tractR == "sealed"} && {!_tubeR}};
private _openL = _tractL == "finger" && {!_closedL};
private _openR = _tractR == "finger" && {!_closedR};
private _thoraL = if (_tubeL) then {"T"} else {if (_closedL) then {"C"} else {if (_openL) then {"O"} else {"-"}}};
private _thoraR = if (_tubeR) then {"T"} else {if (_closedR) then {"C"} else {if (_openR) then {"O"} else {"-"}}};
private _bvm = _patient getVariable ["ACM_breathing_isUsingBVM", false];
private _vent = _patient getVariable ["ACME_vent_driving", false];
// B125: classify the airway from ACM's actual patency result, not from a raw collapse latch. A mild collapse
// (C1) can still pass air, and a conscious casualty is explicitly patent in getAirwayState even if a stale collapse
// value has not been reconciled yet. Vomit/blood remain true obstructions and severe loss of patency stays red.
private _airwayPatency = if (!isNil "ACM_airway_fnc_getAirwayState") then {
    [_patient] call ACM_airway_fnc_getAirwayState
} else {
    if (_vomit > 0 || {_bloodObs > 0}) then {0} else {1 - ((_collapse min 3) / 3)}
};
private _fluidObstruction = (_vomit > 0) || {_bloodObs > 0};
private _airwayTxt = if (_ett) then {
    "ETT" + (if (_cuff) then {"+cuff"} else {""})
} else {if (_cric) then {
    "CRIC"
} else {if (_fluidObstruction || {_airwayPatency <= 0.20}) then {
    "OBSTRUCTED"
} else {if (_airwayPatency < 0.90) then {"NARROWED"} else {"OPEN"}}}};
private _airwayCol = if (_fluidObstruction || {_airwayPatency <= 0.20}) then {_cBad} else {if (_airwayPatency < 0.90) then {_cWarn} else {_cGood}};
private _obsCol = if (_vomit > 0 || {_bloodObs > 0} || {_collapse >= 3}) then {_cBad} else {if (_collapse > 0) then {_cWarn} else {_cGood}};
_left pushBack (["AIRWAY / CHEST"] call _sect);
_left pushBack (["Airway", _airwayTxt, _airwayCol, "Reflex", [_airReflex] call _yn, if (_airReflex) then {_cGood} else {_cWarn}] call _pair);
private _adj = [];
if (_opa != "") then {_adj pushBack "OPA";}; if (_npa != "") then {_adj pushBack "NPA";};
_left pushBack (["Adjunct", if (_adj isEqualTo []) then {"none"} else {_adj joinString "+"}, if (_adj isEqualTo []) then {_cMute} else {_cGood}, "Obs", format ["C%1 V%2 B%3", _collapse, _vomit, _bloodObs], _obsCol] call _pair);
_left pushBack (["PTX", _ptx, if (_ptx > 0) then {_cWarn} else {_cGood}, "TPTX", [_tptx] call _yn, [_tptx, true] call _ynCol] call _pair);
_left pushBack (["Hemo", format ["%1 / %2L", _hemo, _hemoFluid toFixed 2], if (_hemo > 0 || {_hemoFluid > 0.3}) then {_cWarn} else {_cGood}, "Seal", [_seal] call _yn, if (_seal) then {_cGood} else {_cMute}] call _pair);
_left pushBack (["Thora", format ["L:%1 R:%2", _thoraL, _thoraR], if (_tubeL || {_tubeR} || {_closedL} || {_closedR} || {_openL} || {_openR}) then {_cGood} else {_cMute}, "Support", format ["BVM:%1 V:%2", if (_bvm) then {"Y"} else {"-"}, if (_vent) then {"Y"} else {"-"}], if (_bvm || {_vent}) then {_cGood} else {_cMute}] call _pair);

// Neuro/TBI occupies main page because screenshots need to explain consciousness and ICP-related arrest.
private _tbi = _patient getVariable ["ACME_tbi_State", createHashMap];
private _icp = _tbi getOrDefault ["icp", 0];
private _cpp = _map - _icp;
private _tbiSev = _tbi getOrDefault ["severity", 0];
private _tbiStruct = _tbi getOrDefault ["structuralSeverity", _tbiSev];
private _tbiAutoreg = _tbi getOrDefault ["autoregIntegrity", 1];
private _tbiAutoInt = _tbi getOrDefault ["autonomicIntegrity", 1];
private _tbiTone = _tbi getOrDefault ["autonomicTone", 0];
private _hern = _tbi getOrDefault ["herniating", false];
private _cush = _tbi getOrDefault ["cushing", false];
private _obt = _patient getVariable ["ACME_obtunded", false];
_left pushBack (["NEURO / TBI"] call _sect);
_left pushBack (["Acute", _tbiSev toFixed 2, if (_tbiSev >= 0.65) then {_cBad} else {if (_tbiSev >= 0.30) then {_cWarn} else {_cGood}}, "Struct", _tbiStruct toFixed 2, if (_tbiStruct >= 0.80) then {_cBad} else {if (_tbiStruct >= 0.60) then {_cWarn} else {_cLabel}}] call _pair);
_left pushBack (["ICP", round _icp, if (_icp >= 30) then {_cBad} else {if (_icp > 20) then {_cWarn} else {_cGood}}, "CPP", round _cpp, if (_cpp < 50) then {_cBad} else {if (_cpp < 70) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Autoreg", _tbiAutoreg toFixed 2, if (_tbiAutoreg < 0.40) then {_cBad} else {if (_tbiAutoreg < 0.70) then {_cWarn} else {_cGood}}, "Auto", format ["%1 / %2", _tbiAutoInt toFixed 2, _tbiTone toFixed 2], if (_tbiTone < -0.35) then {_cBad} else {if (abs _tbiTone > 0.55) then {_cWarn} else {_cLabel}}] call _pair);
_left pushBack (["Hern", [_hern] call _yn, [_hern, true] call _ynCol, "Cushing", [_cush] call _yn, [_cush, true] call _ynCol] call _pair);
_left pushBack (["Obtund", [_obt] call _yn, if (_obt) then {_cWarn} else {_cMute}, "PerfOK", [(_tbi getOrDefault ["perfusionOK", true])] call _yn, if (_tbi getOrDefault ["perfusionOK", true]) then {_cGood} else {_cWarn}] call _pair);

// Resuscitation / rhythm.
private _nativeRh = _patient getVariable ["ACM_circulation_Cardiac_RhythmState", 0];
private _activeRh = _patient getVariable ["ACME_rhythm_active", 0];
private _aedRh = _patient getVariable ["ACM_circulation_AED_EKGRhythm", _nativeRh];
private _visualRh = if (_activeRh >= 100 && {!(_aedRh in [-1,1,2])}) then {_activeRh} else {_aedRh};
private _cpr = _patient getVariable ["ACM_circulation_isPerformingCPR", false];
private _revArr = _patient getVariable ["ACM_circulation_ReversibleCardiacArrest_State", false];
private _shockRes = _patient getVariable ["ACM_circulation_CardiacArrest_ShockResistant", false];
_right pushBack (["RHYTHM / RESUS"] call _sect);
_right pushBack (["Active", _activeRh, if (_activeRh >= 100 || {_nativeRh in [1,2,3,4,5]}) then {_cBad} else {_cGood}, "Native", _nativeRh, _cLabel] call _pair);
_right pushBack (["AED", _visualRh, if (_visualRh > 0) then {_cWarn} else {_cMute}, "CPR", [_cpr] call _yn, if (_cpr) then {_cGood} else {_cMute}] call _pair);
_right pushBack (["Arrest", [_arrest] call _yn, [_arrest, true] call _ynCol, "Rev", [_revArr] call _yn, if (_revArr) then {_cWarn} else {_cMute}] call _pair);
_right pushBack (["ShockR", [_shockRes] call _yn, if (_shockRes) then {_cWarn} else {_cMute}, "ROSCblk", _circState getOrDefault ["roscBlock", "-"], _cMute] call _pair);

// Hemostasis / devices.
private _jParts = ["leftarm", "rightarm", "leftleg", "rightleg"];
private _jTxt = [];
{private _s = _patient getVariable [format ["ACME_Junc_%1", _x], ""]; if (_s != "") then {_jTxt pushBack format ["%1:%2", _x select [0,2], _s];};} forEach _jParts;
// B129: ACM_disability_Tourniquet_Time is presentation data and may contain strings such as "13:37".
// Count the native ACE numeric tourniquet state instead, with a type guard for old/restored saves.
private _tq = _patient getVariable ["ace_medical_tourniquets", [0,0,0,0,0,0]];
private _tqCount = {_x isEqualType 0 && {_x > 0}} count _tq;
private _aajt = [];
if (_patient getVariable ["ACME_AAJT_zone3", false]) then {_aajt pushBack "Z3";};
if (_patient getVariable ["ACME_AAJT_inguinal", false]) then {_aajt pushBack format ["Ing-%1", _patient getVariable ["ACME_AAJT_inguinalSide", "?"]];};
if (_patient getVariable ["ACME_AAJT_axillaleft", false]) then {_aajt pushBack "AxL";};
if (_patient getVariable ["ACME_AAJT_axillaright", false]) then {_aajt pushBack "AxR";};
private _xstat = _patient getVariable ["ACME_XStat_needsSurgery", false];
private _dp = _patient getVariable ["ACME_DP_Active", false];
_right pushBack (["HEMOSTASIS / DEVICES"] call _sect);
_right pushBack (["TQ", _tqCount, if (_tqCount > 0) then {_cWarn} else {_cMute}, "DP", [_dp] call _yn, if (_dp) then {_cGood} else {_cMute}] call _pair);
_right pushBack (["Junc", if (_jTxt isEqualTo []) then {"none"} else {_jTxt joinString ","}, if (_jTxt isEqualTo []) then {_cMute} else {_cWarn}] call _one);
_right pushBack (["AAJT", if (_aajt isEqualTo []) then {"none"} else {_aajt joinString "+"}, if (_aajt isEqualTo []) then {_cMute} else {_cWarn}, "XStat", [_xstat] call _yn, if (_xstat) then {_cWarn} else {_cMute}] call _pair);
private _hpmk = _patient getVariable ["ACME_hpmk_state", ""];
private _fract = _patient getVariable ["ACM_disability_Fracture_State", [0,0,0,0,0,0]];
private _splints = _patient getVariable ["ace_medical_treatment_splints", [0,0,0,0,0,0]];
private _fractN = {_x > 0} count _fract;
private _splintN = {_x > 0} count _splints;
_right pushBack (["HPMK", if (_hpmk == "") then {"none"} else {_hpmk}, if (_hpmk in ["wrapped","exposed"]) then {_cGood} else {_cMute}, "Fr/Spl", format ["%1/%2", _fractN, _splintN], if (_fractN > _splintN) then {_cWarn} else {if (_fractN > 0) then {_cGood} else {_cMute}}] call _pair);

// Sedation and paralysis. Keep one compact block even when empty so a screenshot proves the state was checked.
([_patient] call ACME_fnc_sedationComponents) params ["_ket", "_prop", "_mid", "_fent", "_adjunct", "_sed"];
private _roc = [_patient] call ACME_fnc_rocuroniumOnBoard;
private _sedated = _patient getVariable ["ACME_ket_sedated", false];
private _par = _patient getVariable ["ACME_roc_paralyzed", false];
private _awakePar = _patient getVariable ["ACME_roc_awakeParalysis", false];
_right pushBack (["SEDATION / PARALYSIS"] call _sect);
_right pushBack (["Sed", _sed toFixed 2, if (_sed >= 1 || {_sedated}) then {_cGood} else {if (_sed > 0) then {_cWarn} else {_cMute}}, "Roc", _roc toFixed 2, if (_roc > 0.5) then {_cWarn} else {_cMute}] call _pair);
_right pushBack (["Ket", _ket toFixed 2, _cLabel, "Prop", _prop toFixed 2, _cLabel] call _pair);
_right pushBack (["Mid", _mid toFixed 2, _cLabel, "Fent", _fent toFixed 2, _cLabel] call _pair);
_right pushBack (["Paral", [_par] call _yn, if (_par) then {_cWarn} else {_cMute}, "Aware", [_awakePar] call _yn, if (_awakePar) then {_cCrit} else {_cGood}] call _pair);

// Cerebral seizure state is independent of motor expression under neuromuscular blockade.
private _szState = _patient getVariable ["ACME_lido_seizureState", ""];
private _szDrive = _patient getVariable ["ACME_seizure_drive", 0];
private _szSupp = _patient getVariable ["ACME_seizure_suppression", 0];
private _szControlled = _patient getVariable ["ACME_seizure_suppressed", false];
private _szMasked = _par && {_szState == "active"};
private _szMotor = if (_szState != "active") then {"none"} else {if (_szMasked) then {"MASKED"} else {"VISIBLE"}};
_right pushBack (["SEIZURE CONTROL"] call _sect);
_right pushBack (["Seiz", if (_szState == "") then {"none"} else {_szState}, if (_szState == "active") then {_cCrit} else {if (_szState == "postictal") then {_cWarn} else {_cMute}}, "Motor", _szMotor, if (_szMasked) then {_cWarn} else {if (_szState == "active") then {_cCrit} else {_cMute}}] call _pair);
_right pushBack (["Drive", _szDrive toFixed 2, _cLabel, "Suppress", _szSupp toFixed 2, if (_szControlled) then {_cGood} else {if (_szSupp > 0) then {_cWarn} else {_cMute}}] call _pair);

// Fluids / infusions: physical hung bags, with medication contents folded into the same line.
private _medEntries = _patient getVariable ["ACME_infusion_BagMedications", []];
private _ivMap = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _fluidRows = [];
private _bpShort = {
    params ["_bp"];
    switch (toLowerANSI _bp) do {
        case "leftarm": {"LA"}; case "rightarm": {"RA"};
        case "leftleg": {"LL"}; case "rightleg": {"RL"};
        case "body": {"B"}; default {_bp};
    }
};
private _fluidShort = {
    params ["_t"];
    switch (toLowerANSI _t) do {
        case "blood": {"Blood"}; case "freshblood": {"FreshB"}; case "plasma": {"Plasma"};
        case "saline": {"NS"}; case "acme_saliney": {"NS-Y"}; case "plasmalyte": {"PL"};
        case "hts": {"HTS"}; case "hypertonicsaline": {"HTS"}; case "mannitol": {"Mtol"};
        case "fbtk": {"FBTK"}; case "acme_empty": {""}; case "acme_emptysaline": {""};
        default {_t};
    }
};
{
    private _bp = _x;
    private _arrB = _y;
    {
        private _bag = _x;
        private _type = _bag param [0, ""];
        private _remain = _bag param [1, 0];
        private _site = _bag param [3, -1];
        private _isIV = _bag param [4, true];
        private _uid = _bag param [8, ""];
        if (_uid == "") then {_uid = [_patient, _bp, _forEachIndex] call ACME_fnc_bagIdentity;};
        private _short = [_type] call _fluidShort;
        if (_short != "" && {_remain > 0.01}) then {
            private _meds = _medEntries select {(_x param [23, ""]) == _uid && {(_x param [14, 0]) > 0.0001}};
            private _medNames = _meds apply {_x param [11, "?"]};
            private _what = _short + (if (_medNames isEqualTo []) then {""} else {"+" + (_medNames joinString "+")});
            private _where = format ["%1 %2%3", [_bp] call _bpShort, if (_isIV) then {"IV"} else {"IO"}, if (_site >= 0) then {str _site} else {""}];
            private _rate = if (_meds isEqualTo []) then {-1} else {(_meds select 0) param [21, 0]};
            _fluidRows pushBack [_what, _where, _remain, _rate];
        };
    } forEach _arrB;
} forEach _ivMap;
_right pushBack (["FLUIDS / INFUSIONS"] call _sect);
if (_fluidRows isEqualTo []) then {
    _right pushBack (["Bags", 0, _cGood, "Pressor", _pressor toFixed 2, if (_pressor > 0) then {_cGood} else {_cMute}] call _pair);
} else {
    // Every active bag stays on the clinical screenshot. Font fitting below handles unusually busy patients.
    for "_i" from 0 to ((count _fluidRows) - 1) do {
        (_fluidRows select _i) params ["_what", "_where", "_rem", "_rate"];
        private _tail = if (_rate >= 0) then {format ["%1mL/%2g", _rem toFixed 0, round _rate]} else {format ["%1mL", _rem toFixed 0]};
        _right pushBack format ["<t color='%1'>%2@%3</t> <t color='%4'>%5</t>", _cLabel, [_what] call _safe, [_where] call _safe, if (_rate == 0) then {_cWarn} else {_cGood}, _tail];
    };
};

// Metabolic/coagulation summary.
private _acid = _circState getOrDefault ["totalAcidosis", _circState getOrDefault ["acidosis", 0]];
private _paCO2 = _circState getOrDefault ["paCO2", 40];
private _coag = _circState getOrDefault ["coagMult", 1];
private _shock = _circState getOrDefault ["shockSeverity", 0];
_right pushBack (["METABOLIC"] call _sect);
_right pushBack (["Acid", _acid toFixed 2, if (_acid >= 0.65) then {_cBad} else {if (_acid >= 0.30) then {_cWarn} else {_cGood}}, "PaCO2", _paCO2 toFixed 0, if (_paCO2 > 70) then {_cBad} else {if (_paCO2 > 50) then {_cWarn} else {_cGood}}] call _pair);
_right pushBack (["Coag", _coag toFixed 2, if (_coag > 1.5) then {_cBad} else {if (_coag > 1.1) then {_cWarn} else {_cGood}}, "Shock", _shock toFixed 2, if (_shock > 0.6) then {_cBad} else {if (_shock > 0.2) then {_cWarn} else {_cGood}}] call _pair);
private _cbrnExp = _patient getVariable ["ACM_cbrn_Exposed_State", false];
private _cbrnCont = _patient getVariable ["ACM_cbrn_Contaminated_State", false];
private _cbrnAir = _patient getVariable ["ACM_cbrn_AirwayInflammation", 0];
private _cbrnLung = _patient getVariable ["ACM_cbrn_LungTissueDamage", 0];
if (_cbrnExp || {_cbrnCont} || {_cbrnAir > 0} || {_cbrnLung > 0}) then {
    _right pushBack (["CBRN", format ["E:%1 C:%2", if (_cbrnExp) then {"Y"} else {"-"}, if (_cbrnCont) then {"Y"} else {"-"}], _cWarn, "Air/Lung", format ["%1/%2", _cbrnAir toFixed 1, _cbrnLung toFixed 1], _cWarn] call _pair);
};

private _render = {
    params ["_s"];
    _ctrlL ctrlSetStructuredText parseText format ["<t size='%1' font='EtelkaMonospacePro'>%2</t>", _s, _left joinString "<br/>"];
    _ctrlR ctrlSetStructuredText parseText format ["<t size='%1' font='EtelkaMonospacePro'>%2</t>", _s, _right joinString "<br/>"];
};
[_scale] call _render;
private _need = (ctrlTextHeight _ctrlL) max (ctrlTextHeight _ctrlR);
if (_need > _h) then {
    private _fit = ((_scale * (((_h * 0.985) / _need) min 1)) max 0.34) min _scale;
    [_fit] call _render;
};
