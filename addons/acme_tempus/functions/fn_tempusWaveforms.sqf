/* Continuous sample blocks on a control-local clock. Only a changed patient/device episode resets the strip. */
params ["_control","_device",["_ls",false],["_force",false]];
private _prefix = ["acme_tempus","acme_tempusls"] select _ls;
private _api = ["tp","tls"] select _ls;
private _patient = _device getVariable [_prefix+"_pat",objNull];
private _power = _device getVariable [_prefix+"_pw",[false]];
private _vitals = _device getVariable [_prefix+"_v",[]];
private _episode = if (isNull _patient) then {-1} else {[_patient] call ACME_fnc_clinicalEpoch};
private _session = [_device,_patient,_power param [0,false],_power param [1,0],_episode];
private _newSession = _session isNotEqualTo (_control getVariable ["ACME_wave_session",[]]);
private _now = diag_tickTime;
if (_newSession || _force) then {
    _control setVariable ["ACME_wave_session",_session];
    _control setVariable ["ACME_wave_cursor",0];
    _control setVariable ["ACME_wave_origin",_now];
    _control setVariable ["ACME_wave_missionOrigin",CBA_missionTime];
    _control setVariable ["ACME_wave_beat",[]];
    _control setVariable ["ACME_wave_hasRate",false];
    _control setVariable ["ACME_wave_resp",[]];
    _control ctrlWebBrowserAction ["ExecJS",_api+".resetWaveforms()"];
};
if (!(_power select 0) || {isNull _patient} || {_device distance _patient > 6}) exitWith {};
private _step = 0.03;
private _count = 40;
private _origin = _control getVariable ["ACME_wave_origin",_now];
private _elapsed = (_now - _origin) max 0;
private _column = _control getVariable ["ACME_wave_cursor",0];
if (_column * _step > _elapsed + 0.65) exitWith {};
// After a real stall skip expired sample time, never replay it as new beats.
_column = _column max (floor (_elapsed / _step) - 3);
private _offset = _column * _step;
private _at = (_control getVariable ["ACME_wave_missionOrigin",CBA_missionTime]) + _offset;
_control setVariable ["ACME_wave_cursor",_column+_count];
private _sensors = _device getVariable ["acme_tempus_sensors",[true,false,false,false,false]];
private _ecgOn = if (_ls) then {(_device getVariable ["acme_tempusls_pads",true]) || {_device getVariable ["acme_tempusls_ecg",false]}} else {_sensors select 0};
private _cpr = alive (_patient getVariable ["ace_medical_CPR_provider",objNull]);
private _rhythm = if (alive _patient) then {[_patient] call ACME_fnc_rhythmGet} else {1};
if (_cpr) then {_rhythm = -1;};
private _hr = [_patient] call ACM_circulation_fnc_getEKGHeartRate;
if (_cpr) then {_hr = 110;};
if (!_cpr && {alive _patient} && {[_patient] call ACM_circulation_fnc_recentAEDShock}) then {_rhythm = 1;_hr = 0;};
private _rr = 60 / (_hr max 1);
private _clock = _control getVariable ["ACME_wave_beat",[]];
if ((_hr > 0) isNotEqualTo (_control getVariable ["ACME_wave_hasRate",false])) then {
    _clock = [];
    _control setVariable ["ACME_wave_hasRate",_hr > 0];
};
private _plan = [_at,_at+_step*_count,_rr,_rhythm,_clock] call ACME_fnc_tempusBeatPlan;
_plan params ["_carry","_beats"];
_control setVariable ["ACME_wave_beat",_carry];
private _pulseIndex = 1;
if (!_ls && {_vitals isEqualTo []} && {(_sensors select 1) || {_sensors select 3}}) then {
    _vitals = [_patient] call ACME_fnc_tempusVitals;
};
private _ecg = []; _ecg resize [_count,0];
private _pleth = +_ecg;
private _capno = +_ecg;
private _markers = [];
private _phases = [];
if (_ecgOn) then {
    private _sample = [_rhythm,0,0,[_patient,_at,_hr,_count,_beats]] call ACM_circulation_fnc_displayAEDMonitor_generateEKG;
    _ecg = (_sample select 0) select [0,_count];
    _phases = (_sample param [3,[]]) select [0,_count];
    if (_ls && {(_device getVariable ["acme_tempusls_pads",true])}
        && {_rhythm in [0,4,5,100,101,103,104]} && {(_sample param [2,[]]) isNotEqualTo []}
        && {([_patient] call ACME_fnc_ecgArtifactStrength) < 0.8}) then {
        _markers = (_sample param [2,[]]) select {_x < _count};
    };
};
if (!_ls && {_vitals isNotEqualTo []}) then {
    private _saturation = _vitals param [5,0];
    private _respRate = _vitals param [6,0];
    private _co2 = _vitals param [7,-1];
    private _perfusing = [_patient] call ACM_circulation_fnc_hasPulse;
    private _breathPeriod = 60 / (_respRate max 1);
    private _breath = _control getVariable ["ACME_wave_resp",[_at,_breathPeriod]];
    _breath params [["_breathAt",_at],["_oldPeriod",_breathPeriod]];
    if (_at - _breathAt > 12 || {_at < _breathAt}) then {_breathAt = _at;};
    private _phase = ((_at - _breathAt) / _oldPeriod) mod 1;
    _breathAt = _at - _phase * _breathPeriod;
    _control setVariable ["ACME_wave_resp",[_breathAt,_breathPeriod]];
    for "_i" from 0 to (_count-1) do {
        private _time = _at+_i*_step;
        if ((_sensors select 1) && {_saturation>0} && {_perfusing || {_cpr}} && {_hr>0}) then {
            private _pulseTime = _time - 0.10;
            while {_pulseIndex+1 < count _beats && {((_beats select (_pulseIndex+1)) select 0) <= _pulseTime}} do {
                _pulseIndex = _pulseIndex+1;
            };
            private _pulseBeat = (_beats select _pulseIndex) select 0;
            private _pulseRR = ((_beats param [_pulseIndex+1,[_pulseBeat+_rr]]) select 0) - _pulseBeat;
            private _pulse = ((_pulseTime-_pulseBeat)/_pulseRR) max 0 min 1;
            private _height = if (_pulse < 0.22) then {_pulse/0.22} else {(1-_pulse)/0.78};
            _pleth set [_i,round (-50*_height*_height*_saturation/100)];
        };
        if ((_sensors select 3) && {_respRate>0} && {_co2>0}) then {
            private _point = ((_time-_breathAt)/_breathPeriod) mod 1;
            private _height = (linearConversion [0.26,0.38,_point,0,1,true]) * (linearConversion [0.83,0.90,_point,1,0,true]);
            _capno set [_i,round (-3*_co2*_height)];
        };
    };
};
private _leads = if (_ls) then {["I","II","III"]} else {["I","II","III","AVR","AVL","AVF","V1","V2","V3","V4","V5","V6"]};
private _packets = [];
{
    private _lead = _x;
    private _trace = [_lead,_ecg,_phases] call ACME_fnc_tempusProjectLead;
    _packets pushBack format ['{"channel":"ecg","lead":"%1","units":"acme","sampleRateHz":33.3333333333,"samples":%2}',_lead,_trace];
} forEach _leads;
if (!_ls) then {
    _packets pushBack format ['{"channel":"pleth","units":"acme","sampleRateHz":33.3333333333,"samples":%1}',_pleth];
    _packets pushBack format ['{"channel":"capno","units":"acme","sampleRateHz":33.3333333333,"samples":%1}',_capno];
};
// Keep browser messages small, and commit the whole sample block on the same sweep clock.
for "_first" from 0 to (count _packets - 1) step 3 do {
    private _part = (_packets select [_first,3]) joinString ",";
    _control ctrlWebBrowserAction ["ExecJS",format ["%1.waveformPart(%2,%3,%4,[%5],%6,%7)",
        _api,_offset,_elapsed,_first,_part,count _packets,_markers]];
};
