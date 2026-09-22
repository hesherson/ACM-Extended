"""B10 source contracts and executable reference models. Does not execute SQF."""
from historical_source import read_source
from pathlib import Path
import json,math,re,unittest
ROOT=Path(__file__).resolve().parents[1]
def src(n):return read_source(ROOT/'functions'/('fn_'+n+'.sqf'))
def code(n):return re.sub(r'/\*.*?\*/|//[^\n]*','',src(n),flags=re.S)

def smooth(target,previous,dt,tau=.12):
    def val(v):return v if isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) else 0
    target=list(map(val,target));previous=list(map(val,previous))
    dt=max(0,val(dt));tau=max(.02,min(.4,tau if math.isfinite(tau) else .12))
    a=1-math.exp(-min(dt,.1)/tau)
    return [p+(t-p)*a for t,p in zip(target,previous)]

def match(b,device,key,mods=(False,False,False),held=()):
    action,main,combo,double,required=b
    if len(main)<2:return False
    k,d=main[:2];k=k%128 if d=='MOUSE_BUTTON' else k
    if (d,k)!=(device,key):return False
    actual=list(mods)
    for i,group in enumerate(((42,54),(29,157),(56,184))):
        if device=='KEYBOARD' and key in group:actual[i]=False
    if required:return actual==list(required)
    want=[False]*3;ok=not combo
    if len(combo)>=2:
        ck,cd=combo[:2];ck=ck%128 if cd=='MOUSE_BUTTON' else ck
        ok=(cd,ck) in held
        if cd=='KEYBOARD':
            for i,group in enumerate(((42,54),(29,157),(56,184))):
                if ck in group:want[i]=True;ok=mods[i]
    return bool(ok and actual==want)

def binding(key=49,combo=(),double=False,action='nv',mods=(),device='KEYBOARD'):
    return [action,[key,device],list(combo),double,list(mods)]

class InputModel:
    def __init__(self):self.held={};self.taps={};self.actions=[];self.released=None
    def event(self,key,bindings,up=False,mods=(False,False,False),t=1,frame=1,device='KEYBOARD',edit=False,goggles=True):
        token=(device,key)
        if up:
            if token in self.held:
                result=self.held.pop(token);self.released=(frame,token,result);return result
            return bool(self.released and self.released==(frame,token,True))
        if token in self.held:return self.held[token]
        self.held[token]=False
        if edit:return False
        chosen=next((b for b in bindings if match(b,device,key,mods,self.held)),None)
        if chosen is None:return False
        self.held[token]=True
        if chosen[3]:
            ident=str(chosen);last=self.taps.get(ident,-10);run=t-last<=.3
            self.taps[ident]=-10 if run else t
            if not run:return True
        if chosen[0]!='nv' or goggles:self.actions.append(chosen[0])
        return True

class FocusModel:
    def __init__(self):self.users=set();self.handle=None;self.native=object();self.created=0;self.destroyed=0;self.amount=-1
    def tick(self,panel,on=True,amount=.35):
        if on:self.users.add(panel)
        else:self.users.discard(panel)
        if not self.users or amount<=0:
            if self.handle is not None:self.destroyed+=1
            self.handle=None;self.amount=-1;return
        if self.handle is None:self.handle=object();self.created+=1
        self.amount=amount

