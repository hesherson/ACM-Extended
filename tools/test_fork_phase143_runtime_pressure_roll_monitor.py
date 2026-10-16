#!/usr/bin/env python3
"""Phase 143 runtime regression guards, updated for current DP pose ownership."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def txt(p): return (ROOT/p).read_text(encoding="utf-8",errors="replace")
def test_syringe_duration_layout_is_local():
    for name,p in [("carousel","addons/acm_extended/functions/fn_skCarouselRender.sqf"),("dynamic layout","addons/acm_extended/functions/fn_skDynamicLayout.sqf")]:
        body=txt(p); assert 'private _duration = 0;' in body, name; assert 'params [["_duration"' not in body, name
def test_direct_pressure_uses_shared_pose_controller_and_two_second_resume():
    pose=txt("addons/acm_extended/functions/fn_directPressurePose.sqf"); stop=txt("addons/acm_extended/functions/fn_directPressureStop.sqf")
    for p in ("addons/acm_extended/functions/fn_directPressureLimb.sqf","addons/acm_extended/functions/fn_directPressureTorso.sqf"):
        body=txt(p)
        assert 'setVariable ["ACME_DP_InPose", false]' in body
        assert 'setVariable ["ACME_DP_IdleStart", CBA_missionTime - 2]' in body
        assert 'call ACME_fnc_directPressurePose;' in body
    assert 'missionNamespace getVariable ["ACME_DP_idleToPose", 2]' in pose
    assert 'toLower animationState _medic' in pose and '"ACME_DirectPressureHold"' in pose
    assert 'ACME_DP_LastPoseAssert' in pose and 'ACME_DP_LastPoseAssert' in stop
def test_direct_pressure_menu_order_stays_explicit():
    menu=txt("addons/gui/overrides/fnc_updateActions.sqf")
    assert "'acme_stopdirectpressure'" in menu
    assert '_menuActions = _manualCarrier + _bvmEmma + _stopPressure + _pressure + _menuActions + _dogTags;' in menu
def test_roll_and_chest_seal_body_map_contracts():
    roll=txt("addons/acm_extended/functions/fn_chestSealRoll.sqf")
    assert 'call ACME_fnc_patientAnimRequest' in roll
    assert 'if (_leaseToken == "") exitWith' in roll
    assert '[_p, _trans, 2] call ACME_fnc_doAnim;' in roll
    assert 'ACME_patientAnimLock' in roll
    assert 'ACME_CS_rollToken' in roll and '0.15] call CBA_fnc_waitAndExecute' in roll
    body=txt("addons/gui/functions/fnc_updateBodyImage.sqf")
    assert 'ACME_CS_holeData' in body and '(_x select 4) isEqualTo true' in body
    assert 'ChestSeal_State' in body and '_hasDetailedSeal' in body
def test_monitor_and_pea_electrical_rate_contracts():
    ekg=txt("addons/circulation/functions/fnc_displayAEDMonitor_generateEKG.sqf"); custom=txt("addons/acm_extended/functions/fn_genRhythmEKG.sqf")
    handle=txt("addons/circulation/functions/fnc_handleAED.sqf"); monitor=txt("addons/circulation/functions/fnc_displayAEDMonitor.sqf")
    gethr=txt("addons/circulation/functions/fnc_getEKGHeartRate.sqf")
    assert '_rhythm = _lastShown;' not in ekg
    assert '[_target] call ACM_circulation_fnc_getEKGHeartRate' in ekg
    assert '[_tgtForRate] call ACM_circulation_fnc_getEKGHeartRate' in custom
    assert '_lastSync + 5.25 < CBA_missionTime' in handle and '_roundedEKG != _shownEKG' not in handle
    assert 'private _ekgHR = [_patient] call FUNC(getEKGHeartRate)' in monitor
    assert 'round _ekgHR) > 10' in monitor and 'QGVAR(AED_Monitor_HR), _ekgHR' in monitor
    assert 'ACME_rhythm_targetHR' in gethr and 'if (_effective >= 100)' in gethr and 'setVariable' not in gethr
    update=txt("addons/circulation/functions/fnc_updateEKGHeartRate.sqf")
    assert 'case ACM_Rhythm_VF' in update and 'round (100 + random 120)' in update
    assert 'case ACM_Rhythm_PEA' in update and 'max 60) min 100' in update
    assert 'private _beatOrdinal' in ekg and 'private _amp = 0.84 +' in ekg and 'ACME_AED_PreviousRR' in ekg and 'ACME_AED_NextRR' in ekg
    cfg=txt("addons/acm_extended/functions/fn_initRhythmHemodynamicsConfig.sqf")
    assert 'ACME_peaBradyChance        = 0;' in cfg and 'ACME_peaNormalMinHR        = 60;' in cfg and 'ACME_peaNormalMaxHR        = 100;' in cfg and 'ACME_peaVariationHz        = 4;' in cfg
    for p in ("addons/circulation/functions/fnc_handleReversibleCardiacArrest.sqf","addons/circulation/functions/fnc_handleCardiacArrest.sqf","addons/acm_extended/functions/fn_rhythmSet.sqf"):
        assert 'ACME_peaElectricalHR' in txt(p)
