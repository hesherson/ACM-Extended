/*
 * Local-only ACME perception mixer.
 *
 * Physiology contributes continuous magnitudes. Debug actions contribute deterministic local tiers. One controller
 * owns the PP handles so effects cannot fight each other, leak across respawn, or depend on patient-scoped debug vars.
 */
if (!hasInterface) exitWith {};
private _u = player;
if (isNull _u) exitWith {};

private _enabled = missionNamespace getVariable ["ACME_visualFx_enabled",true];
private _epoch = if (!isNil "ACME_fnc_clinicalEpoch") then {[_u] call ACME_fnc_clinicalEpoch} else {0};
private _lastUnit = uiNamespace getVariable ["ACME_VFX_LastUnit",objNull];
private _lastEpoch = uiNamespace getVariable ["ACME_VFX_LastEpoch",-9999];
private _lifeChanged = !(_lastUnit isEqualTo _u) || {_lastEpoch != _epoch};

// The previous implementation created WetDistortion enabled, then tried to neutralize it later in the same tick.
// It also kept debug severity on the casualty object.  Both are bad spawn semantics.  Every new life/clinical epoch
// starts from a hard local zero and ignores physiology for a few seconds while ACE initializes its vital variables.
if (_lifeChanged) then {
    uiNamespace setVariable ["ACME_VFX_LastUnit",_u];
    uiNamespace setVariable ["ACME_VFX_LastEpoch",_epoch];
    uiNamespace setVariable ["ACME_VFX_PhysReadyAt",diag_tickTime + 5.0];
    {
        uiNamespace setVariable [format ["ACME_VFX_Debug_%1",_x],0];
    } forEach ["hypoxia","hypotension","hypercapnia","ketamine","syncope"];
    {
        private _h = uiNamespace getVariable [_x,-1];
        if (_h isEqualType 0 && {_h >= 0}) then {_h ppEffectEnable false;};
    } forEach ["ACME_VFX_Wet","ACME_VFX_KetWetDebug","ACME_VFX_KetMotion","ACME_VFX_KetZoom","ACME_VFX_Chrom","ACME_VFX_Blur","ACME_VFX_Color","ACME_VFX_Tunnel"];
    uiNamespace setVariable ["ACME_VFX_WetActive",false];
    uiNamespace setVariable ["ACME_VFX_WetLast",[]];
    uiNamespace setVariable ["ACME_VFX_TunnelLast",[]];
    uiNamespace setVariable ["ACME_VFX_KetZoomLast",-1];
    uiNamespace setVariable ["ACME_VFX_KetWetSmooth",0];
    uiNamespace setVariable ["ACME_VFX_KetWetSmoothAt",diag_tickTime];
    uiNamespace setVariable ["ACME_VFX_KetGeneralSmooth",0];
    uiNamespace setVariable ["ACME_VFX_KetGeneralSmoothAt",diag_tickTime];
    uiNamespace setVariable ["ACME_VFX_KetWetDebugLast",[]];
    uiNamespace setVariable ["ACME_VFX_KetLastDoseAt",-1];
    uiNamespace setVariable ["ACME_VFX_HeartPhase",0];
    uiNamespace setVariable ["ACME_VFX_HeartPhaseAt",diag_tickTime];
    uiNamespace setVariable ["ACME_VFX_ForceRefresh",true];
    uiNamespace setVariable ["ACME_VFX_WetForceRefresh",true];
};
private _physReady = diag_tickTime >= (uiNamespace getVariable ["ACME_VFX_PhysReadyAt",diag_tickTime + 5]);

// Create handles DISABLED. Each effect block below explicitly enables only when its requested magnitude is nonzero.
private _mk = {
    params ["_slot","_name","_prio"];
    private _h = uiNamespace getVariable [_slot,-1];
    if (!(_h isEqualType 0) || {_h < 0}) then {
        private _p = _prio;
        _h = -1;
        while {_h < 0 && {_p < (_prio + 40)}} do {
            _h = ppEffectCreate [_name,_p];
            _p = _p + 1;
        };
        uiNamespace setVariable [_slot,_h];
        if (_h >= 0) then {_h ppEffectEnable false;};
    };
    _h
};
private _wet = ["ACME_VFX_Wet","WetDistortion",330] call _mk;
// Dedicated debug-ketamine wet pass. It is deliberately later than DynamicBlur so Moderate/Severe blur cannot
// visually wash out the displacement. This handle is local, starts disabled, and is asserted while any ketamine
// debug tier is active.
private _ketWetDebugHandle = ["ACME_VFX_KetWetDebug","WetDistortion",480] call _mk;
// RadialBlur is the closest scriptable approximation to the mild motion-lag / trailing sensation described with
// ketamine. Keep it very weak and strongest in the mild-to-moderate range; the separate zoom-like pass below owns
// the stronger depth-perception cue at clearly dissociative exposure.
private _ketMotion = ["ACME_VFX_KetMotion","RadialBlur",485] call _mk;
// Arma has no safe scripting command for changing the live player's FOV. A very light RadialBlur pass provides a
// slow optical push-in impression for Moderate/Severe ketamine without replacing the gameplay camera.
private _ketZoom = ["ACME_VFX_KetZoom","RadialBlur",490] call _mk;
private _chrom = ["ACME_VFX_Chrom","ChromAberration",230] call _mk;
private _blur = ["ACME_VFX_Blur","DynamicBlur",430] call _mk;
private _color = ["ACME_VFX_Color","ColorCorrections",1530] call _mk;
// Same radial geometry ACM uses for the severe low-oxygen/pneumothorax tunnel, but with an independent handle.
private _tunnel = ["ACME_VFX_Tunnel","ColorCorrections",1531] call _mk;