class InputTests(unittest.TestCase):
    def test_default_n(self):self.assertTrue(match(binding(),'KEYBOARD',49))
    def test_rebound_key(self):self.assertTrue(match(binding(34),'KEYBOARD',34));self.assertFalse(match(binding(34),'KEYBOARD',49))
    def test_ctrl_chord(self):self.assertTrue(match(binding(combo=[29,'KEYBOARD']),'KEYBOARD',49,(False,True,False)))
    def test_ctrl_chord_not_plain(self):self.assertFalse(match(binding(combo=[29,'KEYBOARD']),'KEYBOARD',49))
    def test_plain_does_not_steal_transport_nv(self):self.assertFalse(match(binding(),'KEYBOARD',49,(False,True,False)))
    def test_shift_chord(self):self.assertTrue(match(binding(combo=[42,'KEYBOARD']),'KEYBOARD',49,(True,False,False)))
    def test_alt_chord(self):self.assertTrue(match(binding(combo=[56,'KEYBOARD']),'KEYBOARD',49,(False,False,True)))
    def test_extra_modifier_not_accepted(self):self.assertFalse(match(binding(combo=[29,'KEYBOARD']),'KEYBOARD',49,(True,True,False)))
    def test_nonmodifier_chord(self):self.assertTrue(match(binding(combo=[30,'KEYBOARD']),'KEYBOARD',49,held=[('KEYBOARD',30)]))
    def test_missing_nonmodifier_chord(self):self.assertFalse(match(binding(combo=[30,'KEYBOARD']),'KEYBOARD',49))
    def test_main_modifier(self):self.assertTrue(match(binding(157),'KEYBOARD',157,(False,True,False)))
    def test_device_not_confused(self):self.assertFalse(match(binding(2,device='MOUSE_BUTTON'),'KEYBOARD',2))
    def test_native_mouse_code(self):self.assertTrue(match(binding(129,device='MOUSE_BUTTON'),'MOUSE_BUTTON',1))
    def test_custom_cba_modifier(self):self.assertTrue(match(binding(33,action='flip',mods=[True,True,False]),'KEYBOARD',33,(True,True,False)))
    def test_custom_cba_unmodified_rejected(self):self.assertFalse(match(binding(33,action='flip',mods=[True,False,False]),'KEYBOARD',33))
    def test_unknown_joystick_not_as_keyboard(self):self.assertFalse(match(binding(49,device='JOYSTICK_BUTTON'),'KEYBOARD',49))
    def test_no_bind_means_no_action(self):m=InputModel();self.assertFalse(m.event(49,[]));self.assertEqual(m.actions,[])
    def test_multiple_alternates(self):m=InputModel();m.event(34,[binding(49),binding(34)]);self.assertEqual(m.actions,['nv'])
    def test_repeat_no_toggle_spam(self):
        m=InputModel()
        for _ in range(1000):m.event(49,[binding()])
        self.assertEqual(m.actions,['nv'])
    def test_release_allows_second_toggle(self):
        m=InputModel();m.event(49,[binding()]);m.event(49,[binding()],up=True);m.event(49,[binding()],frame=2);self.assertEqual(m.actions,['nv','nv'])
    def test_duplicate_up_consumed_same_frame(self):
        m=InputModel();m.event(49,[binding()]);self.assertTrue(m.event(49,[],up=True));self.assertTrue(m.event(49,[],up=True))
    def test_stale_up_does_not_claim(self):m=InputModel();m.event(49,[binding()]);m.event(49,[],up=True);self.assertFalse(m.event(49,[],up=True,frame=2))
    def test_doubletap_first_only_reserves(self):m=InputModel();self.assertTrue(m.event(49,[binding(double=True)]));self.assertEqual(m.actions,[])
    def test_doubletap_second_executes(self):m=InputModel();b=[binding(double=True)];m.event(49,b,t=1);m.event(49,b,up=True,t=1.05);m.event(49,b,t=1.2);self.assertEqual(m.actions,['nv'])
    def test_doubletap_timeout(self):m=InputModel();b=[binding(double=True)];m.event(49,b,t=1);m.event(49,b,up=True);m.event(49,b,t=1.4);self.assertEqual(m.actions,[])
    def test_triple_tap_does_not_toggle_twice(self):
        m=InputModel();b=[binding(double=True)]
        for t in [1,1.15,1.25]:m.event(49,b,t=t);m.event(49,b,up=True,t=t+.01)
        self.assertEqual(m.actions,['nv'])
    def test_edit_field_retains_character(self):m=InputModel();self.assertFalse(m.event(49,[binding()],edit=True));self.assertEqual(m.actions,[])
    def test_nv_wins_same_key_flip_conflict(self):m=InputModel();m.event(33,[binding(33),binding(33,action='flip',mods=[False]*3)]);self.assertEqual(m.actions,['nv'])
    def test_no_goggles_no_helper_or_action(self):m=InputModel();m.event(49,[binding()],goggles=False);self.assertEqual(m.actions,[])
    def test_flip_distinct_from_nvg(self):m=InputModel();m.event(33,[binding(),binding(33,action='flip',mods=[False]*3)]);self.assertEqual(m.actions,['flip'])
    def test_separate_displays_not_sticky(self):m=InputModel();m.event(49,[binding()]);n=InputModel();n.event(49,[binding()]);self.assertEqual(n.actions,['nv'])

