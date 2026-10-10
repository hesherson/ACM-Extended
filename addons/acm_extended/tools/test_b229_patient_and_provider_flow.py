"""B229 source/runtime contracts with explicit Arma engine boundaries.

Runs shipped SQF decisions and finite controllers. Namespace stand-ins, native moves,
control painting, clock/locality and network transport are simulated, not rendered Arma.
"""
import hashlib
import json
import re
import subprocess

import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b227_line_service_and_assessments import basic, fn, src
from test_b228_line_service_network_audit import service_paint_setup
from test_b213_direct_pressure_flow import setup as pressure_setup, observer_setup
from test_b209_direct_pressure_locality import source as pressure_source
from test_b222_suction_input import block
from test_b223_interaction_flow import mask_button_setup
from test_b222_niv import func as vent_func
from test_b156_shared_action_gates import ACTIONS


@pytest.mark.parametrize('part', ['head','body','leftarm','rightarm','leftleg','rightleg'])
@pytest.mark.parametrize('amount', [0,1,2,3])
def test_priority_requires_exactly_one_isolated_limb_wound(part,amount):
    expected=f'["{part}",7]' if amount==1 and part not in ['head','body'] else '[]'
    execute(basic()+fn('priorityJunctionalCandidate')+f'''
      private _open=createHashMapFromArray [["{part}",[[7,{amount},.8,2]]]];
      [[_open] call ACME_fnc_priorityJunctionalCandidate isEqualTo {expected},"priority wound-count policy failed"] call _check;
    ''')


@pytest.mark.parametrize('extra', ['second-limb','small-body','second-same-limb','internal','hemothorax'])
def test_priority_other_wound_or_bleeding_disallows_junctional(extra):
    mutation={
      'second-limb':'_open set ["rightleg",[[3,1,.1,0]]];',
      'small-body':'_open set ["body",[[0,1,0,0]]];',
      'second-same-limb':'_open set ["leftarm",[[7,1,1,2],[1,1,.01,0]]];',
      'internal':'_internal set ["body",[[0,1,.1,0]]];',
      'hemothorax':'_hemo=.001;'
    }[extra]
    execute(basic()+fn('priorityJunctionalCandidate')+'''
      private _open=createHashMapFromArray [["leftarm",[[7,1,1,2]]]];
      private _internal=createHashMap;private _hemo=0;
    '''+mutation+'''
      [[_open,_internal,_hemo] call ACME_fnc_priorityJunctionalCandidate isEqualTo [],"second injury allowed a priority junctional"] call _check;
    ''')


def test_priority_defers_roll_until_full_injury_batch_but_not_ordinary_combat():
    s=(ROOT/'addons/mission/functions/fnc_generatePatient.sqf').read_text()
    assert s.index('if (_severity == 0)') < s.index('_patient setVariable ["ACME_spawnSeverity", _severity, true];',s.index('if (_severity == 0)')) < s.index('for "_i"')
    assert s.index('} forEach _injuryArray;') < s.index('"ACME_trainingSpawnFinalize", true') < s.index('call ACME_fnc_junctionalRollSpawn')
    roll=read('junctionalRollSpawn')
    assert '&& {_unit getVariable ["ACME_trainingSpawnInProgress", false]}' in roll
    assert 'if (_prioritySpawn && {!(_unit getVariable ["ACME_trainingSpawnFinalize", false])}) exitWith {};' in roll
    assert 'if (_prioritySpawn) then {_cap = 1;' in roll
    assert '_cap = [2, 4] select (_sev >= 4);' in roll
    assert 'ACM_damage_InternalWounds' in roll and 'ACM_breathing_Hemothorax_Fluid' in roll and 'ACM_breathing_Hemothorax_State' in roll


