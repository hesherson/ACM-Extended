/* Feed the existing browser sweeper from the ACM/ACME LifePak generators.
   Generated samples stay client-local; only ordinary device vitals use network replication. */
params ["_control", "_device", ["_ls", false], ["_force", false]];
private _prefix = ["acme_tempus", "acme_tempusls"] select _ls;
private _patient = _device getVariable [_prefix + "_pat", objNull];
private _powered = (_device getVariable [_prefix + "_pw", [false]]) select 0;
if (_ls) then {_powered=_powered && {(_device getVariable ["acme_tempusls_pads",true]) || {_device getVariable ["acme_tempusls_ecg",false]}};};
private _vitals = _device getVariable [_prefix + "_v", []];
private _episode = if (isNull _patient) then {-1} else {[_patient] call ACME_fnc_clinicalEpoch};
private _sensors=if (_ls) then {[true,true,true,true,true]} else {_device getVariable ["acme_tempus_sensors",[true,false,false,false,false]]};
private _signature = str [_patient, _powered, _vitals, _episode,_sensors];
private _changed = _force || {_signature isNotEqualTo (_control getVariable ["ACME_wave_signature", ""])};
if (!_changed && {diag_tickTime < (_control getVariable ["ACME_wave_next", 0])}) exitWith {};
_control setVariable ["ACME_wave_signature", _signature];
_control setVariable ["ACME_wave_next", diag_tickTime + 5.28];
private _ecg = []; _ecg resize [176, 0];
private _pleth = +_ecg;
private _capno = +_ecg;
if (_powered && {!isNull _patient} && {!(_vitals isEqualTo [])}) then {
    // The LifePak generator uses a selected target and cursor context. Restore both immediately,
    // so a Tempus view cannot redirect another monitor or mutate its beat/cursor state.
    private _oldTarget = missionNamespace getVariable ["ACM_circulation_AED_Monitor_Target", objNull];
    private _oldCursor = _patient getVariable "ACME_AED_MonitorCursorTime";
    private _oldStep = _patient getVariable "ACM_circulation_AED_UpdateStep";
    missionNamespace setVariable ["ACM_circulation_AED_Monitor_Target", _patient];
    _patient setVariable ["ACME_AED_MonitorCursorTime", CBA_missionTime];
    _patient setVariable ["ACM_circulation_AED_UpdateStep", 0];
    private _hr = [_patient] call ACM_circulation_fnc_getEKGHeartRate;
    private _rhythm = [_patient] call ACME_fnc_rhythmGet;
    private _cpr = alive (_patient getVariable ["ace_medical_CPR_provider", objNull]);
    private _argument = [_rhythm, -1] select _cpr;
    private _spacing = if (_hr > 0) then {60 / _hr * 15} else {0};
    _ecg = ([_argument, _spacing, 0] call ACM_circulation_fnc_displayAEDMonitor_generateEKG) select 0;
    private _perfusing = [_patient] call ACM_circulation_fnc_hasPulse;
    if (!_ls) then {
        private _saturation = _vitals param [5, 0];
        private _rr = _vitals param [6, 0];
        private _co2 = _vitals param [7, 0];
        private _pulseRhythm = [1, _argument] select (_perfusing || {_cpr});
        _pleth = ([_pulseRhythm, _spacing, 0, _saturation] call ACM_circulation_fnc_displayAEDMonitor_generatePO) select 0;
        _capno = ([_argument, _spacing, 0, _co2 max 0, _rr max 0] call ACM_circulation_fnc_displayAEDMonitor_generateCO) select 0;
    };
    missionNamespace setVariable ["ACM_circulation_AED_Monitor_Target", _oldTarget];
    _patient setVariable ["ACME_AED_MonitorCursorTime", if (isNil "_oldCursor") then {nil} else {_oldCursor}];
    _patient setVariable ["ACM_circulation_AED_UpdateStep", if (isNil "_oldStep") then {nil} else {_oldStep}];
};
if (!_ls) then {
    if !(_sensors select 0) then {_ecg=_ecg apply {0};};
    if !(_sensors select 1) then {_pleth=_pleth apply {0};};
    if !(_sensors select 3) then {_capno=_capno apply {0};};
};
// Lead profiles are simulated projections of ACME's ECG, not independently measured electrodes.
private _leads = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"];
private _factors = [0.56, 1, 0.44, -0.78, 0.06, 0.72, -0.35, -0.15, 0.55, 1.10, 0.95, 0.80];
private _packets = [format ['{"channel":"ecg","units":"acme","sampleRateHz":33.3333333333,"samples":%1}', _ecg apply {(round (_x * 100)) / 100}]];
{
    private _factor = _factors select _forEachIndex;
    private _samples = _ecg apply {(round (_x * _factor * 100)) / 100};
    _packets pushBack format ['{"channel":"ecg","lead":"%1","units":"acme","sampleRateHz":33.3333333333,"samples":%2}', _x, _samples];
} forEach _leads;
if (!_ls) then {
    _packets pushBack format ['{"channel":"pleth","units":"acme","sampleRateHz":33.3333333333,"samples":%1}', _pleth apply {(round (_x * 100)) / 100}];
    _packets pushBack format ['{"channel":"capno","units":"acme","sampleRateHz":33.3333333333,"samples":%1}', _capno apply {(round (_x * 100)) / 100}];
};
_control ctrlWebBrowserAction ["ExecJS", format ["%1.waveforms([%2],%3)", ["tp", "tls"] select _ls, _packets joinString ",", _changed]];