class MotionTests(unittest.TestCase):
    def test_step_never_overshoots(self):
        p=[0,0]
        for _ in range(200):p=smooth([.03,-.04],p,1/20);self.assertTrue(0<=p[0]<=.03);self.assertTrue(-.04<=p[1]<=0)
    def test_zero_time_is_no_motion(self):self.assertEqual(smooth([1,1],[.2,-.2],0),[.2,-.2])
    def test_settle_frame_independent_constant_target(self):
        values=[]
        for fps in (10,15,20,30,60,120):
            p=[0,0]
            for _ in range(fps):p=smooth([.05,-.03],p,1/fps)
            values.append(p)
        for p in values:self.assertAlmostEqual(p[0],values[0][0],places=12)
    def test_smaller_tau_more_responsive(self):self.assertGreater(smooth([1,0],[0,0],.02,.04)[0],smooth([1,0],[0,0],.02,.3)[0])
    def test_stall_step_capped(self):self.assertEqual(smooth([1,1],[0,0],2),smooth([1,1],[0,0],.1))
    def test_bad_vectors_do_not_poison_controls(self):self.assertTrue(all(math.isfinite(v) for v in smooth([float('nan'),float('inf')],[float('nan'),0],.02)))
    def test_bad_dt_no_jump(self):self.assertEqual(smooth([1,1],[0,0],float('nan')),[0,0])
    def test_tau_clamped(self):self.assertEqual(smooth([1,1],[0,0],.02,0),smooth([1,1],[0,0],.02,.02))
    def test_lowfps_alternating_jitter_attenuated(self):
        for fps in (10,15,20,30):
            p=[0,0];out=[]
            for i in range(200):p=smooth([.03*(-1)**i,0],p,1/fps);out.append(abs(p[0]))
            self.assertLess(max(out[-50:]),.015)
    def test_shake_ui_uses_returned_offset(self):
        t=src('uiShakeApply');self.assertIn('([] call ACME_fnc_motionShake) params',t);self.assertIn('_c ctrlCommit 0',t);self.assertTrue(t.rstrip().endswith('[_dx, _dy]'))
    def test_lowfps_frequency_cutoff_has_no_20fps_floor(self):self.assertIn('(diag_fps max 1) * 0.45',src('motionShake'))
    def test_smooth_disables_unresolvable_random_jumps(self):self.assertIn('if (_buzz > 0 && {!_smooth})',src('motionShake'))
    def test_frame_cache_before_physics(self):
        t=src('motionShake');self.assertLess(t.index('== diag_frameNo'),t.index('private _isAir'));self.assertIn('ACME_motion_sampleKey',t)
    def test_player_and_vehicle_reset(self):self.assertIn('private _key = [_unit, _veh, _smooth,',src('motionShake'))
    def test_long_gap_reset(self):self.assertIn('_now - _lastTime > 0.5',src('motionShake'))
    def test_off_switch_returns_zero(self):self.assertIn('if (!_enabled || {isNull _unit}) exitWith',src('motionShake'))
    def test_no_control_interpolation(self):self.assertNotIn('ctrlCommit',code('motionSmooth'))
    def test_no_network_or_patient_write(self):
        for n in ('motionShake','motionSmooth'):
            for term in ('remoteExec','globalEvent','targetEvent','publicVariable','_patient setVariable'):self.assertNotIn(term,code(n))

