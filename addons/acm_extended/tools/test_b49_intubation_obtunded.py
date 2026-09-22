from historical_source import read_source
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8-sig', errors='ignore')


def test_version_batch():
    assert 'version = "1.0.100-r13";' in txt('config.cpp')
    p = txt('functions/fn_postInit.sqf')
    assert 'ACME_buildBatch = "B49";' in p
    assert 'ACME_infusion_version = "1.0.100-r13"' in p


def test_replacement_ten_ml_barrel_is_used_in_both_views():
    c = txt('config.cpp')
    d = txt('functions/fn_skOpenDraw.sqf')
    asset = ROOT / 'ui/syringe/syringe_flush_10_barrel_ca.paa'
    assert asset.is_file() and asset.stat().st_size > 0
    assert 'idc = 87818;' in c
    assert r'text = "\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa";' in c
    assert 'displayCtrl 84012' in d
    assert r'ctrlSetText "\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa"' in d


def test_cuff_syringe_tip_anchor_target_and_one_second_push():
    c = txt('functions/fn_laryngoCuff.sqf')
    p = txt('functions/fn_postInit.sqf')
    assert 'ACME_laryngo_cuffPilotUV = [0.5164, 0.4112]' in p
    assert 'ACME_laryngo_syrTipUV = [0.50, 0.370]' in p
    assert 'ACME_laryngo_cuffRunTime = 1.0' in p
    assert '_pX - (_stU * _sw)' in c and '_pY - (_stV * _sh)' in c
    assert '_plTravel * (1 - _amtVis)' in c
    assert '["ACME_laryngo_cuffRunTime", 1.0]' in c


def test_syringe_stows_when_other_laryngoscopy_tool_selected():
    g = txt('functions/fn_laryngoGrab.sqf')
    t = txt('functions/fn_laryngoTick.sqf')
    assert 'case "syringe"' in g
    assert '[87814,87817,87818]' in g
    assert '== "syringe") then' in t
    assert '[87814,87817,87818]' in t


def test_tongue_is_real_adjacent_frame_crossfade():
    f = txt('functions/fn_laryngoFrames.sqf')
    tick = txt('functions/fn_laryngoTick.sqf')
    assert 'private _frames = [87801, 87851, 87852, 87853];' in f
    assert 'private _blend = _f * _f * (3 - (2 * _f));' in f
    assert 'case (_forEachIndex == _i): {1 - _blend};' in f
    assert 'case (_forEachIndex == (_i + 1)): {_blend};' in f
    assert 'ACME_fnc_laryngoFrames' in tick


def test_ett_seats_deeper_for_most_patients():
    i = txt('functions/fn_laryngoInit.sqf')
    t = txt('functions/fn_laryngoTick.sqf')
    p = txt('functions/fn_postInit.sqf')
    assert 'ACME_ETT_MinSeatFrame = 5' in p
    assert '((_ideal - 1) max (missionNamespace getVariable ["ACME_ETT_MinSeatFrame", 5])) min _ideal' in i
    assert 'ACME_laryngo_requiredSeatFrame' in i
    assert t.count('ACME_laryngo_requiredSeatFrame') >= 3


def test_established_airway_does_not_disclose_patency():
    f = txt('functions/fn_airwayInjuryRelabel.sqf')
    assert 'private _suffix = "";' in f
    executable = '\n'.join(line for line in f.splitlines() if not line.lstrip().startswith('//'))
    assert 'airway is patent' not in executable.lower()


def test_obtunded_no_longer_owns_body_posture():
    s = txt('functions/fn_obtundedSet.sqf')
    a = txt('functions/fn_obtundedApply.sqf')
    tr = txt('functions/fn_obtundedTransition.sqf')
    lock = txt('functions/fn_obtundedInputLock.sqf')
    auto = txt('functions/fn_obtundedAuto.sqf')
    assert 'private _newPos = if (_on) then {"free"}' in s
    assert 'ACME_obtunded_forcedBack", false' in s
    for source in (s, a, tr):
        active = '\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('//'))
        assert 'forceRagdoll' not in active
        assert 'setUnitPos "DOWN"' not in active
    assert 'displayAddEventHandler' not in lock
    assert 'private _posture = "free";' in auto


def test_obtunded_get_up_is_slow_not_blocked():
    g = txt('overrides/fn_getUp.sqf')
    cfg = txt('config.cpp')
    p = txt('functions/fn_postInit.sqf')
    assert 'too obtunded to get up' not in g.lower()
    assert 'ACME_obtunded_getUpTime = 5.5' in p
    assert 'ACME_obtunded_getUpTime' in g
    assert 'setAnimSpeedCoef _coef' in g
    assert "!(_player getVariable ['ACME_obtunded', false])" not in cfg


def test_obtunded_visuals_match_severe_pain_scale_and_debug_uses_them():
    t = txt('functions/fn_obtundedTick.sqf')
    p = txt('functions/fn_postInit.sqf')
    v = txt('functions/fn_obtundedVoice.sqf')
    assert 'ppEffectCreate ["DynamicBlur", 816]' in t
    assert 'ppEffectCreate ["ColorCorrections", 13510]' in t
    assert 'ACME_obtunded_blurWaveMax = 1.00' in p
    assert 'ACME_obtunded_blurWaveMin = 0.12' in p
    assert 'ACME_obtunded_vignetteMin' in t and 'ACME_obtunded_vignetteMax' in t
    assert '[0,0,0,_blackAlpha]' in t and '[_vIn,_vOut,0,0,0,0,1]' in t
    assert '_systemOn || _manual' in t
    assert 'ACME_obtunded_manual' in v


def test_sprint_attempt_is_only_new_obtunded_drop_path():
    t = txt('functions/fn_obtundedTick.sqf')
    p = txt('functions/fn_postInit.sqf')
    assert 'inputAction "Turbo"' in t
    assert 'ACME_obtunded_sprintFallChance = 0.35' in p
    assert 'setUnconscious true' in t
    assert 'ACE_isUnconscious", true' not in t


def test_debug_obtunded_is_same_free_state():
    a = txt('functions/fn_setObtunded.sqf')
    b = txt('functions/fn_debugObtundedBack.sqf')
    z = txt('functions/fn_zeusInduceObtundation.sqf')
    for s in (a, b, z):
        assert '"free"' in s
    assert 'true, "free"' in a or 'true, "free"' in b or 'true, "free"' in z
