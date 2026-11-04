"""Execute actual equipment and shared-cooler lifetimes. Native objects/RPC/UI are explicit boundaries."""
from pathlib import Path
import json
import math
import re
import struct
import subprocess
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_historical_vial_execution import map_defaults
from test_b287_cooler_timing import fixture as cold_fixture, source as cold_source
from test_b306_tempus_clinical import shock_setup, pacing_setup
from test_b307_tempus_lifetimes import charge_setup

E=ROOT/'addons/acme_equipment/functions'

def raw(name):
    return (E/f'fn_{name}.sqf').read_text()

def converted(name):
    s=raw(name).replace('serverTime','_clock')
    s=s.replace('nearestObjects [_patient,[(_types get _kind) select 1],8]','_nearby')
    s=s.replace('isRemoteExecuted','_remote').replace('remoteExecutedOwner','_caller').replace('owner _actor','7')
    s=s.replace('alive _actor','_actorAlive').replace('local _actor','true')
    s=s.replace('_actor distance _patient','_distance').replace('_actor distance _box','_distance').replace('_actor distance _device','_distance')
    s=s.replace('isNull objectParent _actor','true').replace('objectParent _patient','objNull')
    s=s.replace('_actor getVariable ["ACE_isUnconscious",false]','false')
    s=s.replace('_device isKindOf ((_types get _kind) select 1)','true')
    # Retained fixtures represent unparented field devices; B312 separately
    # executes the external-carry admission guard with an actual attachment boundary.
    s=s.replace('isNull attachedTo _device','true')
    s=s.replace('vectorDir _actor','[0,1,0]').replace('ASLToAGL (_pose select 0)','(_pose select 0)')
    s=s.replace('_o=createVehicle [_r get "class",(_pose select 0),[],0,"CAN_COLLIDE"]','_spawnCount=_spawnCount+1;_o=_deviceFixture')
    s=s.replace('deleteVehicle _device','_deleted=_deleted+1')
    s=s.replace('_actor canAdd _item','true').replace('_actor addItem _item','_stock=_stock+1')
    s=re.sub(r'values (_\w+)',r'((keys \1) apply {\1 get _x})',s)
    # Fixed transport endpoints. Invocations are delivered explicitly by each test.
    s=s.replace('[_actor,_id,_record get "phase",_item] remoteExecCall ["ACME_fnc_equipmentInventory",_actor]', '_inventoryMessages pushBack [_actor,_id,_record get "phase",_item]')
    s=s.replace('[_actor,_id,_operation,_ok] remoteExecCall ["ACME_fnc_equipmentAck",2]', '_acks pushBack [_actor,_id,_operation,_ok]')
    s=s.replace('[_o,_patient] remoteExecCall ["ACME_fnc_tempusFeed",_patient]', '_feeds=_feeds+1')
    s=s.replace('[_o,_patient] remoteExecCall ["ACME_fnc_tempusLsFeed",_patient]', '_feeds=_feeds+1')
    s=s.replace('[_actor,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select (_kind=="ls"),_patient]', '_feeds=_feeds+1')
    s=s.replace('[_actor,_id,"refund",_r get "item"] remoteExecCall ["ACME_fnc_equipmentInventory",_actor]','_refundMessages pushBack [_actor,_id,"refund",_r get "item"]')
    return adapt(map_defaults(s))

def setup():
    return '''
      private _clock=10;private _remote=true;private _caller=7;private _actorAlive=true;private _distance=1;
      private _stock=1;private _spawnCount=0;private _deleted=0;private _feeds=0;
      private _inventoryMessages=[];private _acks=[];private _refundMessages=[];private _nearby=[];
      private _deviceFixture=missionNamespace;
      ACME_fnc_itemCount={_stock};
      ACME_fnc_itemTake={if (_stock<1) exitWith {false};_stock=_stock-1;true};
      ACME_fnc_equipmentPose={[[100,200,1000],[0,1,0]]};
      ACME_fnc_equipmentSeat={};ACME_fnc_tempusLsChargeClear={};
      private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    '''+''.join(f'ACME_fnc_{n}={{'+converted(n)+'};' for n in ['equipmentRequest','equipmentInventory','equipmentAck'])


@pytest.mark.parametrize('kind',['pro','ls','accu'])
def test_setup_debits_one_item_only_and_duplicate_acks_never_spawn_again(kind):
    execute(setup()+f'''
      [_medic,_patient,"{kind}"] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==1,"setup not admitted"] call _check;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==0,"duplicate inventory delivery debited twice"] call _check;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      (_acks select 0) call ACME_fnc_equipmentAck;
      [_spawnCount==1,"duplicate ack spawned another device"] call _check;
      [(_patient getVariable ["ACME_eq_{kind}",objNull]) isEqualTo _deviceFixture,"patient lost default equipment slot"] call _check;
      [(_medic getVariable ["ACME_equipmentWorldPending","busy"])=="","terminal request blocked persistence"] call _check;
    ''')