class FocusTests(unittest.TestCase):
    def test_repeated_open_keeps_native_identity(self):
        m=FocusModel();native=m.native
        for _ in range(500):m.tick('IV')
        self.assertIs(m.native,native);self.assertEqual(m.created,1)
    def test_child_shares_one_blur(self):m=FocusModel();m.tick('IV');m.tick('child');m.tick('child',False);self.assertEqual(m.created,1);self.assertEqual(m.destroyed,0)
    def test_last_close_destroys_only_owned_blur(self):m=FocusModel();native=m.native;m.tick('IV');m.tick('IV',False);self.assertEqual(m.destroyed,1);self.assertIs(m.native,native)
    def test_repeated_close_is_idempotent(self):m=FocusModel();m.tick('IV');m.tick('IV',False);m.tick('IV',False);self.assertEqual(m.destroyed,1)
    def test_zero_setting_disables_own_effect(self):m=FocusModel();m.tick('IV');m.tick('IV',amount=0);self.assertIsNone(m.handle)
    def test_setting_reenabled_once(self):m=FocusModel();m.tick('IV',amount=0);m.tick('IV',amount=.2);self.assertEqual(m.created,1)
    def test_other_title_change_left_alone(self):m=FocusModel();m.tick('IV');m.native='replacement';m.tick('IV');m.tick('IV',False);self.assertEqual(m.native,'replacement')
    def test_no_mutation_of_native_layer_or_effects(self):
        text='\n'.join(code(n) for n in ('minigameVisionTick','minigameVisionClear','minigameVisionNative'))
        for term in ('cutRsc','cutText','titleRsc','setupDisplayEffects','refreshGoggleType','setFog','setAperture','setCamUseTi','ColorCorrections','FilmGrain','ctrlCreate','ctrlSetText','ctrlSetTextColor'):
            self.assertNotIn(term,text)
    def test_single_owned_pp_allocation(self):
        t=code('minigameVisionNative');self.assertEqual(t.count('ppEffectCreate'),1);self.assertIn('"ACME_NV_FocusHandle"',t);self.assertNotIn('ace_nightvision_',t)
    def test_bounded_allocation_retry(self):t=src('minigameVisionNative');self.assertIn('from 0 to 7',t);self.assertIn('diag_tickTime + 2',t)
    def test_texture_map_not_loaded(self):self.assertNotIn('call ACME_fnc_minigameVisionTextures',code('postInit'))
    def test_blur_is_small_and_adjustable(self):self.assertIn('"ACME_minigameNV_focusBlur", 0.35',src('minigameVisionNative'));self.assertIn('_amount max 0 min 1',src('minigameVisionNative'))
    def test_no_fake_grayscale_picture_path(self):self.assertNotIn('ACME_NV_Variant',code('minigameVisionTick'))
    def test_limitation_explained_in_code_and_option(self):self.assertIn('not part of the scene PP pass',src('minigameVisionTick'));self.assertIn('does not blur 2D dialog text or art',read_source(ROOT/'XEH_settings.hpp'))

