"""B57 static contracts for the requested animation/menu/reset/Narc Box changes.
Static only: Arma runtime validation is still required for RTM timing/camera behavior."""
from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
def txt(rel): return read_source(ROOT / rel, encoding="utf-8")

def _if_not_precedence_traps(source):
    hits=[]
    for m in re.finditer(r"\bif\s*!\s*\(", source):
        i=m.end()-1; depth=0
        while i < len(source):
            c=source[i]
            if c == "(": depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0: break
            i += 1
        rest=source[i+1:i+8].lstrip()
        if rest.startswith("&&") or rest.startswith("||"):
            hits.append(source[:m.start()].count("\n")+1)
    return hits

def test_version_is_r21_b57():
    assert_release_identity()
    post=txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_no_if_not_precedence_trap_anywhere():
    for folder in ('functions','overrides'):
        for p in (ROOT/folder).glob('*.sqf'):
            src=read_source(p, encoding='utf-8', errors='replace')
            code='\n'.join(l for l in src.splitlines() if not l.lstrip().startswith(('*','//','/*')))
            assert not _if_not_precedence_traps(code), p.name

def test_exact_freeze_rules_retained():
    from test_historical_pose_lifecycle import test_owner_freeze_uses_current_mode_timeline_despite_frame_overshoot
    # Pulse now shares the approved stethoscope sample; do not restore its retired 0.691 value.
    for mode,hold in [('roll',2.2),('chestAccess',2.2),('inspect',2.2),('pulse',.421),('stethoscope',.421)]:
        test_owner_freeze_uses_current_mode_timeline_despite_frame_overshoot(mode,hold,12)
    assert '["roll", 0.25]' in txt('functions/fn_postInit.sqf')

def test_owner_freezes_locally_and_sync_does_not_restart_owner():
    from test_historical_pose_lifecycle import test_hold_receiver_owner_does_not_seek_and_observer_seeks_before_freezing, test_duplicate_hold_reuses_one_observer_worker_and_release_is_idempotent
    for local,server,client in [(True,False,7),(False,False,8),(False,True,2)]:
        test_hold_receiver_owner_does_not_seek_and_observer_seeks_before_freezing(local,server,client)
    test_duplicate_hold_reuses_one_observer_worker_and_release_is_idempotent()

def test_menu_open_is_only_empty_hands_and_crouch_transition():
    start=txt('functions/fn_menuPoseStart.sqf')
    assert 'selectWeapon ""' in start
    assert 'setUnitPos "MIDDLE"' in start
    assert 'AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon' in start
    code='\n'.join(line for line in start.splitlines() if not line.lstrip().startswith(('*','//','/*')))
    for forbidden in ('UnconsciousMedicFromUnarmedKneel','UnconsciousReviveMedic_B','switchMove [','addPerFrameHandler','ACME_menuPoseFallback'):
        assert forbidden not in code
    stop=txt('functions/fn_menuPoseStop.sqf')
    assert 'setUnitPos "AUTO"' in stop
    assert 'AmovPercMstpSnonWnonDnon' not in stop

def test_roll_inspect_pulse_cannot_exit_standing():
    stop=txt('functions/fn_treatmentPoseStop.sqf')
    assert '_currentMode in ["roll","inspect","pulse"]' in stop
    assert 'setUnitPos (["MIDDLE", "UP"] select _exitUpright)' in stop
    assert 'if (stance _unit == "STAND") then {' in stop
    assert 'AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon' in stop

def test_exact_roll_inspect_pulse_states_are_never_replaced_by_medicup():
    from test_historical_pose_lifecycle import test_selected_assessment_states_are_crouch_authored_not_standing_substitutes
    for mode,main in [('roll','AinvPknlMstpSnonWnonDnon_medic4'),('inspect','ACME_ChestInspectWork'),('pulse','ACME_StethoscopeWork')]:
        test_selected_assessment_states_are_crouch_authored_not_standing_substitutes(mode,main)

def test_release_has_no_pose_rpt_diagnostic():
    pose=txt('functions/fn_poseUprightState.sqf')
    assert '[ACME POSE]' not in pose
    assert 'diag_log' not in pose