@pytest.mark.parametrize('kind',['pro','ls','accu'])
def test_two_providers_cannot_reserve_same_default_slot(kind):
    execute(setup()+f'''
      [_medic,_patient,"{kind}"] call ACME_fnc_equipmentRequest;
      _remote=false;[parsingNamespace,_patient,"{kind}"] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==1,"concurrent providers reserved one slot twice"] call _check;
    ''')


@pytest.mark.parametrize('change',['_caller=8;','_actorAlive=false;','_distance=5;'])
def test_invalid_setup_cannot_debit_inventory(change):
    execute(setup()+change+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==0 && {_stock==1},"invalid setup debited inventory"] call _check;
    ''')


def test_late_inventory_delivery_requires_current_pending_identity():
    execute(setup()+'''
      _medic setVariable ["ACME_equipmentWorldPending","current"];
      _caller=2;[_medic,"retired","take","ACM_ACCUVAC"] call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==0},"retired inventory command stole a later item"] call _check;
    ''')


def test_unproven_ack_cannot_fund_a_world_device():
    execute(setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      private _message=_inventoryMessages select 0;
      [_medic,_message select 1,"take",true] call ACME_fnc_equipmentAck;
      [_spawnCount==0 && {_stock==1},"ack without physical debit funded device"] call _check;
    ''')


@pytest.mark.parametrize('kind,expected',[('vent',[.65,.7]),('accu',[-.65,.7]),('pro',[.8,-.1]),('ls',[1.3,-.4])])
def test_dedicated_anatomical_layout(kind,expected):
    execute('ACME_fnc_equipmentLayout={'+raw('equipmentLayout')+'};'+f'[["{kind}"] call ACME_fnc_equipmentLayout isEqualTo {expected},"wrong dedicated offset"] call _check;')


@pytest.mark.parametrize('head',[ [100,201,1000],[101,200,1000],[100,199,1000],[99,200,1000] ])
def test_pose_preserves_raised_surface_and_patient_relative_right(head):
    pose=raw('equipmentPose')
    pose=pose.replace('_patient modelToWorldVisualWorld (_patient selectionPosition "pelvis")','[100,200,1000]')
    pose=pose.replace('_patient modelToWorldVisualWorld (_patient selectionPosition "head")',str(head))
    pose=pose.replace('vectorDirVisual _patient','[0,1,0]')
    pose=re.sub(r'lineIntersectsSurfaces \[[^;]+\]', '[[[_position select 0,_position select 1,999.75]]]',pose)
    execute('ACME_fnc_equipmentLayout={'+raw('equipmentLayout')+'};ACME_fnc_equipmentPose={'+pose+'''};
      private _vent=[_patient,"vent"] call ACME_fnc_equipmentPose;
      private _accu=[_patient,"accu"] call ACME_fnc_equipmentPose;
      [abs (((_vent select 0) select 2)-999.75)<0.001,"surface altitude was replaced by terrain"] call _check;
      [abs (((_vent select 0) distance (_accu select 0))-1.3)<0.001,"left and right devices overlap"] call _check;
    ''')


def test_persistent_cooling_and_warm_use_are_real_time():
    execute(cold_fixture()+'''
      missionNamespace setVariable ["ACME_persistentCampaignTiming",true];
    '''+'ACME_fnc_bloodTimingApply={'+cold_source('bloodTimingApply')+'''};
      call ACME_fnc_bloodTimingApply;
      [ACME_bloodLooseSpoilTime==14400,"persistent use window is compressed"] call _check;
      [["ACME_BloodCooler_CSWB1U"] call ACME_fnc_coolerColdChainTime==172800,"1U duration incorrect"] call _check;
      [["ACME_BloodCooler_CSWB2U"] call ACME_fnc_coolerColdChainTime==86400,"2U duration incorrect"] call _check;
      [["ACME_BloodCooler_CSWB4U"] call ACME_fnc_coolerColdChainTime==259200,"4U duration incorrect"] call _check;
      private _state=[["ACME_BloodCooler_CSWB1U",0,[[_bag,0]],172799],172900] call ACME_fnc_coolerAdvance;
      [((_state select 2) select 0) select 1==100,"warm tail not charged at real time"] call _check;
    ''')