private _commit = missionNamespace getVariable ["ACME_visualFx_commitSec",0.30];
private _clamp = {params ["_v"]; (_v max 0) min 1};
private _dbgLevel = {
    params ["_kind"];
    private _d = uiNamespace getVariable [format ["ACME_VFX_Debug_%1",_kind],0];
    if !(_d isEqualType 0) exitWith {0};
    round ((_d max 0) min 3)
};
private _dbgMag = {params ["_level"]; [0,0.34,0.68,1.00] param [_level,0]};

private _dbgHyp = ["hypoxia"] call _dbgLevel;
private _dbgLow = ["hypotension"] call _dbgLevel;
private _dbgCO2 = ["hypercapnia"] call _dbgLevel;
private _dbgKet = ["ketamine"] call _dbgLevel;
private _dbgSyn = ["syncope"] call _dbgLevel;

private _hyp = 0;
private _low = 0;
private _co2 = 0;
private _ket = 0;
private _ketWetReal = 0;
private _ketDoseNorm = 0;
private _ketAnalgesicActive = false;
private _ketAnalgesicEnvelope = 1;
private _ketAnalgesicBlurEnvelope = 1;
private _ketAnalgesicChromEnvelope = 1;
private _ketAnalgesicWetEnvelope = 1;
private _syn = 0;

if (_enabled && {alive _u} && {_physReady}) then {
    private _spo2 = _u getVariable ["ace_medical_spo2",100];
    if !(_spo2 isEqualType 0 && {finite _spo2}) then {_spo2 = 100;};
    _hyp = [((missionNamespace getVariable ["ACME_visualFx_hypoxiaStart",95]) - _spo2) /
        (((missionNamespace getVariable ["ACME_visualFx_hypoxiaStart",95]) - (missionNamespace getVariable ["ACME_visualFx_hypoxiaSevere",72])) max 1)] call _clamp;

    if (!isNil "ace_medical_status_fnc_getBloodPressure") then {
        private _bp = [_u] call ace_medical_status_fnc_getBloodPressure;
        private _dia = _bp param [0,80];
        private _sys = _bp param [1,120];
        if (_dia isEqualType 0 && {_sys isEqualType 0} && {finite _dia} && {finite _sys} && {_sys > 0}) then {
            private _map = _dia + ((_sys - _dia) / 3);
            _low = [((missionNamespace getVariable ["ACME_visualFx_mapStart",70]) - _map) /
                (((missionNamespace getVariable ["ACME_visualFx_mapStart",70]) - (missionNamespace getVariable ["ACME_visualFx_mapSevere",35])) max 1)] call _clamp;
        };
    };

    private _cs = _u getVariable ["ACME_circ_State",createHashMap];
    private _pa = if (_cs isEqualType createHashMap) then {_cs getOrDefault ["paCO2",40]} else {40};
    if !(_pa isEqualType 0 && {finite _pa}) then {_pa = 40;};
    _co2 = [(_pa - (missionNamespace getVariable ["ACME_visualFx_co2Start",48])) /
        (((missionNamespace getVariable ["ACME_visualFx_co2Severe",85]) - (missionNamespace getVariable ["ACME_visualFx_co2Start",48])) max 1)] call _clamp;

    if (!isNil "ACME_fnc_ketamineOnBoard") then {
        private _k = [_u] call ACME_fnc_ketamineOnBoard;
        if (_k isEqualType 0 && {finite _k} && {_k > 0}) then {
            // ketamineOnBoard is an ACM effect-ratio sum, not a normalized dissociation severity. ACME's own
            // sedation model treats ~ACME_ket_induceThreshold (default 7) as a full induction-equivalent load.
            // Normalize against that same clinical scale before feeding perception. This prevents a small 20 mg
            // (0.4 mL of the 50 mg/mL vial) IV dose from looking like near-induction dissociation while still using
            // ACM's native route onset and washout timing.
            private _ketInduce = (missionNamespace getVariable ["ACME_ket_induceThreshold",7]) max 0.1;
            private _kNorm = (_k / _ketInduce) max 0;
            _ketDoseNorm = _kNorm;

            // ACME is the sole owner of ketamine ChromAberration. Disable ACM's legacy handle here and reproduce
            // its former dose/HR-synchronous contribution numerically below. This preserves the stronger stacked-era
            // magnitude without running two ChromAberration PP effects against each other.
            private _acmKetChrom = missionNamespace getVariable ["ACM_core_ppAnestheticEffect_chrom",-1];
            if (_acmKetChrom isEqualType 0 && {_acmKetChrom >= 0}) then {_acmKetChrom ppEffectEnable false;};

            // Analgesic/sub-dissociative visuals are intentionally transient and waxing/waning. A new ketamine dose
            // refreshes ACME_VFX_KetLastDoseAt through the ACE medicationLocal event registered in fn_postInit.
            // If a mission starts with ketamine already on board, begin the window when ACME first detects it.
            private _lastKetDoseAt = uiNamespace getVariable ["ACME_VFX_KetLastDoseAt",-1];
            if !(_lastKetDoseAt isEqualType 0 && {finite _lastKetDoseAt} && {_lastKetDoseAt >= 0}) then {
                _lastKetDoseAt = diag_tickTime;
                uiNamespace setVariable ["ACME_VFX_KetLastDoseAt",_lastKetDoseAt];
            };
            private _ketVisualAge = (diag_tickTime - _lastKetDoseAt) max 0;
            private _analgesicMax = missionNamespace getVariable ["ACME_visualFx_ketamineAnalgesicMax",0.22];
            _ketAnalgesicActive = _kNorm <= _analgesicMax;
            if (_ketAnalgesicActive) then {
                private _maxVisualSec = missionNamespace getVariable ["ACME_visualFx_ketamineAnalgesicWindowSec",300];
                if (_ketVisualAge >= _maxVisualSec) then {
                    // Keep pharmacology intact, but end the local perception layer after five minutes unless redosed.
                    _ketDoseNorm = 0;
                    _ketAnalgesicEnvelope = 0;
                    _ketAnalgesicBlurEnvelope = 0;
                    _ketAnalgesicChromEnvelope = 0;
                    _ketAnalgesicWetEnvelope = 0;
                } else {
                    private _cycle = (missionNamespace getVariable ["ACME_visualFx_ketamineAnalgesicWaveSec",28]) max 6;
                    private _wave01 = 0.5 - (0.5 * cos (360 * ((_ketVisualAge mod _cycle) / _cycle)));
                    private _waveShaped = _wave01 ^ 1.35;
                    // Analgesic ketamine should breathe in and out rather than look continuously blurred. Keep the
                    // general/saturation layer gently present, let blur almost clear between crests, retain a steadier
                    // chromatic base for the separate pulse below, and preserve the existing water-displacement range.
                    _ketAnalgesicEnvelope = 0.55 + (0.45 * _wave01);
                    _ketAnalgesicBlurEnvelope = _waveShaped;
                    _ketAnalgesicChromEnvelope = 0.72 + (0.28 * _wave01);
                    _ketAnalgesicWetEnvelope = 0.78 + (0.32 * _wave01);
                };
            };
            // Real-dose perception uses a deliberately bottom-heavy response curve.  A small analgesic exposure
            // (~0.25 mg/kg IV, e.g. 0.4 mL of 50 mg/mL in a ~79 kg casualty) should be barely perceptible, not a
            // miniature dissociative state.  Moderate exposure reaches roughly the OLD low-dose visual level, while
            // the high/induction endpoint remains exactly 1.0 so Severe is not weakened.
            private _curve = {
                params ["_x","_onset","_lowIn","_midIn","_fullIn","_lowOut","_midOut"];
                if (_x <= _onset) exitWith {0};
                if (_x <= _lowIn) exitWith {linearConversion [_onset,_lowIn,_x,0,_lowOut,true]};
                if (_x <= _midIn) exitWith {linearConversion [_lowIn,_midIn,_x,_lowOut,_midOut,true]};
                linearConversion [_midIn,_fullIn,_x,_midOut,1,true]
            };

            private _fullIn = missionNamespace getVariable ["ACME_visualFx_ketamineFull",0.82];
            private _lowIn = missionNamespace getVariable ["ACME_visualFx_ketamineDoseLowPoint",0.16];
            private _midIn = missionNamespace getVariable ["ACME_visualFx_ketamineDoseModeratePoint",0.45];

            _ket = [
                _kNorm,
                missionNamespace getVariable ["ACME_visualFx_ketamineStart",0.08],
                _lowIn,
                _midIn,
                _fullIn,
                missionNamespace getVariable ["ACME_visualFx_ketamineLowGeneralOut",0.010],
                missionNamespace getVariable ["ACME_visualFx_ketamineModerateGeneralOut",0.060]
            ] call _curve;

            // Water starts slightly earlier than chromatic/blur. The low/mid response stays subtle but is lifted
            // enough to remain perceptible before high dissociative exposure; the final high-dose ceiling is unchanged.
            _ketWetReal = [
                _kNorm,
                missionNamespace getVariable ["ACME_visualFx_ketamineWetStart",0.05],
                _lowIn,
                _midIn,
                missionNamespace getVariable ["ACME_visualFx_ketamineWetFull",0.82],
                missionNamespace getVariable ["ACME_visualFx_ketamineLowWetOut",0.065],
                missionNamespace getVariable ["ACME_visualFx_ketamineModerateWetOut",0.215]
            ] call _curve;

            if (_ketAnalgesicActive) then {
                if (_ketAnalgesicEnvelope <= 0) then {
                    _ket = 0;
                    _ketWetReal = 0;
                } else {
                    _ket = _ket * _ketAnalgesicEnvelope;
                    // Slightly more obvious analgesic water movement, but still below the authored Mild debug point.
                    _ketWetReal = (_ketWetReal * _ketAnalgesicWetEnvelope) min 0.30;
                };
            };
        };
    };
    _syn = ((_low * 0.75) + (_hyp * 0.35)) min 1;
};

