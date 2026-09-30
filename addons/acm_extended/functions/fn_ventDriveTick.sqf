// running-ventilator drive. there are three real modes with distinct physiology, driven off lung compliance.
// SIMV vc ps, volume control: the set vt is guaranteed delivered. pressure is the dependent variable, so stiff
// lungs drive PIP up and minute ventilation is preserved.
// SIMV pc, pressure control: the vent holds a set inspiratory pressure. volume is the dependent variable, so as
// compliance worsens the delivered vt falls and a stiff-lunged patient silently hypoventilates. PIP stays
// capped by design.
// CPAP ps hf, spontaneous: there are no mandatory breaths. it supports the patient's own effort, so it cannot
// ventilate an apneic or paralyzed casualty, which is a real and lethal mis-selection. it is the definitive
// treatment for fluid-overload pulmonary edema, because it recruits flooded alveoli, which raises SpO2, and
// raises intrathoracic pressure, which cuts preload and lv afterload, so bp and hr fall.
// on the respiration rate: ACM's fnc_updaterespirationrate hardcodes rr to 10 whenever a BVM provider is active,
// and the vent registers as one. it also forces rr to 0 whenever the patient is not breathing spontaneously,
// which is exactly the paralyzed or apneic patient the vent exists for. that rr of 0 is the bug where the rate
// drops to zero and ventilation stops even though the vent is running. in the mandatory modes we therefore pin
// the respiration rate to the set BPM every tick, so the machine delivers exactly what it is set to.
// call it as [_patient] call ACME_fnc_ventDriveTick.
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};
if (_patient getVariable ["ACME_vent_recovering", false]) exitWith {
    if ((_patient getVariable ["ACME_vent_driving", false]) || {_patient getVariable ["ACME_vent_circuit", false]} || {_patient getVariable ["ACME_vent_connected", false]} || {_patient getVariable ["ACME_vent_configured", false]}) then {
        [_patient, _patient getVariable ["ACME_vent_custodyId", ""], false] call ACME_fnc_ventPatientClear;
    };
};

// Owner-published mode episode rejects delayed manual commands across live toggles.
private _simpleNow = missionNamespace getVariable ["ACME_vent_simpleMode", false];
private _episode = _patient getVariable ["ACME_vent_simpleEpisode", [!_simpleNow, 0]];
if !((_episode select 0) isEqualTo _simpleNow) then {
    [_patient, "ACME_vent_simpleEpisode", [_simpleNow, (_episode select 1) + 1]] call ACME_fnc_setVarNet;
};