@pytest.mark.parametrize('volume',[250,500,1000])
def test_spoiled_class_preserves_original_volume(volume):
    execute(cold_fixture()+f'''
      private _class=["ACM_BloodBag_ON_{volume}"] call ACME_fnc_bloodSpoiledClass;
      [[_class] call ACME_fnc_coolerBagVolume=={volume},"spoilage altered cooler capacity"] call _check;
    ''')


def test_accuvac_rotation_updates_every_point_and_normal_without_other_mesh_changes():
    path=ROOT/'addons/acme_accuvac/accuvac_rescue.p3d'
    previous=subprocess.check_output(['git','show','3cc73d55:addons/acme_accuvac/accuvac_rescue.p3d'],cwd=ROOT)
    current=path.read_bytes();expected=bytearray(previous)
    assert len(current)==len(previous)
    cursor=12;lod_count=struct.unpack_from('<I',previous,8)[0]
    for _ in range(lod_count):
        off=previous.find(b'P3DM',cursor);assert off>=0
        _,_,points,normals,_,_=struct.unpack_from('<6I',previous,off+4)
        start=off+28
        for i in range(points):
            x,y,z=struct.unpack_from('<3f',previous,start+16*i)
            struct.pack_into('<3f',expected,start+16*i,x,-y,-z)
        start+=points*16
        for i in range(normals):
            x,y,z=struct.unpack_from('<3f',previous,start+12*i)
            struct.pack_into('<3f',expected,start+12*i,x,-y,-z)
        cursor=start+normals*12
    assert current==bytes(expected)
    assert lod_count==10


@pytest.mark.parametrize('kind,prefix',[('pro','acme_tempus'),('ls','acme_tempusls')])
def test_manual_monitor_is_reused_without_repositioning_or_new_item_debit(kind,prefix):
    execute(setup()+f'''
      _deviceFixture setVariable ["{prefix}_pat",_patient];
      _deviceFixture setVariable ["ACME_eq_manual",true];
      _nearby=[_deviceFixture];
      [_medic,_patient,"{kind}"] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==0 && {{_stock==1}} && {{_spawnCount==0}},"manual placement was replaced"] call _check;
    ''')


