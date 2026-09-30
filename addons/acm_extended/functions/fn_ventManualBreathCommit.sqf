/* Advanced/manual ventilator breath clinical commit. Runs on the casualty owner.
   The operator UI only requests a breath; refractory timing, gas-exchange timestamps, breath ledgers and
   barotrauma are all serialized with the same owner that runs the patient's physiology. */
params [
    ["_patient", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_custody", "", [""]],
    ["_epoch", -1, [0]],
    ["_id", "", [""]]
];
if (isNull _patient || {isNull _medic}) exitWith {false};
if (!local _patient) exitWith {
    [_patient, "ventManualBreath", [_patient, _medic, _custody, _epoch, _id]] call ACME_fnc_ownerDispatch;
    true
};
if (_id == "" || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {false};

private _receipts = +(_patient getVariable ["ACME_vent_manualReceipts", []]);
if (_id in _receipts) exitWith {false};
_receipts pushBack _id;
if (count _receipts > 64) then {_receipts deleteAt 0;};
_patient setVariable ["ACME_vent_manualReceipts", _receipts, false];

if (!(missionNamespace getVariable ["ACME_sys_vent", true])
    || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {!([_medic, "ventilator", true] call ACME_fnc_procedureAllowed)}
    || {!([_medic, _patient] call ACME_fnc_ventRecoveryNear)}
    || {_custody == ""} || {_custody != (_patient getVariable ["ACME_vent_custodyId", ""])}
    || {_patient getVariable ["ACME_vent_recovering", false]}
    || {!(_patient getVariable ["ACME_vent_configured", false])}
    || {!(_patient getVariable ["ACME_vent_connected", false])}
    || {(_patient getVariable ["ACME_vent_iface", ""]) != "INVASIVE"}) exitWith {false};

private _ett = _patient getVariable ["ACME_ETT_Inserted", false];
private _igel = ((_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) isEqualTo "SGA");
private _cric = _patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false];
if (!_ett && {!_igel} && {!_cric}) exitWith {false};

private _now = CBA_missionTime;
private _minGap = (missionNamespace getVariable ["ACME_vent_manualBreathMinGap", 1.5]) max 0.5;
if ((_now - (_patient getVariable ["ACME_vent_manualBreathT", -999])) < _minGap) exitWith {false};

private _vtSet = (_patient getVariable ["ACME_vent_vt", 500]) max 1;
private _fio2 = _patient getVariable ["ACME_vent_fio2", 21];
private _comp = _patient getVariable ["ACME_vent_compliance", 1];
if (_comp <= 0) then {_comp = 1;};
private _vti = _vtSet;
private _pip = 8 + (12 * (_vtSet / 500) / _comp);
private _ptx = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
private _leak = 0.03;
if (_ptx > 0) then {_leak = _leak + (0.10 * (linearConversion [0, 3, _ptx, 0, 1, true]));};
if ((_patient getVariable ["ACME_thora_tube_left", false]) || {_patient getVariable ["ACME_thora_tube_right", false]}) then {
    _leak = _leak + 0.08;
};
_leak = _leak min 0.45;
private _vte = _vti * (1 - _leak);

[_patient, "ACME_vent_vti", round _vti] call ACME_fnc_setVarNet;
[_patient, "ACME_vent_vte", round _vte] call ACME_fnc_setVarNet;
[_patient, "ACME_vent_pip", round _pip] call ACME_fnc_setVarNet;

// Device controls and pressure/volume feedback remain usable on a corpse.
// Engine death cannot re-establish gas exchange or a native BVM provider.
if (alive _patient) then {
    private _o2 = _fio2 > 21;
    private _bvmState = [["bvmLastBreath", _now], ["bvmConnectedOxygen", _o2]];
    if (_o2) then {_bvmState pushBack ["bvmLastBreathOxygen", _now];};
    private _provider = _patient getVariable ["ACM_breathing_BVM_provider", objNull];
    if (isNull _provider || {_provider isEqualTo _patient}) then {_bvmState pushBack ["bvmProvider", _patient];};
    [_patient, _bvmState, true] call ACM_breathing_fnc_setRuntimeState;
    _patient setVariable ["ACME_bvm_lastBreathServer", serverTime, true];
};

private _times = +(_patient getVariable ["ACME_vent_manualBreathTimes", []]);
_times pushBack _now;
_times = _times select {(_now - _x) <= 60};
_patient setVariable ["ACME_vent_manualBreathTimes", _times, false];
[_patient, "ACME_vent_manualRR", count _times] call ACME_fnc_setVarNet;
_patient setVariable ["ACME_vent_manualBreathT", _now, false];
[_patient, "ACME_vent_manualBreathServer", serverTime] call ACME_fnc_setVarNet;

private _pipDanger = missionNamespace getVariable ["ACME_vent_baroPIPThreshold", 35];
if (alive _patient && {_pip > _pipDanger}) then {
    [_patient, "ACME_vent_baroDose", (_patient getVariable ["ACME_vent_baroDose", 0]) + 0.02] call ACME_fnc_setVarNet;
};

["ACME_ventManualAccepted", [_patient, _medic, _custody], _medic] call CBA_fnc_targetEvent;
true