class SourceTests(unittest.TestCase):
    def test_versions(self):v=re.search(r'version = "([^"]+)"',read_source(ROOT/'config.cpp')).group(1);self.assertIn('version = "'+v+'"',read_source(ROOT/'config.cpp'));self.assertIn('ACME_infusion_version = getText',src('postInit'));self.assertIn('1.0.100-r7',src('postInit'))
    def test_no_separate_nvg_binding(self):self.assertNotIn('"ACME_vent_nvgToggle"',code('postInit'));self.assertNotIn('0x31',code('postInit'))
    def test_native_bindings_read(self):self.assertIn('actionKeysEx "NightVision"',src('minigameInputBindings'))
    def test_vent_bind_keeps_existing_id(self):self.assertIn('"ACME_vent_flipDevice"',src('postInit'));self.assertIn('{false}, {false}, [0x21',src('postInit'))
    def test_current_all_cba_binds(self):self.assertIn('_data param [8, [], [[]]]',src('minigameInputBindings'));self.assertIn('isNil "_data"',src('minigameInputBindings'))
    def test_unbound_no_fallback_f(self):self.assertNotIn('0x21',code('minigameInputBindings'));self.assertNotIn('F: Flip Device',read_source(ROOT/'config.cpp'));self.assertIn('"Unbound"',src('ventFlipKeyHint'))
    def test_hint_refresh_is_throttled(self):self.assertIn('diag_tickTime + 0.5',src('ventFlipKeyHint'));self.assertIn('call ACME_fnc_ventFlipKeyHint',src('ventPanelTick'))
    def test_all_ten_primary_procedures_have_input_hook(self):
        t=read_source(ROOT/'config.cpp')
        for name in ('RollerClamp','ChestSeal','Thoracostomy','IVMinigame','SyringeKit','Ventilator','Laryngoscopy','BloodFridgeContents','BloodFridge'):
            m=re.search(r'class ACME_'+name+r'_Dialog\b[^\{]*\{(.*?)(?=\n\s*class )',t,re.S);self.assertIsNotNone(m,name);self.assertIn('ACME_fnc_minigameInputInstall',m[1])
        self.assertIn('ACME_fnc_minigameInputInstall',re.search(r'class ACME_CoolerManager_Dialog\b[^\{]*\{(.*?)(?=\n\s*class )',t,re.S)[1])
    def test_local_state_and_no_hints(self):
        t=code('minigameInput')
        for term in ('remoteExec','globalEvent','targetEvent','displayTextStructured','hint','systemChat','diag_log'):self.assertNotIn(term,t)
    def test_uses_goggles_actions_not_inventory(self):t=code('minigameInput');self.assertIn('action ["NVGogglesOff"',t);self.assertIn('action ["NVGoggles"',t);self.assertNotIn('removeItem',t)
    def test_text_edit_exemption(self):self.assertIn('ctrlType _focus == 2',src('minigameInput'))
    def test_laryngo_keys_check_bridge_first(self):
        t=src('laryngoInit');self.assertRegex(t,r'displayAddEventHandler \["KeyDown", \{\s*if \(_this call ACME_fnc_minigameInput\) exitWith \{true\};')
    def test_iv_withdraw_respects_nv(self):self.assertRegex(src('ivMinigameInit'),r'displayAddEventHandler \["KeyDown", \{\s*if \(_this call ACME_fnc_minigameInput\)')
    def test_mouse_choke_points_respect_bindings(self):
        for n in ('ivMinigameClick','chestSealMouseDown','thoraMouseDown'):
            self.assertTrue(src(n).startswith('if ([_this,"down"] call ACME_fnc_minigameInputMouse)'))
        t=src('laryngoClick')
        self.assertIn('ACME_laryngo_sucPinned',t)
        self.assertIn('== "suction"',t)
        self.assertLess(t.index('ACME_fnc_laryngoSuctionPin'),t.index('ACME_fnc_minigameInputMouse'))
        self.assertIn('if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true}',t)
    def test_client_local_accessibility_settings(self):
        t=read_source(ROOT/'XEH_settings.hpp')
        for setting in ('ACME_motion_interpolate','ACME_motion_interpolationTime','ACME_minigameNV_focusBlur'):
            segment=t[t.index('"'+setting+'"'):];segment=segment[:segment.index('] call CBA_fnc_addSetting;')]
            self.assertRegex(segment,r',\s*0,\s*\{\}')
    def test_no_dbg_in_new_helpers(self):
        for p in ROOT.glob('functions/fn_minigameInput*.sqf'):self.assertNotIn('diag_log',read_source(p))

if __name__=='__main__':unittest.main()
