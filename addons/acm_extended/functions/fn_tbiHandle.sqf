// per-frame TBI physiology loop. it is a decoupled pfh: it reads ACM vitals and nudges its own state and a few
// ACM outputs, and it does not extend ACM's medical state, by design.
// the integrated CPP loop runs like this.
// MAP comes straight from ACM, including the circ bpoffset for pressor, push-dose and shock.
// CPP is map_eff minus ICP.
// a low CPP or hypoxia raises severity, which raises the ICP ceiling and the rise rate.
// osmotherapy lowers ICP, capped by sodium, and fn_tbiapplyosmotherapy handles it.
// ICP drives the cushing tell, then the herniation cascade, then the pupils, GCS-m and vitals.
// all clinical numbers are placeholder tunables, in postinit and CBA, marked todo[ref]. drop in real ACM
// cardiology and pharmacology reference values.
if !(missionNamespace getVariable ["ACME_sys_tbi", true]) exitWith {};
ACME_tbi_activePatients = ACME_tbi_activePatients select {!isNull _x && {local _x} && {alive _x} && {(_x getVariable ["ACME_tbi_HasTBI", false])}};

{
    private _patient = _x;
    if !(local _patient) then {continue};

    private _state = _patient getVariable ["ACME_tbi_State", createHashMap];
    if (count _state == 0) then {continue};

    private _now = CBA_missionTime;
    private _dt = ((_now - (_state getOrDefault ["lastTick", _now])) max 0) min (missionNamespace getVariable ["ACME_tbi_maxDeltaSeconds", 5]);
    _state set ["lastTick", _now];
    if (_dt <= 0) then {continue};

    // Separate structural ICP from the previous transient airway contribution.
    private _icp = ((_state getOrDefault ["icp", 10]) - (_state getOrDefault ["laryngoICPApplied", 0])) max 0;
    private _icpStart = _icp;  // a hard rate-cap anchor for this tick. it stops stacked levers spiking ICP in seconds.
    private _severity = (_state getOrDefault ["severity", 0.5]) max 0 min 1;  // a clamp, so a bad state can never go negative.
    private _severityStart = _severity;  // a rise-cap anchor. however many insults stack this tick, severity climbs no faster than the fixed cap.

    // B119 separates permanent injury history from the current acute burden. Existing save states migrate on first
    // tick by taking their current severity as the structural high-water mark. Structural severity does not itself
    // keep a stable patient deteriorating; it defines vulnerability and the best autoregulatory/autonomic reserve
    // the brain can recover to. The ordinary severity value remains the reversible burden used by ICP progression.
    private _structural = (_state getOrDefault ["structuralSeverity", _severity]) max 0 min 1;
    _structural = _structural max (_state getOrDefault ["severityFloor", 0]);
    _state set ["structuralSeverity", _structural];

    private _mildMax = missionNamespace getVariable ["ACME_tbi_structuralMildMax", 0.35];
    private _modMax  = missionNamespace getVariable ["ACME_tbi_structuralModerateMax", 0.60];
    private _sevMax  = missionNamespace getVariable ["ACME_tbi_structuralSevereMax", 0.80];

    private _autoregBase = switch (true) do {
        case (_structural <= _mildMax): { missionNamespace getVariable ["ACME_tbi_autoregMild", 1.00] };
        case (_structural <= _modMax): {
            linearConversion [_mildMax, _modMax, _structural, missionNamespace getVariable ["ACME_tbi_autoregMild", 1.00], missionNamespace getVariable ["ACME_tbi_autoregModerate", 0.95], true]
        };
        case (_structural <= _sevMax): {
            linearConversion [_modMax, _sevMax, _structural, missionNamespace getVariable ["ACME_tbi_autoregModerate", 0.95], missionNamespace getVariable ["ACME_tbi_autoregSevere", 0.70], true]
        };
        default {
            linearConversion [_sevMax, 1, _structural, missionNamespace getVariable ["ACME_tbi_autoregSevere", 0.70], missionNamespace getVariable ["ACME_tbi_autoregCritical", 0.35], true]
        };
    };
    private _prevStage = (_state getOrDefault ["herniationStage", 0]) max 0 min 3;
    private _prevComp = (_state getOrDefault ["compFrac", 0]) max 0;
    private _autoregPenaltyAcute = linearConversion [0.45, 1, _severity, 0, 0.28, true];
    private _autoregPenaltyStage = [0, 0.06, 0.22, 0.48] param [_prevStage, 0.48];
    private _autoregPenaltyComp = linearConversion [0.75, 1.75, _prevComp, 0, 0.22, true];
    private _autoregTarget = (_autoregBase - _autoregPenaltyAcute - _autoregPenaltyStage - _autoregPenaltyComp) max 0.05 min 1;
    private _autoregRaw = _state getOrDefault ["autoregIntegrity", -1];
    private _autoreg = if (_autoregRaw < 0) then {_autoregBase} else {_autoregRaw max 0.05 min 1};
    private _autoRate = if (_autoregTarget < _autoreg) then {
        missionNamespace getVariable ["ACME_tbi_autoregFallPerSec", 0.018]
    } else {
        missionNamespace getVariable ["ACME_tbi_autoregRecoverPerSec", 0.0035]
    };
    private _autoStep = _autoRate * _dt;
    _autoreg = _autoreg + (((_autoregTarget - _autoreg) max (-_autoStep)) min _autoStep);
    _autoreg = _autoreg max 0.05 min 1;
    _state set ["autoregIntegrity", _autoreg];
    _state set ["autoregTarget", _autoregTarget];

    private _autonomicBase = switch (true) do {
        case (_structural <= _mildMax): { missionNamespace getVariable ["ACME_tbi_autonomicMild", 1.00] };
        case (_structural <= _modMax): {
            linearConversion [_mildMax, _modMax, _structural, missionNamespace getVariable ["ACME_tbi_autonomicMild", 1.00], missionNamespace getVariable ["ACME_tbi_autonomicModerate", 0.97], true]
        };
        case (_structural <= _sevMax): {
            linearConversion [_modMax, _sevMax, _structural, missionNamespace getVariable ["ACME_tbi_autonomicModerate", 0.97], missionNamespace getVariable ["ACME_tbi_autonomicSevere", 0.80], true]
        };
        default {
            linearConversion [_sevMax, 1, _structural, missionNamespace getVariable ["ACME_tbi_autonomicSevere", 0.80], missionNamespace getVariable ["ACME_tbi_autonomicCritical", 0.55], true]
        };
    };
    private _autonomicPenaltyAcute = linearConversion [0.60, 1, _severity, 0, 0.32, true];
    private _autonomicPenaltyStage = [0, 0.04, 0.24, 0.55] param [_prevStage, 0.55];
    private _autonomicPenaltyComp = linearConversion [0.85, 1.85, _prevComp, 0, 0.25, true];
    private _autonomicTarget = (_autonomicBase - _autonomicPenaltyAcute - _autonomicPenaltyStage - _autonomicPenaltyComp) max 0.05 min 1;
    private _autonomicRaw = _state getOrDefault ["autonomicIntegrity", -1];
    private _autonomicIntegrity = if (_autonomicRaw < 0) then {_autonomicBase} else {_autonomicRaw max 0.05 min 1};
    private _autonomicRate = if (_autonomicTarget < _autonomicIntegrity) then {
        missionNamespace getVariable ["ACME_tbi_autonomicFallPerSec", 0.022]
    } else {
        missionNamespace getVariable ["ACME_tbi_autonomicRecoverPerSec", 0.004]
    };
    private _autonomicStep = _autonomicRate * _dt;
    _autonomicIntegrity = _autonomicIntegrity + (((_autonomicTarget - _autonomicIntegrity) max (-_autonomicStep)) min _autonomicStep);
    _autonomicIntegrity = _autonomicIntegrity max 0.05 min 1;
    _state set ["autonomicIntegrity", _autonomicIntegrity];
    _state set ["autonomicTarget", _autonomicTarget];

    // head-of-bed elevation, at about 30 degrees. while elevated, ICP eases down through venous drainage, see
    // below, CPP eases down through a small MAP haircut, because gravity lowers cerebral arterial pressure, and
    // herniation is impossible, which is gated in the cascade below. everything else runs unchanged.
    private _elevated = [_patient] call ACME_fnc_headElevEffective;
    _state set ["headElevated", _elevated];  // a tell for the HUD and the aar.

    // pressor, push-dose and shock support live in fn_circhandle now and are applied through the getbloodpressure
    // offset, so tbiGetMAP already reflects them here. adding pressor MAP again would double-count.
    private _mapNative = [_patient] call ACME_fnc_tbiGetMAP;
    private _map = _mapNative;
    if (_elevated) then { _map = (_map - (missionNamespace getVariable ["ACME_headElev_mapDrop", 6])) max 0; };
    private _cpp = _map - _icp;

    // cerebral autoregulation: the vasodilatory and vasoconstriction cascade.
    // a CPP below the autoregulation band gives reflex cerebral vasodilation, which raises the cerebral blood
    // volume, which raises ICP. that is rosner's vasodilatory cascade. because CPP is MAP minus ICP, that ICP rise
    // drops CPP further, which dilates harder, so it is a self-feeding spiral. restoring CPP, with a norepi drip
    // lifting MAP into the 80 to 90 target so CPP climbs into 60 to 70, reverses it: vasoconstriction, cbv down and
    // ICP falls.
    // this is what makes a clean norepi drip the single most effective ICP treatment here. osmotherapy only trims
    // structural ICP and is sodium-capped, so it can blunt but never break a CPP-driven cascade, and only pressure
    // support does. the vasodilatory add rides on top of the severity-driven structural ceiling and is capped, at
    // ACME_tbi_vasoICPmax, so the spiral is dangerous and bounded.
    private _autoUpper = missionNamespace getVariable ["ACME_tbi_autoregUpperCPP", 70];
    private _autoLower = missionNamespace getVariable ["ACME_tbi_autoregLowerCPP", 40];
    private _intactVasoFrac = linearConversion [_autoUpper, _autoLower, _cpp, 0, 1, true];
    // Lost autoregulation blunts protective low-CPP dilation and becomes pressure-passive at high CPP.
    private _vasoFrac = _intactVasoFrac * _autoreg;
    private _pressurePassiveFrac = (linearConversion [
        missionNamespace getVariable ["ACME_tbi_pressurePassiveCPPstart", 70],
        missionNamespace getVariable ["ACME_tbi_pressurePassiveCPPfull", 100],
        _cpp, 0, 1, true
    ]) * (1 - _autoreg);
    private _vasoCeil = (_vasoFrac * (missionNamespace getVariable ["ACME_tbi_vasoICPmax", 20]))
        + (_pressurePassiveFrac * (missionNamespace getVariable ["ACME_tbi_pressurePassiveICPmax", 8]));
    _state set ["vasoFrac", _vasoFrac];
    _state set ["pressurePassiveFrac", _pressurePassiveFrac];

    // fluid overload gives cerebral edema, which raises ICP. over-resuscitation, where
    // ACM_circulation_Overload_Volume is above 0, drives ICP up hard, because the injured brain has no compliance
    // left, so even a small overload bites. while the patient is still hypovolemic there is no overload volume, so
    // giving blood or fluid costs nothing here. the penalty only starts the moment they tip over the limit. it
    // rewards blood-first and punishes over-filling.
    private _overload = _patient getVariable ["ACM_circulation_Overload_Volume", 0];
    private _overloadCeil = ((missionNamespace getVariable ["ACME_tbi_overloadICPperVol", 5]) * _overload) min (missionNamespace getVariable ["ACME_tbi_overloadICPmax", 10]);
    _state set ["overloadICP", _overloadCeil];  // a tell for the HUD and the aar.

    // CO2 cerebral vasoreactivity, the chemical limb, which is distinct from the CPP and pressure limb above.
    // PaCO2 is the fastest ICP lever in neurotrauma. CO2 retention, from hypoventilation such as a lost airway, an
    // untreated tension pneumothorax or hemothorax, or too-slow bagging, dilates cerebral vessels, which raises the
    // cerebral blood volume and raises ICP. hyperventilation, from fast bagging, blows off CO2, which gives
    // vasoconstriction and lowers ICP. that is a real temporising tool against herniation.
    // we read alveolar ventilation the same way ACM's capnograph derives EtCO2, as rr times the airway and
    // breathing throttle, normalized against the metabolic target, because raw EtCO2 is non-monotonic and
    // consciousness-skewed. it would misread the unconscious apneic patient, who is the most hypercapnic. a vent
    // ratio below 1 retains CO2, which raises the ICP ceiling, and above 1 blows it off, which lowers the
    // ceiling.
    private _co2Ceil = 0; private _co2Rise = 0;
    private _ttRR = _patient getVariable ["ACM_core_TargetVitals_RespirationRate", 16];
    if (_ttRR > 0) then {
        private _aw = ((([_patient] call ACM_airway_fnc_getAirwayState) / 0.95) min 1) max 0;
        private _br = ((([_patient] call ACM_breathing_fnc_getBreathingState) / 0.85) min 1) max 0;

        // the effective rate is the spontaneous or the bagged one, whichever is doing the work.
        // this is the fix for the provider who must bag. a patient in cardiac arrest, or breathing under 8, has a
        // spontaneous rate near zero, so on spontaneous rate alone the CO2 ratio pins ICP at the hypoventilation
        // ceiling and nothing the medic does moves it. but bagging is ventilation, and CO2 does not care whether a
        // breath came from the diaphragm or a bag. so a fresh, active BVM rate stands in for the spontaneous one when
        // it is higher: bag an apneic head injury at a decent rate and the ratio climbs and ICP comes down, exactly as
        // it should. the provider doing the indicated thing is rewarded rather than charged with the arrest.
        // it takes whichever is higher rather than the sum, so you cannot double-count a patient who is both breathing
        // and being bagged, and it is freshness-gated, so a bag set down two minutes ago stops counting.
        // the spontaneous rate is smoothed. the ICP CO2 lever must react to the ventilation trend rather than to
        // per-tick jitter in the instantaneous rate. an irregular cheyne-stokes pattern, or a re-rolling seizure rate,
        // would otherwise swing _ventRatio into _co2Ceil into ICP and move every cushing vital several times a second,
        // which is the flicker. exponential smoothing with a short time constant keeps the physiology responsive and
        // visually stable.
        private _spontRaw = _patient getVariable ["ACM_breathing_RespirationRate", 18];
        if (!(_spontRaw isEqualType 0) || {_spontRaw != _spontRaw}) then { _spontRaw = 18 };
        private _spontPrev = _state getOrDefault ["co2RRsmooth", _spontRaw];
        private _tau = missionNamespace getVariable ["ACME_tbi_co2RRSmoothTau", 4];  // seconds.
        private _alpha = (_dt / (_tau max 0.1)) min 1;
        private _spontR = _spontPrev + ((_spontRaw - _spontPrev) * _alpha);
        _state set ["co2RRsmooth", _spontR];
        private _bagFresh = ((serverTime - (_patient getVariable ["ACME_bvm_lastBreathServer", -1e9])) max 0)
            < (missionNamespace getVariable ["ACME_tbi_bvmFreshSec", 12]);
        private _bagR = if (_bagFresh) then { _patient getVariable ["ACME_bvm_rate", 0] } else { 0 };
        private _effRate = _spontR max _bagR;

        // when a medic is actively bagging, the ventilation floor lifts. there are two adjustments, both aimed at making
        // sure a provider who must bag, in an arrest or at an rr under 8, is not hammered for it.
        // 1. the airway and breathing throttle gets a floor. a blocked airway should still blunt bagging, because that
        // is real, and a provider bagging a reasonably managed airway should always make progress on ICP rather than
        // being zeroed out by a throttle they have already partly addressed. the floor defaults to 0.6.
        // 2. the metabolic divisor is met by a realistic bag rate. adequate manual ventilation is about 10/min, not the
        // about 16 of full spontaneous metabolic demand, and dividing bagging by 16 declared good bagging inadequate.
        // while bagging, the target eases to the bag target, so a steady 10/min reads as adequate, at a ratio near 1,
        // and the CO2 ceiling clears.
        private _thr = _aw min _br;
        private _div = _ttRR;
        if (_bagFresh && {_bagR > 0}) then {
            _thr = _thr max (missionNamespace getVariable ["ACME_tbi_bvmThrottleFloor", 0.6]);
            _div = _div min (missionNamespace getVariable ["ACME_tbi_bvmTargetRR", 10]);
        };

        private _ventRatio = (_effRate * _thr) / _div;
        _state set ["ventRatio", _ventRatio];  // published for the recovery gate below.
        if (_ventRatio < 1) then {
            _co2Ceil = linearConversion [1, 0, _ventRatio, 0, (missionNamespace getVariable ["ACME_tbi_co2VasoICPmax", 18]), true];
            _co2Rise = (missionNamespace getVariable ["ACME_tbi_co2RisePerSec", 0.12]) * (linearConversion [1, 0, _ventRatio, 0, 1, true]);
        } else {
            _co2Ceil = -(linearConversion [1, 2, _ventRatio, 0, (missionNamespace getVariable ["ACME_tbi_co2HyperventICPdrop", 12]), true]);
            // overcooked hyperventilation buys ICP at the cost of cerebral ischemia, which is a secondary injury.
            if (_ventRatio > (missionNamespace getVariable ["ACME_tbi_co2IschemiaRatio", 1.8])) then {
                _severity = (_severity + ((missionNamespace getVariable ["ACME_tbi_co2IschemiaPerSec", 0.008]) * _dt)) min 1;
                _state set ["severity", _severity];
            };
        };
    };
    _state set ["co2Ceil", _co2Ceil];  // a tell for the HUD and the aar.

    // the mechanical limb: intrathoracic pressure into ICP.
    // the CO2 limb above is the chemical route to raised ICP. this is the mechanical one, and it is a genuinely
    // separate mechanism. positive-pressure ventilation raises intrathoracic pressure, and intrathoracic pressure
    // obstructs cerebral venous outflow through the jugulars. blood that cannot leave the head is blood that raises
    // ICP, immediately and whatever the CO2 is doing.
    // it has two drivers, and the second is the one people forget.
    // PEEP is baseline airway pressure that never lets the chest fully empty. it is modest with normal lungs and
    // ugly when high, and it is the clean, always-present component.
    // dyssynchrony is a spontaneously breathing patient driven by the ventilator fighting it, through coughing,
    // breath stacking and valsalva against the circuit, and each of those is an intrathoracic-pressure spike far
    // larger than PEEP. the fix a medic is supposed to reach for is sedation, because a sedated patient does not
    // fight. so the penalty is gated on the patient having spontaneous effort the vent is overriding, and it
    // vanishes once they are unconscious or sedated enough to stop fighting. that is the teaching point: you do not
    // just ventilate the head-injured patient, you ventilate them smoothly.
    // a controlled mode on a patient with no spontaneous drive carries the PEEP component only, which is small, and
    // that is correct. controlled ventilation of a sedated TBI patient is protective rather than harmful, and the
    // harm is specifically the fight.
    private _mechCeil = 0;
    if (_patient getVariable ["ACME_vent_driving", false]) then {
        private _effective = [_patient] call ACME_fnc_ventEffectiveSettings;
        private _peep = _effective select 5;
        private _mode = _effective select 1;

        // the PEEP component: intrathoracic pressure that is always there while driving. IMV vc (CPR) forces PEEP to 0,
        // so it contributes nothing here either, which is consistent with the drive tick.
        private _peepEff = if (_mode == "IMV VC (CPR)") then {0} else {_peep};
        private _peepCeil = (_peepEff / 20) * (missionNamespace getVariable ["ACME_tbi_peepICPmax", 6]);

        // Use the ventilator's actual unresolved dyssynchrony state. Normal patient-triggered SIMV/PS breaths are
        // synchronized breathing and must not be reclassified here as "fighting" merely because neural RR is present.
        // The vent drive already excludes arrest/paralysis and eases coughing/missed-trigger/insufficient-support stress
        // over time, so the TBI mechanical ICP limb follows that same bounded state rather than inventing a second one.
        private _dys = (_patient getVariable ["ACME_vent_dyssync", 0]) max 0 min 1;
        private _dysCeil = _dys * (missionNamespace getVariable ["ACME_tbi_dyssynchronyICPmax", 14]);

        _mechCeil = _peepCeil + _dysCeil;
    };
    _state set ["mechCeil", _mechCeil];  // a tell for the HUD and the aar, a peer to co2ceil.

    private _structCeil = (missionNamespace getVariable ["ACME_tbi_baseICP", 10]) max ((missionNamespace getVariable ["ACME_tbi_icpMax", 40]) * _severity);  // acute burden can resolve, but ICP normalizes to baseline rather than zero.
    private _combinedCeil = (_structCeil + _vasoCeil + _overloadCeil + _co2Ceil + _mechCeil) max 0;
    private _baseRise = (missionNamespace getVariable ["ACME_tbi_icpRisePerSec", 0.05]) * _severity;  // todo[ref].
    private _vasoRise = _vasoFrac * (missionNamespace getVariable ["ACME_tbi_vasoRisePerSec", 0.035]);  // the active dilation push.
    private _overRise = if (_overloadCeil > 0) then { missionNamespace getVariable ["ACME_tbi_overloadRisePerSec", 0.035] } else { 0 };  // overload accrues slowly.
    if (_icp < _combinedCeil) then {
        // climbing toward the ceiling: structural creep, active vasodilation, fluid overload and CO2 retention.
        // mechanical ICP rises quickly, because venous outflow obstruction is a plumbing problem rather than a chemical
        // one, so it acts about as fast as the airway pressure that causes it.
        private _mechRise = if (_mechCeil > 0) then { missionNamespace getVariable ["ACME_tbi_mechRisePerSec", 0.10] } else {0};
        _icp = (_icp + ((_baseRise + _vasoRise + _overRise + _co2Rise + _mechRise) * _dt)) min _combinedCeil;
    } else {
        // with the CPP restored or the ceiling dropped, hyperventilation included, vasoconstriction relaxes ICP down
        // toward it.
        _icp = (_icp - ((missionNamespace getVariable ["ACME_tbi_vasoRelaxPerSec", 0.04]) * _dt)) max _combinedCeil;
    };
    // head elevation. ease the structural ICP down on top of the cascade, through venous drainage. the rate is
    // tunable.
    if (_elevated) then {
        _icp = (_icp - ((missionNamespace getVariable ["ACME_headElev_icpDropPerSec", 0.15]) * _dt)) max 0;
    };

    // a hard global ICP rate cap. the ceiling math can still decide where ICP wants to go, and the value cannot move
    // faster than a physiologic accumulation curve. this is the main protection against instant CPP and ICP spikes,
    // fluid-overload death spirals, and the rapid rise and fall sawtooth seen in debug.
    private _riseCap = missionNamespace getVariable ["ACME_tbi_globalRiseCapPerSec", 0.025];
    private _fallCap = missionNamespace getVariable ["ACME_tbi_globalFallCapPerSec", 0.04];
    if (_riseCap > 0) then { _icp = _icp min (_icpStart + (_riseCap * _dt)); };
    if (_fallCap > 0) then { _icp = _icp max (_icpStart - (_fallCap * _dt)); };
    _icp = _icp max 0;  // ICP can never be negative.
    _state set ["icpRiseCap", _riseCap];
    _state set ["icpFallCap", _fallCap];

    private _laryngoICP = ([_patient] call ACME_fnc_laryngoStimulusEffect)
        * (missionNamespace getVariable ["ACME_laryngo_icpSurge", 4])
        * (0.45 + 0.55 * _severity);
    _laryngoICP = _laryngoICP max 0;
    _icp = _icp + _laryngoICP;
    _state set ["laryngoICPApplied", _laryngoICP];

    // recompute CPP against the updated ICP, so the downstream insults read the post-cascade value.
    _cpp = _map - _icp;

    // THE PERFUSION PREDICATE. ONE STATEMENT, READ BY EVERY GATE BELOW.
    // the brain is being perfused well enough to stop losing ground when MAP satisfies the structural-grade floor
    // and ICP is off the pressure, at or below ACME_tbi_recoverICPmax. Mild/moderate injuries retain the normal
    // recovery band; severe/critical structural injury progressively requires more MAP. MAP is the gate rather
    // than CPP because MAP is what the medic can see, target and treat. a CPP gate at 70
    // against a live ICP demanded a MAP of 70 plus the ICP, so a casualty carrying an ICP of 15 needed a MAP of 85
    // before anything healed, and the medic had no way to read that requirement off the panel.
    // THIS IS ALSO THE DEAD BAND. before r-59 the damage threshold and the recovery threshold were the same
    // number, CPP 70, so a casualty was always either being damaged or healing and never neutral. one predicate
    // drives the insult, the compensation budget and the recovery, so the three can no longer disagree and a
    // casualty held in the band simply holds.
    private _recovICPgate = missionNamespace getVariable ["ACME_tbi_recoverICPmax", 25];
    private _baseRecovMAPmin = missionNamespace getVariable ["ACME_tbi_recoverMAPmin", 65];
    private _structMAPfloor = switch (true) do {
        case (_structural <= _mildMax): { missionNamespace getVariable ["ACME_tbi_hypotensionMAPMild", 60] };
        case (_structural <= _modMax): {
            linearConversion [_mildMax, _modMax, _structural, missionNamespace getVariable ["ACME_tbi_hypotensionMAPMild", 60], missionNamespace getVariable ["ACME_tbi_hypotensionMAPModerate", 65], true]
        };
        case (_structural <= _sevMax): {
            linearConversion [_modMax, _sevMax, _structural, missionNamespace getVariable ["ACME_tbi_hypotensionMAPModerate", 65], missionNamespace getVariable ["ACME_tbi_hypotensionMAPSevere", 75], true]
        };
        default {
            linearConversion [_sevMax, 1, _structural, missionNamespace getVariable ["ACME_tbi_hypotensionMAPSevere", 75], missionNamespace getVariable ["ACME_tbi_hypotensionMAPCritical", 85], true]
        };
    };
    private _recovMAPmin = _baseRecovMAPmin max _structMAPfloor;
    // Mild and moderate TBI are not forced into a high CPP target simply because the injury exists. Severe and
    // critical structural injury, where autoregulatory reserve is intentionally reduced, add a minimum CPP gate.
    private _structCPPfloor = 0;
    if (_structural > _modMax) then {
        _structCPPfloor = if (_structural <= _sevMax) then {
            missionNamespace getVariable ["ACME_tbi_perfusionCPPSevereMin", 55]
        } else {
            missionNamespace getVariable ["ACME_tbi_perfusionCPPCriticalMin", 60]
        };
    };
    private _perfusionOK = (_map >= _recovMAPmin) && {_icp <= _recovICPgate} && {(_structCPPfloor <= 0) || {_cpp >= _structCPPfloor}};
    _state set ["perfusionOK", _perfusionOK];
    _state set ["recoverMAPmin", _recovMAPmin];
    _state set ["recoverCPPfloor", _structCPPfloor];

    // a secondary insult: a sustained low CPP worsens severity.
    private _cppTarget = missionNamespace getVariable ["ACME_tbi_cppTarget", 70];  // todo[ref].
    _state set ["map", _map];
    _state set ["cpp", _cpp];
    _state set ["cppTarget", _cppTarget];
    private _lowTime = _state getOrDefault ["lowCPPTime", 0];
    // the timer still tracks the CPP target, because that is the ideal the panel reports and the aar reads.
    // the DAMAGE is gated on the perfusion predicate instead. a casualty at a MAP of 65 with a controlled ICP is
    // held, not harmed, even though a CPP of 70 is not reached. that is the dead band, and it is the whole point:
    // the medic now has somewhere to stand.
    if (_cpp < _cppTarget) then {
        _lowTime = _lowTime + _dt;
        if (!_perfusionOK) then {
            private _autoLowCPPMult = 1 + ((1 - _autoreg) * ((missionNamespace getVariable ["ACME_tbi_autoregLowCPPMultMax", 2.0]) - 1));
            _severity = (_severity + ((missionNamespace getVariable ["ACME_tbi_severityPerSecLowCPP", 0.01]) * _autoLowCPPMult * _dt)) min 1;
        };
    } else {
        _lowTime = (_lowTime - (_dt * 0.5)) max 0;
    };
    _state set ["lowCPPTime", _lowTime];

    // the hypoxia insult, driven by delivery rather than by saturation.
    // an injured brain does not care what fraction of the remaining hemoglobin is saturated. it cares how much
    // oxygen actually arrives. a casualty who is exsanguinating with a clear airway saturates in the high nineties
    // the whole way down, so keying this on SpO2 meant a bleeding head injury took no hypoxic insult at all, right
    // up until they arrested. delivery catches it, and saturation still contributes, because it is one of the terms
    // inside DO2.
    private _spo2 = _patient getVariable ["ace_medical_SpO2", 97];
    private _do2 = [_patient] call ACME_fnc_oxygenDelivery;
    private _do2Thresh = missionNamespace getVariable ["ACME_tbi_do2Threshold", 0.7];

    // hysteresis, so a casualty sitting on the threshold does not flicker in and out of being insulted, plus a
    // reperfusion window, so a brain whose delivery has just been restored is recovering rather than still being
    // damaged while the blood circulates. it is the same shape as the acidosis guards in fn_circhandle, for the
    // same reason: DO2 is invisible, so it must be forgiving at the boundaries.
    private _do2Clear = missionNamespace getVariable ["ACME_tbi_do2ClearFrac", 0.78];
    private _tbiDef = _state getOrDefault ["do2Deficit", false];
    if (_tbiDef) then {
        if (_do2 >= _do2Clear) then { _tbiDef = false; _state set ["do2RecoveredAt", CBA_missionTime]; };
    } else {
        if (_do2 < _do2Thresh) then { _tbiDef = true; };
    };
    _state set ["do2Deficit", _tbiDef];
    private _tbiReperf = (CBA_missionTime - (_state getOrDefault ["do2RecoveredAt", -1e9]))
        < (missionNamespace getVariable ["ACME_tbi_do2ReperfusionWindow", 45]);

    if (_tbiDef && {!_tbiReperf}) then {
        // scaled by how far below the threshold it is, so a marginal deficit is not treated like a catastrophic one.
        private _sev = linearConversion [_do2Thresh, (missionNamespace getVariable ["ACME_tbi_do2Critical", 0.35]), _do2, 0.35, 1, true];
        _severity = (_severity + ((missionNamespace getVariable ["ACME_tbi_severityPerSecHypoxia", 0.01]) * _sev * _dt)) min 1;
    };
    _state set ["do2", _do2];

    // Pressure secondary injury now uses the same structural-grade floor as recovery, so stable mild/moderate TBI
    // cannot be injured and healed by two contradictory gates in the same tick.
    private _hypoFloor = _structMAPfloor;
    private _insultT = _state getOrDefault ["hypotensionTime", 0];
    if (_map < _hypoFloor) then {
        _insultT = _insultT + _dt;
        private _deepFloor = ((missionNamespace getVariable ["ACME_tbi_hypotensionSevereMAP", 60]) - 10) min (_hypoFloor - 10);
        private _depth = linearConversion [_hypoFloor, _deepFloor, _map, 0.25, 1, true];
        private _autoHypoMult = 1 + ((1 - _autoreg) * 0.75);
        _severity = (_severity + ((missionNamespace getVariable ["ACME_tbi_severityPerSecHypotension", 0.012]) * _depth * _autoHypoMult * _dt)) min 1;
        if (_map < (missionNamespace getVariable ["ACME_tbi_hypotensionSevereMAP", 60])) then {
            _severity = (_severity + ((missionNamespace getVariable ["ACME_tbi_severityPerSecHypotension", 0.012]) * 0.5 * _autoHypoMult * _dt)) min 1;
        };
    } else {
        _insultT = (_insultT - (_dt * 0.25)) max 0;
    };
    _state set ["hypotensionTime", _insultT];
    _state set ["hypotensionFloor", _hypoFloor];

    // the compensation budget: a raised-ICP brain defends perfusion only for so long.
    // while the insult is engaged, with ICP at or above the cushing threshold or CPP under target, a compensation
    // clock runs. within budget the patient holds, because cushing defends MAP and the vitals stay compensated.
    // once the budget is spent they decompensate: severity climbs faster, which pushes the ICP cascade up and CPP
    // down, and the vitals slide from the cushing pattern toward collapse, because fn_tbiapplyvitals reads
    // compfrac.
    // this is what stops a defended but untreated TBI sitting compensated forever. it now tips over on a timer and
    // correlates the vitals to the failing perfusion. relieve the insult, by restoring CPP or dropping ICP, and the
    // reserve recovers slowly. the budget is tunable, at ACME_tbi_compBudgetSeconds.
    private _budget = (missionNamespace getVariable ["ACME_tbi_compBudgetSeconds", 600]) max 1;
    private _compTime = _state getOrDefault ["compTime", 0];
    // the same predicate again, so the budget cannot burn on a casualty the recovery gate calls well perfused.
    // it was ICP at or above cushing OR CPP under target, and the CPP half fired on a casualty at a MAP of 65 who
    // was otherwise fine, so the budget ran out and the decompensation term at 0.012 per second, four times the
    // base insult rate, took over.
    private _compEligible = (_structural >= _modMax) || {_severity >= 0.65} || {_icp >= (missionNamespace getVariable ["ACME_tbi_cushingICP", 25])};
    private _compEngaged = (!_perfusionOK) && {_compEligible};
    if (_compEngaged) then {
        _compTime = _compTime + _dt;
    } else {
        _compTime = (_compTime - (_dt * (missionNamespace getVariable ["ACME_tbi_compRecoverMult", 0.4]))) max 0;
    };
    _state set ["compTime", _compTime];
    private _compFrac = _compTime / _budget;  // 0 is fresh, 1 is exhausted, and above 1 is failing.
    _state set ["compFrac", _compFrac];
    if (_compFrac > 1) then {
        // past the budget: progressive decompensation. severity, and therefore the ICP ceiling and rise next tick,
        // accelerates with the overshoot, so a defended brain that is never treated tips over and herniates.
        private _over = (_compFrac - 1) min 1;
        _severity = (_severity + ((missionNamespace getVariable ["ACME_tbi_decompSeverityPerSec", 0.012]) * _over * _dt)) min 1;
    };

    // severity recovery: a treated brain heals.
    // when every physiology gate is met, meaning ICP is controlled, the structural-grade MAP floor is met, oxygen
    // delivery is adequate, and ventilation is good enough that CO2 is not retained, the acute burden is relieved and
    // severity heals toward its damage floor. This is what lets a stable mild/moderate TBI settle rather than
    // deteriorate simply because its structural injury history still exists. ICP normalizes toward base ICP as
    // acute burden falls, while structural severity continues to define reserve and future vulnerability.
    // achieving good physiology is sufficient on its own, and a recent HTS or mannitol bolus multiplies the heal
    // rate, because it actively pulls water out of the brain rather than merely moving the reading. it is gated so
    // a still-pressured, hypoxic or hypoventilated brain does not heal, and only recovers when the provider is
    // genuinely doing the right things. the floor is set later from the herniation high-water mark: 0 if never
    // impending, a light permanent floor after impending, and the irreversible floor after actual herniation.
    private _recovICPmax  = missionNamespace getVariable ["ACME_tbi_recoverICPmax", 25];
    private _recovCPPmin  = missionNamespace getVariable ["ACME_tbi_recoverCPPmin", 70];
    private _recovSpO2min = missionNamespace getVariable ["ACME_tbi_recoverSpO2min", 90];
    private _recovVentMin = missionNamespace getVariable ["ACME_tbi_recoverVentMinRatio", 0.9];
    // _ventRatio was computed in the CO2 limb above and stored in state. it defaults to 1, meaning adequate and not
    // retaining CO2, when no airway or breathing model ran this tick.
    private _ventRatioNow = _state getOrDefault ["ventRatio", 1];
    private _ventOK = _ventRatioNow >= _recovVentMin;
    private _spo2now = _patient getVariable ["ace_medical_SpO2", 97];
    // the perfusion half is the shared predicate, so recovery, damage and the budget all agree by construction.
    // _recovCPPmin is kept and published for the panel and the aar as the CPP the medic is aiming for. it no
    // longer gates the heal, because MAP is the number a medic can actually treat.
    _state set ["recoverCPPmin", _recovCPPmin];
    private _insultRelieved = _perfusionOK && {!_tbiDef} && {_spo2now >= _recovSpO2min} && {_ventOK};
    _state set ["insultRelieved", _insultRelieved];
    if (_insultRelieved) then {
        private _healRate = missionNamespace getVariable ["ACME_tbi_recoverPerSec", 0.0025];
        // the osmotherapy bonus. within the window after an HTS or mannitol bolus, heal faster.
        private _lastOsmo = _state getOrDefault ["lastOsmoTime", -1e9];
        if ((CBA_missionTime - _lastOsmo) <= (missionNamespace getVariable ["ACME_tbi_osmoRecoverWindow", 120])) then {
            _healRate = _healRate * (missionNamespace getVariable ["ACME_tbi_osmoRecoverBonus", 2.0]);
        };
        // heal toward the damage floor, computed from maxstage after the herniation block. use the last known floor
        // here, defaulting to 0 so a never-herniated brain can fully recover this tick.
        private _floor = _state getOrDefault ["severityFloor", 0];
        _severity = (_severity - (_healRate * _dt)) max _floor;
    };

    // B119 systemic autonomic/vasomotor response. Rising ICP first produces a coherent sympathetic clamp. Once
    // reserve is exhausted or herniation progresses, output becomes increasingly labile and then fails toward
    // vasodilation/hypotension. Stable mild/moderate TBI sits near zero tone.
    private _cushingTrigger = missionNamespace getVariable ["ACME_tbi_cushingICP", 25];
    private _hernToneICP = missionNamespace getVariable ["ACME_tbi_herniationICP", 30];
    private _pressureDrive = linearConversion [_cushingTrigger, _hernToneICP + 8, _icp, 0, 1, true];
    private _stageForTone = (_state getOrDefault ["herniationStage", 0]) max 0 min 3;
    private _stageDecomp = (missionNamespace getVariable ["ACME_tbi_herniationStageDecomp", [0,0.15,0.30,1.0]]) param [_stageForTone, 0];
    private _reserveDecomp = linearConversion [0.85, 1.75, _compFrac, 0, 1, true];
    private _decompDrive = _reserveDecomp max _stageDecomp;
    private _sympatheticDrive = _pressureDrive * (1 - _decompDrive) * (0.55 + (0.45 * _autonomicIntegrity));
    private _failureDrive = (linearConversion [0.35, 1, _decompDrive, 0, 1, true]) * (0.55 + (0.45 * (1 - _autonomicIntegrity)));
    private _autoPhase = _state getOrDefault ["autonomicPhase", -1];
    if (_autoPhase < 0) then { _autoPhase = random 360; _state set ["autonomicPhase", _autoPhase]; };
    private _autoT = CBA_missionTime;
    private _chaos = ((sin ((_autoT * 41) + _autoPhase)) + (0.65 * sin ((_autoT * 73) + 37 + _autoPhase)) + (0.45 * sin ((_autoT * 19) + 113))) / 2.1;
    private _chaosGate = linearConversion [missionNamespace getVariable ["ACME_tbi_autonomicChaosStart", 0.35], 1, _decompDrive, 0, 1, true];
    _chaosGate = _chaosGate * (0.35 + (0.65 * (1 - _autonomicIntegrity)));
    private _toneTarget = _sympatheticDrive - _failureDrive + (_chaos * _chaosGate * (missionNamespace getVariable ["ACME_tbi_autonomicChaosAmp", 0.55]));
    if (_stageForTone >= 3) then { _toneTarget = _toneTarget min -0.55; };
    _toneTarget = _toneTarget max -1 min 1;
    private _autonomicTone = (_state getOrDefault ["autonomicTone", 0]) max -1 min 1;
    private _toneStep = (missionNamespace getVariable ["ACME_tbi_autonomicToneSlewPerSec", 0.35]) * _dt;
    _autonomicTone = _autonomicTone + (((_toneTarget - _autonomicTone) max (-_toneStep)) min _toneStep);
    _autonomicTone = _autonomicTone max -1 min 1;
    _state set ["autonomicTone", _autonomicTone];
    _state set ["autonomicToneTarget", _toneTarget];
    _state set ["autonomicDecomp", _decompDrive];

    // the cushing reflex tell.
    private _cushing = _icp >= _cushingTrigger;
    _state set ["cushing", _cushing];

    // the herniation cascade.
    private _herniationTrigger = missionNamespace getVariable ["ACME_tbi_herniationICP", 30];  // todo[ref].
    private _stage = _state getOrDefault ["herniationStage", 0];
    private _clock = _state getOrDefault ["herniationClock", -1];
    private _pupils = _state getOrDefault ["pupils", 0];

    // evacuation status. a herniated brain is a neurosurgical emergency. field care only temporises, because the
    // lesion needs definitive, surgical decompression, so the casualty must be evacuated. being loaded into a
    // vehicle is the casevac handoff, as is a mission or zeus-set ACME_evacuated flag. while evacuated the cascade
    // is frozen and the casualty survives transport to higher care. evacuation does not undo damage already
    // done.
    private _evacuated = (_patient getVariable ["ACME_evacuated", false]) ||
        {(missionNamespace getVariable ["ACME_tbi_evacInVehicle", true]) && {!(isNull objectParent _patient)}};
    _state set ["evacuated", _evacuated];

    // herniation is an end-stage event rather than an instant threshold crossing. ICP must remain above the
    // herniation threshold for a minimum gate before the cascade can even arm. if ICP is controlled below the
    // threshold, the gate bleeds down and any active stage recovers instead of continuing to worsen.
    private _aboveHerniation = _icp >= _herniationTrigger;
    private _hernGate = missionNamespace getVariable ["ACME_tbi_herniationMinSeconds", 600];
    private _hernHighTime = _state getOrDefault ["herniationHighTime", 0];
    if (_aboveHerniation && {!_elevated}) then {
        _hernHighTime = _hernHighTime + _dt;
    } else {
        _hernHighTime = (_hernHighTime - (_dt * 0.5)) max 0;
    };
    _state set ["herniationHighTime", _hernHighTime];
    _state set ["herniationGateRemaining", (_hernGate - _hernHighTime) max 0];
    private _hernGateOpen = _hernHighTime >= _hernGate;
    _state set ["herniationGateOpen", _hernGateOpen];

    if (_aboveHerniation && {_hernGateOpen} && {!_elevated}) then {
        _state set ["herniating", true];
        if (_pupils < 1) then {_pupils = 1};  // anisocoria and a sluggish pupil: the warning shot, before a pupil blows.
        if (_clock < 0) then {_clock = missionNamespace getVariable ["ACME_tbi_herniationStageSeconds", 360]};  // todo[ref].
        // frozen while evacuated, as the handoff to higher care. the clock holds and no new stage is reached in
        // transit.
        if (!_evacuated) then {
            _clock = _clock - _dt;
            if (_clock <= 0 && {_stage < 3}) then {
                _stage = _stage + 1;
                _clock = missionNamespace getVariable ["ACME_tbi_herniationStageSeconds", 360];
                switch (_stage) do {
                    // stage 1 is impending herniation: unilateral cn iii compression, so one fixed, dilated pupil, and still
                    // localising, at m5. this is the correctable window. decompress here, through osmotherapy, CPP, ventilation or
                    // head-up, and they can recover, carrying only the permanent stage-1 severity floor.
                    case 1: { _pupils = 2; _state set ["gcsMotor", 5]; };
                    // stage 2 is actual, irreversible herniation: bilateral fixed and dilated, with posturing at m3. the
                    // irreversible severity floor latches here, and field care only temporises to evac.
                    case 2: { _pupils = 3; _state set ["gcsMotor", 3]; };
                    // stage 3 is terminal, at m1.
                    case 3: { _pupils = 3; _state set ["gcsMotor", 1]; };
                };
            };
        };
    } else {
        // with ICP controlled below the trigger, or the head elevated so herniation is impossible, stand the cascade
        // down and recover stepwise. head elevation grants immunity to new herniation and slowly reverses an ongoing
        // one, and the irreversible-severity floor below still applies if stage 2 was ever reached.
        _state set ["herniating", false];
        _clock = -1;
        if (_stage > 0) then {_stage = (_stage - (_dt / 60)) max 0};
        if (_stage <= 0) then {
            if (_icp < _cushingTrigger) then {_pupils = 0} else {_pupils = _pupils min 1};
        };
    };
    _state set ["herniationStage", _stage];
    _state set ["herniationClock", _clock];
    _state set ["pupils", _pupils];

    // the damage high-water mark drives the permanent severity floor that recovery heals down to and never below.
    // a maxstage of 0 gives a floor of 0. they were never even impending, so a viable casualty can fully recover and
    // go back in the fight.
    // a maxstage of 1 gives a floor of 0.01 to 0.30, for impending herniation, which is recoverable. it is scaled by
    // how far the stage-1 clock ran before it was controlled. they can be made combat-effective, and their vitals
    // never fully normalize, and repeat trauma is far more lethal, because the floor stacks on the next insult.
    // a maxstage of 2 or more gives a floor of 0.85, for actual, irreversible herniation. the brain is structurally
    // lost.
    private _maxStage = (_state getOrDefault ["maxStage", 0]) max _stage;
    _state set ["maxStage", _maxStage];

    // track how developed the impending, stage 1, herniation got: the deepest fraction of the stage-1 clock that
    // elapsed. 0 means they only just reached stage 1, and 1 means the full stage-1 clock ran and they were about
    // to tip to actual herniation.
    if (_stage == 1 && {!_evacuated}) then {
        private _stageSecs = missionNamespace getVariable ["ACME_tbi_herniationStageSeconds", 360];
        private _elapsedFrac = ((_stageSecs - _clock) / (_stageSecs max 1)) max 0 min 1;
        _state set ["stage1Depth", ((_state getOrDefault ["stage1Depth", 0]) max _elapsedFrac)];
    };

    private _severityFloor = 0;
    if (_maxStage >= 2) then {
        _severityFloor = missionNamespace getVariable ["ACME_tbi_irreversibleSeverity", 0.85];
    } else {
        if (_maxStage >= 1) then {
            private _fMin = missionNamespace getVariable ["ACME_tbi_stage1FloorMin", 0.01];
            private _fMax = missionNamespace getVariable ["ACME_tbi_stage1FloorMax", 0.30];
            _severityFloor = _fMin + ((_fMax - _fMin) * (_state getOrDefault ["stage1Depth", 0]));
        };
    };

    // the evacuation requirement.
    // at stage 2 or more, actual herniation, it latches requiresevac permanently. a herniated brain is not
    // recoverable in the field, so it can never clear and they must be evacuated.
    // at stage 1, impending herniation, it requires evac only until fully recovered. once severity has healed back
    // down to the stage-1 floor and they are no longer actively herniating, the impending event was corrected in
    // the field and the evac requirement clears, so they can be fully stabilized and returned to duty.
    private _herniatingNow = _state getOrDefault ["herniating", false];
    if (_maxStage >= 2) then {
        [_patient, true, true, true, false] call ACME_fnc_evacuationRequirementCommit;
    } else {
        if (_maxStage >= 1) then {
            private _recovered = (!_herniatingNow) && {_stage <= 0} && {_severity <= (_severityFloor + 0.02)};
            if (_recovered) then {
                // TBI recovery cannot clear another latched, field-unresolved injury.
                private _otherPermanent = _patient getVariable ["ACM_burns_PermanentInjury", false]
                    || {_patient getVariable ["ACM_infection_Sepsis_Permanent", false]}
                    || {_patient getVariable ["ACM_ophthalmology_ocularPermanent", false]};
                if (!_otherPermanent && {_patient getVariable ["ACME_requiresEvac", false]}) then {
                    [_patient, false, true, true, true] call ACME_fnc_evacuationRequirementCommit;
                };
            } else {
                [_patient, true, true, true, false] call ACME_fnc_evacuationRequirementCommit;
            };
        };
    };
    _state set ["severityFloor", _severityFloor];
    // interruptible and capped. new insults during recovery, such as bleeding, overload, a pressor surge or a lost
    // airway, legitimately push severity back up, and however many fire at once, the net rise this tick is clamped
    // to a fixed maximum. so a casualty who suddenly has several things go wrong does not have their ICP tank
    // instantly. it scales with what is happening and climbs at a manageable ceiling rate, which gives the provider
    // time to work the problems. healing below the start is not capped, only the rise is. the ICP value itself is
    // separately rate-capped downstream, and this caps the severity that drives the ICP ceiling.
    private _sevRiseCap = missionNamespace getVariable ["ACME_tbi_severityRiseCapPerSec", 0.02];
    if (_sevRiseCap > 0) then { _severity = _severity min (_severityStart + (_sevRiseCap * _dt)); };
    // enforce the permanent damage floor. the recovery term above healed toward the floor of the last tick, and this
    // pins it.
    _severity = _severity max _severityFloor;

    // apply the cushing, decompensation or terminal pattern onto the vitals of the patient, bounded and eased.
    if (missionNamespace getVariable ["ACME_tbi_applyVitals", true]) then {
        _state set ["icp", _icp];
        _state set ["severity", _severity];
        [_patient, _state, _dt] call ACME_fnc_tbiApplyVitals;
    };

    _state set ["icp", _icp];
    _state set ["severity", _severity];
    [_patient, _state] call ACME_fnc_tbiStateCommit;
} forEach ACME_tbi_activePatients;