@pytest.mark.parametrize('invalidate',['_distance=5;','ACME_fnc_equipmentPose={[]};'])
def test_failed_post_debit_placement_refunds_once_and_rejects_retired_commands(invalidate):
    execute(setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
    '''+invalidate+'''
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_spawnCount==0 && {count _refundMessages==1},"unsafe placement created a world object"] call _check;
      _caller=2;(_refundMessages select 0) call ACME_fnc_equipmentInventory;
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1,"refund delivery duplicated or lost inventory"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1,"late debit consumed refunded equipment"] call _check;
    ''')


def test_spoiled_bag_stays_in_its_original_full_inventory_container():
    text=(ROOT/'addons/acm_extended/functions/fn_ccApply.sqf').read_text()
    text=text.replace('local _unit','true').replace('uniformContainer _unit','_patient')
    text=text.replace('vestContainer _unit','objNull').replace('backpackContainer _unit','objNull')
    text=text.replace('itemCargo _x','_inventory').replace('_unit canAdd _new','false')
    text=text.replace('_destination addItemCargoGlobal [_new,1]','_inventory pushBack _new')
    execute('''
      private _inventory=["ACM_BloodBag_ON_500"];
      ACME_fnc_itemTake={params ["","_class"];private _at=_inventory find _class;if (_at<0) exitWith {false};_inventory deleteAt _at;true};
      ace_common_fnc_displayTextStructured={};
      ACME_fnc_ccApply={'''+adapt(text)+'''};
      [_medic,["ACM_BloodBag_ON_500"],["ACME_SpoiledBlood_500"]] call ACME_fnc_ccApply;
      [_inventory isEqualTo ["ACME_SpoiledBlood_500"],"spoiled bag was dropped, lost or duplicated"] call _check;
      [_medic,["ACM_BloodBag_ON_500"],["ACME_SpoiledBlood_500"]] call ACME_fnc_ccApply;
      [_inventory isEqualTo ["ACME_SpoiledBlood_500"],"failed removal created duplicate spoiled blood"] call _check;
    ''')


def test_shared_cooler_stays_open_until_last_viewer_closes_or_times_out():
    lease=converted('equipmentCoolerLease')
    lease=lease.replace('typeOf _box','"ACME_BloodCoolerBox_CSWB1U"')
    tick=converted('equipmentTick')
    tick=tick.replace('!isNull (_x select 0)','!((_x select 0) isEqualTo objNull)').replace('alive (_x select 0)','true').replace('(_x select 0) distance _box','_distance')
    execute(setup()+'''
      private _sounds=0;private _box=_deviceFixture;
      ACME_fnc_worldSfxNearby={_sounds=_sounds+1};
      ACME_fnc_equipmentCoolerLease={'''+lease+'''};
      ACME_fnc_equipmentTick={'''+tick+'''};
      [_medic,_box,true] call ACME_fnc_equipmentCoolerLease;
      [_patient,_box,true] call ACME_fnc_equipmentCoolerLease;
      call ACME_fnc_equipmentTick;
      [(_box getVariable ["ACME_eqCoolerOpen",false]) && {_sounds==1},"shared open did not produce one transition"] call _check;
      [_medic,_box,false] call ACME_fnc_equipmentCoolerLease;
      call ACME_fnc_equipmentTick;
      [(_box getVariable ["ACME_eqCoolerOpen",false]) && {_sounds==1},"one viewer closed another viewer's cooler"] call _check;
      _clock=17;call ACME_fnc_equipmentTick;
      [!(_box getVariable ["ACME_eqCoolerOpen",true]) && {_sounds==2},"abandoned cooler did not close once"] call _check;
    ''')


@pytest.mark.parametrize('addon,key',[('acme_tempus','ACME_Tempus_Key'),('acme_tempusls','ACME_TempusLS_Key')])
def test_monitor_keys_are_transparent_and_inventory_category_is_medical(addon,key):
    config=(ROOT/'addons'/addon/'config.cpp').read_text()
    block=config.split('class '+key+' : RscButton {',1)[1].split('};',1)[0]
    assert 'colorBackgroundActive[] = {0, 0, 0, 0};' in config
    assert 'colorBorder[] = {0, 0, 0, 0};' in config
    assert 'ACE_isMedicalItem = 1;' in config
    assert ': ACE_ItemCore {' in config
    assert 'ctrlSetTooltip' in (ROOT/'addons'/addon/'functions'/('fn_tempusUiOnLoad.sqf' if addon=='acme_tempus' else 'fn_tempusLsUiOnLoad.sqf')).read_text()


def test_removed_ls_pads_block_shock_charge_and_capture():
    execute(shock_setup()+'''
      _o setVariable ["acme_tempusls_pads",false];_request call ACME_fnc_tempusLsShock;
      [count _calls==0,"removed pads still shocked"] call _check;
    ''')
    execute(charge_setup()+'''
      _o setVariable ["acme_tempusls_pads",false];
      [([_o,"begin",150] call ACME_fnc_tempusLsCharge) isEqualTo [],"removed pads charged"] call _check;
    ''')
    execute(pacing_setup()+'''
      _device setVariable ["acme_tempusls_pads",false];
      _patient setVariable ["acme_tempusls_paceSet",_settings];
      [[_patient,40] call ACME_fnc_tempusLsPacingRate==40,"removed pads captured"] call _check;
    ''')


def test_pro_sensor_removal_masks_readings_and_menu_nibp_request_runs_once():
    text=(ROOT/'addons/acme_tempus/functions/fn_tempusPush.sqf').read_text()
    text=text.replace('_c ctrlWebBrowserAction [','_messages pushBack [')
    # VM has no linearConversion; the unrelated perfusion-index decoration is a native boundary.
    text=text.replace('linearConversion [60, 120, _sys, 4, 60, true]','4')
    execute('''
      private _c=uiNamespace;private _o=missionNamespace;private _messages=[];
      _c setVariable ["acme_tempus_ready",true];
      _o setVariable ["acme_tempus_pat",_patient];
      _o setVariable ["acme_tempus_v",[80,80,0,120,80,98,12,35,37]];
      _o setVariable ["acme_tempus_sensors",[false,false,false,false,false]];
      _o setVariable ["ACME_eq_nibpRequest",10];
      ACME_fnc_tempusWaveforms={};ACME_fnc_tempusPush={'''+adapt(text)+'''};
      [_c,_o,true] call ACME_fnc_tempusPush;[_c,_o,false] call ACME_fnc_tempusPush;
      private _v=_c getVariable ["acme_tempus_sV",[]];
      [_v isEqualTo [-1,-1,0,-1,-1,-1,-1,-1,-1],"detached sensor still reported readings"] call _check;
      [{(_x select 1)=="tp.key('nibp')"} count _messages==1,"NIBP request duplicated"] call _check;
      _o setVariable ["acme_tempus_sensors",[false,true,false,false,false]];
      [_c,_o,false] call ACME_fnc_tempusPush;
      private _v=_c getVariable ["acme_tempus_sV",[]];
      [(_v select 0)==80 && {(_v select 5)==98} && {(_v select 1)==-1},"SpO2 failed to supply pulse without ECG"] call _check;
    ''')
