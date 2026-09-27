// ACME circulation and hemodynamic handler. it is a decoupled pfh with the same design as the TBI loop: it
// reads ACM vitals, owns its own state, and applies effects through a single observable hook. the
// getbloodpressure wrapper, see fn_postInit, consumes the bpoffset. the net mmhg shift on MAP is
// bpoffset = pressorsupport + pushDoseSupport - shockdrop
// shockdrop is distributive, peri-arrest hypotension. it is fluid-refractory, because it is a
// peripheral-resistance-style drop that volume cannot fix.
// pressorsupport is the norepi and epi infusions, summed as mcg/min into mmhg, and volume-gated.
// pushDoseSupport is the push-dose epi boluses. it is transient and decays over minutes.
// because the offset shifts ACM's real bp, the bp cuff, the AED, MAP and CPP all reflect it, and tbiGetMAP
// picks it up automatically. the TBI loop therefore no longer adds pressor MAP itself, because that would
// double-count.
// ICH coupling: an epi-driven MAP overshoot above a threshold accrues intracranial hemorrhage risk, which on a
// TBI patient raises ICP and severity. push-dose epi, titrated and small, stays under the threshold. a 1 mg
// push or a wide-open dirty-epi drip overshoots and bleeds.

ACME_circ_activePatients = ACME_circ_activePatients select {!isNull _x && {local _x} && {alive _x}};

// patients who need a circ tick: anyone with shock, push-dose, a pressor infusion or TBI.
private _circEnabled = missionNamespace getVariable ["ACME_sys_circ", true];
private _patients = ACME_circ_activePatients + ACME_tbi_activePatients + (missionNamespace getVariable ["ACME_clinical_activePatients", []]);
{
    if (!isNull _x && {alive _x} && {local _x}) then {_patients pushBackUnique _x};
} forEach (ACME_infusion_activePatients select {!isNull _x});

// keep acidosis and PaCO2 ticking even when the casualty falls out of an ACME active array. cardiac arrest,
// unconscious airway failure, severe hypoventilation, existing acidosis, TBI, active iv fluids and saline
// reservoir changes all need a continuous physiology tick.
{
    private _u = _x;
    if (isNull _u || {!alive _u} || {!local _u}) then { continue };

    private _circState = _u getVariable ["ACME_circ_State", createHashMap];
    private _arrest = _u getVariable ["ace_medical_inCardiacArrest", false];
    private _uncon = _u getVariable ["ACE_isUnconscious", false];
    private _rr = _u getVariable ["ACM_breathing_RespirationRate", 18];
    private _rrTarget = _u getVariable ["ACM_core_TargetVitals_RespirationRate", 16];
    if (_rrTarget <= 6) then { _rrTarget = 16 };

    private _needsAcidTick =
        _arrest ||
        {_u getVariable ["ACME_vent_connected", false]} ||
        {_u getVariable ["ACME_ETT_Inserted", false]} ||
        {_u getVariable ["ACME_nrb_on", false]} ||
        {(_u getVariable ["ACME_blastLung_State", 0]) > 0} ||
        {count (_u getVariable ["ace_medical_medications", []]) > 0} ||
        {count (_u getVariable ["ACME_yFlushJobs", createHashMap]) > 0} ||
        {_uncon} ||
        {count _circState > 0} ||
        {_u getVariable ["ACME_tbi_HasTBI", false]} ||
        {_rr < (_rrTarget * 0.85)} ||
        {(_u getVariable ["ACME_circ_salineGivenMl", 0]) > 0} ||
        {(_u getVariable ["ACM_circulation_Saline_Volume", 0]) > 0} ||
        {(_u getVariable ["ACME_lido_serumLevel", 0]) > 0.05} ||
        {(_u getVariable ["ACME_lido_seizureState", ""]) != ""} ||
        {count (_u getVariable ["ACM_circulation_IV_Bags", createHashMap]) > 0};

    if (_needsAcidTick) then { _patients pushBackUnique _u };
} forEach (missionNamespace getVariable ["ACME_clinical_ownedUnits", []]);

_patients = _patients arrayIntersect _patients;

private _pressorMeds = missionNamespace getVariable ["ACME_infusion_pressorMedications", []];
private _coeff = missionNamespace getVariable ["ACME_tbi_pressorMAPperMcgMin", 0.9];  // mmhg per mcg/min, before the cap.
private _pressorCap = missionNamespace getVariable ["ACME_tbi_pressorMAPcap", 25];
private _ichThreshold = missionNamespace getVariable ["ACME_circ_ichMAPThreshold", 130];  // the MAP above which an epi-driven overshoot bleeds.
private _ichRate = missionNamespace getVariable ["ACME_circ_ichSeverityPerSec", 0.01];

// small custom-effect envelope for ACME extended effects that do not exist inside ACM's native med model, such
// as pressor MAP support and the epi-equivalent ICH drive. the target is the currently running dose-rate. the
// current effect ramps toward it and decays after the line is stopped or removed, which matches the same
// onset and offset idea as ACM's medication adjustments instead of acting as an electrical on-off switch.
private _easeDrive = {
    params ["_state", "_key", "_target", "_dt", "_riseSec", "_fallSec"];
    private _cur = _state getOrDefault [_key, 0];
    private _tau = [_fallSec, _riseSec] select (_target > _cur);
    private _frac = if (_tau <= 0) then {1} else {(_dt / _tau) min 1};
    _cur = _cur + ((_target - _cur) * _frac);
    if (abs _cur < 0.00001) then {_cur = 0};
    _state set [_key, _cur];
    _cur
};

private _getMedEffect = {
    params ["_patient", "_class"];
    if (isNil "ace_medical_status_fnc_getMedicationCount") exitWith {0};
    private _v = [_patient, _class, false] call ace_medical_status_fnc_getMedicationCount;
    if (_v isEqualType []) exitWith {_v param [1, 0]};
    _v
};