if (_enabled && {alive _u}) then {
    _hyp = _hyp max ([_dbgHyp] call _dbgMag);
    _low = _low max ([_dbgLow] call _dbgMag);
    _co2 = _co2 max ([_dbgCO2] call _dbgMag);
    _ket = _ket max ([_dbgKet] call _dbgMag);
    _syn = _syn max ([_dbgSyn] call _dbgMag);
};

if (!_enabled || {!alive _u}) then {
    _hyp = 0; _low = 0; _co2 = 0; _ket = 0; _ketWetReal = 0; _ketDoseNorm = 0; _syn = 0;
    _dbgHyp = 0; _dbgLow = 0; _dbgCO2 = 0; _dbgKet = 0; _dbgSyn = 0;
};

// Smooth the non-wave ketamine layers too. The old debug path stepped blur/chromatic separation to a new tier in
// one controller tick even when the water layer was being eased, which made the overall ketamine onset still feel
// abrupt. Real medication and debug now share the same gradual visual envelope.
private _ketGeneralTarget = _ket;
private _ketGeneralNow = diag_tickTime;
private _ketGeneralAt = uiNamespace getVariable ["ACME_VFX_KetGeneralSmoothAt",_ketGeneralNow];
private _ketGeneralDt = ((_ketGeneralNow - _ketGeneralAt) max 0) min 0.25;
private _ketGeneralSmooth = uiNamespace getVariable ["ACME_VFX_KetGeneralSmooth",0];
if !(_ketGeneralSmooth isEqualType 0 && {finite _ketGeneralSmooth}) then {_ketGeneralSmooth = 0;};
private _ketGeneralTau = if (_ketGeneralTarget > _ketGeneralSmooth) then {
    missionNamespace getVariable ["ACME_visualFx_ketamineGeneralRiseSec",6.0]
} else {
    missionNamespace getVariable ["ACME_visualFx_ketamineGeneralFallSec",5.0]
};
private _ketGeneralStep = (_ketGeneralDt / (_ketGeneralTau max 0.25)) min 1;
_ketGeneralSmooth = (_ketGeneralSmooth + ((_ketGeneralTarget - _ketGeneralSmooth) * _ketGeneralStep)) max 0 min 1;
if (abs (_ketGeneralTarget - _ketGeneralSmooth) < 0.0005) then {_ketGeneralSmooth = _ketGeneralTarget;};
uiNamespace setVariable ["ACME_VFX_KetGeneralSmooth",_ketGeneralSmooth];
uiNamespace setVariable ["ACME_VFX_KetGeneralSmoothAt",_ketGeneralNow];
_ket = _ketGeneralSmooth;
private _ketOnsetEnvelope = if (_ketGeneralTarget > 0.001) then {(_ketGeneralSmooth / _ketGeneralTarget) min 1} else {0};

