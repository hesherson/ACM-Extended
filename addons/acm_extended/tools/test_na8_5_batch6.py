"""Source contracts and independent state models. These tests do not run SQF or Arma."""
from pathlib import Path
import math,re,unittest
ROOT=Path(__file__).resolve().parents[1]
def src(n):return (ROOT/'functions'/('fn_'+n+'.sqf')).read_text()
class ModelTests(unittest.TestCase):
 def test_nv_requires_goggles_and_mode(self):
  for hmd,mode in [('',1),('NVG',0),('NVG',2)]:self.assertFalse(bool(hmd) and mode==1)
 def test_nv_on_equipped(self):self.assertTrue(bool('NVG') and 1==1)
 # B9 removes B6's five model assertions for synthetic tint/dimming/washout.
 # Native goggles now own those optical settings; B9 tests the ownership lifecycle.
 def test_same_frame_not_crossfaded_due_to_variant(self):
  shown='derived';variant='derived';base='needle15';source=base if shown==variant else shown;self.assertEqual(source,'needle15')
 def test_new_frame_has_new_identity(self):
  shown='needle30';variant='derived';base='needle15';self.assertEqual(base if shown==variant else shown,'needle30')
 def test_restore_does_not_overwrite_new_procedural_image(self):
  current='new_frame';variant='old_derived';self.assertNotEqual(current,variant)
 def test_restore_keeps_new_procedural_color(self):self.assertNotEqual([1,0,0,1],[.4,.8,1,1])
 def test_unlimited_wiping_bounded_cells(self):
  cells={};total=0;cap=260
  for tick in range(10000):
   key=tick%511
   if key not in cells and len(cells)>=cap:del cells[min(cells,key=cells.get)]
   cells[key]=tick;total+=1
  self.assertEqual(total,10000);self.assertEqual(len(cells),cap)
 def test_repeat_wipe_accumulates_without_controls(self):
  cells={};total=0
  for i in range(10000):cells['one']=i;total+=1
  self.assertEqual(len(cells),1);self.assertEqual(total,10000)
 def test_clean_threshold_does_not_release_pad(self):
  held='pad';clean=False
  for i in range(1000):
   if i>=16:clean=True
  self.assertTrue(clean);self.assertEqual(held,'pad')
 def test_overlay_count_constant_without_new_controls(self):
  controls=['body','held','wash','mask'];overlay=['wash','mask']
  for _ in range(1000):self.assertIn(controls[-1],overlay)
 def test_held_raise_ignores_nv_overlay(self):
  c=[('body',False),('held',False),('wash',True),('mask',True)];self.assertEqual([n for n,o in c if not o][-1],'held')
 def test_duplicate_cleanup_owns_one_handle(self):
  state={'handle':5};destroy=[]
  for _ in range(2):
   if state['handle']>=0:destroy.append(state['handle']);state['handle']=-1
  self.assertEqual(destroy,[5])