@pytest.mark.parametrize('old_speed',[1,1.5,2,5,25,100])
def test_pressure_entry_normalizes_unowned_medical_speed_not_captures_it(old_speed):
    execute(pressure_setup()+f'''
      _testAnimationSpeed={old_speed};["body"] call _start;
      [_testAnimationSpeed==1,"pressure inherited old accelerated coefficient"] call _check;
      _animation="acme_directpressurehold";CBA_missionTime=CBA_missionTime+.2;
      [false,_medic] call ACME_fnc_directPressureStop;
      [_testAnimationSpeed==1,"pending exit sped up movement before RTM"] call _check;
      private _exit=count _handlers-1;_animation="ainvpknlmstpsnonwnondnon_medicend";_exit call _tick;
      [_testAnimationSpeed==1.5,"observed exit speed missing"] call _check;
      _animation="amovpercmrunsraswrfldf";_moves=[];_exit call _tick;
      [_testAnimationSpeed==1 && {{count _moves==0}},"armed locomotion inherited exit speed or was overwritten"] call _check;
    ''')


@pytest.mark.parametrize('loss', ['owner','epoch','serial','token','dead'])
def test_speed_lease_releases_on_every_abandoned_local_exit(loss):
    change={
      'owner':'_medic setVariable ["TEST_owner",8];',
      'epoch':'_medic setVariable ["ACME_providerLocalityEpoch",3];',
      'serial':'_medic setVariable ["ACME_DP_Exit",[999]];',
      'token':'_medic setVariable ["ACME_DP_PoseToken",999];',
      'dead':'_medic setVariable ["TEST_alive",false];'
    }[loss]
    execute(pressure_setup()+'''
      ["body"] call _start;_animation="acme_directpressurehold";CBA_missionTime=CBA_missionTime+.2;
      [false,_medic] call ACME_fnc_directPressureStop;
      private _exit=count _handlers-1;_animation="ainvpknlmstpsnonwnondnon_medicend";_exit call _tick;
      [_testAnimationSpeed==1.5,"exit never owned rate"] call _check;
    '''+change+'''
      _moves=[];_exit call _tick;
      [_testAnimationSpeed==1,"abandoned DP exit leaked 1.5"] call _check;
      [count _moves==0 && {_exit in _removed},"abandoned DP worker still animates"] call _check;
    ''')


@pytest.mark.parametrize('rate',[0,.65,1.5,2.7])
def test_new_explicit_speed_owner_is_never_reset_by_retiring_pressure(rate):
    execute(pressure_setup()+f'''
      ["body"] call _start;_animation="acme_directpressurehold";CBA_missionTime=CBA_missionTime+.2;
      [false,_medic] call ACME_fnc_directPressureStop;
      private _exit=count _handlers-1;_animation="ainvpknlmstpsnonwnondnon_medicend";_exit call _tick;
      _medic setVariable ["ACME_treatmentPoseEpoch",99];_medic setVariable ["TEST_speedOwner",true];_testAnimationSpeed={rate};
      _exit call _tick;[_testAnimationSpeed=={rate},"old exit modified successor rate"] call _check;
    ''')


@pytest.mark.parametrize('move',['amovpercmrunsraswrfldf','amovpknlmrunsraswpstdf','amovpercmstpsraswlnrdnon'])
def test_remote_exit_never_leaves_speed_on_armed_movement(move):
    execute(observer_setup()+f'''
      [] call _sync;private _exit=count _handlers-1;
      _animation="ainvpknlmstpsnonwnondnon_medicend";_exit call _tick;
      _animation="{move}";_moves=[];_exit call _tick;
      [_testAnimationSpeed==1 && {{count _moves==0}},"remote rate leaked onto weapon movement"] call _check;
    ''')


def test_remote_transfer_with_overtaking_public_episode_releases_old_local_rate():
    execute(observer_setup()+'''
      [] call _sync;private _exit=count _handlers-1;
      _animation="ainvpknlmstpsnonwnondnon_medicend";_exit call _tick;
      _medic setVariable ["ACME_DP_ExitEpisode",[_networkTime+.1,2,7,true]];
      _medic setVariable ["TEST_owner",7];_exit call _tick;
      [_testAnimationSpeed==1,"locality transfer dropped rate ownership without resetting"] call _check;
    ''')