// Deterministic debug profiles. These are intentionally more obvious than the continuous physiologic thresholds so
// an instructor can verify every layer from the medical menu without guessing whether an effect actually changed.
// Ketamine owns the dedicated late wet pass below for BOTH medication-driven and debug effects. Keeping it out
// of this shared shock/CO2 pass prevents blur ordering and mixed-state profiles from hiding the water displacement.
private _ketWetPhys = 0;
private _ketWetDebug = 0;
private _shockWetPhys = if (_low > 0.20) then {linearConversion [0.20,1,_low,0.20,0.88,true]} else {0};
private _shockWetDebug = [0,0.28,0.62,0.96] param [_dbgLow,0];
private _co2WetPhys = if (_co2 > 0.10) then {linearConversion [0.10,1,_co2,0.08,0.42,true]} else {0};
private _co2WetDebug = [0,0.20,0.48,0.78] param [_dbgCO2,0];
private _dist = (_ketWetPhys max _ketWetDebug max _shockWetPhys max _shockWetDebug max _co2WetPhys max _co2WetDebug) min 1;

// Ketamine uses a different visual vocabulary below dissociation: mild focus loss/diplopia first, then depth
// distortion and stronger perceptual separation later.  Keep a ~0.25 mg/kg exposure in the SUB-dissociative band.
private _ketBlurReal = 0;
if (_ketDoseNorm > 0) then {
    if (_ketDoseNorm <= 0.18) then {
        _ketBlurReal = linearConversion [0.05,0.18,_ketDoseNorm,0,0.028,true];
    } else {
        if (_ketDoseNorm <= 0.45) then {
            _ketBlurReal = linearConversion [0.18,0.45,_ketDoseNorm,0.028,0.135,true];
        } else {
            _ketBlurReal = linearConversion [0.45,0.82,_ketDoseNorm,0.145,0.48,true];
        };
    };
};
if (_ketAnalgesicActive) then {_ketBlurReal = _ketBlurReal * _ketAnalgesicBlurEnvelope;};
_ketBlurReal = _ketBlurReal * _ketOnsetEnvelope;
private _ketSharedBlur = if (_ketDoseNorm > (missionNamespace getVariable ["ACME_visualFx_ketamineAnalgesicMax",0.22])) then {(_ket * 0.10)} else {0};
private _blurV = ((_hyp*0.90)+(_low*0.80)+(_co2*0.70)+_ketSharedBlur+(_syn*1.00)) min 2.6;
_blurV = _blurV max _ketBlurReal;
// Debug ketamine mirrors dose bands: Mild stays subtle, Moderate is clearly altered, Severe owns the strong state.
private _dbgKetTargetMag = [_dbgKet] call _dbgMag;
private _dbgKetEnvelope = if (_dbgKet > 0 && {_dbgKetTargetMag > 0.001}) then {(_ket / _dbgKetTargetMag) min 1} else {0};
private _dbgKetBlur = ([0,0.050,0.18,0.50] param [_dbgKet,0]) * _dbgKetEnvelope;
private _dbgBlur = ([0,0.32,0.90,1.65] param [_dbgHyp,0])
    max ([0,0.28,0.82,1.55] param [_dbgLow,0])
    max ([0,0.40,1.05,1.80] param [_dbgCO2,0])
    max _dbgKetBlur
    max ([0,0.55,1.35,2.35] param [_dbgSyn,0]);
_blurV = _blurV max _dbgBlur;

