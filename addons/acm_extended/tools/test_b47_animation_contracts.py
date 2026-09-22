from historical_source import read_source
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
def txt(rel): return read_source(ROOT / rel, errors='ignore')

def block(src, name):
    m = re.search(r'class\s+' + re.escape(name) + r'\b[^\{]*\{', src)
    assert m, name
    i = m.end(); depth = 1
    while i < len(src) and depth:
        if src[i] == '{': depth += 1
        elif src[i] == '}': depth -= 1
        i += 1
    return src[m.start():i]

def test_version_batch():
    assert 'version = "1.0.100-r11"' in txt('config.cpp')
    assert 'ACME_buildBatch = "B47"' in txt('functions/fn_postInit.sqf')

def test_exact_requested_motion_wrappers():
    c = txt('config.cpp')
    assert 'class ACME_RollProviderWork: AinvPknlMstpSnonWrflDnon_medic4' in c
    assert 'class ACME_ChestInspectWork: AinvPknlMstpSnonWrflDnon_medic4' in c
    assert 'class ACME_ResponseCheckWork: AinvPknlMstpSnonWrflDr_medic3_old' in c
    assert 'class ACME_AirwayCheckWork: AinvPknlMstpSnonWrflDr_medic4_old' in c
    for n in ['ACME_RollProviderWork','ACME_ChestInspectWork','ACME_ResponseCheckWork','ACME_AirwayCheckWork']:
        b = block(c,n)
        assert 'disableWeapons = 1' in b and 'canPullTrigger = 0' in b
        assert 'AmovPknlMstpSnonWnonDnon' in b

def test_check_response_five_seconds_custom_pose():
    b = block(txt('config.cpp'),'CheckResponse')
    assert 'treatmentTime = 5;' in b
    assert "'response', 5" in b
    assert 'ace_medical_treatment_fnc_checkResponse' in b
    assert "'response'] call ACME_fnc_treatmentPoseStop" in b
    for k in ['animationMedic = ""','animationMedicProne = ""']:
        assert k in b

def test_check_airway_medic4_old_custom_pose():
    c = txt('config.cpp'); b = block(c,'CheckAirway')
    assert 'ACME_fnc_airwayMedicPose' in b
    assert 'ACM_airway_fnc_checkAirway' in b
    assert "'airway'] call ACME_fnc_treatmentPoseStop" in b
    f = txt('functions/fn_airwayMedicPose.sqf')
    assert 'checkairway' in f.lower() and '"airway", 2.5' in f

def test_inspect_chest_six_seconds():
    b = block(txt('config.cpp'),'ACME_InspectChest')
    assert 'treatmentTime = 6;' in b
    assert 'callbackStart = "_this call ACME_fnc_inspectChestPoseStart"' in b
    assert '[_medic, "inspect", 6, _patient]' in txt('functions/fn_inspectChestPoseStart.sqf')

def test_shared_pose_timing_and_clean_exit():
    s = txt('functions/fn_treatmentPoseStart.sqf')
    e = txt('functions/fn_treatmentPoseStop.sqf')
    for mode, anim in [('response','ACME_ResponseCheckWork'),('airway','ACME_AirwayCheckWork'),('roll','ACME_RollProviderWork'),('stethoscope','ACME_StethoscopeWork')]:
        assert f'case "{mode}": {{"{anim}"}}' in s
    assert 'ACME_fnc_medicAnimationPrep' in s
    assert 'ace_common_setAnimSpeedCoef' in s
    assert 'AmovPknlMstpSnonWnonDnon' in s and 'AmovPknlMstpSnonWnonDnon' in e
    assert 'selectWeapon ""' in e

def test_stethoscope_hold_is_minigame_owned():
    s = txt('functions/fn_treatmentPoseStart.sqf')
    y = txt('functions/fn_treatmentPoseSync.sqf')
    b = txt('functions/fn_beginStethoscopeAction.sqf')
    assert '0.421' in s
    assert 'case 3:' in s and 'reclaim' in s.lower()
    assert '["lost", "release"] select _hardRelease' in y
    assert 'treatmentPoseEpisode' not in '\n'.join(line for line in b.splitlines()[49:70] if not line.lstrip().startswith('//'))
    assert '[_medic, "stethoscope", _poseEpoch] call ACME_fnc_treatmentPoseStop' in b

def test_tsp_animate_rewrite_optional_sling_support():
    c = txt('config.cpp'); p = txt('functions/fn_medicAnimationPrep.sqf')
    assert 'class medicAnimationPrep {}' in c
    req = c.split('requiredAddons[] = {',1)[1].split('};',1)[0]
    assert 'tsp_animate' not in req
    for x in ['tsp_fnc_animate_sling','tsp_fnc_animate_sling_get','tsp_cba_animate_sling','tsp_slings']:
        assert x in p
    assert '[_medic, true] call tsp_fnc_animate_sling' in p
    assert 'selectWeapon ""' in p
    st = block(c,'UseStethoscope')
    assert 'ACME_fnc_medicAnimationPrep' in st

def test_roll_uses_shared_medic4_pose_for_2_5_seconds():
    r = txt('functions/fn_rollProviderStart.sqf')
    assert '["ACME_rollProviderDuration", 2.5]' in r
    assert '[_medic, "roll", _duration] call ACME_fnc_treatmentPoseStart' in r
    assert '[_unit, "roll", _epoch] call ACME_fnc_treatmentPoseStop' in r
    f = txt('functions/fn_chestSealFlip.sqf')
    assert 'ACME_fnc_rollProviderStart' in f

def test_specific_pose_wins_over_generic_roll():
    p = txt('functions/fn_postInit.sqf')
    assert 'private _poseOwned = (_medic getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []' in p
    assert 'private _isStethoscope = toLower _classname == "usestethoscope"' in p
    assert '{!_poseOwned} && {!_isStethoscope}' in p

def test_auscultate_indentation_normalized():
    s = txt('overrides/fn_updateActions.sqf')
    assert "if (_actionClass == 'usestethoscope')" in s
    assert "private _indent = missionNamespace getVariable ['ACME_menuChildIndent', '        ']" in s
    assert "format ['%1%2', _indent, _baseName]" in s
    assert "_baseName = 'Auscultate Chest'" in s