@pytest.mark.parametrize('state',['acm_genericcontinuous','acme_directpressurehold','acme_chestsealworkspace','acme_junctionalwork'])
@pytest.mark.parametrize('weapon',['rifle','pistol'])
def test_stable_empty_hand_medical_pose_never_replays_weapon_holster(state,weapon):
    code=pressure_source('medicAnimationPrep').replace('handgunWeapon _medic','"pistol"')
    code=code.replace('_medic selectWeapon "";', '_dpWeapon="";_clears=_clears+1;')
    execute(pressure_setup()+'ACME_fnc_medicAnimationPrep={'+code+'};'+f'''
      private _clears=0;_animation="{state}";_dpWeapon="{weapon}";
      [[_medic] call ACME_fnc_medicAnimationPrep==0,"empty pose imposed redraw delay"] call _check;
      [_holsters==0 && {{_dpWeapon==""}} && {{_clears==1}},"empty medical pose redrew a weapon"] call _check;
      [_medic] call ACME_fnc_medicAnimationPrep;
      [_clears==1 && {{_holsters==0}},"repeated empty handoff repeated weapon action"] call _check;
    ''')


@pytest.mark.parametrize('new_owner',[False,True])
def test_menu_exit_speed_cleanup_not_blocked_by_dp_stance(new_owner):
    s=pressure_source('menuPoseStop')
    execute(pressure_setup()+'ACME_fnc_menuPoseStop={'+s+'};'+f'''
      ACME_fnc_providerStanceOwned={{false}};
      _medic setVariable ["ACME_menuPose",[8]];_medic setVariable ["ACME_menuPoseEpoch",8];_medic setVariable ["ACME_menuPoseGenericEpoch",8];
      [_medic,false,8] call ACME_fnc_menuPoseStop;
      [_testAnimationSpeed==1.5,"menu did not start its owned exit"] call _check;
      _medic setVariable ["ACME_DP_Active",true];ACME_fnc_providerStanceOwned={{true}};
      _medic setVariable ["TEST_speedOwner",{str(new_owner).lower()}];
      private _pending=_waits select (count _waits-1);(_pending select 1) call (_pending select 0);
      [_testAnimationSpeed=={1.5 if new_owner else 1},"DP stance stranded menu exit rate or successor was clobbered"] call _check;
    ''')


@pytest.mark.parametrize('kind',['','prime','flush'])
def test_prime_green_pulse_appears_only_before_active_service(kind):
    execute(service_paint_setup()+f'''
      _state=[500,0,false,false,false,"{kind}","reserve",[]];
      [missionNamespace,_patient,"body",false,0,true] call _paint;private _first=+_background;
      _nowTime=_nowTime+.25;[missionNamespace,_patient,"body",false,0,true] call _paint;
      [(!(_background isEqualTo _first)) isEqualTo {str(kind=='').lower()},"prime pulse wrong phase"] call _check;
      if ("{kind}"=="") then {{[(_background select 1)>0 && {{(_background select 0)==0}},"prime not green"] call _check;}};
      _state set [4,true];_state set [5,""];
      [missionNamespace,_patient,"body",false,0,true] call _paint;
      [_background isEqualTo [0,0,0,1],"green persisted after priming"] call _check;
    ''')


def saline_paint():
    text=read('updateTransfusionControls');s=text[text.index('private _rl ='):text.index('private _ctrlInject =')]
    s=s.replace('_display displayCtrl 86005','missionNamespace').replace('lbSize _rl','count _rows').replace('_rl lbData _r','(_rows select _r)')
    s=s.replace('_rl lbSetColor [','_colors set [')
    return basic()+'''private _rows=["ACE_salineIV_500|saline","ACM_BloodBag_ON_500|blood","ACE_salineIV|saline"];
      private _colors=[[1,1,1,1],[1,1,1,1],[1,1,1,1]];
      ACME_fnc_isSalineItem={(_this select 1)=="saline"};
    '''+'private _paintSaline={'+adapt(s)+'};'