// Chromatic aberration is the diplopia / subtle color-edge cue.  The previous scale was too prominent at analgesic
// ACME-only equivalent of ACM's former anesthetic ChromAberration. ACM used:
//   effect = Ketamine(IM)*0.5 + Ketamine_IV*0.8; peak = linearConversion [0,1,effect,0,0.06]; floor = peak*0.3.
// Recreate ~86% of that contribution in this single handle, pulse-synchronous to HR, then layer ACME's slower
// diplopia/vibration texture on top numerically. No second PP effect is enabled.
private _legacyChromEq = 0;
if (_ketDoseNorm > 0 && {!isNil "ace_medical_status_fnc_getMedicationCount"}) then {
    private _imLegacy = [_u,"Ketamine",false] call ACME_fnc_medicationCountCompat;
    private _ivLegacy = [_u,"Ketamine_IV",false] call ACME_fnc_medicationCountCompat;
    if !(_imLegacy isEqualType 0 && {finite _imLegacy}) then {_imLegacy = 0;};
    if !(_ivLegacy isEqualType 0 && {finite _ivLegacy}) then {_ivLegacy = 0;};
    private _legacyEffect = (((_imLegacy max 0) * 0.5) + ((_ivLegacy max 0) * 0.8)) min 1;
    private _legacyScale = missionNamespace getVariable ["ACME_visualFx_ketamineLegacyChromEquivalentScale",1.00];
    private _legacyPeak = (0.06 * _legacyEffect * _legacyScale) max 0;
    // Match the former ACM+ACME peak magnitude with ACME alone, but make the beat easier to read: a quick rise,
    // short relaxation, then a quiet floor before the next beat. Peak is unchanged; only the temporal contrast is
    // sharper than the old overlapping commits.
    private _legacyFloor = _legacyPeak * 0.24;
    private _legacyHR = _u getVariable ["ace_medical_heartRate",80];
    if !(_legacyHR isEqualType 0 && {finite _legacyHR} && {_legacyHR > 0}) then {_legacyHR = 80;};
    private _legacyRR = 60 / ((_legacyHR max 25) min 240);
    private _legacyPhase = (diag_tickTime mod _legacyRR) / (_legacyRR max 0.10);
    private _legacyPulse = if (_legacyPhase < 0.14) then {
        sin ((_legacyPhase / 0.14) * 90)
    } else {
        if (_legacyPhase < 0.52) then {
            private _r = ((_legacyPhase - 0.14) / 0.38) min 1;
            1 - (_r ^ 0.82)
        } else {0}
    };
    _legacyChromEq = _legacyFloor + ((_legacyPeak - _legacyFloor) * (_legacyPulse max 0 min 1));
};

// ACME's authored low-dose edge separation remains as the slower perceptual texture.
private _ketChromReal = 0;
if (_ketDoseNorm > 0) then {
    if (_ketDoseNorm <= 0.18) then {
        _ketChromReal = linearConversion [0.05,0.18,_ketDoseNorm,0,0.000050,true];
    } else {
        if (_ketDoseNorm <= 0.45) then {
            _ketChromReal = linearConversion [0.18,0.45,_ketDoseNorm,0.000050,0.00054,true];
        } else {
            _ketChromReal = linearConversion [0.45,0.82,_ketDoseNorm,0.00060,0.0038,true];
        };
    };
};
if (_ketAnalgesicActive) then {_ketChromReal = _ketChromReal * _ketAnalgesicChromEnvelope;};
_ketChromReal = _ketChromReal * (0.20 + (0.80 * _ketOnsetEnvelope));
private _dbgKetChrom = ([0,0.000080,0.00070,0.0038] param [_dbgKet,0]) * _dbgKetEnvelope;
private _ketChromRaw = ((_ketChromReal + _legacyChromEq) max _dbgKetChrom) min 0.060;
// Slow pulse + damped vibration tail. Dose owns magnitude; modulation is noticeable again without becoming a
// second stacked chromatic effect.
private _chromCycleSec = 5.2;
private _chromCycleT = diag_tickTime mod _chromCycleSec;
private _chromPulse = 0;
private _chromVibe = 0;
if (_chromCycleT < 0.52) then {
    _chromPulse = sin ((_chromCycleT / 0.52) * 180);
} else {
    if (_chromCycleT < 1.32) then {
        private _tailT = _chromCycleT - 0.52;
        private _tailFade = 1 - (_tailT / 0.80);
        _chromVibe = (sin (_tailT * 360 * 4.6)) * _tailFade;
    };
};
// With ACM's duplicate ketamine chromatic pass suppressed, restore a perceptible pulse without making the RGB split
// dominant. Low doses get a larger RELATIVE pulse on a very small base; high-dose modulation tapers down.
private _chromPulseGain = linearConversion [0,0.060,_ketChromRaw,0.080,0.018,true];
private _chromVibeGain = linearConversion [0,0.060,_ketChromRaw,0.022,0.008,true];
private _ketChromX = _ketChromRaw * (1 + (_chromPulseGain * _chromPulse) + (_chromVibeGain * _chromVibe));
private _ketChromY = (_ketChromRaw * 0.62) * (1 + ((_chromPulseGain * 0.72) * _chromPulse) - ((_chromVibeGain * 0.78) * _chromVibe));
private _hypChrom = (_hyp * 0.0015) min 0.0015;
private _chromX = (_ketChromX + _hypChrom) min 0.065;
private _chromY = (_ketChromY + (_hypChrom * 0.65)) min 0.050;
private _chromV = _chromX max _chromY;
private _dark = ((_hyp*0.34)+(_low*0.40)+(_syn*0.45)) min 0.68;
_dark = _dark max ([0,0.08,0.22,0.42] param [_dbgHyp,0])
    max ([0,0.08,0.24,0.46] param [_dbgLow,0])
    max ([0,0.10,0.30,0.56] param [_dbgSyn,0]);
private _sat = (1 - ((_hyp*0.60)+(_low*0.18))) max 0.24;
private _dbgSat = ([1,0.90,0.68,0.42] param [_dbgHyp,1]) min ([1,0.96,0.86,0.72] param [_dbgLow,1]);
_sat = _sat min _dbgSat;
// Mildly vivid color response. Arma's ColorCorrections does not expose a standalone scripted "saturation +N%"
// control, so use a very small contrast/colorization lift. Hypoxia/shock desaturation still remains authoritative.
private _ketVividReal = if (_ketDoseNorm <= 0.05) then {0} else {
    if (_ketDoseNorm <= 0.18) then {linearConversion [0.05,0.18,_ketDoseNorm,0,0.18,true]} else {
        if (_ketDoseNorm <= 0.45) then {linearConversion [0.18,0.45,_ketDoseNorm,0.18,0.52,true]} else {
            linearConversion [0.45,0.82,_ketDoseNorm,0.52,1,true]
        }
    }
};
if (_ketAnalgesicActive) then {_ketVividReal = _ketVividReal * (0.72 + (0.28 * _ketAnalgesicEnvelope));};
private _ketVividDebug = [0,0.16,0.55,1.00] param [_dbgKet,0];
private _ketVivid = (_ketVividReal max (_ketVividDebug * _dbgKetEnvelope)) min 1;

