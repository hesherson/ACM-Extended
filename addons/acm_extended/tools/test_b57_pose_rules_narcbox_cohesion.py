"""B57 static contracts for the requested animation/menu/reset/Narc Box changes.
Static only: Arma runtime validation is still required for RTM timing/camera behavior."""
from historical_source import read_source
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
    assert 'version = "1.0.100-r21";' in txt('config.cpp')
    post=txt('functions/fn_postInit.sqf')
    assert 'ACME_infusion_version = "1.0.100-r21"' in post
    assert 'ACME_buildBatch = "B57";' in post

def test_no_if_not_precedence_trap_anywhere():
    for folder in ('functions','overrides'):
        for p in (ROOT/folder).glob('*.sqf'):
            src=read_source(p, encoding='utf-8', errors='replace')
            code='\n'.join(l for l in src.splitlines() if not l.lstrip().startswith(('*','//','/*')))
            assert not _if_not_precedence_traps(code), p.name

def test_exact_freeze_rules_retained():
    post=txt('functions/fn_postInit.sqf')
    block=post[post.index('ACME_poseHoldAt = createHashMapFromArray ['):]
    block=block[:block.index('];')+2]
    for token in ('["roll", 2.2]','["inspect", 2.2]','["pulse", 0.691]','["stethoscope", 0.421]'):
        assert token in block
    assert '["roll", 0.25]' in post[post.index('ACME_poseStopAfterHold = createHashMapFromArray ['):]

def test_owner_freezes_locally_and_sync_does_not_restart_owner():
    start=txt('functions/fn_treatmentPoseStart.sqf')
    assert 'if (_phase >= 0) then {_medic switchMove [_main, _phase, 1, false];};\n            _medic setAnimSpeedCoef 0;' in start
    assert 'private _elapsed = _now - _stageStarted;' in start
    sync=txt('functions/fn_treatmentPoseSync.sqf')
    assert '_operation == "hold" && {local _medic} && {owner _medic == _owner}' in sync
    assert 'same switchMove through the global event can look like a one-frame animation restart' in sync

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
    start=txt('functions/fn_treatmentPoseStart.sqf')
    assert 'if !(_mode in ["roll", "inspect", "pulse"]) then {' in start
    assert 'case "roll": {"AinvPknlMstpSnonWnonDnon_medic4"};' in start
    assert 'case "inspect": {"AinvPknlMstpSnonWnonDnon_medic4"};' in start
    assert 'case "pulse": {"AinvPknlMstpSnonWrflDnon_medic1"};' in start

def test_release_has_no_pose_rpt_diagnostic():
    pose=txt('functions/fn_poseUprightState.sqf')
    assert '[ACME POSE]' not in pose
    assert 'diag_log' not in pose

def test_flip_diagram_is_locked_to_one_requested_endpoint():
    flip=txt('functions/fn_chestSealFlip.sqf')
    tick=txt('functions/fn_chestSealTick.sqf')
    assert 'ACME_CS_FlipTarget' in flip
    assert 'ACME_CS_FlipLockedUntil' in flip
    guard=flip.index('if (!_willAnimate) exitWith')
    target=flip.index('uiNamespace setVariable ["ACME_CS_Side", _newSide]')
    assert guard < target
    assert 'uiNamespace setVariable ["ACME_CS_Side", _actualSide]' in flip[guard:target]
    assert 'if (_flipLocked) then {' in tick
    assert 'uiNamespace setVariable ["ACME_CS_Side", _flipTarget]' in tick
    assert 'call ACME_fnc_chestSealActualSide' in tick[tick.index('} else {'):]

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
    cfg=txt('config.cpp')
    assert 'class ACME_SK_NameEdit: RscEdit' in cfg
    assert 'maxChars = 25;' in cfg
    assert 'class skFinalName {};' in cfg
    fn=txt('functions/fn_skFinalName.sqf')
    assert 'ctrlText _ctrl' in fn
    assert '_name select [0, 25]' in fn
    for bad in ('toLowerANSI','toUpperANSI','regex','splitString'):
        assert bad not in fn
    inject=txt('functions/fn_skInject.sqf')
    assert 'Final Syringe Name (25 max)' in inject
    assert 'ctrlCreate ["ACME_SK_NameEdit", 84161]' in inject
    for rel in ('overrides/fn_syringeDrawButton.sqf','functions/fn_skWasteDraw.sqf','functions/fn_skCompoundCommit.sqf','functions/fn_epinephrineDrawCardiac.sqf','functions/fn_epinephrinePrepare.sqf'):
        assert 'customName' in txt(rel), rel

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
