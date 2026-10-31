from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8-sig', errors='ignore')

def test_visual_debug_is_client_local_and_spawn_clean():
    cyc = read('functions/fn_visualFxDebugCycle.sqf')
    tick = read('functions/fn_visualFxTick.sqf')
    post = read('functions/fn_registerVisualEffectsRuntime.sqf')
    assert 'call ACME_fnc_registerVisualEffectsRuntime;' in read('functions/fn_postInit.sqf')
    assert 'uiNamespace setVariable [_key,_next]' in cyc
    assert '_patient setVariable [_key' not in cyc
    assert 'ACME_VFX_PhysReadyAt",diag_tickTime + 5.0' in tick
    assert '_h ppEffectEnable false' in tick
    for kind in ('hypoxia','hypotension','hypercapnia','ketamine','syncope'):
        assert f'ACME_VFX_Debug_%1' in cyc or kind in cyc
    # Every active wet tick asserts the engine handle on; severity is not allowed to rely on a stale cache.
    assert '_wet ppEffectEnable true;' in tick
    assert 'ACME_VFX_KetWetDebug' in tick
    assert 'private _kNorm = (_k / _ketInduce) max 0;' in tick
    assert 'private _ketOnsetEnvelope = if (_ketGeneralTarget > 0.001) then {(_ketGeneralSmooth / _ketGeneralTarget) min 1} else {0};' in tick
    assert 'private _zeroKetProfile' in tick
    assert '_ketWetDebugHandle ppEffectCommit 0;' in tick
    assert 'private _f1 = [_k,1.24,1.42,1.50,1.58]' in tick
    assert 'private _a1 = [_k,0.0000,0.004950,0.006075,0.007350]' in tick
    assert 'private _a3 = [_k,0.0000,0.003075,0.003825,0.004650]' in tick
    assert 'private _shockWetDebug = [0,0.28,0.62,0.96]' in tick
    assert 'private _co2WetDebug = [0,0.20,0.48,0.78]' in tick
    assert 'private _dbgTunnel' in tick
    assert 'private _chromCycleSec = 5.2;' in tick
    assert 'private _chromVibe = 0;' in tick
    assert 'sin (_tailT * 360 * 4.6)' in tick
    assert '_chrom ppEffectAdjust [_chromX,_chromY,true];' in tick
    assert 'ACME_VFX_KetMotion' in tick
    assert 'private _ketChromReal = 0;' in tick
    assert '0.000050' in tick
    assert 'private _ketVivid' in tick
    assert 'private _motionSource = _ketWetSmooth;' in tick
    assert 'ACME_visualFx_ketamineAnalgesicWindowSec' in tick
    assert 'ACME_VFX_KetLastDoseAt' in tick
    assert 'ACM_core_ppAnestheticEffect_chrom' in tick
    assert '_acmKetChrom ppEffectEnable false;' in tick
    assert 'private _legacyChromEq = 0;' in tick
    assert '0.06 * _legacyEffect * _legacyScale' in tick
    assert 'private _ketAnalgesicEnvelope = 1;' in tick
    assert 'private _ketAnalgesicBlurEnvelope = 1;' in tick
    assert 'private _ketAnalgesicChromEnvelope = 1;' in tick
    assert '_ketAnalgesicBlurEnvelope = _waveShaped;' in tick
    assert 'private _wave01 = 0.5 - (0.5 * cos' in tick
    assert 'private _chromPulseGain = linearConversion [0,0.060,_ketChromRaw,0.080,0.018,true];' in tick
    assert 'ace_medical_treatment_medicationLocal' in post
    assert 'ACME_VFX_KetLastDoseAt' in post

def test_torsades_progressively_loses_mechanical_perfusion():
    tick = read('functions/fn_rhythmTick.sqf')
    pulse = read('functions/fn_pulsePerfusionProfile.sqf')
    rset = read('functions/fn_rhythmSet.sqf')
    assert 'ACME_rhythm_torsadesPerfusion", 1' in rset
    assert '_torsadesPerfusion = (1 - _progress) max 0 min 1' in tick
    assert 'ACME_rhythm_torsadesArrestRequestAt' in tick
    assert '(CBA_missionTime - _lastReq) >= 0.75' in tick
    assert '[["cardiacRhythmState", 3]]' in tick
    assert 'call ACM_circulation_fnc_handleCardiacArrest' in tick
    assert '_strength = _strength * ((_p ^ 1.35) max 0)' in pulse
    assert 'linearConversion [1,0,_p,0.04,0.98,true]' in pulse
    assert '_torsadesMature' in pulse
    assert '&& {!_torsadesMature}' in pulse

def test_mature_torsades_drives_aed_arrest_alarm():
    aed = read('../circulation/functions/fnc_handleAED.sqf')
    assert 'ACME_rhythm_torsadesNonPerfusing' in aed
    assert '_torsadesPulseless' in aed
    assert 'ACM_Rhythm_PVT]) || {_torsadesPulseless}' in aed
    assert '&& {!_torsadesPulselessPO}' in aed


def test_chrom_equivalent_is_single_owner_and_wet_profile_is_reduced():
    cfg = read('functions/fn_initVisualEffectsConfig.sqf')
    tick = read('functions/fn_visualFxTick.sqf')
    assert 'ACME_visualFx_ketamineLegacyChromEquivalentScale = 1.00;' in cfg
    assert '_acmKetChrom ppEffectEnable false;' in tick
    assert 'private _legacyFloor = _legacyPeak * 0.24;' in tick
    assert 'if (_legacyPhase < 0.14)' in tick
    # Preserve frequency and chromatic behavior while reducing water displacement.
    assert 'private _f1 = [_k,1.24,1.42,1.50,1.58]' in tick
    assert 'private _a1 = [_k,0.0000,0.004950,0.006075,0.007350]' in tick
    assert 'private _a3 = [_k,0.0000,0.003075,0.003825,0.004650]' in tick