private _tunnelSource = (_syn max _low max (_hyp*0.85));
private _tunnelStart = missionNamespace getVariable ["ACME_visualFx_tunnelStart",0.50];
private _tunnelI = linearConversion [_tunnelStart,1,_tunnelSource,0,1,true];
private _dbgTunnel = ([0,0.00,0.42,0.95] param [_dbgHyp,0])
    max ([0,0.08,0.52,1.00] param [_dbgLow,0])
    max ([0,0.32,0.74,1.00] param [_dbgSyn,0]);
_tunnelI = _tunnelI max _dbgTunnel;

private _forceAll = uiNamespace getVariable ["ACME_VFX_ForceRefresh",false];
if (_forceAll) then {uiNamespace setVariable ["ACME_VFX_ForceRefresh",false];};

// Ketamine has ONE authoritative wave magnitude. Debug tiers and real medication only select a target; the actual
// WetDistortion intensity eases toward that target over several seconds. This prevents the old fast first burst,
// makes Mild genuinely mild, and stops Moderate/Severe from stacking another speed contribution on top of Mild.
private _ketDbgTarget = [0,0.34,0.68,1.00] param [_dbgKet,0];
private _ketWetTarget = (_ketWetReal max _ketDbgTarget) min 1;
private _ketSmoothNow = diag_tickTime;
private _ketSmoothAt = uiNamespace getVariable ["ACME_VFX_KetWetSmoothAt",_ketSmoothNow];
private _ketSmoothDt = ((_ketSmoothNow - _ketSmoothAt) max 0) min 0.25;
private _ketWetSmooth = uiNamespace getVariable ["ACME_VFX_KetWetSmooth",0];
if !(_ketWetSmooth isEqualType 0 && {finite _ketWetSmooth}) then {_ketWetSmooth = 0;};
private _ketTau = if (_ketWetTarget > _ketWetSmooth) then {
    missionNamespace getVariable ["ACME_visualFx_ketamineWetRiseSec",7.0]
} else {
    missionNamespace getVariable ["ACME_visualFx_ketamineWetFallSec",6.0]
};
private _ketStep = (_ketSmoothDt / (_ketTau max 0.25)) min 1;
_ketWetSmooth = (_ketWetSmooth + ((_ketWetTarget - _ketWetSmooth) * _ketStep)) max 0 min 1;
if (abs (_ketWetTarget - _ketWetSmooth) < 0.0005) then {_ketWetSmooth = _ketWetTarget;};
uiNamespace setVariable ["ACME_VFX_KetWetSmooth",_ketWetSmooth];
uiNamespace setVariable ["ACME_VFX_KetWetSmoothAt",_ketSmoothNow];

// Never layer the shock/CO2 WetDistortion pass over an active/fading ketamine wave. Two WetDistortion handles with
// different frequencies were the source of apparent speed spikes. Ketamine owns the wave pass until it fully fades.
if (_ketWetTarget > 0.001 || {_ketWetSmooth > 0.001}) then {_dist = 0;};

// WetDistortion: assert ENABLED every active tick. Do not trust a cached boolean and do not disable/recreate it
// between Mild -> Moderate -> Severe. Only its profile is recommitted when the requested tier/magnitude changes.
if (_wet >= 0) then {
    if (_dist <= 0.001) then {
        _wet ppEffectEnable false;
        uiNamespace setVariable ["ACME_VFX_WetActive",false];
        uiNamespace setVariable ["ACME_VFX_WetLast",[]];
    } else {
        _wet ppEffectEnable true;
        uiNamespace setVariable ["ACME_VFX_WetActive",true];
        private _forceWet = _forceAll || {uiNamespace getVariable ["ACME_VFX_WetForceRefresh",false]};
        if (_forceWet) then {uiNamespace setVariable ["ACME_VFX_WetForceRefresh",false];};

        private _lastWet = uiNamespace getVariable ["ACME_VFX_WetLast",[]];
        private _signature = [_dist,_ket,_low,_co2,_dbgKet,_dbgLow,_dbgCO2];
        private _changed = _forceWet || {!(_lastWet isEqualTo _signature)};
        if (_changed) then {
            private _ketMix = 0;
            private _shockMix = (_low max 0) min 1;
            private _co2Mix = (_co2 max 0) min 1;
            private _speedBias = ((_shockMix * 0.36) + (_co2Mix * 0.22)) min 1;

            // Explicit debug amplification.  Mild remains obvious; Moderate is ~2.3x the mild wave gain and Severe
            // ~4x. Shock and hypercapnia have their own slower/smaller gains and can combine with ketamine.
            private _shockGain = [1.00,1.15,1.75,2.55] param [_dbgLow,1.00];
            private _co2Gain = [1.00,1.05,1.35,1.80] param [_dbgCO2,1.00];
            private _waveGain = _shockGain max _co2Gain;
            private _amp = _dist;

            _wet ppEffectAdjust [
                1,
                0.94 + (0.06*_amp),
                0.94 + (0.06*_amp),
                3.00 + (2.25*_speedBias),
                2.65 + (1.95*_speedBias),
                1.95 + (1.75*_speedBias),
                1.45 + (1.50*_speedBias),
                (0.0044 + (0.0034*_amp)) * _waveGain,
                (0.0034 + (0.0028*_amp)) * _waveGain,
                (0.0074 + (0.0072*_amp)) * _waveGain,
                (0.0057 + (0.0057*_amp)) * _waveGain,
                0.50 + (0.42*_amp),
                0.32 + (0.40*_amp),
                9 + (5*_ketMix),
                5.5 + (4.0*_ketMix)
            ];
            _wet ppEffectCommit 0.06;
            uiNamespace setVariable ["ACME_VFX_WetLast",_signature];
        };
    };
};