@pytest.mark.parametrize('finish',['selected','cancelled','inventory-changed'])
def test_saline_pulse_resets_after_selection_or_abandoned_pairing(finish):
    change='missionNamespace setVariable ["ACME_yPendingSaline","selected"];' if finish=='selected' else 'missionNamespace setVariable ["ACME_yPending",""];'
    execute(saline_paint()+'''
      missionNamespace setVariable ["ACME_yPending","blood"];missionNamespace setVariable ["ACME_yPendingSaline",""];
      call _paintSaline;
      [(_colors select 0 select 1)==.95 && {(_colors select 2 select 1)==.95},"saline cue missing"] call _check;
      [(_colors select 1) isEqualTo [1,1,1,1],"blood row painted as saline"] call _check;
    '''+change+'''
      call _paintSaline;
      [(_colors select 0) isEqualTo [1,1,1,1] && {(_colors select 2) isEqualTo [1,1,1,1]},"saline stayed green after selection"] call _check;
    ''')


@pytest.mark.parametrize('bound,key,modifier,closes',[(41,41,False,True),(41,42,False,False),(41,41,True,False),
 (248,248,False,False),(249,249,False,False),(250,250,False,False),(-1,-1,False,False)])
def test_transfusion_only_real_keyboard_binding_closes_display(bound,key,modifier,closes):
    text=(ROOT/'addons/circulation/functions/fnc_openTransfusionMenu.sqf').read_text()
    s=block(text,'_display displayAddEventHandler ["KeyDown",')
    s=s.replace('_dialog closeDisplay 0;', '_closes=_closes+1;')
    execute('private _closes=0;private _reopens=[];ace_medical_gui_fnc_openMenu={};CBA_fnc_execNextFrame={_reopens pushBack _this;};'+
      'private _keyHandler={'+adapt(s)+'};'+f'''
      missionNamespace setVariable ["ACME_TX_CloseKey",{bound}];missionNamespace setVariable ["ACME_TX_CloseTarget",_patient];
      private _r=[missionNamespace,{key},{str(modifier).lower()},false,false] call _keyHandler;
      [_r isEqualTo {str(closes).lower()} && {{_closes=={int(closes)}}} && {{count _reopens=={int(closes)}}},"wheel/mismatched key closed menu"] call _check;
    ''')
    assert 'call CBA_fnc_addKeyHandler' not in text
    assert '_display displayAddEventHandler ["MouseZChanged", {true}];' in text


@pytest.mark.parametrize('part', [2,3,4,5])
@pytest.mark.parametrize('hardcore',[False,True])
def test_ezio_button_has_only_requested_site_label(part,hardcore):
    label='Humeral Head' if part in [2,3] else 'Tibial Tuberosity'
    execute(fn('ivSiteRelabel')+f'''
      missionNamespace setVariable ["ACME_hc_descriptors",{str(hardcore).lower()}];
      [["Insert EZ-IO (old) IO",{part},true,"InsertIO_EZ"] call ACME_fnc_ivSiteRelabel=="Insert EZ-IO ({label})","EZ-IO wording wrong"] call _check;
    ''')


def mask_apply_setup():
    return mask_button_setup()+vent_func('ventMaskApplyStart')+vent_func('ventMaskApplyReply')+'''
      private _reaches=[];private _messages=[];private _replies=[];
      ACME_fnc_headElevMedicSeq={_reaches pushBack _this;};
      ace_common_fnc_displayTextStructured={_messages pushBack _this;};
      ACME_fnc_ownerDispatch={params ["_target","_command","_args"];
        if (_command=="ventMaskApplyReply") then {_replies pushBack _args;};
      };
    '''


def test_attached_mask_acks_one_reach_and_does_not_start_power_or_buy_device():
    execute(mask_apply_setup()+'''
      [[_medic,_patient] call ACME_fnc_ventMaskApplyStart,"mask request refused"] call _check;
      [count _replies==1 && {count _reaches==0},"reach not gated by owner ACK"] call _check;
      [!([_medic,_patient] call ACME_fnc_ventMaskApplyStart),"pending request spammable"] call _check;
      (_replies select 0) call ACME_fnc_ventMaskApplyReply;(_replies select 0) call ACME_fnc_ventMaskApplyReply;
      [count _reaches==1 && {(_reaches select 0 select 1)=="mask"},"ACK replayed/did not play mask reach"] call _check;
      [_patient getVariable ["ACME_vent_nivMask",false],"accepted selection did not fit mask"] call _check;
      [!(_patient getVariable ["ACME_vent_powerOn",false]),"mask selection switched on power"] call _check;
    ''')