def test_flip_diagram_is_locked_to_one_requested_endpoint():
    from test_historical_chest_workspace import test_procedural_canvas_retains_selected_endpoint_without_geometry_reclassification
    for side,target,expiry,expected in (
        ('front','back',11,'back'),('back','front',11,'front'),
        ('back','back',11,'back'),('front','back',10,'front'),
        ('back','front',9,'back'),('back','invalid',11,'back')):
        test_procedural_canvas_retains_selected_endpoint_without_geometry_reclassification(side,target,expiry,expected)

def test_pulse_escape_is_consumed_on_main_display():
    p=txt('overrides/fn_feelPulse.sqf')
    assert 'findDisplay 46' in p
    assert 'displayAddEventHandler ["KeyDown"' in p
    assert 'if (_key != 1' in p
    assert 'ACME_PulseCheckEscape' in p
    assert 'true\n    }];' in p
    assert 'displayRemoveEventHandler ["KeyDown", _escEH]' in p
    assert '[_patient,"examine"] call ACME_fnc_reopenMedicalMenu' in p

def test_hard_reset_scrubs_only_full_heal_and_new_life_not_corpses():
    clear=txt('functions/fn_clearAllAilments.sqf')
    assert 'private _preserveDeathInterventions = false' in clear
    assert 'ACME_IV_Marks' in clear and 'ACME_EJTransfusionSite' in clear
    for key in ('incision','incisionScore','prep','infection','open','ribTarget','site','tube','sealed'):
        assert f'"{key}"' in clear

    life=txt('functions/fn_registerClinicalLifecycleRuntime.sqf')
    resp=txt('functions/fn_registerRhythmLifecycleRuntime.sqf')
    death=txt('functions/fn_deathFreeze.sqf')
    assert 'addMissionEventHandler ["EntityKilled"' in life
    assert '[_unit] call ACME_fnc_deathFreeze' in life
    assert '["ace_medical_FullHeal", {_this call ACME_fnc_clearAllAilments}]' in life
    assert 'addMissionEventHandler ["EntityRespawned"' in resp
    assert '[_oldUnit] call ACME_fnc_deathFreeze' in resp
    assert '[_newUnit] call ACME_fnc_clearAllAilments' in resp
    assert 'forEach [_oldUnit, _newUnit]' not in resp
    assert '[_patient, "begin", true] call ACME_fnc_clinicalReset' in death
    assert 'ACME_fnc_clearAllAilments' not in death

def test_obsolete_medication_background_diagnostic_is_removed():
    assert not (ROOT/'functions/fn_medicationDiagTick.sqf').exists()
    assert 'medicationDiagTick' not in txt('config.cpp')
    assert 'medicationDiagTick' not in txt('functions/fn_skUiTick.sqf')

def test_final_syringe_name_is_25_char_unicode_metadata():
    # Final-name UI is retired. Three 25-character tag lines carry clinical metadata.
    from test_bounded_tag_contracts import test_retired_final_name_shim_does_not_change_prepared_metadata, test_three_line_roundtrip_preserves_case_payload_identity_and_other_syringes
    test_retired_final_name_shim_does_not_change_prepared_metadata()
    test_three_line_roundtrip_preserves_case_payload_identity_and_other_syringes(26, True)

def test_narcbox_cohesive_section_and_selection_fix_retained():
    r=txt('functions/fn_skListRefresh.sqf')
    assert '[84006,84303,"medication"]' in r
    assert '"ACME_SK_Backdrop"' in r
    assert '_backdrop ctrlSetBackgroundColor [0,0,0,0.55];' in r
    assert '"RobotoCondensedBold"' in r
    assert 'private _indent = safeZoneW / 240;' in r
    assert '_list ctrlShow (_kind == "medication")' not in r

def test_auscultate_indent_and_dogtag_handoff_retained():
    s=txt('overrides/fn_updateActions.sqf')
    assert 'private _wasChild = _nestEnabled' in s
    assert '_paintName = if (_wasChild) then {' in s
    cfg=txt('config.cpp')
    assert 'fn_showDogtag.sqf' not in cfg
    assert 'class dogtagMenuTick' not in cfg
