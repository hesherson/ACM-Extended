/* NA3 pressure composition. [unit, includeExtended, omitTBI] -> [diastolic,systolic]. */
params ["_unit", ["_includeExtended", true], ["_omitTBI", false], ["_resistanceProbe", -1, [0]]];
if (isNull _unit) exitWith {[0, 0]};
// True PEA has organized electrical activity but no mechanical circulation. No modifier may manufacture a pressure.
if (([_unit] call ACME_fnc_rhythmGet) == 5) exitWith {[0, 0]};

// modifier_bp_high and modifier_bp_low, chosen by ACM so the default co times the default resistance gives 120
// over 80.
private _MODIFIER_BP_HIGH = 9.4736842;
private _MODIFIER_BP_LOW  = 6.3157894;

private _cardiacOutput = [_unit] call ace_medical_status_fnc_getCardiacOutput;

// ACME disease preload effects reduce effective filling without falsifying RBC/blood loss.
// Burn capillary leak is expressed as an effective-volume deficit, so IV fluid can partially
// restore filling. Sepsis supplies a separate relative-preload multiplier. Native probes
// (_includeExtended=false) deliberately remain free of these ACME additions.
if (_includeExtended) then {
    private _burnDeficit = (_unit getVariable ["ACM_burns_EffectiveVolumeDeficitL",0]) max 0;
    private _bloodNow = (_unit getVariable ["ACM_circulation_Blood_Volume",6]) max 0;
    private _salineNow = (_unit getVariable ["ACM_circulation_Saline_Volume",0]) max 0;
    private _plasmaNow = (_unit getVariable ["ACM_circulation_Plasma_Volume",0]) max 0;
    private _totalNow = (_bloodNow + _salineNow + _plasmaNow) max 0.1;
    private _burnPreloadFrac = (((_totalNow - _burnDeficit) max 0.1) / _totalNow) max 0.25 min 1;
    private _burnCO = _burnPreloadFrac ^ 1.35;
    private _sepsisCO = (_unit getVariable ["ACM_infection_Preload_Mult",1]) max 0.55 min 1;
    _cardiacOutput = _cardiacOutput * _burnCO * _sepsisCO;
};

private _resistance = _unit getVariable ["ace_medical_peripheralResistance", 100];
if (!_includeExtended) then {_resistance = _unit getVariable ["ACME_nativeResistance", _resistance];};
if (_includeExtended && {_omitTBI}) then {_resistance = _resistance - (_unit getVariable ["ACME_resistanceApplied_tbi", 0]);};
if (_resistanceProbe >= 0 && {finite _resistanceProbe}) then {_resistance = _resistanceProbe;};
_resistance = _resistance max 1;
private _bloodPressure = _cardiacOutput * _resistance;

private _HR = _unit getVariable ["ace_medical_heartRate", 80];
if (_HR > 140) then {
    _bloodPressure = _bloodPressure * (linearConversion [140, 200, _HR, 1, 0.75, true]);
} else {
    if (_HR < 70) then {
        _bloodPressure = _bloodPressure * (linearConversion [70, 50, _HR, 1, 0.75, true]);
    };
};

private _bloodVolume = _unit getVariable ["ace_medical_bloodVolume", 6];
if (_bloodVolume < 4.8) then {
    _bloodPressure = _bloodPressure * (linearConversion [4.8, 3.6, _bloodVolume, 1, 0.5, true]);
};

private _bleedEffect = 1 - (0.2 * (_unit getVariable ["ace_medical_woundBleeding", 0]));
private _hemothoraxBleeding = 0.5 * ((_unit getVariable ["ACM_breathing_Hemothorax_State", 0]) / 10);
private _internalBleedingEffect = 1 min (1 - (0.8 * ((_unit getVariable ["ACM_damage_InternalBleeding", 0]) + _hemothoraxBleeding))) max 0.5;

private _tensionEffect = 0;
private _HTXFluid = _unit getVariable ["ACM_breathing_Hemothorax_Fluid", 0];
private _PTXState = _unit getVariable ["ACM_breathing_Pneumothorax_State", 0];

private _overloadEffect = linearConversion [0, 1, (_unit getVariable ["ACM_circulation_Overload_Volume", 0]), 1, 1.5];

private _poisonEffect = 1;
if (missionNamespace getVariable ["ACM_CBRN_enable", false]) then {
    _poisonEffect = linearConversion [0, 100, (_unit getVariable ["ACM_CBRN_CapillaryDamage", 0]), 1, 0.7];
};

private _diastolicModifier = 1;
if (_bloodVolume < 6) then {
    _diastolicModifier = linearConversion [5.1, 4.2, _bloodVolume, 1, 1.2, true];
};

if (_PTXState > 0 || {_HTXFluid > 0.1}) then {
    _tensionEffect = (_PTXState * 8) max (_HTXFluid / 46);
};

if ((_unit getVariable ["ACM_breathing_TensionPneumothorax_State", false]) || {_unit getVariable ["ACM_breathing_Hardcore_Pneumothorax", false]}) then {
    // the one ACME change. the full penalty is still 35, and it is reached at severity 1.
    // the floor keeps a freshly tensioned chest worse than the state 4 pneumothorax it came from, so the numbers
    // never improve at the moment it tensions.
    private _sev = _unit getVariable ["ACME_ptx_tensionSeverity", 1];
    if !(_sev isEqualType 0) then { _sev = 1 };
    _tensionEffect = (35 * (_sev max 0 min 1)) max _tensionEffect;
};

private _bp = [
    (round (((_bloodPressure * _MODIFIER_BP_LOW * _diastolicModifier) - _tensionEffect) * _bleedEffect * _internalBleedingEffect * _overloadEffect * _poisonEffect)) max 0,
    (round (((_bloodPressure * _MODIFIER_BP_HIGH) - _tensionEffect) * _bleedEffect * _internalBleedingEffect * _overloadEffect * _poisonEffect)) max 0
];
if (!_includeExtended) exitWith {_bp};
// No residual modifier can manufacture pressure in a patient with no mechanical output.
if (_cardiacOutput <= 0 || {!alive _unit}) exitWith {[0,0]};
_bp params ["_dia", "_sys"];
if (!_omitTBI && {missionNamespace getVariable ["ACME_sys_tbi", true]}) then {
    private _ppTarget = _unit getVariable ["ACME_tbi_pulsePressureTarget", -1];
    if (_ppTarget >= 0) then {
        // SVR already carries the TBI mean-pressure effect. Shape pulse pressure at constant MAP once.
        private _map = _dia + ((_sys - _dia) / 3);
        private _pp = (_ppTarget max 0) min (3 * _map);
        _dia = _map - _pp / 3;
        _sys = _map + 2 * _pp / 3;
    };
};
private _rhythmOffset = 0;
if (([_unit] call ACME_fnc_rhythmGet) in [100,101,103,104]) then {_rhythmOffset = _unit getVariable ["ACME_rhythm_bpOffset", 0];};
_dia = (_dia + _rhythmOffset) max 0;
_sys = (_sys + _rhythmOffset) max _dia;
private _stim = [_unit] call ACME_fnc_laryngoStimulusEffect;
_dia = _dia + _stim * (missionNamespace getVariable ["ACME_laryngo_diastolicSurge", 10]);
_sys = _sys + _stim * (missionNamespace getVariable ["ACME_laryngo_systolicSurge", 20]);
[round _dia, round _sys]