@pytest.mark.parametrize('fail',['denied','expired','wrong-pending','unavailable'])
def test_mask_reply_does_not_play_reach_on_invalid_or_late_ack(fail):
    execute(mask_apply_setup()+(' _near=false;' if fail=='denied' else '')+'''
      [_medic,_patient] call ACME_fnc_ventMaskApplyStart;
    '''+{
      'denied':'', 'expired':'_serverTime=104;',
      'wrong-pending':'_medic setVariable ["ACME_ventMaskPending",[999]];',
      'unavailable':'_alive=false;'
    }[fail]+'''
      (_replies select 0) call ACME_fnc_ventMaskApplyReply;
      [count _reaches==0,"invalid mask ACK played provider theatre"] call _check;
    ''')


@pytest.mark.parametrize('variant',['usebvm','usebvm_oxygen','usebvm_vehicleoxygen','usebvm_portableoxygen'])
def test_bvm_acquire_returns_before_any_carrier_or_patient_mutation(variant):
    s=read('chestAccessVestAcquire');s=s[:s.index('private _preserveHeadElevation')]
    execute('private _acquire={'+adapt(s)+'};'+f'''
      _patient setVariable ["ACME_chestAccess_vestBusy","unchanged"];
      [[_patient,_medic,"access",false,"{variant}"] call _acquire,"BVM did not bypass carrier"] call _check;
      [(_patient getVariable "ACME_chestAccess_vestBusy")=="unchanged" && {{count _events==0}},"BVM mutated carrier ownership"] call _check;
    ''')
    classes=re.search(r'private _classes = (\[[^;]+);',read('registerChestAccessVestRuntime'))
    assert classes and variant not in classes[1] and '"cpr"' in classes[1]
    assert '"'+variant+'"' in read('chestAccessVestEvent')


def test_bvm_to_cpr_with_worn_carrier_routes_back_through_preparation():
    text=(ROOT/'addons/breathing/functions/fnc_useBVM.sqf').read_text()
    # Run the actual new terminal branch; setup/episode checks remain in existing native suite.
    start=text.index('if (vest _patient != ""');end=text.index('};',text.index('} else {',start))+2
    s=text[start:end].replace('vest _patient','_vest').replace('isNull objectParent _patient','_onFoot')
    execute('private _vest="carrier";private _onFoot=true;private _prepare=0;private _native=0;'+
      'ace_medical_treatment_fnc_treatment={_prepare=_prepare+1;};ACM_circulation_fnc_beginCPR={_native=_native+1;};'+
      'private _swap={'+adapt(s)+'};'+'''
      call _swap;[_prepare==1 && {_native==0},"BVM skipped carrier prep before CPR"] call _check;
      _vest="";call _swap;[_prepare==1 && {_native==1},"exposed chest failed direct native handoff"] call _check;
      _vest="carrier";_onFoot=false;call _swap;[_prepare==1 && {_native==2},"vehicle BVM forced carrier removal"] call _check;
    ''')


@pytest.mark.parametrize('cls',['ACME_AttachEMMA','ACME_RemoveEMMA','ACME_AttachEMMAETT','ACME_RemoveEMMAETT','ACME_AttachEMMAIGel','ACME_RemoveEMMAIGel'])
def test_all_emma_attachment_actions_are_head_only(cls):
    # Config inheritance may supply the selection from the original head-only parent.
    props={};chain=cls
    for _ in range(10):
      a=ACTIONS.get(chain,{})
      for k,v in a.get('props',{}).items():props.setdefault(k,v)
      chain=a.get('parent','')
      if not chain:break
    assert props['allowedSelections']==['Head']
    assert cls.lower() in (ROOT/'addons/gui/overrides/fnc_updateActions.sqf').read_text()


@pytest.mark.parametrize('cls',['ACME_OpenPlateCarrierInventory','ACME_FlushLine'])
def test_obsolete_actions_not_rendered_or_executable(cls):
    assert ACTIONS[cls]['props']['condition']=='false'
    assert ACTIONS[cls]['props']['allowedSelections']==[]
    assert cls.lower() in (ROOT/'addons/gui/overrides/fnc_updateActions.sqf').read_text()
    wrapper=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    assert 'if (_classname in ["ACME_OpenPlateCarrierInventory", "ACME_FlushLine"]) exitWith {false};' in wrapper