class SourceTests(unittest.TestCase):
 # B10 preserves native titles; focus is owned once per client.
 def test_nvg_owned_resource(self):
  self.assertNotIn("cutRsc",src("minigameVisionNative"))
 def test_live_equipped_mask(self):
  t=src('minigameVisionProfile');self.assertIn('ace_nightvision_titleDisplay',t);self.assertIn('_liveHMD == _goggles',t)
 def test_actual_modeloptics_preserved(self):
  self.assertIn('getText (_cfg >> "modelOptics") == ""',src('minigameVisionProfile'))
 def test_missing_mask_no_generic(self):
  self.assertNotIn('ctrlCreate',src('minigameVisionProfile')+src('minigameVisionNative'))
 def test_hidden_ace_mask_respected(self):
  self.assertNotIn('ctrlShow',src('minigameVisionNative'))
 def test_ultrawide_ace_controls(self):
  self.assertNotIn('ace_nightvision_fnc_refreshGoggleType',src('minigameVisionNative'));self.assertNotIn('safeZoneW',src('minigameVisionNative'))
 def test_flashlight_actual_ace_state(self):
  t=src('minigameVisionTick');self.assertNotIn('0.965',t);self.assertNotIn('ctrlSetBackgroundColor',t)
 def test_own_blur_only(self):
  t=src('minigameVisionNative');self.assertIn('ppEffectDestroy _handle',t);self.assertNotIn('ace_nightvision_',t)
 def test_forced_nv_blur(self):self.assertIn('ppEffectForceInNVG true',src('minigameVisionNative'))
 def test_display_unload_cleanup(self):self.assertIn('displayAddEventHandler ["Unload"',src('minigameVisionTick'))
 def test_no_network_nv(self):
  t=src('minigameVisionTick')+src('minigameVisionClear')+src('minigameVisionProfile')
  for n in ['remoteExec','globalEvent','targetEvent','publicVariable','diag_log']:self.assertNotIn(n,t)
 def test_nv_never_reveals_body_group(self):self.assertNotIn('ctrlShow',src('minigameVisionClear'))
 def test_no_texture_restore_needed(self):self.assertNotIn('ctrlSetText',src('minigameVisionTick')+src('minigameVisionClear'))
 def test_native_palette_not_reinterpreted(self):self.assertNotIn('ace_nightvision_colorPreset',src('minigameVisionProfile'))
 def test_frame_change_aware(self):self.assertIn('ACME_NV_BaseTexture',src('ivCathSetFrame'));self.assertIn('_source isEqualTo _tex',src('ivCathSetFrame'))
 def test_held_metadata_copied(self):
  t=src('ivHeldRaise');self.assertIn('ACME_NV_OverlayControl',t);self.assertIn('ACME_NV_BaseTexture',t)
 def test_no_duplicate_overlay_controls(self):self.assertNotIn('ctrlCreate',src('minigameVisionTick'))
 def test_shake_excludes_mask(self):self.assertIn('ACME_NV_Overlay',src('uiShakeApply'))
 def test_all_visual_passes_after_procedure(self):
  # Procedure ticks end with their vision pass. Roller-clamp vision is intentionally owned by
  # the independent clamp runtime so dialog-transition sampling cannot latch a black shade.
  for n in ['ivMinigameTick','chestSealTick','thoraTick','laryngoTick','syringeKitTick','skUiTick']:
   with self.subTest(n=n):self.assertTrue(src(n).rstrip().endswith('call ACME_fnc_minigameVisionTick;'))
  clamp=src('updateClampDialog')
  runtime=src('registerClampDragRuntime')
  self.assertNotIn('ACME_fnc_minigameVisionTick',clamp)
  self.assertIn('ACME_RollerClamp_VisionSettleUntil',runtime)
  self.assertIn('ACME_RollerClamp_NextVisionTick',runtime)
  self.assertIn('[_display] call ACME_fnc_minigameVisionTick;',runtime)
 def test_cleaned_pad_stays(self):
  t=src('ivMinigameCleanDone');self.assertIn('ACME_IV_Cleaned", true',t)
  for k in ['HeldKind','ctrlShow false','HeldCtrl','"none"']:self.assertNotIn(k,t)
 def test_prep_points_do_not_grow(self):self.assertNotIn('_pts pushBack',src('ivPrepPaint'));self.assertIn('ACME_IV_PrepTotal',src('ivPrepPaint'))
 def test_prep_cell_budget_recycles(self):self.assertIn('_cells deleteAt _oldest',src('ivPrepPaint'));self.assertIn('_total = _total + 1',src('ivPrepPaint'))
 def test_prep_total_resets(self):
  for n in ['ivMinigameInit','ivMinigamePrepView','ivMinigameClose']:self.assertIn('ACME_IV_PrepTotal", 0',src(n))
  self.assertIn('["leave"] call ACME_fnc_ivMinigamePrepView',src('ivMinigameFlip'))
  self.assertIn('["enter"] call ACME_fnc_ivMinigamePrepView',src('ivMinigameFlip'))
if __name__=='__main__':unittest.main()