{
    private _patient = _x;
    if (isNull _patient || {!alive _patient} || {!local _patient}) then {continue};

    private _dt = [_patient, "clinicalMaintenance", 0.25, 5] call ACME_fnc_clinicalTickDelta;
    // Consume only newly admitted mass even when custom circulation is disabled: never replay old doses.
    private _deliveredRates = [_patient,_dt] call ACME_fnc_medicationDriveTick;
    [_patient] call ACME_fnc_yFlushTick;

    // dose-dependent ketamine sedation. an induction dose drives the casualty unconscious, so a medic can manage
    // the airway and intubate. a decaying load wakes them unless something else holds them down.
    [_patient] call ACME_fnc_midazolamTick;
    [_patient] call ACME_fnc_ketamineSedationTick;

    // rocuronium paralysis. an intubating dose paralyzes, which gives apnea and forces ventilation. paralysis with
    // no adequate sedation is the awake-paralysis danger. it is optional, for RSI, and not required for
    // intubation.
    [_patient] call ACME_fnc_ettAirwayProtect;
    [_patient] call ACME_fnc_sugammadexTick;
    [_patient] call ACME_fnc_rocuroniumTick;
    [_patient] call ACME_fnc_laryngoIrritationTick;

    // running ventilator. if this patient is intubated, configured and connected to a running vent, the vent
    // breathes for them and keeps ACM's BVM oxygenation alive at the set rate and FiO2. that matters most for a
    // paralyzed, apneic casualty.
    // order matters. altitude runs first, because it publishes the ambient pressure ratio the oxygenation model of
    // the ventilator needs. run it the other way round and the vent computes a saturation that altitude then
    // overwrites a few lines later, which silently throws away the whole shunt model on any terrain above 500 m.
    // the tick delta is resolved before any sub-tick runs. it used to be computed further down, after the
    // ventilator ticks below were called. because call runs in the caller's scope, fn_ventdrivetick reads _dt
    // straight out of here. with the definition below the calls it was reading an undefined variable, erroring out
    // part way through, and never reaching the line that publishes ACME_vent_driving. that flag is what the server
    // sound engine keys the running loop and the shutdown clip off, which is why both went silent while the
    // self-test clip, played from the panel by a different function, carried on working.
    private _state = _patient getVariable ["ACME_circ_State", createHashMap];
    private _now = CBA_missionTime;
    // _dt was measured before the independent maintenance calls.
    _state set ["lastTick", _now];

    // Acid/base state is integrated on the same one-second class of cadence as ACE/ACM vital updates.  The broader
    // circulation PFH still runs at 0.25 s for devices/infusions, but those extra passes must not advance PaCO2 or
    // acidosis four times inside one vital-sign second.  Delta time comes from this acid clock and is capped after
    // stalls, preserving hysteresis/elapsed-time behavior without double updates.
    private _acidLastTick = _state getOrDefault ["acidLastTick", -1];
    private _acidDt = 0;
    if (_acidLastTick < 0) then {
        _state set ["acidLastTick", _now];
    } else {
        private _acidElapsed = (_now - _acidLastTick) max 0;
        if (_acidElapsed >= 1) then {
            _acidDt = _acidElapsed min 5;
            _state set ["acidLastTick", _now];
        };
    };
    _state set ["acidTickDt", _acidDt];

    [_patient] call ACME_fnc_vomitDislodgeOPA;
    [_patient] call ACME_fnc_altitudeTick;
    [_patient] call ACME_fnc_ventLeashTick;
    // slow air accumulation from repeated needle decompressions. see fn_ncdairleaktick.
    [_patient] call ACME_fnc_ncdAirLeakTick;
    [_patient] call ACME_fnc_ventDriveTick;
    [_patient] call ACME_fnc_ventBatteryTick;
    [_patient] call ACME_fnc_ventAlarmTick;
    [_patient] call ACME_fnc_ventStatusTick;
    [_patient] call ACME_fnc_blastLungTick;

    // True PEA is nonperfusing even if Extended circulation options are disabled. Clear any NIBP value measured
    // before the arrest so the LifePak cannot display a stale systolic/diastolic/MAP while electrical activity continues.
    if ((_patient getVariable ["ace_medical_inCardiacArrest", false]) && {([_patient] call ACME_fnc_rhythmGet) == 5}) then {
        if !((_patient getVariable ["ACM_circulation_AED_NIBP_Display", [0,0]]) isEqualTo [0,0]) then {
            [_patient, [["aedNibpDisplay", [0,0]]], true] call ACM_circulation_fnc_setRuntimeState;
        };
    };

    if (_circEnabled) then {
    private _inCardiacArrest = _patient getVariable ["ace_medical_inCardiacArrest", false];

    // stable resting hr baseline. ACM's updateheartrate eases hr toward ACM_core_TargetVitals_HeartRate, and the
    // branch-2 drives below, for esmolol, epi, shock and hypothermia, steer hr by setting that target directly.
    // that is the same mechanism the rhythm and megacode systems already use, and the only one that works,
    // because ACM compilefinal-blocks the updateheartrate wrapper and it never installs.
    // because we overwrite the target with the drive value, we cannot also read it back as the resting base. it
    // would feed its own output and run away. so capture the resting value once here and use that as the base. it
    // is re-captured after an ailment clear, because the reset blanks ACME_hrRestBaseline.
    private _hrRestBaseline = _patient getVariable ["ACME_hrRestBaseline", -1];
    if (_hrRestBaseline < 0) then {
        _hrRestBaseline = _patient getVariable ["ACM_core_TargetVitals_HeartRate", 77];
        [_patient, "ACME_hrRestBaseline", _hrRestBaseline] call ACME_fnc_setVarNet;
    };


    // native MAP, which is ACM's own without our offset. shock and acidosis both reuse it.
    private _origBP = ACME_fnc_bpNative;
    private _nativeBP = [_patient] call _origBP;
    _nativeBP params [["_nd", 80], ["_ns", 120]];
    private _nativeMAPforAcid = _nd + ((_ns - _nd) / 3);

    // shock, fluid-refractory and peri-arrest.
    private _shockActive = _state getOrDefault ["shockActive", false];
    private _shockSeverity = _state getOrDefault ["shockSeverity", 0];
    private _shockDrop = 0;
    if (_shockActive) then {
        private _creep = missionNamespace getVariable ["ACME_circ_shockProgressPerSec", 0.006];
        _shockSeverity = (_shockSeverity + (_creep * _dt)) min 1;
        // this is target-based. it pulls the effective MAP down to a severity-scaled target. low severity gives
        // peri-arrest, which is symptomatic and near the line, and full severity goes below ACM's own MAP under 55
        // cardiac-arrest trigger, so an unsupported patient actually crashes. the target is absolute, which makes it
        // fluid-refractory: raising the native MAP with fluids or blood only grows the drop to the same target. only
        // pressor and push-dose support, added back below, lifts it.
        private _floorMAP = missionNamespace getVariable ["ACME_circ_shockFloorMAP", 38];
        private _targetMAP = linearConversion [0, 1, _shockSeverity, _nativeMAPforAcid, _floorMAP, true];
        _shockDrop = (_nativeMAPforAcid - _targetMAP) max 0;
    };

    // calcium and citrate. a massive transfusion causes hypocalcemia.
    // stored blood is citrated, and transfusing it chelates ionized calcium. past a threshold, at massive
    // transfusion, ionized ca falls. that weakens cardiac contractility, which lowers MAP, and it costs a clotting
    // cofactor, factor iv, which worsens bleeding through the coag multiplier the bleed override reads. calcium
    // chloride repletes it. this is the calcium leg of the lethal triad. acidosis is modeled in the offset
    // section below, and hypothermia just below.
    private _transfused  = _patient getVariable ["ACM_circulation_TransfusedBlood_Volume", 0];
    private _caCl2Given  = _patient getVariable ["ACME_ca_caCl2Given", 0];  // grams pushed.
    private _citrateThresh = missionNamespace getVariable ["ACME_ca_citrateThreshold", 1.0];  // liters before it bites.
    private _citrateDeficit = ((_transfused - _citrateThresh) max 0) * (missionNamespace getVariable ["ACME_ca_citratePerLiter", 0.18]);
    private _caFloor = missionNamespace getVariable ["ACME_ca_floor", 0.55];
    private _ionizedCa = (1 - _citrateDeficit + (_caCl2Given * (missionNamespace getVariable ["ACME_ca_creditPerGram", 0.12]))) min 1 max _caFloor;
    _state set ["ionizedCa", _ionizedCa];
    // calcium pressor gate. catecholamine signal transduction needs ionized calcium, because beta-inotropy works
    // through calcium handling and alpha-vasoconstriction needs calcium in vascular smooth muscle. profound
    // hypocalcemia therefore blunts both pressors rather than one of them. it applies equally to the norepi into
    // resistance channel and the epi into hr channel below, so a hypocalcemic bleeder does not get a spurious
    // advantage for epi over norepi. both are damped, and the model rewards the real answer, which is to replete
    // calcium rather than out-pressor it. it is 1.0 at normal ca and tapers to a floor at full hypocalcemia. a
    // normal patient, at ionizedca of 1, is unaffected.
    private _caPressorGate = linearConversion [
        (missionNamespace getVariable ["ACME_ca_pressorGateStart", 0.85]),
        (missionNamespace getVariable ["ACME_ca_pressorGateFull", 0.6]),
        _ionizedCa, 1, (missionNamespace getVariable ["ACME_ca_pressorGateMin", 0.5]), true];
    _state set ["caPressorGate", _caPressorGate];
    // eased, not stepped. calcium chloride does restore vascular tone and contractility, so correcting a
    // hypocalcaemic casualty genuinely does raise their pressure. the shape was what was wrong. the drop was
    // recomputed straight from the variable, so the moment the syringe went in, up to 18 mmhg of suppression
    // vanished on the next 0.25 s tick. real calcium takes a minute or two to do that, and an instantaneous
    // pressure step is exactly what tears fresh clots off.
    // the target is the same. it is now walked toward at a bounded rate, so the pressure climbs across about
    // ninety seconds instead of jumping.
    private _caMAPtarget = (1 - _ionizedCa) * (missionNamespace getVariable ["ACME_ca_mapDropPerUnit", 40]);
    private _caMAPdrop = _patient getVariable ["ACME_ca_mapDropEased", _caMAPtarget];
    private _caStep = (missionNamespace getVariable ["ACME_ca_mapEasePerSec", 0.2]) * _dt;
    if (_caMAPdrop < _caMAPtarget) then {
        _caMAPdrop = (_caMAPdrop + _caStep) min _caMAPtarget;  // falling calcium. the pressure sags in.
    } else {
        _caMAPdrop = (_caMAPdrop - _caStep) max _caMAPtarget;  // repleted calcium. the pressure comes back gradually.
    };
    [_patient,"ACME_ca_mapDropEased",_caMAPdrop,0.02,2] call ACME_fnc_setVarNetApprox;
    _state set ["caMAPdrop", _caMAPdrop];

    // hypothermia, the third leg of the lethal triad. cold impairs the clotting cascade, which is a coagulopathy
    // multiplied onto the calcium one. it blunts the response to catecholamines, because the myocardium is cold,
    // and that is folded into the support calc below. it also slows the sa node, which gives a bradycardia applied
    // after the shock hr arc. the core temp is in degrees c.
    private _temp = _patient getVariable ["ACME_hypo_temp", 37];
    _state set ["temp", _temp];
    private _hypoBlunt = linearConversion [
        (missionNamespace getVariable ["ACME_hypo_bluntStartTemp", 34]),
        (missionNamespace getVariable ["ACME_hypo_bluntFullTemp", 30]),
        _temp, 0, (missionNamespace getVariable ["ACME_hypo_maxBlunt", 0.5]), true];
    _state set ["hypoBlunt", _hypoBlunt];

    // hypothermia does not create acidosis by itself. it makes shock and lactic acidosis accumulate faster, and it
    // makes metabolic acidosis recover more slowly until a medic rewarms the patient.
    private _hypoAcidGainMult = linearConversion [
        (missionNamespace getVariable ["ACME_hypo_acidStartTemp", 35]),
        (missionNamespace getVariable ["ACME_hypo_acidFullTemp", 30]),
        _temp, 1, (missionNamespace getVariable ["ACME_hypo_acidMaxGainMult", 1.5]), true];
    private _hypoAcidRecoveryMult = linearConversion [
        (missionNamespace getVariable ["ACME_hypo_acidStartTemp", 35]),
        (missionNamespace getVariable ["ACME_hypo_acidFullTemp", 30]),
        _temp, 1, (missionNamespace getVariable ["ACME_hypo_acidMinRecoveryMult", 0.25]), true];
    _state set ["hypoAcidGainMult", _hypoAcidGainMult];
    _state set ["hypoAcidRecoveryMult", _hypoAcidRecoveryMult];
    _state set ["caAcidosisIndirectMAPdrop", _caMAPdrop];
    // the acidosis leg of the triad. a falling ph slows thrombin generation, so the clotting cascade weakens. mild
    // acidosis barely matters, because clotting holds until the ph drops meaningfully, so the multiplier only
    // ramps in past a threshold. severe acidosis adds substantial bleeding, synergistic with cold. it uses the
    // acidosis carried in state, recomputed in the offset section below, which gives a one-tick lag that is
    // immaterial at the accrual rate. correcting acidosis, through restored perfusion or a plasma-lyte buffer,
    // therefore improves clotting as well as the pressor response.
    private _coagParts = [_patient, _ionizedCa, _state getOrDefault ["acidosis", 0]] call ACME_fnc_coagulationBase;
    _coagParts params ["_coagBase", "_coagMult", "_hypoCoag", "_acidCoag"];
    _state set ["calciumCoagMult", _coagMult];
    _state set ["hypoCoagMult", _hypoCoag];
    _state set ["acidCoagMult", _acidCoag];
    // Circulation owns the base; only coagulationTick publishes the combined bleeding multiplier.
    // A changed base enrolls immediately, including recovery back to normal.
    private _previousBase = _patient getVariable ["ACME_ca_coagBaseMult", 1];
    [_patient,"ACME_ca_coagBaseMult",_coagBase,([0.005,0] select (_coagBase == 1)),0] call ACME_fnc_setVarNetApprox;
    _state set ["coagMult", _coagBase];
    if (_coagBase != _previousBase) then {[[_patient]] call ACME_fnc_coagulationTick;};

    // Route observations do not synthesize drug dose or turn norepinephrine into epinephrine.
    private _pressorDrive = 0;
    private _epiInfusionDrive = 0;
    private _epiLikeDrive = 0;
    private _distalDripActive = false;
    private _distalDrugEffectActive = false;
    private _distalPressorActive = false;
    private _distalEpiRunning = false;
    private _amioMg = 0;
    private _amioRateMgMin = 0;
    private _caRateMgMin = 0;
    private _caElemMgMin = 0;
    private _magRateMgMin = 0;
    private _driveByMed = createHashMap;
    private _lidoDrive = 0;
    private _esmololRunning = false;
    private _esmololInfusionDrive = 0;
    {
        private _running = (_x param [14,0]) > 0 && {(_x param [17,0]) > 0}
            && {CBA_missionTime - (_x param [18,-1]) < 3};
        private _distal = (_x param [5,true]) && {(_x param [4,0]) >= 1}
            && {(_x param [1,""]) in ["leftarm","rightarm","leftleg","rightleg"]};
        if (_running && {_distal}) then {
            _distalDripActive = true;
            _distalDrugEffectActive = true;
            if ((_x param [11,""]) in _pressorMeds) then {_distalPressorActive = true;};
            if ((_x param [11,""]) == "Epinephrine") then {_distalEpiRunning = true;};
        };
    } forEach (_patient getVariable ["ACME_infusion_BagMedications",[]]);

    // B14: actual admitted mass, both bolus and infusion, replaces sampled bag-rate estimates.
    // No double-credit for native infusion pulses or final empty-bag tails.
    _driveByMed = _deliveredRates;
    _epiInfusionDrive = _deliveredRates getOrDefault ["Epinephrine",0];
    _pressorDrive = _epiInfusionDrive + (_deliveredRates getOrDefault ["Norepinephrine",0]);
    _epiLikeDrive = _epiInfusionDrive; // norepinephrine is never reclassified as epinephrine by vein location.
    _amioRateMgMin = _deliveredRates getOrDefault ["Amiodarone",0];
    _amioMg = _amioRateMgMin * _dt / 60;
    _caRateMgMin = (_deliveredRates getOrDefault ["CalciumChloride",0]) + (_deliveredRates getOrDefault ["CalciumGluconate",0]);
    _caElemMgMin = (_deliveredRates getOrDefault ["CalciumChloride",0]) * 0.273
        + (_deliveredRates getOrDefault ["CalciumGluconate",0]) * 0.093;
    _magRateMgMin = _deliveredRates getOrDefault ["Magnesium",0];
    _lidoDrive = _deliveredRates getOrDefault ["Lidocaine",0];
    _esmololInfusionDrive = _deliveredRates getOrDefault ["Esmolol",0];
    _esmololRunning = _esmololInfusionDrive > 0;

    // apply the onset and offset envelopes to the custom pressor effects. the physical flow can stop immediately,
    // and the pharmacodynamic effect does not. it ramps in and washes out instead of changing MAP or ICP
    // instantly.
    private _pressorOnset = missionNamespace getVariable ["ACME_infusion_pressorOnsetSec", 45];
    private _pressorOffset = missionNamespace getVariable ["ACME_infusion_pressorOffsetSec", 120];
    private _pressorDriveTarget = _pressorDrive;
    private _epiInfusionDriveTarget = _epiInfusionDrive;
    private _epiLikeDriveTarget = _epiLikeDrive;
    _pressorDrive = [_state, "pressorDriveEffMgMin", _pressorDriveTarget, _dt, _pressorOnset, _pressorOffset] call _easeDrive;
    _epiInfusionDrive = [_state, "epiInfusionDriveEffMgMin", _epiInfusionDriveTarget, _dt, _pressorOnset, _pressorOffset] call _easeDrive;
    _epiLikeDrive = [_state, "epiLikeDriveEffMgMin", _epiLikeDriveTarget, _dt, _pressorOnset, _pressorOffset] call _easeDrive;
    _state set ["pressorDriveTargetMgMin", _pressorDriveTarget];
    _state set ["epiInfusionDriveTargetMgMin", _epiInfusionDriveTarget];
    _state set ["epiLikeDriveTargetMgMin", _epiLikeDriveTarget];
    // esmolol drip drive. ease the bag rate so the onset and washout are smooth, because beta-blockade does not
    // appear or vanish the instant flow starts or stops. esmolol is fast on and off, so it uses shorter envelopes
    // than the pressors.
    private _esmololInfusionDriveTarget = _esmololInfusionDrive;
    _esmololInfusionDrive = [_state, "esmololInfusionDriveEffMgMin", _esmololInfusionDriveTarget, _dt,
        (missionNamespace getVariable ["ACME_esmolol_driveOnsetSec", 60]),
        (missionNamespace getVariable ["ACME_esmolol_driveOffsetSec", 150])] call _easeDrive;
    _state set ["esmololInfusionDriveTargetMgMin", _esmololInfusionDriveTarget];

    // fast-infusion consequences for the push-slow drugs: amiodarone, calcium and magnesium.
    // each is harmless dripped at a sane rate and turns dangerous wide open. amiodarone vasodilates, which gives
    // hypotension. calcium and magnesium suppress the node, which gives bradycardia, and they also drop the
    // pressure. each is driven off its eased mg/min, so the penalty tracks how hard the clamp is opened rather
    // than the cumulative dose. the bradycardia is applied in the hr section below, where these fractions stay in
    // scope, and the hypotension is summed into a negative resistance here, the same lever the lidocaine-tox and
    // esmolol-overdose vasodilation use. ACM's native hr for mag and calcium is zeroed in config, so this does not
    // double-count.
    private _infToxOnset = missionNamespace getVariable ["ACME_infusionTox_onsetSec", 15];
    private _infToxOffset = missionNamespace getVariable ["ACME_infusionTox_offsetSec", 35];
    _amioRateMgMin = [_state, "amioRateEffMgMin", _amioRateMgMin, _dt, _infToxOnset, _infToxOffset] call _easeDrive;
    _caRateMgMin   = [_state, "caRateEffMgMin",   _caRateMgMin,   _dt, _infToxOnset, _infToxOffset] call _easeDrive;
    _caElemMgMin   = [_state, "caElemEffMgMin",    _caElemMgMin,   _dt, _infToxOnset, _infToxOffset] call _easeDrive;
    _magRateMgMin  = [_state, "magRateEffMgMin",  _magRateMgMin,  _dt, _infToxOnset, _infToxOffset] call _easeDrive;
    private _amioFast = linearConversion [(missionNamespace getVariable ["ACME_amio_fastOnsetMgMin", 20]), (missionNamespace getVariable ["ACME_amio_fastMaxMgMin", 80]), _amioRateMgMin, 0, 1, true];
    private _magFast  = linearConversion [(missionNamespace getVariable ["ACME_mag_fastOnsetMgMin", 300]), (missionNamespace getVariable ["ACME_mag_fastMaxMgMin", 1500]), _magRateMgMin, 0, 1, true];

    // calcium serum level, as elemental mg/dl of excess, plus the overdose severity.
    // the serum is a first-order accumulator off the eased elemental calcium drive. the plateau is drive divided
    // by clearance, and a compressed half-life lets a fast push spike it and a stopped drip clear it.
    // the overdose severity is the worse of two levers. the rate term is elemental mg/min past the rate onset,
    // which is a high concentration hitting the heart too fast. the serum term is the accumulated level past the
    // narrow therapeutic ceiling, which is simply too much. both are physiologic, and both must stay clear for a
    // proper slow correction.
    private _caSerum = _patient getVariable ["ACME_ca_serumLevel", 0];
    private _caClear = (missionNamespace getVariable ["ACME_ca_serumClearance", 60]) max 0.001;
    private _caHalfMin = ((missionNamespace getVariable ["ACME_ca_serumHalfLifeSec", 120]) / 60) max 0.1;
    private _caSteady = _caElemMgMin / _caClear;  // the mg/dl plateau for the current elemental drive.
    private _caK = 0.693 / _caHalfMin;  // the per-minute elimination rate constant.
    _caSerum = (_caSerum + (_caK * (_caSteady - _caSerum) * (_dt / 60))) max 0;
    [_patient,"ACME_ca_serumLevel",_caSerum,0.002,3] call ACME_fnc_setVarNetApprox;
    private _caSerumOd = linearConversion [
        (missionNamespace getVariable ["ACME_ca_serumTherapeuticHigh", 1.0]),
        (missionNamespace getVariable ["ACME_ca_serumOverdoseArrest", 4.0]),
        _caSerum, 0, 1, true];
    private _caRateOd = linearConversion [
        (missionNamespace getVariable ["ACME_ca_rateOnsetElemMgMin", 100]),
        (missionNamespace getVariable ["ACME_ca_rateMaxElemMgMin", 280]),
        _caElemMgMin, 0, 1, true];
    private _caOd = _caSerumOd max _caRateOd;  // the combined overdose severity, from 0 to 1.

    // amiodarone serum, for display and parity. the effects are the fast-infusion hypotension and the cumulative
    // torsades ceiling.
    private _amioSerum = _patient getVariable ["ACME_amio_serumLevel", 0];
    private _amioClear = (missionNamespace getVariable ["ACME_amio_serumClearance", 6]) max 0.001;
    private _amioHalfMin = ((missionNamespace getVariable ["ACME_amio_serumHalfLifeSec", 420]) / 60) max 0.1;
    private _amioSteady = _amioRateMgMin / _amioClear;
    private _amioK = 0.693 / _amioHalfMin;
    _amioSerum = (_amioSerum + (_amioK * (_amioSteady - _amioSerum) * (_dt / 60))) max 0;
    [_patient,"ACME_amio_serumLevel",_amioSerum,0.005,3] call ACME_fnc_setVarNetApprox;

    // amiodarone and magnesium vasodilate, which drops resistance and lowers bp, and they ride their fast
    // fractions. calcium is handled separately below, because acute hypercalcemia does the opposite early on.
    private _infResistDrop =
          (_amioFast * (missionNamespace getVariable ["ACME_amio_fastResistDrop", 35]))
        + (_magFast  * (missionNamespace getVariable ["ACME_mag_fastResistDrop", 30]));

    // calcium overdose is two-phase on the vasculature. acute to moderate hypercalcemia vasoconstricts, so SVR
    // rises and gives hypertension. that is the bp spike you see on a calcium push. only as the toxicity deepens
    // toward arrest does vessel tone give way to vasoplegia, where SVR falls and gives the terminal hypotension.
    // the constriction is a triangle over _caOd. it rises from 0 to a peak at the band boundary, then decays back
    // to 0 as the vasoplegia term ramps in from the boundary to full overdose. the net calcium SVR delta is
    // therefore positive, giving hypertension, in the acute band, and crosses to negative, giving vasoplegia, near
    // arrest. it tracks the bradycardia the hr block applies over the same _caOd. a therapeutic slow correction
    // leaves _caOd near 0 and moves nothing.
    private _caConstrictBand = missionNamespace getVariable ["ACME_ca_overdoseConstrictBand", 0.6];
    private _caConstrictAdd  = missionNamespace getVariable ["ACME_ca_overdoseConstrictAdd", 40];
    private _caVasoplegiaDrop = missionNamespace getVariable ["ACME_ca_overdoseResistDrop", 45];
    private _caConstrict = if (_caOd <= _caConstrictBand) then {
        linearConversion [0, _caConstrictBand, _caOd, 0, _caConstrictAdd, true]
    } else {
        linearConversion [_caConstrictBand, 1, _caOd, _caConstrictAdd, 0, true]
    };
    private _caVasoplegia = linearConversion [_caConstrictBand, 1, _caOd, 0, _caVasoplegiaDrop, true];
    private _caResistDelta = _caConstrict - _caVasoplegia;  // a positive value is constriction, which is acute. a negative value is vasoplegia, which is pre-arrest.

    private _infResistTarget = (-_infResistDrop) + _caResistDelta;
    if ((_patient getVariable ["ACME_infusionTox_resistDelta", 0]) != _infResistTarget) then {
        [_patient, "ACME_infusionTox_resistDelta", _infResistTarget] call ACME_fnc_setVarNet;
    };
    // surface the eased delivery rates and the fast fractions for the debug panel, so the actual mg/min is
    // visible. that is what the thresholds are calibrated against, and a therapeutic drip should read well under
    // its fast onset.
    _state set ["amioRateMgMin", _amioRateMgMin]; _state set ["amioFast", _amioFast];
    _state set ["caRateMgMin", _caRateMgMin];
    _state set ["caElemMgMin", _caElemMgMin];     _state set ["caSerum", _caSerum]; _state set ["caOverdose", _caOd];
    _state set ["amioSerum", _amioSerum];
    _state set ["magRateMgMin", _magRateMgMin];   _state set ["magFast", _magFast];

    // generalized serum accumulator for every other infusion, for display and the therapeutic band.
    // the drugs with a bespoke model, lidocaine, esmolol, calcium and amiodarone, are handled elsewhere. every
    // remaining infusible drug in the pk table gets a first-order serum level here, off its summed drip mg/min,
    // cleared per its half-life so it washes out after the bag stops. it is display only, with no downstream
    // effect wired, and the debug panel reads the level and the band. the levels are stored per med in
    // ACME_serum_<med> and cleaned up when they decay.
    private _pkTable = missionNamespace getVariable ["ACME_infusion_pk", createHashMap];
    {
        private _pkMed = _x;
        _y params [["_pkClear", 0.5], ["_pkHalf", 300]];
        private _pkDrive = _driveByMed getOrDefault [_pkMed, 0];
        private _lvlKey = format ["ACME_serum_%1", _pkMed];
        private _lvl = _patient getVariable [_lvlKey, 0];
        if (_pkDrive > 0 || {_lvl > 0.0001}) then {
            private _pkHalfMin = ((_pkHalf) / 60) max 0.1;
            private _pkSteady = _pkDrive / (_pkClear max 0.001);
            private _pkK = 0.693 / _pkHalfMin;
            _lvl = (_lvl + (_pkK * (_pkSteady - _lvl) * (_dt / 60))) max 0;
            if (_lvl < 0.00005 && {_pkDrive <= 0}) then { _lvl = 0; };
            [_patient, _lvlKey, _lvl] call ACME_fnc_setVarNet;
        };
    } forEach _pkTable;

    // B14 one-compartment concentration proxy. Independent volume and clearance are required:
    // deriving a tiny distribution volume from a compressed half-life made ordinary boluses enormous.
    // Clearance/Vd defines washout; native therapeutic-effect clocks remain a separate game abstraction.
    private _lidoLevel = _patient getVariable ["ACME_lido_serumLevel", 0];
    private _lidoClear = missionNamespace getVariable ["ACME_lido_clearanceLmin", 0.40];  // the plateau in mcg/ml is the drip divided by this.
    private _lidoClearFrac = 1;
    if (_shockActive) then {_lidoClearFrac = _lidoClearFrac * (missionNamespace getVariable ["ACME_lido_shockClearFrac",0.6]);};
    if ((_patient getVariable ["ACME_esmolol_serumLevel",0]) > 0.1) then {
        _lidoClearFrac = _lidoClearFrac * (missionNamespace getVariable ["ACME_lido_betaClearFrac",0.7]);
    };
    _lidoClearFrac = _lidoClearFrac max 0.05;
    private _weightPK = (_patient getVariable ["ACM_core_BodyWeight",80]) max 30;
    private _lidoVd = _weightPK * 0.7; // L; simple game distribution calibration, not a patient assay.
    private _lidoEffClear = (_lidoClear * _lidoClearFrac) max 0.001;
    private _lidoKSec = _lidoEffClear / (_lidoVd * 60);
    private _lidoDecay = exp (-_lidoKSec * _dt);
    _lidoLevel = (_lidoLevel * _lidoDecay + ((_lidoDrive / 60) / _lidoVd)
        * (1 - _lidoDecay) / _lidoKSec) max 0;
    [_patient,"ACME_lido_serumLevel",_lidoLevel,0.005,3] call ACME_fnc_setVarNetApprox;

    // lidocaine toxicity arc, the seizure. it reads the level just computed, drives apnea through the dedicated
    // seizure rr channel, and sets ACME_lido_seizureState, which the hr drive block and the debug line below
    // consume.
    [_patient, _lidoLevel, _dt] call ACME_fnc_lidoToxTick;
    _state set ["epiLikeDriveEffMgMin", _epiLikeDrive];

    // native ACM medication effects for the premixed and custom rhythm logic. these use ACM's own onset, plateau
    // and washout curve from the ACM_Medication entries, so stopping or removing the bag does not remove the
    // effect instantly.
    private _magEffect = [_patient, "Magnesium_IV"] call _getMedEffect;
    private _esmololEffect = [_patient, "Esmolol_IV"] call _getMedEffect;
    // Both bolus and bag doses are already in native history; no parallel onset bypass.
    _state set ["magEffect", _magEffect];
    _state set ["esmololEffect", _esmololEffect];
    // Esmolol distribution and clearance apply to every admitted route, including bolus.
    private _esmClear = missionNamespace getVariable ["ACME_esmolol_clearanceLmin", 3.5];
    [_patient, "ACME_esmolol_driveMgMin", _esmololInfusionDrive] call ACME_fnc_setVarNet;
    private _esmOld = _patient getVariable ["ACME_esmolol_serumLevel",0];
    private _esmVd = ((_patient getVariable ["ACM_core_BodyWeight",80]) max 30) * 0.5;
    private _esmK = (_esmClear max 0.001) / (_esmVd * 60); // clearance/Vd, per second
    private _esmDecay = exp (-_esmK * _dt);
    private _esmInput = _deliveredRates getOrDefault ["Esmolol",0];
    private _esmSerum = (_esmOld * _esmDecay + (_esmInput / 60 / _esmVd) * (1 - _esmDecay) / _esmK) max 0;
    [_patient,"ACME_esmolol_serumLevel",_esmSerum,0.005,3] call ACME_fnc_setVarNetApprox;
    // esmolol overdose band. past the therapeutic ceiling, where the serum exceeds
    // ACME_esmolol_serumTherapeuticHigh, the beta-blockade stops being rate control and becomes toxicity: a
    // high-grade av block, which is a severe bradycardia applied in the sinus drive below, plus hypotension. the
    // overdose fraction is how far the serum has climbed from the therapeutic ceiling toward
    // ACME_esmolol_serumOverdoseMax, and it drives both the hr floor drop and the resistance drop.
    // the hypotension is layered as a negative peripheral resistance, exactly like the lidocaine-tox vasodilation,
    // so bp actually falls on top of the bradycardia. the hr into cardiac-output term alone caps out and left a
    // too-fast drip floating around 97/68. it resets to 0 below the ceiling.
    private _esmOverdose = linearConversion [
        (missionNamespace getVariable ["ACME_esmolol_serumTherapeuticHigh", 2.0]),
        (missionNamespace getVariable ["ACME_esmolol_serumOverdoseMax", 5.0]),
        _esmSerum, 0, 1, true];
    private _esmResistTarget = -(_esmOverdose * (missionNamespace getVariable ["ACME_esmolol_overdoseResistDrop", 45]));
    if ((_patient getVariable ["ACME_esmololTox_resistDelta", 0]) != _esmResistTarget) then {
        [_patient, "ACME_esmololTox_resistDelta", _esmResistTarget] call ACME_fnc_setVarNet;
    };

    // magnesium. it terminates torsades only once a therapeutic effect has developed. while the effect is
    // therapeutic, recurrence is suppressed. when it washes out, unresolved causes can re-induce torsades.
    if (([_patient] call ACME_fnc_rhythmGet) == 102
        && {_magEffect >= (missionNamespace getVariable ["ACME_rhythm_magTerminateEffect", 0.60])}
        && {alive _patient}
        && {CBA_missionTime >= (_patient getVariable ["ACME_rhythm_magNextAttempt", -1])}
    ) then {
        [_patient, "ACME_rhythm_magNextAttempt", CBA_missionTime + 1] call ACME_fnc_setVarNet;
        private _converted = false;
        if (_patient getVariable ["ace_medical_inCardiacArrest",false]) then {
            _converted = [_patient, [_patient] call ACME_fnc_clinicalEpoch] call ACME_fnc_shockROSC;
        } else {
            [_patient,0,[_patient] call ACME_fnc_clinicalEpoch] call ACME_fnc_rhythmSet;
            _converted = ([_patient] call ACME_fnc_rhythmGet) != 102;
        };
        if (_converted) then {
            [_patient, "ACME_rhythm_torsadesRefractoryUntil", CBA_missionTime + (missionNamespace getVariable ["ACME_rhythm_magRefractorySec", 20])] call ACME_fnc_setVarNet;
            private _ceil = missionNamespace getVariable ["ACME_rhythm_amioCeilingMg", 2200];
            [_patient, "ACME_rhythm_amioCum", (_patient getVariable ["ACME_rhythm_amioCum", 0]) min (_ceil * 0.75)] call ACME_fnc_setVarNet;
        };
    };
    if (_magEffect < 0.10) then {[_patient, "ACME_rhythm_magTerminatedLogged", false] call ACME_fnc_setVarNet;};

    // esmolol. it rate-controls the tachyarrhythmias once ACM's native esmolol effect has developed, not the
    // moment the bag is hung. a medic can stop or remove the bag and the effect still persists until ACM's washout
    // removes it. AFib-RVR is rate-controlled, so the rhythm persists and slows. SVT and atrial tach are
    // terminated to sinus by the av-nodal block, which is the rate-control indication of esmolol for SVT. the hr
    // after conversion is owned by the rhythm system for AFib, or by the sinus esmolol drive below after SVT or
    // atrial tach breaks.
    if ((_esmololEffect >= (missionNamespace getVariable ["ACME_rhythm_esmololControlEffect", 0.35]))
        && {alive _patient}
    ) then {
        switch (_patient getVariable ["ACME_rhythm_active", 0]) do {
            case 100: { [objNull, _patient, 103, "Atrial Fibrillation", (missionNamespace getVariable ["ACME_rhythm_afibControlledHR", 90])] call ACME_fnc_rhythmToggle; };  // AFib-RVR becomes rate-controlled AFib.
            case 101: { [objNull, _patient, 101, "Atrial Tachycardia", 0] call ACME_fnc_rhythmToggle; };  // atrial tach becomes sinus, by toggling off.
            case 104: { [objNull, _patient, 104, "SVT", 0] call ACME_fnc_rhythmToggle; };  // SVT becomes sinus, by toggling off.
        };
        // there is no activity-log line, because naming the rhythm would reveal the condition of the patient.
    };

    // amiodarone in the perfusing casualty.
    // ACM models amiodarone as an arrest drug only. its handler gives a conversion chance for vf and pVT, then
    // exits the moment the casualty is out of arrest and 30 s past ROSC. so once there was a pulse, amiodarone did
    // nothing at all, while our layer had already added rate-dependent hypotension and a cumulative qt ceiling on
    // top. that left the drug carrying consequences and no benefit outside arrest, and a maintenance infusion
    // buying nothing but risk. this closes that asymmetry.
    // it acts on the rhythms we actually have. there is no monomorphic vt with a pulse in the rhythm system, so
    // the atrial tachyarrhythmias are where it lands, which is a real indication for it.
    // AFib-RVR becomes rate-controlled AFib, because amiodarone is a recognized option for af rate and rhythm
    // control.
    // atrial tach becomes sinus.
    // SVT becomes sinus, at a higher effect threshold only, because adenosine is first line and amiodarone is a
    // later choice, so it must not out-compete the correct drug.
    // torsades is deliberately absent from this list. amiodarone prolongs qt, so it does not treat polymorphic vt,
    // it causes it, which the cumulative ceiling below already models. magnesium remains the answer there. that
    // asymmetry is the clinically important part of this drug and it should stay visible.
    private _amioEffect = [_patient, "Amiodarone_IV"] call _getMedEffect;
    if ((_amioEffect >= (missionNamespace getVariable ["ACME_rhythm_amioControlEffect", 0.40]))
        && {alive _patient}
        && {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
    ) then {
        private _amioSVT = missionNamespace getVariable ["ACME_rhythm_amioSVTEffect", 0.70];
        switch (_patient getVariable ["ACME_rhythm_active", 0]) do {
            case 100: { [objNull, _patient, 103, "Atrial Fibrillation", (missionNamespace getVariable ["ACME_rhythm_afibControlledHR", 90])] call ACME_fnc_rhythmToggle; };
            case 101: { [objNull, _patient, 101, "Atrial Tachycardia", 0] call ACME_fnc_rhythmToggle; };
            case 104: { if (_amioEffect >= _amioSVT) then { [objNull, _patient, 104, "SVT", 0] call ACME_fnc_rhythmToggle; }; };
        };
        // there is no activity-log line, because naming the rhythm would reveal the condition of the patient.
    };

    // a distal epi drip is not allowed to induce a rhythm just because the bag exists. it contributes to the
    // pressor-surge gate below through _epiLikeDrive, and SVT or atrial tach is induced only if the catecholamine
    // effect is genuinely sustained and clinically meaningful.

    // Recurrent torsades uses current calcium, ICP and amiodarone burden.
    // The current native magnesium effect suppresses recurrence above the configured threshold.
    // Defibrillation supplies a separate refractory period. No bolus-time suppression clock is used.
    private _amioCum = (_patient getVariable ["ACME_rhythm_amioCum", 0]) + _amioMg;
    [_patient, "ACME_rhythm_amioCum", _amioCum] call ACME_fnc_setVarNet;
    if ((_patient getVariable ["ACME_rhythm_active", 0]) == 0
        && {alive _patient} && {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
        && {CBA_missionTime > (_patient getVariable ["ACME_rhythm_torsadesRefractoryUntil", 0])}
        && {_magEffect < (missionNamespace getVariable ["ACME_rhythm_magSuppressEffect", 0.45])}
    ) then {
        private _caThresh   = missionNamespace getVariable ["ACME_rhythm_torsadesCaThresh", 0.62];
        private _caSevere   = missionNamespace getVariable ["ACME_rhythm_torsadesCaSevere", 0.57];
        private _amioCeil    = missionNamespace getVariable ["ACME_rhythm_amioCeilingMg", 2200];
        private _icpThresh  = missionNamespace getVariable ["ACME_rhythm_torsadesICPThresh", 24];
        private _icpSevere  = missionNamespace getVariable ["ACME_rhythm_torsadesICPSevere", 30];
        private _icp = (_patient getVariable ["ACME_tbi_State", createHashMap]) getOrDefault ["icp", 10];

        private _severe   = (_ionizedCa <= _caSevere) || {_icp >= _icpSevere};
        private _moderate = (_ionizedCa <= _caThresh) || {_icp >= _icpThresh} || {_amioCum >= _amioCeil};

        // torsades is paroxysmal and uncommon even with the substrate present, so this is a low per-tick chance,
        // higher when the substrate is severe, and never deterministic. the old severe tier fired on every eligible
        // 0.25 s tick, which made torsades immediate and guaranteed and made magnesium look useless, because torsades
        // re-induced the instant after mag terminated it. it now appears occasionally while the substrate persists,
        // which gives a magnesium drip time to develop, terminate it and suppress recurrence.
        private _torsChance = if (_severe) then {
            missionNamespace getVariable ["ACME_rhythm_torsadesChanceSevere", 0.0012]
        } else {
            missionNamespace getVariable ["ACME_rhythm_torsadesChancePerTick", 0.0004]
        };

        if (_moderate && {random 1 < _torsChance}) then {
            // induce on the transition into torsades only. rhythmtoggle is a genuine toggle, so calling it again while
            // already at 102 would flip it back off. a guard on the active rhythm keeps it stable.
            if ((_patient getVariable ["ACME_rhythm_active", 0]) != 102) then {
                [objNull, _patient, 102, "Torsades (polymorphic VT)", (missionNamespace getVariable ["ACME_rhythm_torsadesHR", 220])] call ACME_fnc_rhythmToggle;
                // there is no activity-log line, because naming the rhythm or its cause would reveal the condition of the
                // patient.
            };
        };
    };

    private _requestedPressor = (_pressorDrive * 1000) * _coeff * _caPressorGate;  // mcg/min into mmhg, blunted by hypocalcemia.
    // volume gate. a pressor squeezing an empty tank does little, so give blood first.
    private _pres = [_patient, _requestedPressor] call ACME_fnc_tbiApplyPressorMAP;
    _pres params ["_pressorEff", "_pressorGated"];

    // a pure-vasoconstrictor pressor works through real peripheral resistance.
    // bpoffset is dead, because getbloodpressure is final, so the bp effect of a vasopressor has to go through
    // resistance, which ACM's getbloodpressure reads as bp = co * r. route only the non-epi share of the pressor
    // MAP support here, because epi already gets its bp through the hr drive and the co chain, so counting epi
    // here too would double it.
    // the override of updatePeripheralResistance folds ACME_pressorResistAdd into ACE's resistance each cycle.
    // ACM's baroreflex then opposes it naturally, strongly at a normal MAP and little when the patient is
    // hypotensive, which is where norepi is actually used, so it lands hardest exactly when it should. tune the
    // gain in CBA.
    private _norepiFrac = if (_pressorDrive > 0) then {((_pressorDrive - _epiInfusionDrive) max 0) / _pressorDrive} else {0};
    private _resistAdd = (_pressorEff * _norepiFrac) * (missionNamespace getVariable ["ACME_pressor_resistPerMmHg", 2.0]);
    // Publish only after the cold/acidosis gates have been computed below.

    // push-dose epi, a transient bolus support.
    private _pushDose = _state getOrDefault ["pushDoseSupport", 0];
    if (_pushDose > 0.01) then {
        // a roughly exponential decay. push-dose epi lasts a few minutes per bolus.
        private _halfLife = missionNamespace getVariable ["ACME_circ_pushDoseHalfLife", 120];  // seconds.
        _pushDose = _pushDose * (0.5 ^ (_dt / (_halfLife max 1)));
        if (_pushDose < 0.05) then {_pushDose = 0};
    };
    private _reserve = _state getOrDefault ["epiBolusReserve", 0];
    if (_reserve > 0.001) then {
        private _onset = (missionNamespace getVariable ["ACME_circ_epiBolusOnsetSec", 5]) max 0.1;
        private _entered = _reserve * (1 - exp (-_dt / _onset));
        _reserve = (_reserve - _entered) max 0;
        _pushDose = (_pushDose + _entered) min (missionNamespace getVariable ["ACME_circ_epiBolusMAPcap", 90]);
    } else {_reserve = 0;};
    _state set ["epiBolusReserve", _reserve];
    _state set ["pushDoseSupport", _pushDose];

    // B14: a distal catheter does not turn norepinephrine into epinephrine.
    // Local injury is handled by exact-site leakage. No location-only systemic surge.
    private _hyperSpike = 0;
    _state set ["hyperSpike",0];

    // vasopressor-surge atrial tachyarrhythmia gate.
    // this is the only automatic SVT and atrial tach path. a high hr from hemorrhage alone stays sinus
    // tachycardia. a custom atrial rhythm is induced only when a catecholamine or surge burden is present: the
    // push-dose support, the epinephrine-equivalent pressor drive, or a distal-line hypertensive spike. ACM still
    // owns its native critical rhythms, so if hr exceeds the stock 220 line, vt and PVT take priority.
    // Arrhythmia burden is deliberately separate from the hemodynamic MAP-support cap. B20 reused the 25 mmHg
    // pressor cap here while the SVT threshold was 35, which made infusion-only SVT mathematically unreachable:
    // even a massive epinephrine drip could score at most 25 and could only induce atrial tachycardia. Keep the
    // blood-pressure support capped, but let catecholamine arrhythmia burden continue to a separate bounded ceiling.
    private _surgeScoreCap = missionNamespace getVariable ["ACME_rhythmPressorSurgeScoreCap", 60];
    private _epiArrhythmiaBurden = (((_epiLikeDrive * 1000) * _coeff) min _surgeScoreCap);
    private _surgeScore = (_pushDose + _hyperSpike + _epiArrhythmiaBurden) min _surgeScoreCap;
    _state set ["pressorSurgeScore", _surgeScore];
    private _surgeATThr = missionNamespace getVariable ["ACME_rhythmPressorSurgeATThreshold", 18];
    private _surgeSVTThr = missionNamespace getVariable ["ACME_rhythmPressorSurgeSVTThreshold", 35];
    private _surgeClearFactor = missionNamespace getVariable ["ACME_rhythmPressorSurgeClearFactor", 0.55];
    private _surgeEnabled = missionNamespace getVariable ["ACME_rhythmPressorSurgeEnabled", true];
    private _hrNowSurge = _patient getVariable ["ace_medical_heartRate", 80];
    private _nativeRhythmSurge = _patient getVariable ["ACM_circulation_Cardiac_RhythmState", 0];
    private _surgeCanInduce = _surgeEnabled
        && {alive _patient}
        && {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
        && {(_patient getVariable ["ACME_rhythm_active", 0]) == 0}
        && {_nativeRhythmSurge == 0}
        && {_hrNowSurge >= (missionNamespace getVariable ["ACME_rhythmPressorSurgeMinHR", 115])}
        && {_hrNowSurge < (missionNamespace getVariable ["ACME_rhythmPressorSurgeMaxHR", 220])}
        && {CBA_missionTime >= (_patient getVariable ["ACME_rhythmPressorSurgeRefractoryUntil", 0])};

    if (!_surgeCanInduce || {_surgeScore < (_surgeATThr * _surgeClearFactor)}) then {
        _patient setVariable ["ACME_rhythmPressorSurgeStart", -1, false];
        _patient setVariable ["ACME_rhythmPressorSurgeKind", "", false];
    } else {
        if (_surgeScore >= _surgeATThr) then {
            private _kind = ["atrialTach", "svt"] select (_surgeScore >= _surgeSVTThr);
            private _curKind = _patient getVariable ["ACME_rhythmPressorSurgeKind", ""];
            private _start = _patient getVariable ["ACME_rhythmPressorSurgeStart", -1];
            if (_curKind != _kind || {_start < 0}) then {
                _patient setVariable ["ACME_rhythmPressorSurgeKind", _kind, false];
                _patient setVariable ["ACME_rhythmPressorSurgeStart", CBA_missionTime, false];
            } else {
                if ((CBA_missionTime - _start) >= (missionNamespace getVariable ["ACME_rhythmPressorSurgeSustainSec", 6])) then {
                    private _code = [101, 104] select (_kind == "svt");
                    private _label = ["Atrial Tachycardia", "SVT"] select (_kind == "svt");
                    private _targetHR = [
                        (missionNamespace getVariable ["ACME_rhythm_atHR", 185]),
                        (missionNamespace getVariable ["ACME_rhythm_svtHR", 190])
                    ] select (_kind == "svt");
                    [objNull, _patient, _code, _label, _targetHR] call ACME_fnc_rhythmToggle;
                    [_patient, "ACME_rhythmPressorSurgeRefractoryUntil", CBA_missionTime + (missionNamespace getVariable ["ACME_rhythmPressorSurgeRefractorySec", 90])] call ACME_fnc_setVarNet;
                    _patient setVariable ["ACME_rhythmPressorSurgeStart", -1, false];
                    _patient setVariable ["ACME_rhythmPressorSurgeKind", "", false];
                    _state set ["pressorSurgeInduced", _label];
                    // there is no activity-log line, because naming the induced rhythm would reveal the condition of the
                    // patient.
                };
            };
        };
    };

    // net offset.
    // acidosis from sustained hypoperfusion blunts catecholamines: the longer a patient sits profoundly
    // hypotensive, the less the pressors and push-dose do. it accrues while the effective MAP is low and recovers
    // once perfusion is restored. fast treatment therefore keeps pressors working, and delay makes them
    // refractory, which is the death spiral of decompensated shock. it is capped, so it never fully zeroes
    // support.
    private _rawSupport = _pressorEff + _pushDose + _hyperSpike;
    private _acidMAPBase = _nativeMAPforAcid;
    if (_inCardiacArrest && {missionNamespace getVariable ["ACME_circ_arrestForcesAcidosis", true]}) then {
        _acidMAPBase = 0;
    };
    private _effMAPpre = (_acidMAPBase + _rawSupport - _shockDrop - _caMAPdrop);
    _state set ["acidMAPBase", _acidMAPBase];
    _state set ["acidEffMAP", _effMAPpre];
    _state set ["acidArrestDriver", _inCardiacArrest];

    // separated acidosis model.
    // metabolicacidosis is the hypoperfusion and lactic component, floored by the hyperchloremic ns load.
    // respiratoryacidosis is the CO2 retention from inadequate ventilation.
    // acidosis is the total scalar used by the pressor blunting and the coagulopathy, capped from 0 to 1.
    private _legacyAcid = _state getOrDefault ["acidosis", 0];
    private _metabolicAcidosis = _state getOrDefault ["metabolicAcidosis", _legacyAcid];
    private _respAcidosis = _state getOrDefault ["respiratoryAcidosis", 0];
    private _acidThresh = missionNamespace getVariable ["ACME_circ_acidosisMAPThreshold", 55];

    private _shockMetAcidGain = 0;
    private _shockMetAcidRecover = 0;
    private _shockMetAcidFrac = 0;
    // metabolic, or lactic, acidosis from hypoperfusion is slow and needs sustained poor flow. it is not a linear
    // ramp from the first second of a low MAP, because tissue has to sit anaerobic long enough for lactate to
    // build.
    // 0 to 3 min: hypoperfusion is underway with little to show for it.
    // 3 to 10 min: lactate and the base deficit start to accumulate.
    // 10 to 20 min: meaningful metabolic acidosis.
    // 20 to 40 min and beyond: severe, if nobody fixes the shock.
    // it is modeled with a dwell timer, so the first minutes barely move the needle, and a nonlinear severity
    // response, so a marginal MAP creeps while a truly collapsed one accelerates.
    private _shockDwell = _state getOrDefault ["shockDwell", 0];
    if (_effMAPpre < _acidThresh) then {
        _shockDwell = _shockDwell + _acidDt;
        private _acidFullMAP = missionNamespace getVariable ["ACME_circ_acidosisFullMAP", 25];
        _shockMetAcidFrac = linearConversion [_acidThresh, _acidFullMAP, _effMAPpre, 0, 1, true];
        // onset ramp. it is about 5 percent of the full rate at the moment perfusion fails, and reaches the full rate
        // only after the hypoperfusion has been sustained, which defaults to 5 min. this is what stops acidosis
        // appearing instantly.
        private _onsetSecs = missionNamespace getVariable ["ACME_circ_acidosisOnsetSecs", 300];
        private _dwellRamp = linearConversion [0, _onsetSecs, _shockDwell, 0.05, 1, true];
        // nonlinear in the depth of shock. an exponent above 1 means mild hypoperfusion is far gentler than a
        // crash.
        private _sevExp = missionNamespace getVariable ["ACME_circ_acidosisSeverityExp", 1.6];
        private _sevCurve = _shockMetAcidFrac ^ _sevExp;
        _shockMetAcidGain = (missionNamespace getVariable ["ACME_circ_acidosisPerSec", 0.00075]) * _sevCurve * _dwellRamp * _hypoAcidGainMult * _acidDt;
        _metabolicAcidosis = (_metabolicAcidosis + _shockMetAcidGain) min 1;
    } else {
        // perfusion restored. the dwell unwinds, faster than it built and not instantly, because a patient who was
        // just in deep shock re-acidifies quickly if they crash again.
        _shockDwell = (_shockDwell - (_acidDt * 2)) max 0;
        // lactate clearance is slow. fixing the shock does not fix the acidosis in seconds.
        _shockMetAcidRecover = (missionNamespace getVariable ["ACME_circ_acidosisRecoverPerSec", 0.0030]) * _hypoAcidRecoveryMult * _acidDt;
        _metabolicAcidosis = (_metabolicAcidosis - _shockMetAcidRecover) max 0;
    };
    _state set ["shockDwell", _shockDwell];

    // an oxygen delivery failure is its own acid source, independent of the blood pressure. the gain above keys on
    // MAP, which is a decent proxy for hypoperfusion and is blind to anemia. a casualty filled with crystalloid
    // can hold a respectable pressure on oxygen-carrying capacity that has been halved, and they are anaerobic
    // while every number a medic can see says otherwise.
    // there are three guards, because this must never become a second gate on consciousness. DO2 is invisible.
    // there is no field device that measures it, so a medic cannot see it coming, cannot chase it and must never
    // be beaten by it. it is a slow background debt for doing the wrong thing, not a mechanism that puts anyone
    // down.
    if (missionNamespace getVariable ["ACME_sys_do2", true]) then {
        private _do2v = [_patient] call ACME_fnc_oxygenDelivery;
        _state set ["do2", _do2v];

        // guard 1. a casualty who is awake and saturating is winning. if they are conscious and their SpO2 meets what
        // ACM needs to keep them up, they are perfusing their brain by definition, whatever the delivery arithmetic
        // says about the rest of them. the accrual stops. this is the guarantee that waking someone up sticks, because
        // nothing invisible is allowed to drag them back under three seconds later.
        // the SpO2 bar sits a couple of points below the wake floor rather than exactly on it. the mercy backstop
        // stabilizes a woken casualty to precisely ACME_ko_wakeFloorSpO2, so matching that number exactly meant the
        // two systems were deciding the fate of the same casualty off the same value with no margin. land at 84.9 and
        // the guard fails on somebody the game just chose to wake up. the tolerance makes them agree.
        private _wakeFloor = missionNamespace getVariable ["ACME_ko_wakeFloorSpO2", 85];
        private _spo2Bar = (missionNamespace getVariable ["ACME_do2_consciousSpO2Floor", -1]);
        if (_spo2Bar < 0) then {
            _spo2Bar = _wakeFloor - (missionNamespace getVariable ["ACME_do2_wakeFloorTolerance", 3]);
        };
        private _spo2Now = _patient getVariable ["ace_medical_spo2", 97];

        // a sedated, intubated, ventilated casualty is also winning. the guard originally required consciousness,
        // which meant the casualty receiving the best possible airway management was the only one it never protected,
        // because a properly managed vented patient is unconscious by definition. being on a secured airway with a
        // machine breathing for them and good saturations is a managed patient, not a neglected one.
        private _ventOK = (_patient getVariable ["ACME_vent_connected", false])
            && {_patient getVariable ["ACME_vent_driving", false]};

        private _awakeOK = (_spo2Now >= _spo2Bar)
            && {(!(_patient getVariable ["ACE_isUnconscious", false])) || {_ventOK}};

        // cardiac arrest owns its own acid. during arrest there is no meaningful delivery by definition, and the
        // arrest physiology already accounts for it. letting this path pile on as well would double-count a casualty
        // in the one state where the medic is doing everything they can. the reperfusion window then covers the
        // post-ROSC recovery, when they are still unconscious with delivery climbing back.
        private _arrestNow = _patient getVariable ["ace_medical_inCardiacArrest", false];

        // guard 2, hysteresis. the entry and exit thresholds differ, so a casualty hovering at the boundary does not
        // chatter in and out of accruing a debt.
        private _crit  = missionNamespace getVariable ["ACME_do2_criticalFrac", 0.5];
        private _clear = missionNamespace getVariable ["ACME_do2_clearFrac", 0.58];
        private _inDeficit = _state getOrDefault ["do2Deficit", false];
        if (_inDeficit) then {
            if (_do2v >= _clear) then {
                _inDeficit = false;
                _state set ["do2RecoveredAt", _now];  // start the reperfusion window.
            };
        } else {
            if (_do2v < _crit) then { _inDeficit = true; };
        };
        _state set ["do2Deficit", _inDeficit];
        // on ROSC, open the reperfusion window. delivery is climbing back and the tissue is repaying, so the moments
        // right after a save are not the moment to start charging them again.
        if ((_state getOrDefault ["do2WasArrest", false]) && {!_arrestNow}) then {
            _state set ["do2RecoveredAt", _now];
        };
        _state set ["do2WasArrest", _arrestNow];

        // guard 3, the reperfusion window. once delivery is restored the tissue is repaying its debt rather than
        // building more of it. for this window nothing re-accrues even if delivery dips again, so a medic who has just
        // given blood is not punished for the wobble while it circulates.
        private _reperfWin = missionNamespace getVariable ["ACME_do2_reperfusionWindow", 45];
        private _inReperf = (_now - (_state getOrDefault ["do2RecoveredAt", -1e9])) < _reperfWin;

        if (_inDeficit && {!_awakeOK} && {!_inReperf} && {!_arrestNow}) then {
            private _deficit = linearConversion [_crit, (missionNamespace getVariable ["ACME_do2_lethalFrac", 0.2]), _do2v, 0, 1, true];
            _metabolicAcidosis = (_metabolicAcidosis
                + ((missionNamespace getVariable ["ACME_do2_acidosisPerSec", 0.0009]) * _deficit * _acidDt)) min 1;
        };
    };

    _state set ["shockMetAcidFrac", _shockMetAcidFrac];
    _state set ["shockMetAcidGain", _shockMetAcidGain];
    _state set ["shockMetAcidRecover", _shockMetAcidRecover];

    // Balanced crystalloid buffering is queued by the native blood-volume admission path and consumed exactly once
    // here.  This prevents getBloodVolumeChange and circHandle from both writing total acidosis in the same vital tick.
    if (_acidDt > 0) then {
        private _plasmaLyteCredit = _patient getVariable ["ACME_plasmaLyteAcidCredit", 0];
        if (_plasmaLyteCredit > 0) then {
            _metabolicAcidosis = (_metabolicAcidosis - _plasmaLyteCredit) max 0;
            _patient setVariable ["ACME_plasmaLyteAcidCredit", 0, false];
        };
    };

    private _salineGivenMl = _patient getVariable ["ACME_circ_salineGivenMl", 0];
    private _salineAcidosis = 0;
    if (missionNamespace getVariable ["ACME_salineAcidosis_enabled", true]) then {
        private _startMl = missionNamespace getVariable ["ACME_salineAcidosis_startMl", 500];
        private _fullMl = missionNamespace getVariable ["ACME_salineAcidosis_fullMl", 3000];
        private _maxAcid = missionNamespace getVariable ["ACME_salineAcidosis_max", 0.65];
        private _expAcid = missionNamespace getVariable ["ACME_salineAcidosis_exponent", 2.0];
        private _frac = (((_salineGivenMl - _startMl) / ((_fullMl - _startMl) max 1)) max 0) min 1;
        _salineAcidosis = (_maxAcid * (_frac ^ _expAcid)) min _maxAcid;
    };
    _state set ["salineGivenMl", _salineGivenMl];
    _state set ["salineAcidosis", _salineAcidosis];
    if (_acidDt > 0) then {
        _metabolicAcidosis = _metabolicAcidosis max _salineAcidosis;
    };

    // a low CPP from TBI or ICP is a secondary metabolic acid source only when cerebral perfusion is genuinely
    // poor. this stops the TBI itself from creating acidosis directly, and still makes low-CPP physiology
    // matter.
    private _tbiCppAcidGain = 0;
    private _tbiCppFrac = 0;
    if (missionNamespace getVariable ["ACME_tbi_cppAcidosisEnabled", true]) then {
        private _tbiState = _patient getVariable ["ACME_tbi_State", createHashMap];
        private _roscAt = _patient getVariable ["ACM_circulation_ROSC_Time", -1e9];
        private _tbiCppReperf = (CBA_missionTime - _roscAt) < (missionNamespace getVariable ["ACME_tbi_cppReperfusionWindow", 45]);
        // B67: cardiac arrest already owns the no-flow acid driver above and DO2 already suppresses its own duplicate
        // source. CPP must follow the same rule. It also observes a brief post-ROSC reperfusion window so a successful
        // resuscitation cannot immediately start stacking a second hidden TBI acid debt while pressure is settling.
        private _tbiStageForAcid = _tbiState getOrDefault ["herniationStage", 0];
        // B67 terminal-only ICP arrest contract: low CPP is clinically meaningful at every stage, but the TBI-specific
        // acid *penalty* is allowed to become an arrest-supporting mechanism only at stage 3. Stages 0-2 can still
        // deteriorate neurologically and show Cushing/irregular breathing, but they cannot create a hidden metabolic
        // debt that later blunts pressors enough to recycle a well-resuscitated patient back into arrest. Unrelated
        // shock, anemia, hypoxia, hypercapnia, saline load, etc. retain their normal acid pathways.
        if (_tbiStageForAcid >= 3 && {!_inCardiacArrest} && {!_tbiCppReperf} && {count _tbiState > 0} && {_patient getVariable ["ACME_tbi_HasTBI", false]}) then {
            private _cppVal = _tbiState getOrDefault ["cpp", -999];
            private _cppTargetAcid = _tbiState getOrDefault ["cppTarget", (missionNamespace getVariable ["ACME_tbi_cppTarget", 70])];
            if (_cppVal > -998 && {_cppVal < _cppTargetAcid}) then {
                _tbiCppFrac = linearConversion [_cppTargetAcid, (missionNamespace getVariable ["ACME_tbi_cppAcidosisFullCPP", 30]), _cppVal, 0, 1, true];
                _tbiCppAcidGain = _tbiCppFrac * (missionNamespace getVariable ["ACME_tbi_cppAcidosisPerSec", 0.0015]) * _hypoAcidGainMult * _acidDt;
                _metabolicAcidosis = (_metabolicAcidosis + _tbiCppAcidGain) min 1;
            };
        };
        _state set ["tbiCppStage", _tbiStageForAcid];
        _state set ["tbiCppReperfusion", _tbiCppReperf];
    };
    _state set ["tbiCppAcidFrac", _tbiCppFrac];
    _state set ["tbiCppAcidGain", _tbiCppAcidGain];

    // respiratory acidosis, from PaCO2 and CO2 retention.
    // PaCO2 is the internal retained CO2 pool that drives respiratory acidosis.
    // EtCO2 is only what can be exhaled and seen on capnography. during apnea it can be low or flat while PaCO2
    // rises.
    private _respDeficit = 0;
    private _rawTargetRR = _patient getVariable ["ACM_core_TargetVitals_RespirationRate", 16];
    private _targetRR = _patient getVariable ["ACME_tbi_savedRRTarget", (_patient getVariable ["ACME_circ_respAcidosisBaselineRR", _rawTargetRR])];
    if (!(_patient getVariable ["ACME_tbi_HasTBI", false]) && {_rawTargetRR > 6}) then {
        _targetRR = _rawTargetRR;
    };
    if (_targetRR <= 6) then {_targetRR = 16};
    // the respiratory deficit must be measured against the rate needed for adequate gas exchange, not against a
    // compensatory drive. edema, acidosis and TBI push ACM's target rr up, because tachypnea is the body asking
    // for more, so a patient breathing a perfectly adequate 18 against a target of 32 showed a permanent deficit
    // of about 44 percent, and CO2 climbed forever and never stopped. clamping the denominator to a normal
    // ventilatory requirement fixes the runaway: you only retain CO2 if you are actually under-ventilating.
    private _targetRRCap = missionNamespace getVariable ["ACME_circ_respAcidosisMaxTargetRR", 20];
    _targetRR = _targetRR min _targetRRCap;
    _patient setVariable ["ACME_circ_respAcidosisBaselineRR", _targetRR, false];

    private _airway = ((([_patient] call ACM_airway_fnc_getAirwayState) / 0.95) min 1) max 0;
    private _breath = ((([_patient] call ACM_breathing_fnc_getBreathingState) / 0.85) min 1) max 0;
    private _rrNow = _patient getVariable ["ACM_breathing_RespirationRate", 18];
    private _bvmProvider = _patient getVariable ["ACM_breathing_BVM_provider", objNull];
    private _bvmMedic = _patient getVariable ["ACM_breathing_BVM_Medic", objNull];
    private _bvmActive = (alive _bvmProvider) || {alive _bvmMedic};
    private _ventGate = _airway min _breath;
    private _effVent = _rrNow * _ventGate;
    private _ventFrac = if (_targetRR > 0) then {(_effVent / _targetRR) max 0 min 1.5} else {1};
    if (_targetRR > 0 && {_effVent < _targetRR}) then {
        _respDeficit = ((_targetRR - _effVent) / _targetRR) max 0 min 1;
    };

    // the minute ventilation of the ventilator drives CO2, not its rate alone.
    // without this, the CO2 model saw only the breath count, _rrNow. a machine set to 12 breaths of 200 ml and a
    // machine set to 12 breaths of 500 ml looked identical to the PaCO2 of the patient, which is wrong. the first
    // is profoundly hypoventilating and the second is normal. mvadequacy already captures rate times alveolar
    // volume, in fn_ventdrivetick as alveolar mv over target mv, so when the vent is the thing breathing the
    // patient it sets the effective ventilation fraction. so:
    // small tidal volumes at a fine rate give a low mvadequacy and a low _ventFrac. CO2 climbs, respiratory
    // acidosis develops, and EtCO2 rises toward the hypoventilation ceiling. the low minute volume alarm and the
    // rising capnograph now agree, and the same number drives both.
    // hyperventilation, from a rate or volume that is too high, gives an mvadequacy above 1 and a _ventFrac above
    // 1. CO2 washes out, EtCO2 falls and respiratory alkalosis develops. that is the mechanism behind the high
    // minute volume alarm and the classic hyperventilated-TBI kill, a cerebral vasoconstriction from a low PaCO2,
    // which the TBI model reads off this same PaCO2.
    // it gates on the vent actually driving, so a mandatory breath is being delivered through a secured airway. a
    // vent in a spontaneous mode with no drive, or one not connected, leaves _ventFrac exactly as the spontaneous
    // model computed it. the machine only owns the CO2 when it is the one moving the gas.
    if ((_patient getVariable ["ACME_vent_driving", false]) && {(_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient}) then {
        private _mvAdq = _patient getVariable ["ACME_vent_mvAdequacy", 1];
        if (!(_mvAdq isEqualType 0) || {!(finite _mvAdq)}) then { _mvAdq = 1 };
        // mvadequacy is alveolar mv over target, already in the 0 to 1.6 range. map it straight onto the ventilation
        // fraction the CO2 model uses, with the same 0 to 1.5 clamp as the spontaneous path, and take the airway and
        // breathing gate into account, so an mvadequacy of 1 through a compromised airway still cannot fully clear
        // CO2.
        _ventFrac = ((_mvAdq * _ventGate) max 0) min 1.5;
        _effVent = _targetRR * _ventFrac;
        _respDeficit = (1 - (_ventFrac min 1)) max 0 min 1;
    };

    // in cardiac arrest ACM can leave stale rr and airway values visible for a moment, and physiologically the
    // patient is not ventilating unless someone is actively bagging. force the internal CO2 and acidosis model to
    // see apnea during arrest. a BVM provides partial effective ventilation and can clear CO2.
    if (_inCardiacArrest && {missionNamespace getVariable ["ACME_circ_arrestForcesAcidosis", true]}) then {
        if (_bvmActive) then {
            // Simple mode's actual alveolar delivery remains authoritative in
            // arrest. The generic hand-bagging floor would otherwise make a very
            // low ventilator rate clear CO2 as if it supplied adequate breaths.
            private _simpleVentArrest = (missionNamespace getVariable ["ACME_vent_simpleMode", false])
                && {_patient getVariable ["ACME_vent_driving", false]}
                && {(_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient};
            if (!_simpleVentArrest) then {
                _ventFrac = (_ventFrac max (missionNamespace getVariable ["ACME_circ_bvmVentFrac", 0.75])) min 1.5;
            };
            _effVent = _targetRR * _ventFrac;
            _respDeficit = (1 - (_ventFrac min 1)) max 0 min 1;
        } else {
            _rrNow = 0;
            _ventGate = 0;
            _effVent = 0;
            _ventFrac = 0;
            _respDeficit = 1;
        };
    };

    private _paCO2Normal = missionNamespace getVariable ["ACME_circ_paCO2Normal", 40];
    private _paCO2Max = missionNamespace getVariable ["ACME_circ_paCO2Max", 95];
    private _paCO2 = _state getOrDefault ["paCO2", _paCO2Normal];
    private _co2Rise = 0;
    private _co2Clear = 0;
    private _exhaleMin = missionNamespace getVariable ["ACME_circ_paCO2ExhaleMinVentFrac", 0.08];
    private _hasExhalation = (_ventFrac > _exhaleMin) && {_rrNow > 1} && {_ventGate > 0.05};
    private _apnea = !_hasExhalation;

    if (missionNamespace getVariable ["ACME_circ_paCO2Enabled", true]) then {
        if (_respDeficit > 0) then {
            // CO2 kinetics are biphasic, not a flat ramp. in apnea, PaCO2 jumps about 12 mmhg in the first minute, as the
            // stored CO2 pool equilibrates, then settles to about 3.4 mmhg/min of metabolic production. the old flat 8.4
            // mmhg/min was simultaneously too slow at onset and far too fast in sustained apnea, which is why acidosis
            // came on hard and never stopped.
            private _hypoDwell = _state getOrDefault ["hypoventDwell", 0];
            _hypoDwell = _hypoDwell + _acidDt;
            _state set ["hypoventDwell", _hypoDwell];
            private _fastRate = (missionNamespace getVariable ["ACME_circ_paCO2RiseFastPerMin", 19]) / 60;  // mmhg/s initially. it decays to slow, and integrates to about 12 mmhg over the first minute.
            private _slowRate = (missionNamespace getVariable ["ACME_circ_paCO2RiseSlowPerMin", 3.4]) / 60;  // mmhg/s, sustained.
            private _tau = missionNamespace getVariable ["ACME_circ_paCO2RiseTau", 30];  // seconds, for the fast to slow decay.
            private _phaseRate = _slowRate + ((_fastRate - _slowRate) * (0.5 ^ (_hypoDwell / (_tau max 1))));
            _co2Rise = _phaseRate * _respDeficit;
            _paCO2 = (_paCO2 + (_co2Rise * _acidDt)) min _paCO2Max;
        } else {
            _state set ["hypoventDwell", 0];
            private _clearFrac = (_ventFrac max 0.5) min 1.5;
            _co2Clear = (missionNamespace getVariable ["ACME_circ_paCO2ClearPerSec", 0.40]) * _clearFrac;  // good ventilation blows CO2 off fast.
            _paCO2 = (_paCO2 - (_co2Clear * _acidDt)) max _paCO2Normal;
        };
    };

    private _paStart = missionNamespace getVariable ["ACME_circ_paCO2RespAcidStart", 45];
    private _paFull = missionNamespace getVariable ["ACME_circ_paCO2RespAcidFull", 80];
    // nonlinear. a mildly raised PaCO2 is well buffered and barely acidotic, and the ph falls away steeply only as
    // the CO2 climbs into the severe range. it was a straight linear ramp from 45.
    private _respAcidCurveExp = missionNamespace getVariable ["ACME_circ_respAcidosisCurveExp", 1.5];
    private _respAcidTarget = (linearConversion [_paStart, _paFull, _paCO2, 0, 1, true]) ^ _respAcidCurveExp;
    if (_respAcidTarget > _respAcidosis) then {
        private _riseStep = (missionNamespace getVariable ["ACME_circ_respAcidosisPerSec", 0.006]) * ((0.35 + _respAcidTarget) min 1) * _acidDt;
        _respAcidosis = (_respAcidosis + _riseStep) min _respAcidTarget min 1;
    } else {
        private _fallStep = (missionNamespace getVariable ["ACME_circ_respAcidosisRecoverPerSec", 0.035]) * _acidDt;  // respiratory acidosis corrects quickly once a medic ventilates the patient.
        _respAcidosis = (_respAcidosis - _fallStep) max _respAcidTarget max 0;
    };

    private _perfFracEt = linearConversion [20, 65, _effMAPpre, 0.15, 1, true];
    private _etco2Estimate = if (_hasExhalation) then {(_paCO2 * _perfFracEt * (linearConversion [0.1, 1, _ventFrac, 0.45, 1, true])) max 0 min 90} else {0};

    // the capnograph tells you during the arrest, not after it. hyperinflation from wrong-mode venting during CPR
    // impedes venous return, so less blood transits the lungs and less CO2 reaches the airway, and the number on
    // the EMMA falls. a medic watching ETCO2 during the resus, which is exactly what ETCO2 during a resus is for,
    // can see the ventilator fighting the compressions and fix the mode before ROSC is ever at stake.
    // it reaches full effect at 45 s of accrued hyperinflation, which is roughly a 60 percent haircut. that is
    // deep enough to read as something being wrong with the resus, and shallow enough not to read as a dislodged
    // tube.
    private _cprBadEt = _patient getVariable ["ACME_vent_cprBadTime", 0];
    if (_cprBadEt > 0) then {
        _etco2Estimate = _etco2Estimate * (linearConversion [0, 45, _cprBadEt, 1, 0.4, true]);
    };
    private _etco2Observed = -1;
    if (!isNil "ACM_breathing_fnc_getEtCO2") then {
        _etco2Observed = [_patient] call ACM_breathing_fnc_getEtCO2;
    };

    // Diagnostic mirror only; the common getter is the source, never a consumer of this cache.
    [_patient,"ACME_vent_etco2Adj",_etco2Observed,0.10,2] call ACME_fnc_setVarNetApprox;
    _patient setVariable ["ACME_vent_etco2AdjAt",CBA_missionTime,false];

    _state set ["paCO2", _paCO2];
    _state set ["paCO2Burden", linearConversion [_paCO2Normal, _paCO2Max, _paCO2, 0, 1, true]];
    _state set ["paCO2Rise", _co2Rise];
    _state set ["paCO2Clear", _co2Clear];
    _state set ["respAcidosisTarget", _respAcidTarget];
    _state set ["respAcidosisTargetRR", _targetRR];
    _state set ["respAcidosisEffectiveVent", _effVent];
    _state set ["respVentFrac", _ventFrac];
    _state set ["respBVMActive", _bvmActive];
    _state set ["respHasExhalation", _hasExhalation];
    _state set ["respApnea", _apnea];
    _state set ["etco2Estimate", _etco2Estimate];
    _state set ["etco2Observed", _etco2Observed];
    _state set ["paCO2EtCO2Gap", if (_etco2Observed >= 0) then {(_paCO2 - _etco2Observed) max 0} else {(_paCO2 - _etco2Estimate) max 0}];

    private _acidosis = (_metabolicAcidosis + _respAcidosis) min 1;
    _state set ["metabolicAcidosis", _metabolicAcidosis];
    _state set ["respiratoryAcidosis", _respAcidosis];
    _state set ["respiratoryAcidosisDeficit", _respDeficit];
    _state set ["totalAcidosis", _acidosis];
    _state set ["acidosis", _acidosis];
    private _maxBlunt = missionNamespace getVariable ["ACME_circ_acidosisMaxBlunt", 0.45];
    // the catecholamine response is blunted by acidosis and hypothermia together, and they compound. a cold,
    // acidotic myocardium barely answers the pressors.
    private _acidBluntFrac = ((_acidosis * _maxBlunt) max 0) min 0.95;
    private _hypoBluntFrac = (_hypoBlunt max 0) min 0.95;
    private _support = _rawSupport * (1 - _acidBluntFrac) * (1 - _hypoBluntFrac);
    private _supportLoss = (_rawSupport - _support) max 0;
    [_patient,"ACME_pressorResistAdd",((_resistAdd max 0) * (1 - _acidBluntFrac) * (1 - _hypoBluntFrac)),0.10,2] call ACME_fnc_setVarNetApprox;
    // Distributive shock and hypocalcemia change tone, not a second final-pressure offset.
    private _nativeR = _patient getVariable ["ACME_nativeResistance", 100];
    private _toneDelta = -(_shockDrop + _caMAPdrop) * (_nativeR / (_nativeMAPforAcid max 1));
    [_patient,"ACME_circ_resistDelta",_toneDelta,0.10,2] call ACME_fnc_setVarNetApprox;
    _state set ["rawPressorSupport", _rawSupport];
    _state set ["effectivePressorSupport", _support];
    _state set ["pressorSupportLoss", _supportLoss];
    _state set ["acidPressorBluntFrac", _acidBluntFrac];
    _state set ["hypoPressorBluntFrac", _hypoBluntFrac];

    private _offset = _support - _shockDrop - _caMAPdrop; // Diagnostic estimate only; effects are carried by HR/SVR, never added twice.
    // broadcast on a meaningful change only, at 1 mmhg or more, or a crossing of zero. the getbloodpressure
    // wrapper reads this on remote machines too, so it must be global, and a per-tick rebroadcast for every
    // patient would flood the network.
    private _prevOffset = _patient getVariable ["ACME_circ_bpOffset", 0];
    if (abs (_offset - _prevOffset) >= 1 || {(_offset == 0) != (_prevOffset == 0)}) then {
        [_patient, "ACME_circ_bpOffset", _offset] call ACME_fnc_setVarNet;
    };
    _state set ["pressorSupport", _pressorEff];
    _state set ["pressorGated", _pressorGated && {_pressorDrive > 0}];
    _state set ["shockDrop", _shockDrop];
    _state set ["shockSeverity", _shockSeverity];
    _state set ["distalDrip", _distalDripActive];
    _state set ["distalDrugEffectActive", _distalDrugEffectActive];
    _state set ["distalPressor", _distalPressorActive];

    // [ACME-dbg] temporary pharmacodynamics instrumentation, for a diagnostic build. it is throttled to about 1 hz
    // per patient and runs only for patients carrying a drug or a rhythm. it dumps the exact engine values behind
    // the esmolol, push-epi, dirty-epi, norepi and lidocaine reports, so each root can be fixed precisely. remove
    // it after triage.
    if (missionNamespace getVariable ["ACME_circ_debugVitals", true]) then {
        private _hasDrug = (count (_patient getVariable ["ACME_infusion_BagMedications", []]) > 0)
            || {_pushDose > 0} || {_pressorDrive > 0}
            || {(_patient getVariable ["ACME_rhythm_active", 0]) != 0}
            || {count (_patient getVariable ["ace_medical_medications", []]) > 0};
        if (_hasDrug && {(_now - (_state getOrDefault ["dbgLogAt", 0])) >= 1}) then {
            _state set ["dbgLogAt", _now];
            private _bp = [_patient] call ace_medical_status_fnc_getBloodPressure;
            private _lido = [_patient] call ACME_fnc_lidoEffectiveness;
            private _volAdeq = [_patient] call ACME_fnc_tbiIsVolumeAdequate;
        };
    };

    // shock heart-rate arc.
    // this makes the crash show on the monitor and opens a second road to arrest. early shock is a compensatory
    // tachycardia, where the body defends cardiac output. as the patient decompensates the rate collapses into
    // bradycardia, which reaches ACM's own heartrate under 40 cardiac-arrest trigger. pressor and push-dose
    // support is chronotropic and restores perfusion, so it pulls the rate back up out of the bradycardia and
    // rescues both the MAP and the hr arrest paths at once. it is a bounded nudge, so ACM keeps ownership of the
    // actual heart-rate sim and we only bias it.
    // we no longer write ace_medical_heartRate here. instead we publish a desired hr target, and the
    // updateheartrate wrapper, in postinit, is the sole writer and drives hr toward it. that stops ACM's own
    // updateheartrate from fighting our value each cycle, which was the vitals switching back and forth. -1 means
    // not driving, so the wrapper hands hr back to ACM.
    private _hrDrive = -1;
    if (_shockActive) then {
        private _peak  = missionNamespace getVariable ["ACME_circ_shockTachyPeak", 120];
        private _brady = missionNamespace getVariable ["ACME_circ_shockBradyFloor", 32];
        private _arc = if (_shockSeverity < 0.5) then {
            linearConversion [0, 0.5, _shockSeverity, 85, _peak, true]  // compensate.
        } else {
            linearConversion [0.5, 1, _shockSeverity, _peak, _brady, true]  // decompensate.
        };
        private _chrono = missionNamespace getVariable ["ACME_circ_supportChronotropy", 0.8];  // bpm per mmhg.
        _hrDrive = _arc + (_support * _chrono);
        _state set ["shockHRTarget", _hrDrive];
    } else {
        _state set ["shockHRTarget", 0];
    };

    // hypothermia bradycardia.
    // cold slows the sa node independently of shock. the target interpolates from a nominal 80 down to a cold floor
    // as the core temp falls, and at the severe end it reaches ACM's own hr under 40 arrest path. the colder of
    // the shock arc and the cold target wins.
    if (_temp < (missionNamespace getVariable ["ACME_hypo_bradyStartTemp", 33])) then {
        private _coldTarget = linearConversion [
            (missionNamespace getVariable ["ACME_hypo_bradyStartTemp", 33]),
            (missionNamespace getVariable ["ACME_hypo_bradyFullTemp", 28]),
            _temp, 80, (missionNamespace getVariable ["ACME_hypo_bradyFloorHR", 34]), true];
        _hrDrive = if (_hrDrive < 0) then { _coldTarget } else { _hrDrive min _coldTarget };
    };

    // esmolol beta-blockade sinus rate.
    // ACM's esmolol hr adjustment is zeroed in config, because it misfired for a continuous infusion and
    // accumulated a spurious tachycardia. we own the chronotropy here, off the bounded esmolol effect. the
    // tachyarrhythmias were rate-controlled by the rhythm conversion above, and the rhythm system then owns hr
    // through the wrapper, so this branch is the sinus, non-custom-rhythm case. beta-blockade slows the resting
    // rate toward a bounded floor and never raises it. publishing the target routes hr through the updateheartrate
    // wrapper, which is the sole writer and bypasses ACM's path entirely.
    if (_esmololEffect > (missionNamespace getVariable ["ACME_esmolol_sinusOnsetEff", 0.08])
        && {(_patient getVariable ["ACME_rhythm_active", 0]) < 100}
    ) then {
        private _base = _hrRestBaseline;
        private _factor = linearConversion [
            (missionNamespace getVariable ["ACME_esmolol_sinusOnsetEff", 0.08]),
            (missionNamespace getVariable ["ACME_esmolol_sinusFullEff", 0.6]),
            _esmololEffect, 1.0, (missionNamespace getVariable ["ACME_esmolol_sinusFactor", 0.78]), true];
        private _esmTarget = (_base * _factor) max (missionNamespace getVariable ["ACME_esmolol_sinusFloorHR", 55]);
        // overdose. drop the target below the normal floor toward a dangerous bradycardia, a high-grade av block,
        // scaling with how far past therapeutic the serum sits. at full overdose the rate heads for
        // ACME_esmolol_overdoseFloorHR. this is what makes a runaway drip crash the hr instead of parking at about
        // 61.
        if (_esmOverdose > 0) then {
            _esmTarget = linearConversion [0, 1, _esmOverdose, _esmTarget, (missionNamespace getVariable ["ACME_esmolol_overdoseFloorHR", 35]), true];
        };
        _hrDrive = if (_hrDrive < 0) then { _esmTarget } else { _hrDrive min _esmTarget };
    };

    // magnesium fast-push bradycardia.
    // a fast magnesium infusion suppresses the sa and av node toward the shared tox floor, which is a bradycardia
    // rather than an arrest. the matching hypotension rides the resistance lever, so the two together tank the
    // patient. it lowers only, through min.
    private _drugBrady = _magFast;
    if (_drugBrady > 0) then {
        private _drugBradyTarget = linearConversion [0, 1, _drugBrady, _hrRestBaseline, (missionNamespace getVariable ["ACME_infusionTox_bradyFloorHR", 40]), true];
        _hrDrive = if (_hrDrive < 0) then { _drugBradyTarget } else { _hrDrive min _drugBradyTarget };
    };

    // calcium overdose: bradycardia into arrhythmia into arrest.
    // a calcium overdose, from the rate or the accumulated serum, suppresses the node progressively. the hr floor
    // scales from the resting baseline down to an arrest-capable floor, below 40, which fires ACM's native hr
    // arrest path. a rapid or excessive push therefore walks bradycardia into a junctional or escape arrhythmia
    // and then into asystole. the vasculature is two-phase and handled on the resistance lever above, with an
    // acute constriction and hypertension, then vasoplegia and hypotension near arrest. a therapeutic slow
    // correction leaves _caOd near 0 and does nothing.
    if (_caOd > 0) then {
        private _caFloor = missionNamespace getVariable ["ACME_ca_overdoseArrestFloorHR", 18];
        private _caBradyTarget = linearConversion [0, 1, _caOd, _hrRestBaseline, _caFloor, true];
        _hrDrive = if (_hrDrive < 0) then { _caBradyTarget } else { _hrDrive min _caBradyTarget };
    };

    // epinephrine chronotropy.
    // ACM's epi hr adjustment is zeroed in config, because it accumulated and misfired for a continuous drip. we
    // own the chronotropy of epi here, off the epi-specific infusion drive in mg/min, which is the same eased
    // value the pressor system uses and is non-zero for a fluid-delivered epi drip. a medication count is not,
    // because the bag-delivered epi is not registered as a counted medication. that is why an earlier
    // getMedicationCount version never fired and hr sat flat wide open. epi raises the rate, because it is a
    // catecholamine, unlike the lowering drives above, so this takes the max. it is skipped in shock, where the
    // shock arc already folds pressor support, epi included, into the hr target.
    if (!_shockActive) then {
        if (_epiInfusionDrive > (missionNamespace getVariable ["ACME_epi_chronoOnsetMgMin", 0.0005])) then {
            private _epiBase = _hrRestBaseline;
            private _epiBoost = (linearConversion [
                (missionNamespace getVariable ["ACME_epi_chronoOnsetMgMin", 0.0005]),
                (missionNamespace getVariable ["ACME_epi_chronoFullMgMin", 0.015]),
                _epiInfusionDrive, 0, (missionNamespace getVariable ["ACME_epi_chronoBoostBpm", 50]), true]) * _caPressorGate;
            private _epiTarget = _epiBase + (_epiBoost * (1 - _acidBluntFrac) * (1 - _hypoBluntFrac));
            _hrDrive = if (_hrDrive < 0) then { _epiTarget } else { _hrDrive max _epiTarget };
        };
    };

    // B12 boluses enter through native medication admission at their actual mg dose.
    // The decaying circulation support drives a bounded HR target; it never accumulates
    // a fresh native HR adjustment every frame. Quantitative gains are game tuning.
    if (!_shockActive && {_pushDose > 0.05}) then {
        private _pdMcg = _pushDose / ((missionNamespace getVariable ["ACME_circ_pushDoseMAPperMcg", 1.4]) max 0.1);
        private _pdBoost = (_pdMcg * (missionNamespace getVariable ["ACME_circ_pushDoseChronoBpmPerMcg", 2.0]))
            min (missionNamespace getVariable ["ACME_circ_pushDoseChronoMaxBpm", 55]);
        _pdBoost = _pdBoost * (1 - _acidBluntFrac) * (1 - _hypoBluntFrac);
        private _pdTarget = _hrRestBaseline + _pdBoost;
        _hrDrive = if (_hrDrive < 0) then { _pdTarget } else { _hrDrive max _pdTarget };
        _state set ["pushDoseHRBoost", _pdBoost];
    } else {
        _state set ["pushDoseHRBoost", 0];
    };

    // lidocaine-toxicity seizure: a sympathetic tachycardia during the active convulsion. it folds into the hr
    // drive so it coexists with whatever else is driving hr, through max, because a seizure raises the floor.
    if ((_patient getVariable ["ACME_lido_seizureState", ""]) == "active") then {
        private _seizHR = _hrRestBaseline + (missionNamespace getVariable ["ACME_lido_seizureHRBoost", 35]);
        _hrDrive = if (_hrDrive < 0) then { _seizHR } else { _hrDrive max _seizHR };
    };

    // lidocaine cardiac toxicity: bradycardia. it applies after the seizure tachycardia, through min, so as the
    // heart fails the falling rate overrides the sympathetic surge.
    private _lidoBrady = _patient getVariable ["ACME_lidoTox_hrTarget", -1];
    if (_lidoBrady >= 0) then {
        _hrDrive = if (_hrDrive < 0) then { _lidoBrady } else { _hrDrive min _lidoBrady };
    };

    // rocuronium awake-paralysis tachycardia, published by fn_rocuroniumtick above. it is a stress response, so it
    // raises the hr floor through max. this is the last of the direct hr writers converted to the publish-and-fold
    // model, so the line below is now the single sole writer of ACM_core_TargetVitals_HeartRate on a live
    // casualty.
    private _rocDrive = _patient getVariable ["ACME_hrDrive_roc", -1];
    if (_rocDrive >= 0) then {
        _hrDrive = if (_hrDrive < 0) then { _rocDrive } else { _hrDrive max _rocDrive };
    };

    // vent CPAP relief, published by fn_ventdrivetick above. it off-loads the heart, which pulls the compensatory
    // tachycardia down toward normal, through min.
    private _ventRelief = _patient getVariable ["ACME_hrDrive_ventRelief", -1];
    if (_ventRelief >= 0) then {
        _hrDrive = if (_hrDrive < 0) then { _ventRelief } else { _hrDrive min _ventRelief };
    };

    [_patient,"ACME_hrTarget_circ",_hrDrive,0.25,2] call ACME_fnc_setVarNetApprox;

    // NA3: native HR integration consumes source-separated targets. Never overwrite its resting baseline here.
    // ICH risk from an epi-equivalent MAP overshoot.
    // the dangerous positive component is epinephrine, where the surge and tachycardia bleed a fragile brain, plus
    // norepinephrine run peripherally, which behaves like dirty epi. clean norepi through an upper iv or an io
    // raises SVR without the surge, so it is not in _epiLikeDrive and does not bleed. the distal-peripheral
    // hypertensive spike counts too, because it is a surge.
    private _epiSupport = _pushDose + _hyperSpike + ((_epiLikeDrive * 1000) * _coeff min _pressorCap);
    private _mapNow = [_patient] call ACME_fnc_tbiGetMAP;  // it already includes the offset, through the wrapper.
    private _overshoot = (_mapNow - _ichThreshold) max 0;
    if (_overshoot > 0 && {_epiSupport > 1}) then {
        private _ich = _state getOrDefault ["ichRisk", 0];
        _ich = (_ich + (_ichRate * (_overshoot / 20) * _dt)) min 1;
        _state set ["ichRisk", _ich];
        // feed a co-existing TBI. an epi overshoot worsens ICP and structural severity.
        private _tbi = _patient getVariable ["ACME_tbi_State", createHashMap];
        if (count _tbi > 0) then {
            // do not write ICP directly from the circulation loop. a direct ICP write bypasses the TBI global accumulation
            // cap, and it was the main source of instant CPP and ICP blow-ups during resuscitation. feed the secondary
            // injury into severity only, and fn_tbihandle then converts that into ICP through the normal capped,
            // time-gated pathway.
            private _ichSeverityAdd = 0.05 * _ichRate * (_overshoot / 20) * _dt;
            private _newTbiSeverity = ((_tbi getOrDefault ["severity", 0]) + _ichSeverityAdd) min 1;
            _tbi set ["severity", _newTbiSeverity];
            // This is a new intracranial structural insult, not merely a transient physiology penalty. Preserve it
            // in the high-water structural grade while still allowing the acute burden itself to recover later.
            _tbi set ["structuralSeverity", (_tbi getOrDefault ["structuralSeverity", _newTbiSeverity]) max _newTbiSeverity];
            _tbi set ["ichSecondarySeverityAdd", _ichSeverityAdd];
            [_patient, _tbi] call ACME_fnc_tbiStateCommit;
        };
    };

    [_patient, _state] call ACME_fnc_circStateCommit;
    if (_shockActive || {_inCardiacArrest} || {_offset != 0} || {_hyperSpike > 0} || {(_state getOrDefault ["ichRisk", 0]) > 0} || {_ionizedCa < 1} || {_temp < 36} || {(_state getOrDefault ["salineAcidosis", 0]) > 0} || {_acidosis > 0.001} || {_paCO2 > ((missionNamespace getVariable ["ACME_circ_paCO2Normal", 40]) + 0.1)} || {_respDeficit > 0.001} || {_effMAPpre < _acidThresh}) then {
        ACME_circ_activePatients pushBackUnique _patient;
    };

    } else {
        {[_patient, _x, 0] call ACME_fnc_setVarNet;} forEach ["ACME_circ_resistDelta", "ACME_pressorResistAdd", "ACME_lidoTox_resistDelta", "ACME_esmololTox_resistDelta", "ACME_infusionTox_resistDelta"];
        [_patient, "ACME_hrTarget_circ", -1] call ACME_fnc_setVarNet;
    };

    // post-failure ventilation debt, paid only while a medic is genuinely ventilating the patient. pressure cuffs
    // bleed down as their bag empties.
    [_patient] call ACME_fnc_pressureInfuserTick;

    // hardcore systems. each does nothing unless its own setting is on.
    [_patient] call ACME_fnc_hcCircTick;
    [_patient] call ACME_fnc_hcVentTick;

    // Actual chest-wound bleeding can contaminate the seal vent.
    [_patient] call ACME_fnc_chestSealOcclusionTick;
    // The single PTX controller balances current leakage against actual venting.
    [_patient] call ACME_fnc_ptxTensionTick;

    // ACM repositioning a casualty whose head we are holding up. get out of the way first, properly.
    [_patient] call ACME_fnc_headElevAnimGuard;

    // a tube past the carina ventilates one lung. it builds a shunt and halves the compliance.
    [_patient] call ACME_fnc_ettMainstemTick;

    // B125 airway wake reconciliation. Collapse is the unconscious soft-tissue/tongue-collapse ladder, not a
    // durable anatomical obstruction. If an old ACM worker or locality edge leaves a nonzero collapse value on a
    // conscious casualty, clear only that collapse field. Vomit, blood, adjuncts and every other airway state stay.
    if (!(_patient getVariable ["ACE_isUnconscious", false])
        && {(_patient getVariable ["ACM_airway_AirwayCollapse_State", 0]) > 0}) then {
        [_patient, [["collapse", 0]], true] call ACM_airway_fnc_setAirwayState;
    };

    // nobody wakes up with a tube in, and vomiting with an OPA in ejects it.
    [_patient] call ACME_fnc_ettWakeGuard;
    [_patient] call ACME_fnc_airwayVomitOPA;

    // a displaced cuff sitting in the glottis keeps the airway producing until a medic puts the tube right.
    [_patient] call ACME_fnc_ettObstructTick;

    // B13 suction debt is integrated once in the native oxygen writer, including at ground level.

    // laryngoventtick is removed. the post-failure ventilation lock came out and nothing has set a ventilation
    // debt since, so this ran every tick on every casualty and read a variable that is never written.


} forEach _patients;
