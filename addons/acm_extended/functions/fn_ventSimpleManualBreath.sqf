/* SIMPLE manual breaths execute on the captured patient owner. Advanced manual
   delivery remains in fn_ventManualBreath. No UI state or device settings are written here. */
params [["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]], ["_custody", "", [""]], ["_epoch", -1], ["_issued", -999], ["_id", "", [""]], ["_episodeId", -1], ["_hops", 0]];
if (isNull _patient || {isNull _medic}) exitWith {};
if (!local _patient) exitWith {
    if (_hops < 4) then {
        ["ACME_ventSimpleManualBreath", [_patient, _medic, _custody, _epoch, _issued, _id, _episodeId, _hops + 1], _patient] call CBA_fnc_targetEvent;
    };
};
private _episode = _patient getVariable ["ACME_vent_simpleEpisode", [false, 0]];
if (_id == "" || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {_episodeId != (_episode select 1)}
    || {!(_episode select 0)}) exitWith {};
private _receipts = +(_patient getVariable ["ACME_vent_simpleManualReceipts", []]);
if (_id in _receipts) exitWith {};
_receipts pushBack _id;
if (count _receipts > 64) then {_receipts deleteAt 0;};
_patient setVariable ["ACME_vent_simpleManualReceipts", _receipts, false];
if (!(missionNamespace getVariable ["ACME_sys_vent", true])
    || {!(missionNamespace getVariable ["ACME_vent_simpleMode", false])}
    || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {!([_medic, "ventilator", true] call ACME_fnc_procedureAllowed)}
    || {!([_medic, _patient] call ACME_fnc_ventRecoveryNear)}
    || {_custody == ""} || {_custody != (_patient getVariable ["ACME_vent_custodyId", ""])}
    || {_patient getVariable ["ACME_vent_recovering", false]}
    || {(_patient getVariable ["ACME_vent_nivMask", false] || {[_patient] call ACME_fnc_ventMaskSelected})}
    || {!(_patient getVariable ["ACME_vent_circuit", false])}
    || {!(_patient getVariable ["ACME_vent_powerOn", false])}
    || {!(_patient getVariable ["ACME_vent_configured", false])}
    || {!(_patient getVariable ["ACME_vent_connected", false])}) exitWith {};
if ((missionNamespace getVariable ["ACME_vent_batteryEnabled", true])
    && {!(_patient getVariable ["ACME_vent_battExternal", false])}
    && {(_patient getVariable ["ACME_vent_battery", 100]) <= 0}) exitWith {};
private _ett = _patient getVariable ["ACME_ETT_Inserted", false];
private _cric = _patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false];
private _igel = (_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "SGA";
if (!_ett && {!_cric} && {!_igel}) exitWith {};
private _now = CBA_missionTime;
private _minGap = (missionNamespace getVariable ["ACME_vent_manualBreathMinGap", 1.5]) max 0.5;
if (_now - (_patient getVariable ["ACME_vent_manualBreathT", -999]) < _minGap) exitWith {};
private _effective = [_patient] call ACME_fnc_ventEffectiveSettings;
private _vt = _effective select 3;
private _peep = _effective select 5;
private _comp = ((_patient getVariable ["ACME_vent_compliance", 1])
    * ((_patient getVariable ["ACME_vent_complianceMult", 1]) max 0.20 min 1)) max 0.10 min 1;
private _auto = (_patient getVariable ["ACME_vent_autoPEEP", 0]) max 0 min 20;
private _pip = 8 + (12 * (_vt / 500) / _comp);
_vt = _vt * (1 - (0.20 * ((_patient getVariable ["ACME_vent_dyssync", 0]) max 0 min 1)));
private _limit = _effective select 11;
private _scale = (((_limit - _auto) max 0) / (_pip max 0.1)) min 1;
_vt = _vt * _scale;
_pip = (_pip min ((_limit - _auto) max 0)) + _auto;
private _ptx = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
private _leak = 0.03 + (0.10 * linearConversion [0, 3, _ptx, 0, 1, true]);
if ((_patient getVariable ["ACME_thora_tube_left", false]) || {_patient getVariable ["ACME_thora_tube_right", false]}) then {_leak = _leak + 0.08;};
if (!_ett) then {_leak = _leak + (if (_cric) then {0.06} else {0.12});};
private _vte = _vt * (1 - (_leak min 0.75));
[_patient, "ACME_vent_vti", round _vt] call ACME_fnc_setVarNet;
[_patient, "ACME_vent_vte", round _vte] call ACME_fnc_setVarNet;
[_patient, "ACME_vent_pip", round (_pip max _peep)] call ACME_fnc_setVarNet;
private _times = +(_patient getVariable ["ACME_vent_manualBreathTimes", []]);
_times = _times select {_now - _x <= 60};
_times pushBack _now;
_patient setVariable ["ACME_vent_manualBreathTimes", _times, false];
[_patient, "ACME_vent_manualRR", count _times] call ACME_fnc_setVarNet;
_patient setVariable ["ACME_vent_manualBreathT", _now, false];
[_patient, "ACME_vent_manualBreathServer", serverTime] call ACME_fnc_setVarNet;
private _volumes = +(_patient getVariable ["ACME_vent_simpleManualVolumes", []]);
_volumes = _volumes select {_now - (_x select 0) <= 60};
_volumes pushBack [_now, _vte];
if (count _volumes > 128) then {_volumes deleteAt 0;};
_patient setVariable ["ACME_vent_simpleManualVolumes", _volumes, false];
["ACME_ventSimpleManualAccepted", [_patient, _medic, _custody], _medic] call CBA_fnc_targetEvent;
// Mechanical breaths remain possible after death, but cannot restart physiology.
// A completely ineffective breath cannot establish an oxygenation provider.
if (alive _patient && {_vte > 150}) then {
    private _provider = _patient getVariable ["ACM_breathing_BVM_provider", objNull];
    if (isNull _provider || {_provider isEqualTo _patient}) then {
        [_patient, [["bvmProvider", _patient], ["bvmLastBreath", _now], ["bvmConnectedOxygen", true], ["bvmLastBreathOxygen", _now]], true] call ACM_breathing_fnc_setRuntimeState;
        _patient setVariable ["ACME_bvm_lastBreathServer", serverTime, true];
    };
};
