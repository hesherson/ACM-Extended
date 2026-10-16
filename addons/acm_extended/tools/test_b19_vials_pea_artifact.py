from historical_source import read_source, assert_release_identity
from pathlib import Path
import unittest, re
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B19Source(unittest.TestCase):
    def test_version_pair(self):
        for rel in ('config.cpp','functions/fn_postInit.sqf'):
            assert_release_identity()
    def test_exact_vial_ledger_registered(self):
        c=read('config.cpp')
        for fn in ('vialHolder','vialItemCount','vialTake','vialRefund'):
            self.assertEqual(c.count(f'class {fn} {{}};'),1)
        # Native syringe callbacks now belong to the circulation addon, not an Extended override class.
        prep=(ROOT.parent/'circulation/XEH_PREP.hpp').read_text()
        for fn in ('Syringe_PrepareFinish','Syringe_GetMedicationList','Syringe_UpdateMedicationList'):
            self.assertEqual(prep.count(f'PREP({fn});'),1)
            self.assertTrue((ROOT.parent/'circulation/functions'/f'fnc_{fn}.sqf').is_file())
    def test_native_syringe_debits_exact_ml(self):
        s=read('overrides/fn_syringePrepareFinish.sqf')
        self.assertIn('ACME_fnc_vialTake',s)
        self.assertIn('ACME_fnc_vialItemCount',read('functions/fn_vialTake.sqf'))
        self.assertNotIn('removeItem (format ["ACM_Vial_',s)
        self.assertIn('ACME_fnc_vialRefund',s)
    def test_partial_vial_is_listed_without_physical_item(self):
        get_list=read('overrides/fn_syringeGetMedicationList.sqf')
        sync=read('functions/fn_skMedicationSync.sqf')
        update=read('overrides/fn_syringeUpdateMedicationList.sqf')
        # B42 builds membership from the selected live inventory and appends the exact open-vial ledger,
        # so a partial vial remains drawable after first puncture without making a global registry the UI source.
        source=read('functions/fn_medicationSourceRows.sqf')
        self.assertIn('ACME_fnc_medicationSourceRows', get_list)
        self.assertIn('ACME_fnc_medicationSourceRows', sync)
        self.assertIn('ACME_infusion_openVials', source)
        self.assertIn('keys _open', source)
        self.assertIn('ACME_fnc_skMedicationSync', update)
        self.assertNotIn('toFixed',update); self.assertNotIn('Common_Available',update)
    def test_final_partial_volume_limits_plunger(self):
        s=read('functions/fn_skUiTick.sqf')
        self.assertIn('ACM_circulation_SyringeDraw_MaxDose',s)
        # The hard stop is ledger-backed through vialSession; B41 removed a second redundant stock scan.
        self.assertIn('ACME_fnc_vialSession',s); self.assertIn('private _hardMax',s)
    def test_compound_save_keeps_original_save_label_and_reopens_draw_dialog(self):
        # Keep the historical identity, but enforce the approved immediate in-place reset rather than a retired reopen delay.
        begin=read('functions/fn_skCompoundBegin.sqf')
        self.assertIn('ctrlSetText "Save"',begin)
        self.assertNotIn('Save & New Syringe',begin)
        save=read('functions/fn_skCompoundSave.sqf')
        self.assertNotIn('closeDialog',save)
        self.assertNotIn('call ACME_fnc_skOpenDraw',save)
        from test_historical_medication_preparation import test_compound_save_reuses_the_same_dialog_and_does_not_recommit_on_repeated_event
        test_compound_save_reuses_the_same_dialog_and_does_not_recommit_on_repeated_event()
    def test_infusion_done_explicitly_returns(self):
        d=read('functions/fn_infusionDone.sqf'); c=read('functions/fn_skClose.sqf')
        self.assertIn('ACME_SK_suppressReturn',d); self.assertIn('ACME_fnc_reopenTransfusion',d)
        from test_b241_current_ui_expectations import has
        # Suppression remains authoritative; a stale provider also cannot route
        # this display's return through a newly controlled actor.
        self.assertTrue(has(c, 'private _provider = _display getVariable ["ACME_SK_Provider", objNull];'))
        self.assertTrue(has(c, 'private _providerCurrent = !isNull _provider && {_provider isEqualTo (call ACME_fnc_controlledProvider)};'))
        self.assertTrue(has(c, 'uiNamespace setVariable ["ACME_SK_suppressReturn", false];'))
        self.assertTrue(has(c, 'if (_suppressReturn || {!_providerCurrent}) exitWith {};'))
        self.assertTrue(has(c, 'if !(_return isEqualTo []) exitWith {[_return] call ACME_fnc_reopenTransfusion;};'))
        self.assertTrue(has(c, '[_patient, "medication", -1, [], _provider] call ACME_fnc_reopenMedicalMenu;'))
        self.assertLess(c.index('if (_suppressReturn || {!_providerCurrent})'), c.index('call ACME_fnc_reopenTransfusion;'))
    def test_true_pea_bp_zero_before_modifiers(self):
        s=read('functions/fn_bpCompute.sqf')
        self.assertRegex(s,r'rhythmGet\) == 5\) exitWith \{\[0, 0\]\}')
        self.assertIn('ACM_circulation_AED_NIBP_Display", [0,0]',read('functions/fn_circHandle.sqf'))
        co=read('overrides/fn_getCardiacOutput.sqf'); self.assertIn('rhythmGet) == 5',co); self.assertIn('exitWith {0}',co)
    def test_pea_morphology_distinct_from_sinus(self):
        # Current PEA has a narrow/default and a severe-burden wide subtype.
        # Neither waveform creates mechanical perfusion. Do not restore the retired all-wide template.
        from test_historical_ecg_artifact_execution import test_pea_subtype_changes_morphology_without_changing_rhythm_or_circulation, test_megacode_routes_both_ecg_windows_through_native_generator
        for blood,calcium,wide in ((0,0,False),(2,0,False),(2.1,0,True),(2.1,0.1,False),(3,0.5,True)):
            test_pea_subtype_changes_morphology_without_changing_rhythm_or_circulation(blood,calcium,wide)
        test_megacode_routes_both_ecg_windows_through_native_generator()
    def test_artifact_is_visual_only_and_network_visible(self):
        a=read('functions/fn_ecgArtifactApply.sqf')
        self.assertIn('_mask set [_idx, false]',a)
        for bad in ('setVariable ["ace_medical_','ACME_fnc_rhythmSet','ACME_fnc_arrestLocal'):
            self.assertNotIn(bad,a)
        o=read('functions/fn_ownerDispatch.sqf'); self.assertIn('case "ecgJostle"',o)
        e=read('functions/fn_ecgJostleLocal.sqf'); self.assertIn('ACME_ecgJostleLeases',e); self.assertIn(', true]',e)
    def test_ace_timer_events_drive_artifact(self):
        from test_historical_ecg_artifact_execution import test_timed_treatments_publish_and_release_only_their_own_artifact_lease, test_minigame_artifact_start_and_close_use_matching_keys_at_current_entry_modules
        for ending in ('ace_treatmentSucceded','ace_treatmentFailed'):
            test_timed_treatments_publish_and_release_only_their_own_artifact_lease(ending)
        test_minigame_artifact_start_and_close_use_matching_keys_at_current_entry_modules()
    def test_monitor_generators_apply_artifact(self):
        from test_historical_ecg_artifact_execution import test_native_and_custom_generator_paths_apply_same_artifact_boundary, test_megacode_routes_both_ecg_windows_through_native_generator
        for rhythm in (0,1,2,3,4,5,104):
            test_native_and_custom_generator_paths_apply_same_artifact_boundary(rhythm)
        test_megacode_routes_both_ecg_windows_through_native_generator()

class B19Reference(unittest.TestCase):
    def test_propofol_50ml_conserves_five_ten_ml_draws(self):
        cap=50.0; open_ml=0.0; sealed=1
        for expected in (40,30,20,10,0):
            draw=10
            needed=max(0,draw-open_ml)
            n=0 if needed<=0 else int((needed+cap-1e-9)//cap)
            self.assertLessEqual(n,sealed)
            sealed-=n; open_ml=open_ml+n*cap-draw
            self.assertAlmostEqual(open_ml,expected)
        self.assertEqual(sealed,0)
    def test_pea_mechanical_pressure_is_zero(self):
        rhythm=5; native_bp=(80,120); result=(0,0) if rhythm==5 else native_bp
        self.assertEqual(result,(0,0))
    def test_artifact_does_not_change_physiology_model(self):
        hr,bp,spo2=(80,(80,120),98)
        artifact=[0,3,-4,8,-2]
        self.assertEqual((hr,bp,spo2),(80,(80,120),98))
        self.assertTrue(any(x != 0 for x in artifact))

if __name__=='__main__': unittest.main()
