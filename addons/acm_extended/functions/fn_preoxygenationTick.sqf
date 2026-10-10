/*
 * ACME oxygen-reserve / preoxygenation layer.
 *
 * Builds a patient-specific reserve when they are effectively oxygenated, then spends it during apnea or near-apnea.
 * It does not replace ACE/ACM oxygen physiology.  It only damps an otherwise instantaneous/over-fast saturation fall
 * while reserve remains, so preoxygenation before RSI has a real payoff and sick lungs/anemia/altitude burn through it.
 */
private _now = CBA_missionTime;
private _candidate = {
    params ["_u"];
    if (isNull _u || {!local _u} || {!alive _u}) exitWith {false};
    private _reserve = (_u getVariable ["ACME_preox_reserve",0.30]) max 0 min 1;
    private _rr = _u getVariable ["ACME_resp_neuralRR", (_u getVariable ["ACM_breathing_RespirationRate",16])];
    private _support = alive (_u getVariable ["ACM_breathing_BVM_Medic",objNull])
        || {_u getVariable ["ACME_vent_onPatient",false]}
        || {_u getVariable ["ACME_nrb_on",false]};
    private _physiology = (_rr <= 2)
        || {_u getVariable ["ACE_isUnconscious",false]}
        || {_u getVariable ["ace_medical_inCardiacArrest",false]}
        || {(_u getVariable ["ace_medical_spo2",97]) < 94}
        || {(_u getVariable ["ACME_blastLung_State",0]) > 0}
        || {(_u getVariable ["ACME_aspiration_load",0]) > 0.001}
        || {(_u getVariable ["ACME_alt_pRatio",1]) < 0.999};
    abs (_reserve - 0.30) > 0.001 || {_support} || {_physiology}
};
private _patients = (missionNamespace getVariable ["ACME_preox_activePatients", []]) select {[_x] call _candidate};
{
    private _u = _x;
    if (isNull _u || {!local _u} || {!alive _u}) then {continue};

    // Healthy room-air units must be network-silent. Only enter the full model when
    // reserve is displaced from baseline, oxygen/support is active, or physiology
    // can actually spend/limit reserve. This keeps the 1 Hz discovery pass cheap.
    private _reserveProbe = (_u getVariable ["ACME_preox_reserve", 0.30]) max 0 min 1;
    private _rrProbe = _u getVariable ["ACME_resp_neuralRR", (_u getVariable ["ACM_breathing_RespirationRate", 16])];
    private _supportProbe = alive (_u getVariable ["ACM_breathing_BVM_Medic", objNull])
        || {_u getVariable ["ACME_vent_onPatient", false]}
        || {_u getVariable ["ACME_nrb_on", false]};
    private _physProbe = (_rrProbe <= 2)
        || {_u getVariable ["ACE_isUnconscious", false]}
        || {_u getVariable ["ace_medical_inCardiacArrest", false]}
        || {(_u getVariable ["ace_medical_spo2", 97]) < 94}
        || {(_u getVariable ["ACME_blastLung_State", 0]) > 0}
        || {(_u getVariable ["ACME_aspiration_load", 0]) > 0.001}
        || {(_u getVariable ["ACME_alt_pRatio", 1]) < 0.999};
    if (abs (_reserveProbe - 0.30) <= 0.001 && {!_supportProbe} && {!_physProbe}) then {continue};

    private _lastAt = _u getVariable ["ACME_preox_lastTick", _now - 1];
    private _dt = ((_now - _lastAt) max 0) min 3;
    _u setVariable ["ACME_preox_lastTick", _now, false];
    if (_dt <= 0) then {continue};

    private _spo2 = _u getVariable ["ace_medical_spo2", 97];
    private _lastSpo2 = _u getVariable ["ACME_preox_lastSpO2", _spo2];
    private _reserve = (_u getVariable ["ACME_preox_reserve", 0.30]) max 0 min 1;

    private _rr = _u getVariable ["ACME_resp_neuralRR", (_u getVariable ["ACM_breathing_RespirationRate", 16])];
    private _airway = if (!isNil "ACM_airway_fnc_getAirwayState") then {[_u] call ACM_airway_fnc_getAirwayState} else {_u getVariable ["ACM_airway_AirwayState",1]};
    private _breathing = if (!isNil "ACM_breathing_fnc_getBreathingState") then {[_u] call ACM_breathing_fnc_getBreathingState} else {_u getVariable ["ACM_breathing_BreathingState",1]};
    private _hasPulse = if (!isNil "ACM_circulation_fnc_hasPulse") then {[_u] call ACM_circulation_fnc_hasPulse} else {true};

    private _spontaneous = _hasPulse && {_rr > 1} && {_airway > 0.05} && {_breathing > 0.05};
    private _bvm = alive (_u getVariable ["ACM_breathing_BVM_Medic", objNull]);
    private _vent = (_u getVariable ["ACME_vent_onPatient", false]) && {_u getVariable ["ACME_vent_driving", false]};
    private _nrb = (_u getVariable ["ACME_nrb_on", false]) && {_u getVariable ["ACME_nrb_hasO2", false]}
        && {(_now - (_u getVariable ["ACME_nrb_lastO2Uptake", -1000])) < 3};

    private _fio2Frac = 0.21;
    if (_nrb) then {_fio2Frac = _fio2Frac max 0.90;};
    if (_bvm) then {_fio2Frac = _fio2Frac max 0.95;};
    if (_vent && {!isNil "ACME_fnc_ventEffectiveSettings"}) then {
        private _vs = [_u] call ACME_fnc_ventEffectiveSettings;
        _fio2Frac = _fio2Frac max (((_vs param [4,21]) / 100) max 0.21 min 1);
    };

    // Lung pathology and altitude reduce how much useful oxygen reserve can actually be built.
    private _blast = (_u getVariable ["ACME_blastLung_State",0]) max 0 min 1;
    private _edema = linearConversion [0.2,1.6,(_u getVariable ["ACM_circulation_Overload_Volume",0]),0,1,true];
    private _asp = (_u getVariable ["ACME_aspiration_load",0]) max 0 min 1;
    private _pRatio = (_u getVariable ["ACME_alt_pRatio",1]) max 0.45 min 1.1;
    private _lungPenalty = ((0.35 * _blast) + (0.30 * _edema) + (0.35 * _asp)) min 0.75;
    private _reserveCeiling = (1 - _lungPenalty) * linearConversion [0.55,1,_pRatio,0.55,1,true];
    _reserveCeiling = (_reserveCeiling max 0.20) min 1;

    private _effectiveVent = _bvm || {_vent} || {_spontaneous};
    private _supplemental = _fio2Frac > 0.22;
    if (_effectiveVent && {_supplemental} && {_spo2 >= 92}) then {
        private _oxygenBonus = linearConversion [0.22,1,_fio2Frac,0,1,true];
        private _buildPerSec = 0.0012 + (0.0032 * _oxygenBonus); // ~3-5 min from ordinary reserve to full preoxygenation.
        if (_spo2 >= 96) then {_buildPerSec = _buildPerSec * 1.25;};
        _reserve = (_reserve + (_buildPerSec * _dt)) min _reserveCeiling;
    };

    private _apneic = !_bvm && {!_vent} && {!_spontaneous || {_rr <= 2}};
    if (_apneic && {_hasPulse}) then {
        private _bloodVol = _u getVariable ["ACM_circulation_Blood_Volume",6];
        private _anemiaF = linearConversion [5.0,2.5,_bloodVol,1,2.4,true];
        private _shockF = 1 + (0.8 * ((_u getVariable ["ACME_shock_severity",0]) max 0 min 1));
        private _lungF = 1 + (1.5 * _lungPenalty);
        private _altF = linearConversion [1,0.55,_pRatio,1,1.8,true];
        private _hr = (_u getVariable ["ace_medical_heartRate",80]) max 20;
        private _metabolicF = linearConversion [60,180,_hr,0.8,1.6,true];
        private _burn = 0.0032 * _anemiaF * _shockF * _lungF * _altF * _metabolicF;
        _reserve = (_reserve - (_burn * _dt)) max 0;

        // If ACE/ACM already dropped saturation this tick, retain a fraction of that loss while reserve exists.
        // Severe pulmonary pathology still falls quickly because it both lowers the ceiling and accelerates reserve use.
        if (_spo2 < _lastSpo2 && {_reserve > 0}) then {
            private _retain = (0.15 + (0.80 * _reserve)) * (1 - (0.55 * _lungPenalty));
            private _buffered = _spo2 + ((_lastSpo2 - _spo2) * (_retain max 0 min 0.92));
            if (_buffered > _spo2) then {
                [_u, [["spo2", (_buffered min 100), true, true]]] call ACM_core_fnc_setAceMedicalState;
                _spo2 = _buffered;
            };
        };
    } else {
        // Room air owns a neutral baseline of 0.30. It may restore a spent reserve,
        // but it must never manufacture "preoxygenation" or retain supplemental reserve forever.
        if (_effectiveVent && {!_supplemental} && {_spo2 >= 94}) then {
            private _baselineStep = 0.0008 * _dt;
            if (_reserve < 0.30) then {_reserve = (_reserve + _baselineStep) min 0.30;};
            if (_reserve > 0.30) then {_reserve = (_reserve - _baselineStep) max 0.30;};
        };
    };

    // Replicated object state already survives JIP. Stable reserve needs no heartbeat;
    // changes and ownership transfer are sufficient publication triggers.
    [_u,"ACME_preox_reserve",_reserve,([0.005,0] select (abs (_reserve - 0.30) <= 0.000001)),0] call ACME_fnc_setVarNetApprox;
    _u setVariable ["ACME_preox_lastSpO2", _spo2, false];
    // Publish only the coarse label transition; setVarNet suppresses unchanged state.
    [_u,"ACME_preox_state",if (_reserve >= 0.80) then {"preoxygenated"} else {if (_reserve >= 0.40) then {"partial"} else {"low"}}] call ACME_fnc_setVarNet;
} forEach _patients;
ACME_preox_activePatients = _patients select {[_x] call _candidate};