// Dedicated late ketamine WetDistortion for BOTH real medication and debug testing. The controller itself smooths
// the scalar, so do NOT start a new ppEffectCommit interpolation every tick. Recommitting while a prior commit is in
// flight was the source of the visible stutter. The profile is applied immediately from the already-smoothed scalar.
// Also adjust BEFORE enabling so a previously disabled Severe profile can never flash for one frame at the start.
if (_ketWetDebugHandle >= 0) then {
    private _ketWetRequested = (_ketWetTarget > 0.001) || {_ketWetSmooth > 0.001};
    private _zeroKetProfile = [1,1,1,2.10,1.88,1.38,1.00,0,0,0,0,0.40,0.24,9.0,5.3];
    if (!_ketWetRequested || {!_enabled} || {!alive _u}) then {
        // Zero the retained engine profile while disabled. WetDistortion remembers its last parameters, so disabling
        // a Severe profile without clearing it can produce a brief strong burst the next time the handle is enabled.
        _ketWetDebugHandle ppEffectAdjust _zeroKetProfile;
        _ketWetDebugHandle ppEffectCommit 0;
        _ketWetDebugHandle ppEffectEnable false;
        uiNamespace setVariable ["ACME_VFX_KetWetDebugLast",[]];
    } else {
        private _tierLerp = {
            params ["_x","_zero","_mild","_moderate","_severe"];
            if (_x <= 0.34) exitWith {linearConversion [0,0.34,_x,_zero,_mild,true]};
            if (_x <= 0.68) exitWith {linearConversion [0.34,0.68,_x,_mild,_moderate,true]};
            linearConversion [0.68,1,_x,_moderate,_severe,true]
        };
        private _k = _ketWetSmooth;

        // One deliberately slow frequency family. Severity is communicated mostly by displacement amplitude, not by
        // wave speed. All four frequencies come only from this scalar, so there is no hidden overlapping speed
        // contribution between Mild, Moderate, Severe, real dose, shock, or CO2.
        private _f1 = [_k,1.24,1.42,1.50,1.58] call _tierLerp;
        private _f2 = [_k,1.10,1.26,1.33,1.40] call _tierLerp;
        private _f3 = [_k,0.80,0.92,0.98,1.04] call _tierLerp;
        private _f4 = [_k,0.58,0.67,0.72,0.77] call _tierLerp;

        // Displacement amplitudes reduced by 25% at every tier; timing and other visual layers are unchanged.
        // Bias ketamine toward horizontal visual drift with a smaller vertical component. This feels less like
        // generic underwater bobbing and more like altered lateral swimming/perceptual slippage.
        private _a1 = [_k,0.0000,0.004950,0.006075,0.007350] call _tierLerp;
        private _a2 = [_k,0.0000,0.003675,0.004575,0.005400] call _tierLerp;
        private _a3 = [_k,0.0000,0.003075,0.003825,0.004650] call _tierLerp;
        private _a4 = [_k,0.0000,0.002250,0.002850,0.003450] call _tierLerp;
        private _phase1 = [_k,0.40,0.46,0.50,0.54] call _tierLerp;
        private _phase2 = [_k,0.24,0.27,0.30,0.33] call _tierLerp;
        private _tail1 = [_k,9.0,9.4,9.7,10.0] call _tierLerp;
        private _tail2 = [_k,5.3,5.5,5.7,5.9] call _tierLerp;

        private _profile = [1,1,1,_f1,_f2,_f3,_f4,_a1,_a2,_a3,_a4,_phase1,_phase2,_tail1,_tail2];
        _ketWetDebugHandle ppEffectAdjust _profile;
        _ketWetDebugHandle ppEffectCommit 0;
        _ketWetDebugHandle ppEffectEnable true;
        uiNamespace setVariable ["ACME_VFX_KetWetDebugLast",[_k]];
    };
};

// Slight motion-lag / trailing approximation for mild-to-moderate ketamine. RadialBlur is video-setting
// dependent, so this is a supplemental cue only; blur, waves, chromatic separation, and color shift remain present
// when the player's Radial Blur option is disabled. Peak this around Moderate rather than making Severe smeary.
if (_ketMotion >= 0) then {
    private _motionSource = _ketWetSmooth;
    private _motionI = if (_motionSource <= 0.68) then {
        linearConversion [0.03,0.68,_motionSource,0,1,true]
    } else {
        linearConversion [0.68,1,_motionSource,1,0.62,true]
    };
    if (_motionI <= 0.005 || {!_enabled} || {!alive _u}) then {
        _ketMotion ppEffectAdjust [0,0,0.10,0.10];
        _ketMotion ppEffectCommit 0.35;
        _ketMotion ppEffectEnable false;
    } else {
        private _p = 0.00035 + (0.00125 * _motionI);
        private _center = 0.115 + (0.025 * _motionI);
        _ketMotion ppEffectAdjust [_p,_p * 0.92,_center,_center];
        _ketMotion ppEffectEnable true;
        _ketMotion ppEffectCommit 0.22;
    };
};