def test_native_holder_and_saline_icon_registered_without_custom_inventory_action():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    assert 'class ACME_RemovedCarrierCargo: GroundWeaponHolder_Scripted' in config
    a=block(config,'class ACME_RemovedCarrierCargo: GroundWeaponHolder_Scripted')
    assert 'simulation = "WeaponHolder";' in a and 'showWeaponCargo = 0;' in a and 'forceSupply = 0;' in a
    assert 'addAction' not in read('carrierInventoryWorld')
    assert 'call ACME_fnc_carrierInventoryWorld' not in read('registerManualPlateCarrierRuntime')
    assert ACTIONS['OpenTransfusionMenu']['props']['ACM_menuIcon']=='ACE_salineIV_500'
    assert 'ACM_MEDICALMENU_ACTION_BUTTON(ACE_salineIV_500,' in (ROOT/'addons/gui/ActionButtons.hpp').read_text()


def test_bandaging_has_direct_unarmed_graph_and_preserves_no_weapon_restore():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    work=block(config,'class ACME_JunctionalWork:')
    assert 'disableWeaponsShort = 1;' in work and 'disableReload = 1;' in work
    assert '"ACM_GenericContinuous", 0.15' in work
    assert 'connectTo[] = {"AinvPknlMstpSnonWnonDnon_medic3", 0.15};' in work
    assert '_emptyHandoff' in read('torsoBandageStart')
    native=(ROOT/'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    assert 'if (_torsoDressing) then {[]} else {weaponState _medic}' in native


def test_testing_mission_loadout_matches_supplied_array_and_retains_partial_stock():
    file=ROOT/'addons/mission/ACM_TestZone.VR/defaultLoadout.sqf'
    text=file.read_text();loadout=json.loads(text[text.index('[[['):].strip().rstrip(';'))
    normalized=json.dumps(loadout,separators=(',',':'),ensure_ascii=False).encode()
    assert hashlib.sha256(normalized).hexdigest()=='97337a6ddc6c6358a35662b6f56c9cba748a7272ef61a7bf9341de05bb00b1c8'
    backpack=loadout[0][5][1]
    assert ['ACM_OxygenTank_425',1,283] in backpack
    assert ['ACM_AmmoniaInhalant',4,8] in backpack
    assert ['ACM_Paracetamol',4,10] in backpack
    assert loadout[0][2][4]==['11Rnd_45ACP_Mag',15]
    assert loadout[1]==[['ace_arsenal_voice','ACE_NoVoice'],['ace_arsenal_face','WhiteHead_24']]
    init=(file.parent/'init.sqf').read_text()
    assert '[_unit, _kit, false] call CBA_fnc_setLoadout;' in init
    assert 'ACME_testZoneKitApplied' in init


@pytest.mark.parametrize('path',['addons/acm_extended/functions/fn_debugMenuClinical.sqf',
 'addons/acm_extended/functions/fn_wakeAnimationEvent.sqf'])
def test_debug_layout_and_patient_wake_presentations_not_redesigned(path):
    baseline=subprocess.check_output(['git','show','f6a9e8d3659ed768d3eaaf452b574a8a14d481ba:'+path],cwd=ROOT)
    assert (ROOT/path).read_bytes()==baseline


@pytest.mark.parametrize('weapon',["rifle","pistol"])
@pytest.mark.parametrize('old_speed',[1.5,10,100])
def test_cancel_during_weapon_preflight_cannot_retain_old_medical_acceleration(weapon,old_speed):
    execute(pressure_setup()+f'''
      _testAnimationSpeed={old_speed};_dpWeapon="{weapon}";_animation="amovpknlmstpsraswrfldnon";
      ["body"] call _start;
      [_testAnimationSpeed==1,"holster began under old accelerated rate"] call _check;
      [false,_medic] call ACME_fnc_directPressureStop;
      [_testAnimationSpeed==1 && {{!(_medic getVariable ["ACME_DP_Active",false])}},"preflight cancel leaked medical rate"] call _check;
    ''')