// tick delta. fn_circhandle computes _dt, and because call runs in the caller's scope, this function has always
// read it from there. that is fragile. reordering the calls in fn_circhandle once left _dt undefined here,
// which errored the function part way through and stopped it ever publishing ACME_vent_driving, silencing the
// running loop and the shutdown clip. a local fallback is declared, so a change somewhere else can never break
// this function again. if the caller supplied a real delta it is used, and otherwise the nominal circ period
// is.
private _dt = [_patient, "ventDrive", 0.25, 5] call ACME_fnc_clinicalTickDelta;
// system toggle, read live, so unticking ventilator in addon options stops this system immediately and
// completely with no mission restart.
if !(missionNamespace getVariable ["ACME_sys_vent", true]) exitWith {
    if ((_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient) then {
        [_patient, [["bvmProvider", objNull], ["bvmConnectedOxygen", false]], true] call ACM_breathing_fnc_setRuntimeState;
    };
    [_patient, "ACME_vent_driving", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_effectiveRR", 0] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_rrDrive", -1] call ACME_fnc_setVarNet;
};

// manual breaths age out. the rolling 60 s window is what the rr override reads while someone is hand-breathing
// the casualty, and it is pruned here so that when they stop, the rate decays to zero on its own and the
// patient goes back to their own respiratory drive, or their lack of one. otherwise a single manual breath
// would prop up the respiratory rate forever and an apneic patient would never deteriorate.
private _mbTimes = _patient getVariable ["ACME_vent_manualBreathTimes", []];
if !(_mbTimes isEqualTo []) then {
    private _tNow = CBA_missionTime;
    private _kept = _mbTimes select {(_tNow - _x) <= 60};
    if ((count _kept) != (count _mbTimes)) then {
        _patient setVariable ["ACME_vent_manualBreathTimes", _kept, false];
        [_patient, "ACME_vent_manualRR", (count _kept)] call ACME_fnc_setVarNet;
    };
};

// Accepted manual volumes are a bounded physical breath ledger, not a dial setting.
private _simpleManual = _patient getVariable ["ACME_vent_simpleManualVolumes", []];
private _keptSimpleManual = _simpleManual select {CBA_missionTime - (_x select 0) <= 60};
if (count _keptSimpleManual != count _simpleManual) then {
    _patient setVariable ["ACME_vent_simpleManualVolumes", _keptSimpleManual, false];
};
_simpleManual = _keptSimpleManual;

if (isNull _patient || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {};

private _ettIn      = _patient getVariable ["ACME_ETT_Inserted", false];
private _configured = _patient getVariable ["ACME_vent_configured", false];
private _iface      = _patient getVariable ["ACME_vent_iface", ""];
private _connected  = _patient getVariable ["ACME_vent_connected", false];
private _effective = [_patient] call ACME_fnc_ventEffectiveSettings;
_effective params ["_simple", "_mode"];

// airway device. three things can carry mandatory ventilation, in descending order of how well they seal.
// an ETT, a cuffed endotracheal tube, is the gold standard: a sealed airway with full efficiency that holds
// PEEP.
// a surgical cric, a cuffed tube through the cricothyroid membrane, is a secured surgical airway, slightly
// leakier than an oral ETT and definitive.
// an i-gel or SGA is supraglottic. it sits over the larynx and does not seal the trachea, so it ventilates and
// leaks, and it leaks worse as airway pressure rises, which is why high PEEP blows past its seal.
// the i-gel and cric states are ACM's own: the SGA on ACM_airway_AirwayItem_Oral, and the cric on
// ACM_airway_SurgicalAirway_TubeInserted.
private _igelIn = ((_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) isEqualTo "SGA");
private _cricIn = (_patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false]);
private _airway = switch (true) do {
    case (_ettIn):  { "ETT" };
    case (_cricIn): { "CRIC" };
    case (_igelIn): { "IGEL" };
    default { "" };
};
// a secured airway is anything that can carry a mandatory breath. an ETT and a cric are secured, and an i-gel is
// a supraglottic rescue airway that we now also allow to drive the vent, just less effectively.
private _securedAirway = (_airway in ["ETT", "CRIC", "IGEL"]);

// mandatory modes need a secured airway, so INVASIVE plus an ETT. CPAP is a support mode and also works through
// a mask, on NON-INVASIVE, and mask CPAP is exactly how fluid-overload edema is treated in the field.
private _mandatory = _mode in ["SIMV VC PS", "SIMV PC", "IMV VC (CPR)", "SIMPLE"];

// ventilating during CPR.
// positive-pressure ventilation and chest compressions are mechanically at war. every mandatory breath raises
// intrathoracic pressure, and intrathoracic pressure is what compressions are fighting to overcome to move
// blood. stack synchronized, patient-triggered, PEEP-carrying breaths on top of an arrest and you get breath
// stacking and hyperinflation: venous return falls, coronary perfusion pressure falls, and CPR that looks
// perfect from the outside is moving less blood than anyone realises. that is why the real sparrow carries IMV
// vc (CPR) as a distinct mode, and why it now exists on ours.
// IMV vc (CPR) overrides the settings below to a fixed 10 breaths a minute, about 6 ml/kg, zero PEEP and no
// patient triggering. that is enough gas exchange to matter and little enough pressure to stay out of the way
// of the compressions. aha secured-airway guidance during CPR is one breath every 6 seconds, which is exactly
// what this delivers.
// every other mode costs you. while compressions run with the vent driving in any other mode, this tick accrues
// hyperinflation time on the patient. ACM still owns arrest/ROSC. This clock now feeds gas-exchange/EtCO2
// consequences only; it does not schedule an automatic post-ROSC VF/re-arrest shortcut.
private _cprProvider = _patient getVariable ["ace_medical_CPR_provider", objNull];
private _cprActive = (_patient getVariable ["ace_medical_inCardiacArrest", false]) && {!isNull _cprProvider};
private _cprMode = (_mode == "IMV VC (CPR)");
private _ifaceOK = if (_mandatory) then { _securedAirway && {_iface == "INVASIVE"} } else { _iface in ["INVASIVE","NON-INVASIVE","NON INVASIVE"] };
if (_simple) then {_ifaceOK = _securedAirway;}; // physical airway; stored interface choice is inactive.
private _hardwareOK = true;
if (_simple) then {
    _hardwareOK = (_patient getVariable ["ACME_vent_circuit", false])
        && {_patient getVariable ["ACME_vent_powerOn", false]}
        && {!(missionNamespace getVariable ["ACME_vent_batteryEnabled", true])
            || {_patient getVariable ["ACME_vent_battExternal", false]}
            || {(_patient getVariable ["ACME_vent_battery", 100]) > 0}};
};
private _driving = _connected && _configured && _ifaceOK && _hardwareOK;
private _wasDriving = _patient getVariable ["ACME_vent_driving", false];

if (_driving) then {
    private _bpm = _effective select 2;
    private _vtSet = _effective select 3;
    private _fio2 = _effective select 4;
    private _simpleManualRR = if (_simple) then {count _simpleManual} else {0};
    private _cprBpm = _bpm + _simpleManualRR;

    // hyperinflation clock. it runs only while compressions are actually happening and the vent is driving in a mode
    // that fights them. it decays when conditions clear, so a mistake corrected early costs little and a whole
    // resus spent in SIMV costs a lot. the cprsucceeded listener in postinit reads it.
    if (_cprActive) then {
        private _bad = _patient getVariable ["ACME_vent_cprBadTime", 0];
        if (_cprMode || {_simple && {_cprBpm <= 10}}) then {
            _bad = (_bad - _dt * 0.5) max 0;  // the correct mode actively works the stacking off.
        } else {
            _bad = _bad + (_dt * (if (_simple) then {linearConversion [10, 30, _cprBpm, 0, 1, true]} else {1}));
        };
        [_patient, "ACME_vent_cprBadTime", _bad, 0.25, 2] call ACME_fnc_setVarNetApprox;
    } else {
        private _bad0 = _patient getVariable ["ACME_vent_cprBadTime", 0];
        if (_bad0 > 0) then { [_patient, "ACME_vent_cprBadTime", (_bad0 - _dt) max 0, 0.25, 2] call ACME_fnc_setVarNetApprox; };
    };

    // lung compliance, where 1.0 is healthy and lower is stiffer.
    private _overload = _patient getVariable ["ACM_circulation_Overload_Volume", 0];
    private _ptx      = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
    private _htxFluid = _patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0];
    private _baroInj = _patient getVariable ["ACME_vent_baroInjury", 0];  // 0 to 1 of ventilator-induced lung injury.
    private _blast   = _patient getVariable ["ACME_blastLung_State", 0];  // 0 to 1 of primary blast injury.
    private _comp = 1
        - (0.45 * (linearConversion [0.2, 1.6, _overload, 0, 1, true]))
        - (0.25 * (linearConversion [0, 3, _ptx, 0, 1, true]))
        - (0.20 * (linearConversion [0, 1500, _htxFluid, 0, 1, true]))
        - (0.30 * _baroInj)  // VILI stiffens the lung further.
        - (0.62 * _blast);  // blast lung, the stiffest of all.
    _comp = (_comp max 0.20) min 1;
    [_patient, "ACME_vent_compliance", _comp, 0.01, 1] call ACME_fnc_setVarNetApprox;

    // the patient's own respiratory drive.
    // this is what the casualty would breathe if the machine were not here. it cannot be read from
    // ACM_breathing_RespirationRate, because in mandatory modes the vent pins that variable, so asking it would
    // return the machine's own rate. that circularity is what pinned CPAP at 0 permanently. it is resolved the same
    // way the updateRespirationRate override would with the vent pin released: paralysis beats everything, then
    // seizure apnea, then the TBI pattern, then blast air hunger, then the body's demanded rate. the target rate is
    // never allowed to be 0, because ACM divides by it, so paralysis and seizure are the real zero cases.
    private _paralyzed = _patient getVariable ["ACME_roc_paralyzed", false];
    private _intrinsic = _patient getVariable ["ACME_resp_neuralRR", (_patient getVariable ["ACM_core_TargetVitals_RespirationRate", 18])];
    if (_paralyzed || {_patient getVariable ["ace_medical_inCardiacArrest", false]}) then {_intrinsic = 0;};
    // mode-specific delivery. B18 separates mandatory and spontaneous breaths. SIMV PC now uses an
    // actual pressure-control setting, PInsp, while both SIMV modes allow patient-triggered breaths supported by
    // P. SUPPORT. A spontaneous breath is not automatically "fighting" the vent; dyssynchrony is a separate,
    // gradually evolving failure of synchrony/support below.
    private _peep = _effective select 5;
    private _pinsp = _effective select 6; // ACME_vent_pinsp is read by the shared settings resolver.
    private _psup = _effective select 7;
    private _cmpMult = (_patient getVariable ["ACME_vent_complianceMult", 1]) max 0.20 min 1;
    private _compEff = (_comp * _cmpMult) max 0.10 min 1;
    private _trigCm = _effective select 8;
    private _trigOff = (_trigCm == 0);
    private _trigSens = linearConversion [0.25, 10, (abs _trigCm), 2, 20, true];
    private _canTrigger = (!_paralyzed) && {!_trigOff} && {_intrinsic >= _trigSens};

    private _spontVtFor = {
        params ["_drive", "_support", "_c"];
        private _effort = linearConversion [4, 30, _drive, 0.80, 1.15, true];
        (((280 + (22 * _support)) * _c * _effort) max 80) min 1000
    };

    private _mandatoryBpm = 0;
    private _spontBpm = 0;
    private _effBpm = 0;
    private _vtiMand = 0;
    private _vtiSpont = 0;
    private _pipMand = _peep;
    private _pipSpont = _peep;
    private _backup = false;

    switch (_mode) do {
        case "SIMPLE": {
            // Set RR stays authoritative even when a saved advanced mode was CPAP/CPR.
            // Fixed volume remains pressure-limited below; injured lungs can receive less.
            _mandatoryBpm = _bpm;
            _vtiMand = _vtSet;
            _pipMand = 8 + (12 * (_vtSet / 500) / _compEff);
        };
        case "SIMV PC": {
            _mandatoryBpm = _bpm;
            _pipMand = _pinsp;
            // Pressure control: driving pressure and compliance determine VT. At the healthy defaults of
            // PInsp 20 / PEEP 5 this is approximately 500 mL; a stiff or one-lung patient receives less volume
            // while the pressure target stays fixed.
            _vtiMand = (500 * (((_pinsp - _peep) max 0) / 15) * _compEff) max 0 min 1500;
            if (_canTrigger && {_intrinsic > _bpm}) then {
                _spontBpm = (_intrinsic - _bpm) max 0;
                _vtiSpont = [_intrinsic, _psup, _compEff] call _spontVtFor;
                _pipSpont = _peep + _psup;
            };
        };
        case "CPAP PS HF": {
            if (_canTrigger && {_intrinsic > 0}) then {
                _spontBpm = _intrinsic;
                _vtiSpont = [_intrinsic, _psup, _compEff] call _spontVtFor;
                _pipSpont = _peep + _psup;
            } else {
                _backup = true;
                private _bkKg = (_patient getVariable ["ACME_vent_weight", 70]) max 1;
                _mandatoryBpm = round (linearConversion [5, 40, _bkKg, 25, 12, true]);
                _vtiMand = _vtSet * _compEff;
                _pipMand = 8 + (12 * (_vtSet / 500) / _compEff);
            };
        };
        case "IMV VC (CPR)": {
            _mandatoryBpm = _bpm;
            _vtiMand = _vtSet;
            _pipMand = 8 + (12 * (_vtSet / 500) / _compEff);
        };
        default {  // SIMV VC PS
            _mandatoryBpm = _bpm;
            _vtiMand = _vtSet;
            _pipMand = 8 + (12 * (_vtSet / 500) / _compEff);
            if (_canTrigger && {_intrinsic > _bpm}) then {
                _spontBpm = (_intrinsic - _bpm) max 0;
                _vtiSpont = [_intrinsic, _psup, _compEff] call _spontVtFor;
                _pipSpont = _peep + _psup;
            };
        };
    };
    _effBpm = (_mandatoryBpm + _spontBpm) max 0;
    if (_mode != "CPAP PS HF") then { _effBpm = _effBpm max _bpm; };

    // Dyssynchrony is actual unresolved respiratory effort, not merely an awake/paralyzed medication state.
    // A well-triggered spontaneous breath is normal SIMV behavior. Coughing, missed triggers, or high respiratory
    // demand with inadequate support make the target rise. The state then eases in over time instead of flipping
    // directly to a lethal stress response.
    private _inArrest = _patient getVariable ["ace_medical_inCardiacArrest", false];
    private _dysTarget = 0;
    private _coughingNow = CBA_missionTime < (_patient getVariable ["ACME_vent_coughUntilT", 0]);
    if (!_inArrest) then {
        if (_coughingNow) then { _dysTarget = 1; };
        if (!_paralyzed && {_intrinsic > 3}) then {
            if (!_simple && {_mandatory} && {!_canTrigger}) then {
                _dysTarget = _dysTarget max (linearConversion [4, 30, _intrinsic, 0.15, 0.85, true]);
            };
            if (_spontBpm > 0) then {
                private _need = linearConversion [12, 32, _intrinsic, 0, 1, true];
                private _supportRelief = linearConversion [0, 14, _psup, 0, 1, true];
                _dysTarget = _dysTarget max ((_need * (1 - _supportRelief) * 0.65) min 0.75);
            };
        };
    };
    private _dys = _patient getVariable ["ACME_vent_dyssync", 0];
    private _dysTau = [missionNamespace getVariable ["ACME_vent_dyssyncFallSec", 9], missionNamespace getVariable ["ACME_vent_dyssyncRiseSec", 18]] select (_dysTarget > _dys);
    private _dysFrac = if (_dysTau <= 0) then {1} else {(_dt / _dysTau) min 1};
    _dys = (_dys + ((_dysTarget - _dys) * _dysFrac)) max 0 min 1;
    [_patient, "ACME_vent_dyssync", _dys, 0.01, 1] call ACME_fnc_setVarNetApprox;

    // Fighting first causes inefficient ventilation and only a modest, slow sympathetic response. It cannot bank
    // an instant post-ROSC hypertensive/tachycardic spike because arrest drives both stress targets to zero.
    private _fightHRMax = missionNamespace getVariable ["ACME_vent_fightHRMax", 18];
    private _fightResMax = missionNamespace getVariable ["ACME_vent_fightResistMax", 9];
    private _fightHRTgt = if (_inArrest) then {0} else {_fightHRMax * _dys};
    private _fightResTgt = if (_inArrest) then {0} else {_fightResMax * _dys};
    private _fightEase = {
        params ["_key", "_target", "_rise", "_fall"];
        private _cur = _patient getVariable [_key, 0];
        private _tau = [_fall, _rise] select (_target > _cur);
        private _f = if (_tau <= 0) then {1} else {(_dt / _tau) min 1};
        private _next = _cur + ((_target - _cur) * _f);
        [_patient, _key, _next, 0.10, 1] call ACME_fnc_setVarNetApprox;
        _next
    };
    ["ACME_vent_fightHRAdjust", _fightHRTgt, missionNamespace getVariable ["ACME_vent_fightStressRiseSec", 45], missionNamespace getVariable ["ACME_vent_fightStressFallSec", 14]] call _fightEase;
    ["ACME_vent_fightResistAdjust", _fightResTgt, missionNamespace getVariable ["ACME_vent_fightStressRiseSec", 45], missionNamespace getVariable ["ACME_vent_fightStressFallSec", 14]] call _fightEase;

    // A badly asynchronous mandatory breath can terminate early. Keep the loss bounded: the principal consequence
    // is gradually worsening ventilation, rising CO2 and then falling oxygenation, not an electrical arrest shortcut.
    _vtiMand = _vtiMand * (1 - (0.20 * _dys));
    _vtiSpont = _vtiSpont * (1 - (0.10 * _dys));

    [_patient, "ACME_vent_spontRR", _spontBpm, 0.25, 1] call ACME_fnc_setVarNetApprox;
    [_patient, "ACME_vent_effectiveRR", _effBpm + _simpleManualRR, 0.25, 1] call ACME_fnc_setVarNetApprox;
    [_patient, "ACME_vent_backupActive", _backup] call ACME_fnc_setVarNet;

    // Airway/circuit leak fraction, shared by mandatory and spontaneous breaths.
    private _leak = 0.03;
    if (_ptx > 0) then { _leak = _leak + (0.10 * (linearConversion [0, 3, _ptx, 0, 1, true])); };
    if ((_patient getVariable ["ACME_thora_tube_left", false]) || {_patient getVariable ["ACME_thora_tube_right", false]}) then { _leak = _leak + 0.08; };
    private _peepOver = (_peep - 5) max 0;
    switch (_airway) do {
        case "CRIC": { _leak = _leak + 0.06 + (0.010 * _peepOver); };
        case "IGEL": { _leak = _leak + 0.12 + (0.035 * _peepOver); };
        default {};
    };
    _leak = _leak min 0.75;

    // I:E and auto-PEEP use the actual total cycling rate, including patient-triggered breaths.
    private _ie = _effective select 9;
    private _cycleRate = ((_effBpm + _simpleManualRR) max _bpm) max 1;
    private _period = 60 / _cycleRate;
    private _tI = _period / (1 + _ie);
    private _tE = (_period - _tI) max 0.05;
    private _tNeeded = (missionNamespace getVariable ["ACME_vent_emptyTimeBase", 1.8]) * _compEff;
    private _autoPEEP = _patient getVariable ["ACME_vent_autoPEEP", 0];
    if (_tE < _tNeeded) then {
        private _deficit = ((_tNeeded - _tE) / (_tNeeded max 0.01)) min 1;
        _autoPEEP = _autoPEEP + (_deficit * (missionNamespace getVariable ["ACME_vent_autoPeepRate", 0.9]) * _dt);
    } else {
        _autoPEEP = _autoPEEP - ((missionNamespace getVariable ["ACME_vent_autoPeepClear", 1.2]) * _dt);
    };
    _autoPEEP = (_autoPEEP max 0) min 20;
    [_patient, "ACME_vent_autoPEEP", _autoPEEP, 0.10, 1] call ACME_fnc_setVarNetApprox;

    // Pressure limit is a real delivery limit for both the mandatory and the pressure-supported breath.
    private _pLimit = _effective select 11;
    private _pLimited = false;
    private _mandTotalP = _pipMand + _autoPEEP;
    if (_mandatoryBpm > 0 && {_mandTotalP > _pLimit}) then {
        private _scale = ((_pLimit - _autoPEEP) max 0) / (_pipMand max 0.1);
        _scale = _scale max 0 min 1;
        _vtiMand = _vtiMand * _scale;
        _pipMand = (_pLimit - _autoPEEP) max 0;
        _pLimited = true;
    };
    private _spontTotalP = _pipSpont + _autoPEEP;
    if (_spontBpm > 0 && {_spontTotalP > _pLimit}) then {
        private _scaleS = ((_pLimit - _autoPEEP) max 0) / (_pipSpont max 0.1);
        _scaleS = _scaleS max 0 min 1;
        _vtiSpont = _vtiSpont * _scaleS;
        _pipSpont = (_pLimit - _autoPEEP) max 0;
        _pLimited = true;
    };
    [_patient, "ACME_vent_pLimited", _pLimited] call ACME_fnc_setVarNet;

    private _vteMand = _vtiMand * (1 - _leak);
    private _vteSpont = _vtiSpont * (1 - _leak);
    private _totalBreaths = (_mandatoryBpm + _spontBpm) max 0;
    private _vti = if (_totalBreaths > 0) then {((_mandatoryBpm * _vtiMand) + (_spontBpm * _vtiSpont)) / _totalBreaths} else {0};
    private _vte = if (_totalBreaths > 0) then {((_mandatoryBpm * _vteMand) + (_spontBpm * _vteSpont)) / _totalBreaths} else {0};
    private _pip = ((_pipMand max _pipSpont) + _autoPEEP) max _peep;
    [_patient, "ACME_vent_vti", round _vti, 5, 0.5] call ACME_fnc_setVarNetApprox;
    [_patient, "ACME_vent_vte", round _vte, 5, 0.5] call ACME_fnc_setVarNetApprox;
    [_patient, "ACME_vent_pip", round _pip, 1, 0.5] call ACME_fnc_setVarNetApprox;
    private _vtReference = if (_mode == "SIMV PC") then {500 * (((_pinsp - _peep) max 0) / 15)} else {_vtSet};
    [_patient, "ACME_vent_vtReference", _vtReference max 1] call ACME_fnc_setVarNet;

    // Recruitment and positive-pressure effects.
    private _recruit = 0;
    if (_compEff < 0.95 && {_ie < 1.5}) then {
        _recruit = (linearConversion [0.95, 0.35, _compEff, 0, 1, true]) * (linearConversion [1.5, 0.5, _ie, 0, 1, true]);
    };
    [_patient, "ACME_vent_recruit", _recruit, 0.01, 1] call ACME_fnc_setVarNetApprox;
    private _targetSat = [_patient, _compEff, _peep, _fio2, _recruit] call ACME_fnc_ventOxygenation;
    _targetSat = (_targetSat - (_patient getVariable ["ACME_o2Drain_mainstem", 0]) - (_patient getVariable ["ACME_o2Drain_vili", 0])) max 0;

    // B35: the shared pleural controller reads actual ACME_vent_driving/pip and
    // effective PEEP. Pressure can amplify an ongoing leak; residual collapse
    // alone does not create air. Do not independently grow PTX or set tension here.

    // Lung-protective stretch uses what was actually delivered, including pressure-controlled and supported breaths.
    private _wtKg = _effective select 10;
    private _largestVt = _vtiMand max _vtiSpont;
    private _mlPerKg = _largestVt / _wtKg;
    if (_mlPerKg > 8 && {_compEff < 0.8}) then {
        private _stretch = (linearConversion [8, 12, _mlPerKg, 0, 1, true]) * (1 - _compEff);
        private _inj = _patient getVariable ["ACME_vent_baroInjury", 0];
        [_patient, "ACME_vent_baroInjury", ((_inj + (_stretch * 0.010 * _dt)) min 1), 0.005, 2] call ACME_fnc_setVarNetApprox;
    };
    [_patient, "ACME_vent_mlPerKg", _mlPerKg, 0.05, 1] call ACME_fnc_setVarNetApprox;

    // Exact exhaled and alveolar minute ventilation: mandatory and spontaneous breath volumes are not assumed equal.
    private _mvDelivered = ((_mandatoryBpm * _vteMand) + (_spontBpm * _vteSpont)) / 1000;
    private _mvAlv = (_mandatoryBpm * ((_vteMand - 150) max 0)) + (_spontBpm * ((_vteSpont - 150) max 0));
    if (_simple) then {
        {
            private _exhaled = _x select 1;
            _mvDelivered = _mvDelivered + (_exhaled / 1000);
            _mvAlv = _mvAlv + ((_exhaled - 150) max 0);
        } forEach _simpleManual;
    };
    private _mvTarget = (12 * (500 - 150)) * ((_wtKg / 70) max 0.3);
    private _mvAdequacy = ((_mvAlv / _mvTarget) max 0) min 1.6;
    [_patient, "ACME_vent_mvDelivered", _mvDelivered max 0, 0.05, 1] call ACME_fnc_setVarNetApprox;
    [_patient, "ACME_vent_mvAdequacy", _mvAdequacy, 0.01, 1] call ACME_fnc_setVarNetApprox;

    // Sustained severe dyssynchrony now decompensates in the respiratory direction first: less effective minute
    // ventilation raises EtCO2 through the existing CO2 model, and a bounded target-saturation penalty makes SpO2
    // trend down. It does not directly call an arrest or rhythm transition.
    private _mvPenaltyFactor = 1 - (linearConversion [0.35, 1.05, _mvAdequacy, 0, 0.8, true]);
    private _fightO2Penalty = (linearConversion [0.35, 1, _dys, 0, missionNamespace getVariable ["ACME_vent_fightO2PenaltyMax", 6], true])
        * (_mvPenaltyFactor max 0 min 1);
    _targetSat = (_targetSat - _fightO2Penalty) max 0;
    [_patient, [["oxygenSaturation", _targetSat]], true] call ACM_core_fnc_setTargetVitalsState;

    // Register the vent as the BVM gas-exchange provider only while meaningful minute ventilation exists.
    private _ventilating = _mvAdequacy > 0.05;
    if (_ventilating) then {
        [_patient, [["bvmProvider", _patient], ["bvmLastBreath", CBA_missionTime]], true] call ACM_breathing_fnc_setRuntimeState;
        private _o2 = _fio2 > 21;
        private _bvmO2State = [["bvmConnectedOxygen", _o2]];
        if (_o2) then {_bvmO2State pushBack ["bvmLastBreathOxygen", CBA_missionTime];};
        [_patient, _bvmO2State, true] call ACM_breathing_fnc_setRuntimeState;
    } else {
        if ((_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient) then {
            [_patient, [["bvmProvider", objNull], ["bvmConnectedOxygen", false]], true] call ACM_breathing_fnc_setRuntimeState;
        };
    };

    // exact BPM.
    // the rate is owned authoritatively by our override of ACM_breathing_fnc_updateRespirationRate, which returns
    // the set BPM for a mandatory-mode vent. writing it from here was useless, because ACM stores the rate in
    // ACM_breathing_RespirationRate rather than ace_medical_respirationrate, which is what this used to set, and
    // its vitals cycle overwrote it with the hardcoded BVM value of 10 four times a second regardless.

    // CPAP: the definitive therapy for fluid-overload pulmonary edema.
    // positive airway pressure recruits flooded alveoli and raises intrathoracic pressure, which drops venous
    // return, the preload, and the lv afterload. SpO2 climbs, the hypertension that drove the edema falls, and the
    // compensatory tachycardia settles as the work of breathing and the myocardial stress come off.
    // the relief hr drive defaults to off each tick, and the CPAP branch below re-arms it only while it is actively
    // off-loading. that guarantees the drive is released the moment CPAP stops, whether the edema cleared or the
    // mode changed, so a stale low target can never linger and hold the hr of the patient down.
    if (!(_mode == "CPAP PS HF" && {_overload > 0.02})) then {
        if ((_patient getVariable ["ACME_hrDrive_ventRelief", -1]) >= 0) then {
            [_patient, "ACME_hrDrive_ventRelief", -1] call ACME_fnc_setVarNet;
        };
    };
    if (_mode == "CPAP PS HF" && {_overload > 0.02}) then {
            // 1. resolve the edema. as the overload falls, the overload multiplier in fn_bpnative falls with it, so the bp
        // comes down on its own and the edema tachypnea pfh releases the rr target back toward baseline.
        private _rate = missionNamespace getVariable ["ACME_vent_cpapEdemaClearRate", 0.020];  // per second.
        private _newOv = (_overload - (_rate * _dt)) max 0;
        [_patient, [["overloadVolume", _newOv]], true] call ACM_circulation_fnc_setRuntimeState;
        if (_newOv <= 0.02) then { [_patient, "ACME_edema_crackles", false] call ACME_fnc_setVarNet; };
        // 2. off-load the heart. publish a descending hr drive, ACME_hrDrive_ventRelief, that circhandle folds in
        // through min, because CPAP relief pulls the compensatory tachycardia down toward normal. publishing rather
        // than writing hr here removes the double-write with the final hr write circhandle does in the same tick. the
        // drive eases from the current target toward 80, and -1 means inactive.
        private _hrTgt = _patient getVariable ["ACM_core_TargetVitals_HeartRate", 80];
        if (_hrTgt > 80) then {
            private _reliefPrev = _patient getVariable ["ACME_hrDrive_ventRelief", -1];
            private _reliefBase = if (_reliefPrev >= 0) then { _reliefPrev } else { _hrTgt };
            private _hrRate = missionNamespace getVariable ["ACME_vent_cpapHRRelief", 1.2];  // bpm per second.
            [_patient, "ACME_hrDrive_ventRelief", ((_reliefBase - (_hrRate * _dt)) max 80), 0.25, 1] call ACME_fnc_setVarNetApprox;
        } else {
            [_patient, "ACME_hrDrive_ventRelief", -1] call ACME_fnc_setVarNet;
        };
        // 3. recruit oxygenation. CPAP reverses the hypoxia of edema faster than baseline gas exchange.
        private _spo2 = _patient getVariable ["ace_medical_spo2", 97];
        if (_spo2 < 97) then {
            private _o2Rate = missionNamespace getVariable ["ACME_vent_cpapO2Recruit", 1.5];  // percent per second.
            [_patient, [["spo2", ((_spo2 + (_o2Rate * _dt)) min 97), true, true]]] call ACM_core_fnc_setAceMedicalState;
        };
        [_patient, "ACME_vent_cpapTherapy", true] call ACME_fnc_setVarNet;
    } else {
        if (_patient getVariable ["ACME_vent_cpapTherapy", false]) then {
            [_patient, "ACME_vent_cpapTherapy", false] call ACME_fnc_setVarNet;
        };
    };

    // barotrauma and VILI: sustained high PIP has consequences.
    // this is what makes the mode choice a real decision. under vc the machine will happily force the set volume
    // into a stiff lung and the pressure goes wherever it has to, and pressure is what injures lungs. sustained PIP
    // above the safe ceiling accumulates a barotrauma dose that does three things. it stiffens the lung further,
    // which is VILI, fed back into compliance above, and that is a vicious circle where a stiffer lung gives a
    // higher PIP which gives more injury. it can pop a pneumothorax. and it drives an existing pneumothorax toward
    // tension. dropping to pc, which caps pressure, or backing the vt down is the way out.
    private _pipDanger = missionNamespace getVariable ["ACME_vent_baroPIPThreshold", 35];  // cmH2O.
    private _dose = _patient getVariable ["ACME_vent_baroDose", 0];
    if (_pip > _pipDanger) then {
        // the dose accrues faster the further over the ceiling you are.
        private _over = linearConversion [_pipDanger, _pipDanger + 20, _pip, 0, 1, true];
        private _rate = (missionNamespace getVariable ["ACME_vent_baroDoseRate", 0.012]) * (0.4 + _over);
        _dose = _dose + (_rate * _dt);
    } else {
        // below the ceiling the lung slowly recovers from the insult. the accumulated injury does not.
        _dose = (_dose - (0.004 * _dt)) max 0;
    };
    [_patient, "ACME_vent_baroDose", _dose, 0.01, 1] call ACME_fnc_setVarNetApprox;

    // injury milestones. each full dose unit inflicts a discrete barotrauma event.
    private _events = _patient getVariable ["ACME_vent_baroEvents", 0];
    if (_dose >= 1) then {
        _dose = 0;
        _events = _events + 1;
        [_patient, "ACME_vent_baroDose", 0] call ACME_fnc_setVarNet;
        [_patient, "ACME_vent_baroEvents", _events] call ACME_fnc_setVarNet;
        // 1. ventilator-induced lung injury, a roughly permanent stiffening that feeds back into compliance.
        [_patient, "ACME_vent_baroInjury", ((_baroInj + 0.20) min 1)] call ACME_fnc_setVarNet;
        // 2. A discrete pressure-injury milestone creates or renews a pleural
        // leak. The ACM entry point is bound to the shared B35 injury controller.
        // Routine positive-pressure ventilation cannot create this event by itself.
        private _ptxNow = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
        private _chance = missionNamespace getVariable ["ACME_vent_baroPTXChance", 55];
        if (_ptxNow > 0) then {_chance = 100;};
        if ((random 100) < _chance) then {
            // Preserve ACM chest findings for the pressure-induced injury. A new
            // insult can renew a leak even while existing tension is present.
            if (!(_patient getVariable ["ACM_breathing_ChestInjury_State", false])) then {
                [_patient, true] call ACM_breathing_fnc_setChestInjuryState;
            };
            [_patient] call ACM_breathing_fnc_handlePneumothorax;
            [_patient, "ACME_vent_baroPTX", true] call ACME_fnc_setVarNet;
        };
        // 3. pain, because barotrauma hurts.
        [_patient, 0.25] call ace_medical_fnc_adjustPainLevel;
    };

    // expose a gauge state for the ui: 0 is safe, 1 is caution and 2 is danger.
    private _pipWarn = missionNamespace getVariable ["ACME_vent_baroPIPCaution", 30];
    private _gaugeState = switch (true) do {
        case (_pip >= _pipDanger): { 2 };
        case (_pip >= _pipWarn):   { 1 };
        default { 0 };
    };
    [_patient, "ACME_vent_pipState", _gaugeState] call ACME_fnc_setVarNet;

    // publish the delivered breath rate on two separate channels, because they answer two different questions.
    // 1. ACME_vent_measRR is the display value: what the machine is actually delivering right now, and the panel
    // reads it directly. it used to read ACM_breathing_RespirationRate instead, which only gets written when ACM's
    // breathing loop calls updateRespirationRate. for a paralyzed, apneic casualty ACM may never call it, so the
    // readout sat at 0 whatever the vent was doing. publishing the number here makes the readout depend on the
    // ventilator alone.
    // 2. ACME_vent_rrDrive is the pin that makes the respiration rate of the patient reflect the machine. that is
    // correct in mandatory modes only, where the machine sets the rate.
    // CPAP is the exception, and it was a feedback loop. under CPAP the machine supplies pressure and the patient
    // supplies every breath, so _effBpm is read from ACM_breathing_RespirationRate above. pinning that same value
    // back into the same variable made it its own input: it latched wherever it started, and if the casualty was
    // apneic when CPAP began it stayed 0 permanently, so they could never be seen to start breathing. under CPAP we
    // release the pin, at -1, and let the patient's own drive own the rate, which is what CPAP means.
    private _mandatory = !(_mode == "CPAP PS HF");

    // count the breaths, do not infer them.
    // this readout has been repaired repeatedly and has never stayed fixed, and the reason is that every repair was
    // to the fallback rather than to the fact that nothing was ever counting anything. _effBpm is a modeled rate:
    // what the machine should be delivering given its settings. publishing that as the measured value means the
    // measured number can never disagree with the set number, which is the entire point of having it.
    // on the real sparrow the parenthetical is a count: every breath actually delivered plus every breath the
    // patient took, over a rolling sixty seconds. that is why it lags a few seconds, why it does not jitter, and
    // why it collapses when the circuit comes apart. a counted number can tell you the machine has stopped. a
    // modeled one never can.
    // breath onset comes from an accumulator rather than a phase crossing. adding dt times rate over 60 each tick
    // and firing whenever it passes 1.0 cannot miss a breath at a low frame rate, and it stays correct when the
    // rate changes mid-breath, which phase-crossing against a moving period does not.
    private _acc = (_patient getVariable ["ACME_vent_breathAcc", 0]) + (_dt * ((_effBpm max 0) / 60));
    private _times = _patient getVariable ["ACME_vent_breathTimes", []];
    private _tNowB = CBA_missionTime;
    while {_acc >= 1} do {
        _acc = _acc - 1;
        _times pushBack _tNowB;
    };
    _patient setVariable ["ACME_vent_breathAcc", _acc];  // local. only this tick reads it.

    // a rolling sixty seconds. it uses the same pruning the manual-breath window already uses, so the two behave
    // identically.
    _times = _times select {(_tNowB - _x) <= 60};
    // local, not broadcast. this is a 60-second window of timestamps, an array, rewritten every tick. nothing off
    // this machine ever reads it, because the panel reads ACME_vent_measRR, which is derived from it and is a
    // single number. syncing the whole array four times a second was the most expensive thing the ventilator did
    // and it bought nothing.
    _patient setVariable ["ACME_vent_breathTimes", _times];

    // a breath the medic squeezed in by hand is a delivered breath. the flow sensor of the machine cannot tell the
    // difference and neither should the readout.
    private _manual = (_patient getVariable ["ACME_vent_manualBreathTimes", []]) select {(_tNowB - _x) <= 60};
    private _counted = (count _times) + (count _manual);

    // a count over a sixty-second window is breaths per minute, by definition. there is no scaling, no smoothing and
    // no floor. until the window has filled it under-reads, which is exactly what a real machine does when you
    // switch it on, so it is left alone.
    [_patient, "ACME_vent_measRR", _counted, 0.25, 0.5] call ACME_fnc_setVarNetApprox;
    if (_mandatory) then {
        [_patient, "ACME_vent_rrDrive", (round ((_effBpm + _simpleManualRR) max 0))] call ACME_fnc_setVarNet;
    } else {
        [_patient, "ACME_vent_rrDrive", -1] call ACME_fnc_setVarNet;
    };

    // stamp when driving began, once, on the transition. the alarm layer uses this for a settle window, because a
    // ventilator that was just connected has not delivered a full breath cycle yet, so its measured minute volume
    // is meaningless for a moment and must not be alarmed on.
    if !(_patient getVariable ["ACME_vent_driving", false]) then {
        [_patient, "ACME_vent_driveT0", CBA_missionTime] call ACME_fnc_setVarNet;
    };
    [_patient, "ACME_vent_driving", true] call ACME_fnc_setVarNet;
} else {
    // not driving. release the vent-driven BVM vars only, and never stomp a real medic-held BVM.
    if (_wasDriving || {(_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient}) then {
        if ((_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient) then {
            [_patient, [["bvmProvider", objNull], ["bvmConnectedOxygen", false]], true] call ACM_breathing_fnc_setRuntimeState;
        };
        [_patient, "ACME_vent_driving", false] call ACME_fnc_setVarNet;
        [_patient, "ACME_vent_effectiveRR", 0] call ACME_fnc_setVarNet;
        [_patient, "ACME_vent_spontRR", 0] call ACME_fnc_setVarNet;
        [_patient, "ACME_vent_rrDrive", -1] call ACME_fnc_setVarNet;  // release rr back to the patient's own drive
        // it is not set to -1. the window is left exactly as it is and simply stops being added to, so the count decays
        // over the next minute as the delivered breaths age out. that decay is the alarm: a machine that has stopped
        // shows its rate falling away, which is what a real one does and what makes a disconnect visible. slamming it
        // to -1 handed the panel a no-reading that it then papered over with the set rate, so a stopped ventilator
        // looked exactly like a running one. that was the bug.
        _patient setVariable ["ACME_vent_breathAcc", 0];
        [_patient, "ACME_vent_driveT0", -1] call ACME_fnc_setVarNet;
        [_patient, "ACME_vent_mvAdequacy", 0] call ACME_fnc_setVarNet;
        [_patient, "ACME_vent_mvDelivered", 0] call ACME_fnc_setVarNet;
        [_patient, "ACME_vent_cpapTherapy", false] call ACME_fnc_setVarNet;
    };
    // No stale fighting response survives a stopped/disconnected circuit.
    private _d0 = _patient getVariable ["ACME_vent_dyssync", 0];
    if (_d0 > 0) then { [_patient, "ACME_vent_dyssync", (_d0 - (_dt / 6)) max 0, 0.01, 1] call ACME_fnc_setVarNetApprox; };
    private _fh = _patient getVariable ["ACME_vent_fightHRAdjust", 0];
    if (_fh > 0) then { [_patient, "ACME_vent_fightHRAdjust", (_fh - (_dt * 2)) max 0, 0.10, 1] call ACME_fnc_setVarNetApprox; };
    private _fr = _patient getVariable ["ACME_vent_fightResistAdjust", 0];
    if (_fr > 0) then { [_patient, "ACME_vent_fightResistAdjust", (_fr - (_dt * 1.2)) max 0, 0.10, 1] call ACME_fnc_setVarNetApprox; };
};