// Moderate/Severe ketamine get a slow zoom-like optical push. This deliberately stays subtle; its job is to make
// the scene feel as if it is gradually closing in, not to create another tunnel-vision effect.
if (_ketZoom >= 0) then {
    private _realZoomTier = if (_ketWetReal >= 0.78) then {3} else {if (_ketWetReal >= 0.45) then {2} else {0}};
    private _zoomTier = _dbgKet max _realZoomTier;
    if (_zoomTier < 2 || {!_enabled} || {!alive _u}) then {
        _ketZoom ppEffectEnable false;
        uiNamespace setVariable ["ACME_VFX_KetZoomLast",-1];
    } else {
        _ketZoom ppEffectEnable true;
        private _lastKetZoomTier = uiNamespace getVariable ["ACME_VFX_KetZoomLast",-1];
        if (_forceAll || {_lastKetZoomTier != _zoomTier}) then {
            private _zoomProfile = if (_zoomTier >= 3) then {
                [0.0050,0.0050,0.125,0.125]
            } else {
                [0.0030,0.0030,0.155,0.155]
            };
            _ketZoom ppEffectAdjust _zoomProfile;
            _ketZoom ppEffectCommit (if (_zoomTier >= 3) then {5.5} else {6.5});
            uiNamespace setVariable ["ACME_VFX_KetZoomLast",_zoomTier];
        };
        _ketZoom ppEffectEnable true;
    };
};

// HR-synchronous ACM-style radial tunnel. The geometry remains recognizable as ACM's low-oxygen tunnel but the
// pulse cadence follows actual HR so shock/hypoxia is visibly different from the fixed pneumothorax cadence.
if (_tunnel >= 0) then {
    if (_tunnelI <= 0.001) then {
        _tunnel ppEffectEnable false;
        uiNamespace setVariable ["ACME_VFX_TunnelLast",[]];
        uiNamespace setVariable ["ACME_VFX_HeartPhase",0];
        uiNamespace setVariable ["ACME_VFX_HeartPhaseAt",diag_tickTime];
    } else {
        _tunnel ppEffectEnable true;
        private _hr = _u getVariable ["ace_medical_heartRate",80];
        if (!(_hr isEqualType 0) || {!finite _hr}) then {_hr = 80;};
        _hr = (_hr max 25) min 240;
        private _rr = 60 / _hr;
        private _lastPulseAt = uiNamespace getVariable ["ACME_VFX_HeartPhaseAt",diag_tickTime];
        private _pulseDt = ((diag_tickTime - _lastPulseAt) max 0) min 0.25;
        private _heartPhase = uiNamespace getVariable ["ACME_VFX_HeartPhase",0];
        _heartPhase = (_heartPhase + (_pulseDt / (_rr max 0.10))) mod 1;
        uiNamespace setVariable ["ACME_VFX_HeartPhase",_heartPhase];
        uiNamespace setVariable ["ACME_VFX_HeartPhaseAt",diag_tickTime];

        // Sharper systolic accent: fast attack, short decay, long quiet diastolic interval. Keep it subtle so the
        // vignette reads as pulse-synchronous perfusion rather than visibly pumping the whole screen.
        private _beatPulse = if (_heartPhase < 0.035) then {
            _heartPhase / 0.035
        } else {
            if (_heartPhase < 0.225) then {1 - ((_heartPhase - 0.035) / 0.190)} else {0}
        };
        private _pulseI = (_tunnelI * (0.93 + (0.07 * _beatPulse))) min 1;
        private _tv = 0.6 * _pulseI;
        private _blendA = _pulseI * (0.992 + (0.008 * _beatPulse));
        private _tone = 0.066 - (0.018 * _beatPulse);
        private _radA = (0.85 - (0.022 * _beatPulse)) - _tv;
        private _radB = (0.80 - (0.022 * _beatPulse)) - _tv;
        private _adjust = [1,1,0,[0,0,0,_blendA],[_tone,_tone,_tone,_tone],[0,0,0,0],[_radA,_radB,0,0,0,0,8]];

        private _last = uiNamespace getVariable ["ACME_VFX_TunnelLast",[]];
        private _signature = [round (_tunnelI*100),round (_beatPulse*100),round _hr];
        if (_forceAll || {!(_last isEqualTo _signature)}) then {
            _tunnel ppEffectAdjust _adjust;
            _tunnel ppEffectCommit 0.02;
            uiNamespace setVariable ["ACME_VFX_TunnelLast",_signature];
        };
    };
};

if (_chrom >= 0) then {
    if (_chromV <= 0.000008) then {_chrom ppEffectEnable false;} else {
        _chrom ppEffectEnable true;
        _chrom ppEffectAdjust [_chromX,_chromY,true];
        // Follow the authored pulse/vibration waveform directly. A long commit here would smear the short tail and
        // restarting that interpolation every 20 Hz tick would reintroduce visual stepping.
        _chrom ppEffectCommit 0.04;
    };
};
if (_blur >= 0) then {
    if (_blurV <= 0.01) then {_blur ppEffectEnable false;} else {
        _blur ppEffectEnable true;
        _blur ppEffectAdjust [_blurV];
        _blur ppEffectCommit _commit;
    };
};
if (_color >= 0) then {
    private _colorActive = _dark > 0.005 || {_sat < 0.995} || {_ketVivid > 0.005};
    if (!_colorActive) then {_color ppEffectEnable false;} else {
        _color ppEffectEnable true;
        private _ketContrast = 0.022 * _ketVivid;
        private _ketBright = 0.008 * _ketVivid;
        private _vR = 1 + (0.018 * _ketVivid);
        private _vG = 1 + (0.012 * _ketVivid);
        private _vB = 1 + (0.024 * _ketVivid);
        _color ppEffectAdjust [1-_dark+_ketBright,1+(_syn*0.08)+_ketContrast,0,[0,0,0,0],[_vR,_vG,_vB,_sat],[0.299,0.587,0.114,0],[-1,-1,0,0,0,0,0]];
        _color ppEffectCommit _commit;
    };
};
