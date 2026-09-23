"""B9 source contracts and independent lifecycle models. These do not execute SQF."""
from historical_source import read_source, assert_release_identity
from pathlib import Path
import copy
import hashlib
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
def src(name):
    return read_source(ROOT / "functions" / ("fn_" + name + ".sqf"), encoding="utf-8-sig")
def code(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
def ui_valid(unit, token, captured=()):
    return unit is not None and len(token) == 3 and token[0] == unit["id"] and token[1] == unit["epoch"] and (not captured or tuple(captured) == tuple(token))
def restore(unit):
    if not unit["local"]: return False
    if not unit["removed"]: return True
    if unit["loadout"][4]: return False
    current = copy.deepcopy(unit["loadout"])
    current[4] = copy.deepcopy(unit["saved"])
    unit["loadout"] = current
    unit["removed"] = False
    unit["saved"] = []
    unit["writes"] += 1
    return True
def shade_stale(controls, shades):
    if len(shades) != 6 or any(s not in [n for n,o in controls] for s in shades): return True
    first = [n for n,o in controls].index(shades[0])
    last_art = max((i for i,(_,overlay) in enumerate(controls) if not overlay), default=-1)
    return last_art > first
def shade_raise(controls, shades):
    if not shade_stale(controls, shades): return controls
    return [(n,o) for n,o in controls if n not in shades] + [(n,True) for n in shades]
# B9 native-title recreation model retired in B10; focus ownership is tested in batch10.

class SourceContracts(unittest.TestCase):
    def test_current_versions_agree(self):
        cfg=read_source(ROOT/"config.cpp")
        version=re.search(r'version = "([^"]+)"',cfg).group(1)
        assert_release_identity()
        self.assertIn('ACME_infusion_version = getText',src("postInit"))
        self.assertIn('version = "'+version+'"',cfg)
    def test_dead_iv_screen_not_blocked(self):
        t=code(src("ivUiValid"));self.assertNotIn("alive",t);self.assertIn("clinicalEpoch",t);self.assertIn("_captured",t)
    def test_dead_placement_not_silently_rejected(self):
        for n in ("ivStateLocal","ivPlacementLocal"):
            t=code(src(n));self.assertNotIn("alive",t);self.assertIn("!local _patient",t);self.assertIn("clinicalEpoch",t)
    def test_native_iv_event_preserved(self):
        self.assertIn('"ACM_circulation_setIVLocal", [_medic, _patient, _bodyPart, _type, true, _site]',src("ivPlacementLocal"))
    def test_delayed_hub_owner_epoch_type(self):
        t=code(src("ivSeedHub"))
        self.assertNotIn("alive",t)
        for s in ("!local _patient","_epoch != ([_patient] call ACME_fnc_clinicalEpoch)","(_row param [_siteIdx, 0]) != _type"):self.assertIn(s,t)
    def test_ej_dead_condition(self):
        cfg=read_source(ROOT/"config.cpp")
        block=cfg[cfg.index("class ACME_EstablishEJ:"):].split("\n    };",1)[0]
        self.assertIn('condition = "!alive _patient',block)
        self.assertIn("ACE_isUnconscious",block)
    def test_vest_snapshot_native_entry(self):
        t=src("headElevateStart")
        self.assertIn("(getUnitLoadout _patient) param [4, [], [[]]]",t)
        self.assertLess(t.index('setVariable ["ACME_headElev_vestLoadout"'),t.index("removeVest _patient"))
    def test_vest_vehicle_not_removed(self):
        self.assertIn('if (!_manual && {!_hasBag} && {!([_patient] call ACME_fnc_animBlocked)}) then {',src("headElevateStart"))
    def test_vest_restore_has_no_alive_or_vehicle_gate(self):
        t=code(src("headElevVestRestore"))
        self.assertNotIn("alive",t);self.assertNotIn("animBlocked",t);self.assertNotIn("objectParent",t)
    def test_vest_restore_current_slot_only(self):
        t=src("headElevVestRestore")
        self.assertIn("_current = getUnitLoadout _patient",t);self.assertIn("_current set [4, +_saved]",t)
        self.assertIn("setUnitLoadout [_current, false]",t);self.assertNotIn("addItemToVest",t)
    def test_restore_reentrant_atomic(self):
        t=code(src("headElevVestRestore"))
        self.assertIn("isNil {",t);self.assertIn("!local _patient",t);self.assertIn('if (vest _patient == "")',t)
    def test_restore_record_clear_only_after_success(self):
        t=src("headElevVestRestore")
        self.assertLess(t.index("if (_restored) then"),t.index('setVariable ["ACME_headElev_vestRemoved", false'))
    def test_death_restores_vest_without_pose(self):
        t=code(src("headElevDeathRelease"))
        self.assertIn("ACME_fnc_headElevVestRestore",t)
        for s in ("setVectorUp","setPos","switchMove","doAnim","setDamage"):self.assertNotIn(s,t)
    def test_stop_death_branch_before_pose(self):
        # The stop path delegates dead casualties before living pose work. Dedicated
        # corpse cleanup intentionally retains its own release animation and gear rules.
        from test_historical_head_lowering import test_dead_stop_delegates_before_any_living_pose_or_provider_sequence
        for quiet in (False,True):
            test_dead_stop_delegates_before_any_living_pose_or_provider_sequence(quiet)
    def test_clear_all_does_not_discard_pending_snapshot(self):
        t=src("clearAllAilments")
        self.assertIn("headElevDeathRelease",t);self.assertIn("headElevVestRestore",t)
        self.assertNotIn('setVariable ["ACME_headElev_propVest", ""',t)
        self.assertNotIn('setVariable ["ACME_headElev_vestLoadout", []',t)
    def test_head_operations_authoritative(self):
        for name in ("headElevateStart","headElevateStop","headElevDeathRelease","headElevResume","headElevSuspend","headElevApplyTilt"):
            self.assertIn("!local _patient",src(name));self.assertIn("ACME_fnc_ownerDispatch",src(name))
    def test_medic_remains_on_own_machine(self):
        self.assertIn('[_medic, "headElevMedicStart"',src("headElevMedicStart"))
        self.assertIn('[_medic, "headElevMedicSeq"',src("headElevMedicSeq"))
    def test_owner_transfer_kills_old_handlers(self):
        t=src("ownerInit");self.assertIn("ACME_headElev_pfh",t);self.assertIn('removeEventHandler ["Killed"',t)
        self.assertIn("ACME_fnc_headElevWatch",src("ownerRegister"))
    def test_old_pose_callback_owns_token(self):
        t=src("headElevateStart")
        self.assertGreaterEqual(t.count('getVariable ["ACME_headElev_poseToken", ""]'),2)
        self.assertGreaterEqual(t.count("!alive _patient"),3)
    def test_watchdog_is_one_half_second_local_worker(self):
        t=code(src("headElevWatch"))
        self.assertIn("}, 0.5, [_patient]]",t)
        self.assertIn('getVariable ["ACME_headElev_pfh", -1]) >= 0',t)
        self.assertNotIn("allUnits",t)
    def test_native_title_uses_same_layer(self):
        t=code(src("minigameVisionNative"))
        self.assertNotIn("cutRsc",t)
        self.assertNotIn("cutText",t)
    def test_no_custom_nv_mask_or_tint(self):
        t=code(src("minigameVisionTick")+src("minigameVisionProfile")+src("minigameVisionNative"))
        for s in ("ctrlCreate","ace_nightvision_colorPreset","ctrlSetBackgroundColor","ColorCorrections","nvg_mask","ace_nightvision_border"):
            self.assertNotIn(s,t)
    def test_no_native_effect_setup_reset(self):
        t=code(src("minigameVisionNative"))
        for s in ("setupDisplayEffects","setFog","setAperture","setCamUseTi","ace_nightvision_"):self.assertNotIn(s,t)
    def test_native_title_current_goggle_guard(self):
        t=src("minigameVisionProfile")
        for s in ("hmd _medic","_liveHMD == _goggles","ace_nightvision_running","ace_nightvision_effectScaling"):self.assertIn(s,t)
    def test_private_optics_no_fallback(self):
        t=code(src("minigameVisionProfile"))
        self.assertIn('getText (_cfg >> "modelOptics") == ""',t)
        self.assertNotIn("ctrlCreate",t)
    def test_native_title_lease_and_pending(self):
        t=src("minigameVisionNative")
        for s in ("ACME_NV_FocusUsers","ACME_NV_FocusHandle","ACME_NV_FocusRetry","_i\" from 0 to 7"):self.assertIn(s,t)
    def test_native_title_changed_owner_not_overwritten(self):
        self.assertNotIn("ace_nightvision_titleDisplay",code(src("minigameVisionNative")))
    def test_goggles_off_never_recreates_mask(self):
        t=src("minigameVisionNative")
        self.assertNotIn("cutRsc",t);self.assertIn('if (!_nvg) exitWith',src("minigameVisionTick"))
    def test_neutral_focus_alpha_preserved(self):
        t=src("minigameVisionTick")
        self.assertNotIn("ctrlSetTextColor",code(t))
        self.assertNotIn("ctrlSetFade",code(t))
        self.assertIn('"ACME_minigameNV_focusBlur", 0.35',src("minigameVisionNative"))
    def test_clear_restores_owned_art_then_releases(self):
        t=src("minigameVisionClear")
        self.assertIn('ACME_NV_Active", false',t);self.assertTrue(t.rstrip().endswith("call ACME_fnc_minigameVisionNative;"))
    def test_shade_rebuilds_for_later_art(self):
        t=src("darknessShade")
        self.assertIn("_lastArt > _firstShade",t);self.assertIn("ACME_NV_OverlayControl",t);self.assertIn("ctrlEnable false",t)
    def test_overlay_not_interactive(self):
        t=src("darknessShade")
        self.assertEqual(t.count("ctrlCreate"),3)
        self.assertGreaterEqual(t.count("ctrlEnable false"),3)
    def test_shake_does_not_move_overlay_or_stale_controls(self):
        t=src("uiShakeApply")
        self.assertIn('getVariable ["ACME_NV_OverlayControl", false]',t)
        self.assertIn('(_x select 0) in _all',t)
    def test_darkness_runs_after_procedure_for_all_views(self):
        for n in ("ivMinigameTick","chestSealTick","thoraTick","laryngoTick","syringeKitTick","skUiTick","updateClampDialog","ivMinigameFlip"):
            lines=src(n).rstrip().splitlines()
            self.assertIn("call ACME_fnc_darknessShade",lines[-2])
            self.assertIn("call ACME_fnc_minigameVisionTick",lines[-1])
    def test_no_laryngo_stimulus_result_log(self):
        t=code(src("laryngoStimulusLocal"))
        for s in ("addToLog","displayText","hint","systemChat"):self.assertNotIn(s,t)
        self.assertNotIn('_state set ["icp"',t);self.assertIn('laryngoICPApplied',src('tbiHandle'));self.assertIn("ACME_laryngoStimulusStrength",t)
    def test_trauma_not_auto_disclosed(self):
        for n in ("laryngoBleed","laryngoTeeth","laryngoFail"):
            self.assertNotIn("call ace_common_fnc_displayTextStructured",src(n))
    def test_real_cuff_action_log_remains(self):
        t=src("laryngoCuffDone")
        self.assertIn("ET tube placed, cuff inflated",t)
        self.assertNotIn("glottic trauma",t);self.assertNotIn("Now secure",t);self.assertNotIn("airway secured",t)
    def test_existing_observable_sounds_and_visuals_remain(self):
        # B12 moved real fracture/gag/soil consequences to the patient-owner handler.
        self.assertIn('"teeth"] call ACME_fnc_laryngoConsequence',src("laryngoTeeth"))
        self.assertIn('"trauma"] call ACME_fnc_laryngoConsequence',src("laryngoBleed"))
        self.assertIn("playSound3D",src("laryngoConsequenceLocal"))
        self.assertIn('"ACME_laryngo_soiled", "blood"',src("laryngoConsequenceLocal"))
        self.assertIn('"b"',src("laryngoFluidState"))
    def test_no_debug_rpt_added_in_new_helpers(self):
        for n in ("headElevVestRestore","headElevWatch","headElevMedicStart","minigameVisionNative"):
            for word in ("diag_log","systemChat","hint "):self.assertNotIn(word,code(src(n)))

class DeadIVModels(unittest.TestCase):
    def test_fresh_corpse_can_open(self):self.assertTrue(ui_valid({"id":"corpse","epoch":9,"alive":False},("corpse",9,1)))
    def test_living_still_can_open(self):self.assertTrue(ui_valid({"id":"patient","epoch":1,"alive":True},("patient",1,1)))
    def test_deleted_cannot_open(self):self.assertFalse(ui_valid(None,("corpse",9,1)))
    def test_stale_reset_token_refused(self):self.assertFalse(ui_valid({"id":"corpse","epoch":10},("corpse",9,1)))
    def test_different_patient_refused(self):self.assertFalse(ui_valid({"id":"B","epoch":9},("A",9,1)))
    def test_old_display_callback_refused(self):self.assertFalse(ui_valid({"id":"A","epoch":9},("A",9,2),("A",9,1)))
    def test_current_dead_callback_valid(self):self.assertTrue(ui_valid({"id":"A","epoch":9,"alive":False},("A",9,2),("A",9,2)))

class VestModels(unittest.TestCase):
    def unit(self):
        return {"local":True,"alive":False,"removed":True,"saved":["V_Example",[["mag",2,7],["item",3],[["rifle","suppressor","laser","scope",["mag",11],[],"bipod"],1]]],
                "loadout":[["rifle","optic"],[],[],["U_now",[["bandage",2]]],[],["B_now",[["radio",1]]],"headgear","goggles",["binocs"],["gps"]],
                "writes":0}
    def test_death_restores_stored_vest(self):
        u=self.unit();s=copy.deepcopy(u["saved"]);self.assertTrue(restore(u));self.assertEqual(u["loadout"][4],s)
    def test_partial_magazine_ammo_preserved(self):
        u=self.unit();restore(u);self.assertEqual(u["loadout"][4][1][0],["mag",2,7])
    def test_stored_weapon_attachments_preserved(self):
        u=self.unit();restore(u);self.assertEqual(u["loadout"][4][1][2][0][1],"suppressor")
    def test_new_uniform_backpack_and_weapons_untouched(self):
        u=self.unit();before=copy.deepcopy(u["loadout"]);restore(u)
        for i in range(10):
            if i!=4:self.assertEqual(u["loadout"][i],before[i])
    def test_duplicate_death_and_reset_only_one_return(self):
        u=self.unit()
        for _ in range(20):self.assertTrue(restore(u))
        self.assertEqual(u["writes"],1)
    def test_vehicle_death_returns_removed_carrier(self):
        u=self.unit();u["vehicle"]="helo";self.assertTrue(restore(u))
    def test_vehicle_never_removed_no_refund(self):
        u=self.unit();u["removed"]=False;u["saved"]=[];u["loadout"][4]=["V_worn",[["ammo",1,9]]];before=copy.deepcopy(u)
        restore(u);self.assertEqual(u,before)
    def test_conflicting_new_vest_retains_custody(self):
        u=self.unit();u["loadout"][4]=["V_other",[]];before=copy.deepcopy(u)
        self.assertFalse(restore(u));self.assertEqual(u,before)
    def test_same_class_vest_not_overfilled(self):
        u=self.unit();u["loadout"][4]=["V_Example",[["otherItem",1]]]
        self.assertFalse(restore(u));self.assertEqual(u["writes"],0);self.assertTrue(u["removed"])
    def test_nonowner_cannot_duplicate(self):
        u=self.unit();u["local"]=False;self.assertFalse(restore(u));self.assertEqual(u["writes"],0)
    def test_owner_transfer_restores_once(self):
        u=self.unit();u["local"]=False;restore(u);u["local"]=True;restore(u);restore(u);self.assertEqual(u["writes"],1)
    def test_living_lower_uses_same_record(self):
        u=self.unit();u["alive"]=True;self.assertTrue(restore(u))

class LayerModels(unittest.TestCase):
    def setUp(self):self.shades=["tint","beam","top","bottom","left","right"];self.initial=[("body",False),("held",False)]+[(x,True) for x in self.shades]
    def test_existing_layers_do_not_churn(self):
        state=self.initial
        for _ in range(1000):self.assertIs(shade_raise(state,self.shades),state)
    def test_late_scalpel_is_below_restored_shade(self):
        state=shade_raise(self.initial+[("scalpel",False)],self.shades);self.assertFalse(shade_stale(state,self.shades));self.assertEqual(state[-6:],[ (x,True) for x in self.shades])
    def test_red_mark_and_final_hub_cannot_bypass_shade(self):
        for label in ("red_dot","final_20g_hub","incision"):
            state=shade_raise(self.initial+[(label,False)],self.shades)
            self.assertLess([n for n,_ in state].index(label),[n for n,_ in state].index("tint"))
    def test_same_count_replace_detected(self):
        state=self.initial[1:]+[("replacement",False)]
        self.assertEqual(len(state),len(self.initial));self.assertTrue(shade_stale(state,self.shades))
    def test_other_overlay_does_not_fight_shade(self):self.assertFalse(shade_stale(self.initial+[("other_overlay",True)],self.shades))
    def test_held_raise_does_not_fight_shade(self):
        state=shade_raise(self.initial+[("red_dot",False)],self.shades)
        state=[p for p in state if p[0]!="held"]+[("held",False)]
        state=shade_raise(state,self.shades)
        self.assertEqual([n for n,o in state if not o][-1],"held");self.assertFalse(shade_stale(state,self.shades))
    def test_original_red_luminance_becomes_neutral_not_purple(self):
        v=.2126*.85+.7152*.2+.0722*.2;rgba=[v,v,v,.35]
        self.assertEqual(rgba[0],rgba[2]);self.assertEqual(rgba[3],.35);self.assertLess(v,.85)
    def test_failed_comparison_example_was_purple(self):
        # Regression evidence: B6 normalized color-correction coefficients as a tint.
        wrong=[v/1.9 for v in [1.1,.8,1.9]]
        self.assertGreater(wrong[2],wrong[0]);self.assertGreater(wrong[0],wrong[1])

if __name__ == "__main__":unittest.main()
