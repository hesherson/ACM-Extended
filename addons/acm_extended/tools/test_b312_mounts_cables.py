"""Production mount, USB, cable and persistence decisions; native transforms/RPC are explicit boundaries."""
import json
import os
import re
import subprocess
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, lex, matching
from test_historical_vial_execution import map_defaults
from test_historical_medication_rows import iteration_scopes
from test_b310_world_equipment import setup as world_setup, source as world_source

E=ROOT/'addons/acme_equipment/functions'


def null_boundaries(s):
    ts=lex(s);pairs=matching(ts);edits=[]
    for i,t in enumerate(ts[:-1]):
        if t.kind!='ident' or t.value!='isNull':continue
        start=ts[i+1].offset;last=pairs[i+1] if ts[i+1].value=='(' else i+1
        end=ts[last].offset+len(ts[last].value)
        edits.append((t.offset,end,'('+s[start:end]+' isEqualTo objNull)'))
    for a,b,v in sorted(edits,reverse=True):s=s[:a]+v+s[b:]
    return s


def convert(s):
    s=re.sub(r'(_\w+) isEqualTypeAll 0',r'(\1 findIf {!(_x isEqualType 0)}) < 0',s)
    s=re.sub(r'!finite (_\w+)',r'!(\1 isEqualType 0)',s)
    s=s.replace('canSuspend','false').replace('isServer','_server').replace('isRemoteExecuted','_remote').replace('remoteExecutedOwner','_caller').replace('owner _actor','7')
    s=s.replace('alive _actor','_actorAlive').replace('!isNull objectParent _actor','_mountedActor').replace('isNull objectParent _actor','!_mountedActor')
    s=s.replace('isNull objectParent _patient','!_mountedPatient')
    s=s.replace('getText(configOf _mount >> "ACME_eq_mountKind")','(_mount getVariable ["fixtureMountKind","pro"])')
    for obj in ['_device','_o']:
        s=s.replace('attachedTo '+obj,'('+obj+' getVariable ["fixtureAttached",objNull])')
    s=s.replace('boundingBoxReal _device','[[-0.2,-0.1,-0.15],[0.2,0.1,0.2]]')
    s=s.replace('simulationEnabled _device','(_device getVariable ["fixtureSimulation",true])')
    s=s.replace('_device attachTo [_mount,_offset]','if (_allowAttach) then {_device setVariable ["fixtureAttached",_mount];_device setVariable ["fixtureOffset",_offset]}')
    s=s.replace('detach _device','_device setVariable ["fixtureAttached",objNull]')
    s=s.replace('getPosASL _device','(_device getVariable ["fixturePosition",[100,200,1000]])')
    s=s.replace('vectorDir _device','[0,1,0]').replace('vectorUp _device','[0,0,1]')
    s=s.replace('_device setVectorDirAndUp [_dir,_up]','_device setVariable ["fixtureOrientation",[_dir,_up]]')
    s=s.replace('_device setVectorDirAndUp [[0,1,0],[0,0,1]]','_device setVariable ["fixtureOrientation",[[0,1,0],[0,0,1]]]')
    s=s.replace('_device setPosASL _pos','_device setVariable ["fixturePosition",_pos]')
    s=re.sub(r'(_device|_mount) enableSimulationGlobal ([^;]+);',r'\1 setVariable ["fixtureSimulation",\2];',s)
    for rhs in ['_mount','_device','_ls','_pro']:s=s.replace('_actor distance '+rhs,'_actorRange')
    s=s.replace('_device distance _mount','_mountRange').replace('_ls distance _pro','_linkRange')
    s=s.replace('_device distance _patient','_patientRange').replace('_device distance _usb','_linkRange').replace('_device distance _link','_linkRange')
    s=s.replace('_x distance _usb','_linkDistance')
    s=s.replace('_o distance _usb','_linkRange')
    s=s.replace('_device isKindOf (["ACME_TempusPro","ACME_TempusLS"] select (_kind=="ls"))','_classMatches')
    s=s.replace('_actor isKindOf "CAManBase"','_actorIsHuman')
    s=s.replace('_device isKindOf ((_types get _kind) select 1)','_classMatches')
    s=s.replace('_ls isKindOf "ACME_TempusLS"','_classMatches').replace('_pro isKindOf "ACME_TempusPro"','_classMatches').replace('_usb isKindOf "ACME_TempusPro"','_classMatches')
    s=re.sub(r'(_\w+) isEqualType objNull',r'(\1 isEqualTo objNull || {\1 isEqualType profileNamespace})',s)
    return adapt(map_defaults(iteration_scopes(null_boundaries(s))))


def defs(names):
    return ''.join('ACME_fnc_'+n+'={'+convert((E/('fn_'+n+'.sqf')).read_text())+'};' for n in names)


def setup():
    return world_setup()+'''
      private _server=true;private _caller=7;private _actorAlive=true;private _mountedActor=false;private _mountedPatient=false;
      private _actorRange=1;private _mountRange=1;private _linkRange=1;private _patientRange=1;
      private _allowAttach=true;private _classMatches=true;private _actorIsHuman=true;
      private _device=missionNamespace;private _mount=parsingNamespace;private _actor=_medic;
      private _ls=missionNamespace;private _pro=parsingNamespace;
      _device setVariable ["ACME_eq_kind","pro"];
      _device setVariable ["acme_tempus_pat",_patient];
      _device setVariable ["ACME_eq_patient",_patient];
      private _connections=0;
      ACME_fnc_tempusConnect={params ["_o","_p"];_connections=_connections+1;_o setVariable ["acme_tempus_pat",_p]};
    '''+defs(['equipmentPickupReady','equipmentUsbRelease','equipmentMountApply','equipmentMountRelease','equipmentMountRequest','equipmentLinkRequest','equipmentMonitorTick','equipmentCableSpecs','equipmentCablePose'])


def usb_setup():
    return setup()+'''
      _ls setVariable ["ACME_eq_kind","ls"];
      _ls setVariable ["acme_tempusls_pat",_patient];
      _ls setVariable ["acme_tempusls_pw",[true,10]];
      _pro setVariable ["ACME_eq_kind","pro"];
      _pro setVariable ["acme_tempus_pw",[true,10,false]];
    '''


def persistence_setup():
    return setup()+''.join('ACME_fnc_'+n+'={'+convert(world_source(n))+'};' for n in ['equipmentWorldSchema','equipmentWorldSnapshot','equipmentWorldCaptureValid','equipmentWorldRestore'])


def v2_pair():
    return '''
      private _second=+_row;_second set [0,"device-B"];_second set [1,"ls"];
      _row append [_null,_null];
      _second append [_null,["0:0","old","device-A"]];
      _save=[2,[_row,_second]];
    '''


def test_mount_reuses_device_and_release_preserves_asl_pose_and_simulation():
    execute(setup()+'''
      [_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;
      [(_device getVariable ["fixtureAttached",objNull]) isEqualTo _mount,"mount did not attach"] call _check;
      [(_mount getVariable ["ACME_eq_device",objNull]) isEqualTo _device,"mount occupancy missing"] call _check;
      [abs (((_device getVariable "fixtureOffset") select 2)-0.173)<0.0001,"mount ignored model base"] call _check;
      [!(_device getVariable ["fixtureSimulation",true]),"mounted device still simulates"] call _check;
      _device setVariable ["fixturePosition",[123,456,1001.5]];
      [_actor,_mount,_device,false] call ACME_fnc_equipmentMountRequest;
      [(_device getVariable ["fixtureAttached",_device]) isEqualTo objNull,"release left attachment"] call _check;
      [(_device getVariable "fixturePosition") isEqualTo [123,456,1001.5],"release changed altitude/position"] call _check;
      [(_device getVariable ["fixtureSimulation",false]),"release lost original simulation state"] call _check;
      [count _spawns==0,"mount/release created another monitor"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_server=false;','_remote=true;_caller=8;','_actorAlive=false;','_mountedActor=true;',
    '_actorRange=4;','_mountRange=3;','_classMatches=false;',
    '_actor setVariable ["ACE_isUnconscious",true];','_actor setVariable ["ACME_persistenceFrozen",true];',
    '_patient setVariable ["ACME_persistenceFrozen",true];','_device setVariable ["ACME_eq_busy",true];',
    '_actor setVariable ["ACME_equipmentWorldPending","transfer"];','_mount setVariable ["fixtureMountKind","ls"];',
    '_mount setVariable ["ACME_eq_device",_patient];','_device setVariable ["fixtureAttached",_patient];',
])
def test_mount_request_refuses_invalid_admissions_without_mutating_inventory(change):
    execute(setup()+change+'''
      [_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;
      [!(_device getVariable ["ACME_eq_mounted",false]),"invalid mount admitted"] call _check;
      [count _spawns==0,"invalid mount created device"] call _check;
    ''')


def test_mount_fail_and_duplicate_claim_do_not_steal_occupied_slot():
    execute(setup()+'''
      _allowAttach=false;[_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;
      [(_mount getVariable ["ACME_eq_device",objNull]) isEqualTo objNull,"failed native attachment occupied mount"] call _check;
      _allowAttach=true;[_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;
      private _r=[_patient,_mount,"pro"] call ACME_fnc_equipmentMountApply;
      [!_r && {(_mount getVariable "ACME_eq_device") isEqualTo _device},"second device stole mount"] call _check;
    ''')


def test_usb_is_separate_from_wireless_pairing_and_unplug_keeps_pair():
    execute(usb_setup()+'''
      [_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",objNull]) isEqualTo _pro,"USB not connected"] call _check;
      [(_pro getVariable ["ACME_eq_usbLs",objNull]) isEqualTo _ls,"reverse USB port missing"] call _check;
      [_actor,_ls,objNull,false] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",_ls]) isEqualTo objNull,"USB unplug failed"] call _check;
      [(_ls getVariable ["acme_tempusls_link",objNull]) isEqualTo _pro,"unplug erased Bluetooth pair"] call _check;
      [_connections==1,"USB did not connect unassigned Pro to the LS patient once"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_remote=true;_caller=8;','_actorAlive=false;','_actorRange=4;','_linkRange=3;',
    '_mountedActor=true;','_classMatches=false;',
    '_ls setVariable ["ACME_eq_busy",true];','_pro setVariable ["ACME_eq_busy",true];',
    '_patient setVariable ["ACME_persistenceFrozen",true];','_actor setVariable ["ACME_persistenceFrozen",true];',
    '_pro setVariable ["ACME_eq_usbLs",_patient];','_pro setVariable ["acme_tempus_pat",_actor];',
    '_ls setVariable ["ACME_eq_kind",""];','_pro setVariable ["ACME_eq_kind",""];',
])
def test_usb_request_refuses_invalid_admissions(change):
    execute(usb_setup()+change+'''
      [_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",objNull]) isEqualTo objNull,"invalid USB admitted"] call _check;
      [_connections==0,"invalid USB rebound patient"] call _check;
    ''')


@pytest.mark.parametrize('change',['_linkRange=3;','_ls setVariable ["ACME_eq_busy",true];','_pro setVariable ["acme_tempus_pat",_actor];'])
def test_usb_tick_releases_stretched_busy_or_cross_patient_physical_link(change):
    execute(usb_setup()+'''
      [_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;
    '''+change+'''
      [_ls] call ACME_fnc_equipmentMonitorTick;
      [(_ls getVariable ["ACME_eq_usb",_ls]) isEqualTo objNull,"invalid USB retained"] call _check;
      [(_pro getVariable ["ACME_eq_usbLs",_pro]) isEqualTo objNull,"USB port remained occupied"] call _check;
    ''')


def test_power_cycle_rebuilds_existing_usb_pair_without_rearming_therapy():
    execute(usb_setup()+'''
      [_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;
      _ls setVariable ["acme_tempusls_link",objNull];
      _ls setVariable ["acme_tempusls_armed",false];
      [_ls] call ACME_fnc_equipmentMonitorTick;
      [(_ls getVariable "acme_tempusls_link") isEqualTo _pro,"USB did not rebuild pair"] call _check;
      [!(_ls getVariable ["acme_tempusls_armed",true]),"physical reconnect armed shock"] call _check;
    ''')


def test_native_disconnect_releases_stale_patient_slot_without_moving_monitor():
    execute(setup()+'''
      _patient setVariable ["ACME_eq_pro",_device];_device setVariable ["acme_tempus_pat",objNull];
      [_device] call ACME_fnc_equipmentMonitorTick;
      [(_patient getVariable ["ACME_eq_pro",_patient]) isEqualTo objNull,"disconnected monitor blocked patient's slot"] call _check;
      [(_device getVariable ["ACME_eq_patient",_patient]) isEqualTo objNull,"canonical patient stale"] call _check;
      [count _spawns==0,"disconnect moved/replaced device"] call _check;
    ''')


@pytest.mark.parametrize('sensor,index',[('ecg',0),('spo2',1),('nibp',2),('capno',3),('temp',4)])
def test_each_pro_sensor_gets_exactly_one_corresponding_patient_lead(sensor,index):
    execute(setup()+f'''
      private _flags=[false,false,false,false,false];_flags set [{index},true];
      _device setVariable ["acme_tempus_sensors",_flags];
      [([_device] call ACME_fnc_equipmentCableSpecs) isEqualTo [["{sensor}",_patient,true]],"wrong sensor cable"] call _check;
    ''')


@pytest.mark.parametrize('change',['_mountedPatient=true;','_patientRange=7;','_device setVariable ["ACME_eq_busy",true];','_device setVariable ["acme_tempus_sensors",[false,false,false,false,false]];'])
def test_patient_leads_disappear_when_in_vehicle_out_of_range_disabled_or_busy(change):
    execute(setup()+change+'''[([_device] call ACME_fnc_equipmentCableSpecs) isEqualTo [],"invalid patient cable remained"] call _check;''')


@pytest.mark.parametrize('endpoint',[[101,200,1000],[100,200,1002],[99,200,1000.2],[100,202,1000]])
def test_cable_transforms_keep_raised_altitude_contiguous_endpoints_and_valid_orientation(endpoint):
    execute(setup()+f'''
      private _from=[100,200,1000];private _to={endpoint};
      private _poses=[_from,_to] call ACME_fnc_equipmentCablePose;
      [count _poses==8,"wrong segment budget"] call _check;
      private _last=_from;
      {{_x params ["_p","_d","_u","_len"];
        private _a=_p vectorDiff (_d vectorMultiply (_len/2));
        private _b=_p vectorAdd (_d vectorMultiply (_len/2));
        [_a distance _last<0.001,"cable gap"] call _check;
        [abs (_d vectorDotProduct _u)<0.001 && {{abs (vectorMagnitude _d-1)<0.001}},"invalid segment basis"] call _check;
        [(_p select 2)>=999.98,"raised cable snapped to terrain"] call _check;_last=_b;
      }} forEach _poses;
      [_last distance _to<0.001,"cable missed endpoint"] call _check;
    ''')


def test_v2_restore_rebinds_usb_graph_and_preserves_disarmed_ls_and_legacy_support():
    execute(persistence_setup()+v2_pair()+'''
      [([_save] call ACME_fnc_equipmentWorldRestore) select 0,"v2 graph refused"] call _check;
      [(parsingNamespace getVariable ["ACME_eq_usb",objNull]) isEqualTo missionNamespace,"USB graph not rebound"] call _check;
      [(missionNamespace getVariable ["ACME_eq_usbLs",objNull]) isEqualTo parsingNamespace,"USB reverse port missing"] call _check;
      [!(parsingNamespace getVariable ["acme_tempusls_armed",true]),"restore armed LS"] call _check;
      private _capture=call ACME_fnc_equipmentWorldSnapshot;
      [_capture select 0==2 && {count (((_capture select 1) select 0))==12},"new checkpoint not version 2"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_row set [10,["0:0","old","missing-mount"]];',
    '_second set [11,["0:0","old","missing-Pro"]];',
    '_second set [11,["0:0","old","device-B"]];',
    '_row set [11,["0:0","old","device-B"]];',
])
def test_v2_invalid_mount_and_usb_references_fail_before_spawning(change):
    execute(persistence_setup()+v2_pair()+change+'''
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0) && {count _spawns==0},"invalid v2 relationship allocated device"] call _check;
    ''')


@pytest.mark.parametrize('fail',[False,True])
def test_v2_mount_restore_stages_attachment_before_publishing_or_rolls_back(fail):
    execute(persistence_setup()+v2_pair()+f'''
      private _mount=_medic;_mount setVariable ["fixtureMountKind","pro"];
      ["bind",_mount,"mount-A"] call ACME_fnc_clinicalObjectRef;
      _row set [10,["0:0","old","mount-A"]];_allowAttach={str(not fail).lower()};
      private _result=[_save] call ACME_fnc_equipmentWorldRestore;
      [(_result select 0) isEqualTo {str(not fail).lower()},"attachment outcome ignored"] call _check;
      {'[count _deleted==2 && {isNil {missionNamespace getVariable "ACME_persistenceId"}},"failed mount import published partial state"] call _check;' if fail else '[(missionNamespace getVariable ["fixtureAttached",objNull]) isEqualTo _mount,"mount not rebound"] call _check;[(_mount getVariable "ACME_eq_device") isEqualTo missionNamespace,"mount occupancy not restored"] call _check;'}
    ''')


def visual_setup():
    s=(E/'fn_equipmentCableVisualTick.sqf').read_text().replace('diag_tickTime','_clock')
    s=s.replace('nearestObjects [positionCameraToWorld [0,0,0],["ACME_TempusPro","ACME_TempusLS"],20]','_visualDevices')
    s=s.replace('isObjectHidden _device','_hidden').replace('netId _device','"fixture-device"')
    s=s.replace('createSimpleObject ["\\acme_equipment\\models\\monitor_cable.p3d",_from,true]','call _createSegment')
    s=s.replace('deleteVehicle _x','_deletes=_deletes+1')
    s=s.replace('_segment setPosWorld _pos','_commands pushBack "position"')
    s=s.replace('_segment setVectorDirAndUp [_dir,_up]','_commands pushBack "direction"')
    s=s.replace('_segment setObjectScale _length','_commands pushBack "scale"')
    return setup()+'''
      private _clock=10;private _hidden=false;private _deletes=0;private _visualSpawns=0;private _commands=[];
      private _failSegments=false;private _visualDevices=[_device];private _visualSpecs=[];
      private _fromPoint=[100,200,1000];private _toPoint=[101,200,1000.2];
      private _createSegment={_visualSpawns=_visualSpawns+1;if (_failSegments) then {objNull} else {parsingNamespace}};
      ACME_fnc_equipmentCableSpecs={_visualSpecs};
      ACME_fnc_equipmentCableAnchor={params ["","","_patient"];if (isNil "_patient") then {+_fromPoint} else {+_toPoint}};
    '''+'ACME_fnc_equipmentCableVisualTick={'+convert(s)+'};'


def test_visual_worker_caps_objects_reuses_stationary_segments_and_scales_last():
    execute(visual_setup()+'''
      for "_i" from 1 to 30 do {_visualSpecs pushBack [str _i,_patient,true];};
      call ACME_fnc_equipmentCableVisualTick;
      [_visualSpawns==128 && {count (missionNamespace getVariable "ACME_eqCableCache")==16},"visual object budget exceeded"] call _check;
      private _first=count _commands;
      call ACME_fnc_equipmentCableVisualTick;
      [_visualSpawns==128 && {count _commands==_first},"stationary cables rebuilt or retransformed"] call _check;
      [(_commands select [0,3]) isEqualTo ["position","direction","scale"],"direction reset scale after sizing"] call _check;
      missionNamespace setVariable ["ACME_equipmentCableVisuals",false];call ACME_fnc_equipmentCableVisualTick;
      [_deletes==128 && {count (missionNamespace getVariable "ACME_eqCableCache")==0},"disabled visuals leaked segments"] call _check;
    ''')


def test_visual_allocation_failure_backs_off_then_recovers_without_extending_timer():
    execute(visual_setup()+'''
      _visualSpecs=[["ecg",_patient,true]];_failSegments=true;
      call ACME_fnc_equipmentCableVisualTick;
      [_visualSpawns==8,"failed allocation loop was unbounded"] call _check;
      _clock=11;call ACME_fnc_equipmentCableVisualTick;
      [_visualSpawns==8 && {(missionNamespace getVariable "ACME_eqCableRetryAt")==12},"backoff retried early or perpetually extended"] call _check;
      _clock=12.1;_failSegments=false;call ACME_fnc_equipmentCableVisualTick;
      [_visualSpawns==16 && {count (missionNamespace getVariable "ACME_eqCableCache")==1},"visuals could not recover after failure"] call _check;
    ''')


@pytest.mark.parametrize('change',['_visualSpecs=[];','_hidden=true;','_visualDevices=[];_clock=11;'])
def test_visual_cleanup_on_disconnect_hidden_device_or_camera_scan_change(change):
    execute(visual_setup()+'''
      _visualSpecs=[["ecg",_patient,true]];call ACME_fnc_equipmentCableVisualTick;
    '''+change+'''
      call ACME_fnc_equipmentCableVisualTick;
      [_deletes==8 && {count (missionNamespace getVariable "ACME_eqCableCache")==0},"retired cable leaked segments"] call _check;
    ''')


def test_external_carry_keeps_its_attachment_and_simulation_when_mount_claim_retires():
    execute(setup()+'''
      [_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;
      _device setVariable ["fixtureAttached",_actor];
      [_device] call ACME_fnc_equipmentMonitorTick;
      [(_device getVariable "fixtureAttached") isEqualTo _actor,"mount cleanup detached external carry"] call _check;
      [!(_device getVariable ["fixtureSimulation",true]),"mount cleanup overrode external simulation"] call _check;
      [!(_device getVariable ["ACME_eq_mounted",true]) && {(_mount getVariable ["ACME_eq_device",_mount]) isEqualTo objNull},"mount remained occupied"] call _check;
    ''')


def test_external_carry_is_refused_by_inventory_pickup_admission():
    s=(E/'fn_equipmentRequest.sqf').read_text()
    s=re.sub(r'values (_\w+)',r'((keys \1) apply {\1 get _x})',s)
    execute(setup()+'ACME_fnc_equipmentRequest={'+convert(s)+'''};
      _device setVariable ["fixtureAttached",_actor];
      [_actor,_patient,"pro","pickup",false,[],_device] call ACME_fnc_equipmentRequest;
      [(_actor getVariable ["ACME_equipmentWorldPending",""])=="","external carry started an inventory grant"] call _check;
    ''')


@pytest.mark.parametrize('change',['_actor="bad";','_mount="bad";','_device=17;'])
def test_malformed_mount_rpc_objects_are_refused_without_native_access_errors(change):
    execute(setup()+change+'''[_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;[count _spawns==0,"malformed RPC spawned equipment"] call _check;''')


@pytest.mark.parametrize('change',['_actor="bad";','_ls="bad";','_pro=17;'])
def test_malformed_usb_rpc_objects_are_refused_without_native_access_errors(change):
    execute(usb_setup()+change+'''[_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;[_connections==0,"malformed RPC connected patient"] call _check;''')


def test_snapshot_refuses_unsupported_external_attachment_instead_of_losing_it():
    execute(persistence_setup()+'''
      [_save] call ACME_fnc_equipmentWorldRestore;
      missionNamespace setVariable ["fixtureAttached",_medic];
      [(call ACME_fnc_equipmentWorldSnapshot) isEqualTo [],"external attachment was silently lost from checkpoint"] call _check;
    ''')


def test_vent_model_binding_handoff_does_not_require_immediate_native_deletion():
    from test_b310_vent_model_swap import setup as vent_setup
    code=vent_setup().replace('_deleted pushBack _old;(missionNamespace getVariable "ACME_clinicalObjectBindings") set [_durable,objNull]','_deleted pushBack _old')
    execute(code+'''
      [_patient,true] call ACME_fnc_equipmentVent;
      [(_new getVariable ["ACME_persistenceId",""])=="vent-A","queued deletion blocked replacement identity"] call _check;
      [(_old getVariable ["ACME_persistenceId","old"])=="","retired live object still claims durable ID"] call _check;
    ''')


def test_mount_deleted_handler_is_registered_once_and_releases_existing_device():
    s=(E/'fn_equipmentMountInit.sqf').read_text()
    s=s.replace('_mount addEventHandler ["Deleted",','_registrations=_registrations+1;_deletedHandler=(["Deleted",').replace('}];','}] select 1);')
    execute(setup()+'''
      private _registrations=0;private _deletedHandler={};
    '''+'ACME_fnc_equipmentMountInit={'+convert(s)+'''};
      [_mount] call ACME_fnc_equipmentMountInit;[_mount] call ACME_fnc_equipmentMountInit;
      [_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;
      _device setVariable ["fixturePosition",[123,456,1001.5]];
      [_mount] call _deletedHandler;
      [_registrations==1,"mount deletion handler duplicated"] call _check;
      [!(_device getVariable ["ACME_eq_mounted",true]) && {(_device getVariable "fixturePosition") isEqualTo [123,456,1001.5]},"deleted mount stranded device"] call _check;
      [count _spawns==0 && {count _deleted==0},"deleted mount recreated or destroyed monitor"] call _check;
    ''')


def test_frozen_pro_patient_prevents_unplugging_an_unassigned_ls():
    execute(usb_setup()+'''
      [_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;
      _ls setVariable ["acme_tempusls_pat",objNull];_patient setVariable ["ACME_persistenceFrozen",true];
      [_actor,_ls,objNull,false] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",objNull]) isEqualTo _pro,"unplug bypassed other endpoint's checkpoint fence"] call _check;
    ''')


def test_mount_and_usb_references_survive_snapshot_and_undocking_invalidates_capture():
    execute(persistence_setup()+v2_pair()+'''
      private _mount=_medic;_mount setVariable ["fixtureMountKind","pro"];
      ["bind",_mount,"mount-A"] call ACME_fnc_clinicalObjectRef;
      _row set [10,["0:0","old","mount-A"]];
      [([_save] call ACME_fnc_equipmentWorldRestore) select 0,"mounted checkpoint restore failed"] call _check;
      private _capture=call ACME_fnc_equipmentWorldSnapshot;
      [(_capture select 0)==2 && {((((_capture select 1) select 0) select 10) select 2)=="mount-A"},"mount ID not captured"] call _check;
      [[_capture] call ACME_fnc_equipmentWorldCaptureValid,"settled mount checkpoint failed final validation"] call _check;
      [missionNamespace] call ACME_fnc_equipmentMountRelease;
      [!([_capture] call ACME_fnc_equipmentWorldCaptureValid),"undocking did not invalidate old checkpoint"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_mount setVariable ["ACME_eq_device",_patient];',
    '_mount setVariable ["fixtureMountKind","ls"];',
])
def test_restore_refuses_occupied_or_wrong_model_mount_before_creation(change):
    execute(persistence_setup()+v2_pair()+'''
      private _mount=_medic;_mount setVariable ["fixtureMountKind","pro"];
      ["bind",_mount,"mount-A"] call ACME_fnc_clinicalObjectRef;
      _row set [10,["0:0","old","mount-A"]];
    '''+change+'''
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0) && {count _spawns==0},"conflicting mount allocated devices"] call _check;
    ''')


def test_schema_refuses_two_ls_units_using_one_usb_port():
    execute(persistence_setup()+v2_pair()+'''
      private _third=+_second;_third set [0,"device-C"];_third set [6,_null];
      (_save select 1) pushBack _third;
      [!([_save] call ACME_fnc_equipmentWorldSchema),"one USB port assigned twice"] call _check;
    ''')


@pytest.mark.parametrize('points',[
    '[[0,0,0],[0,0,0]]','[[0,0,0],[8,0,0]]','["bad",[0,0,0]]','[[0,0,0],[0,"bad",0]]'
])
def test_cable_geometry_refuses_invalid_or_unbounded_endpoints(points):
    execute(setup()+f'[{points} call ACME_fnc_equipmentCablePose isEqualTo [],"invalid cable geometry accepted"] call _check;')


def test_mount_and_usb_helpers_have_no_inventory_grant_or_server_visual_rpc():
    config=(ROOT/'addons/acme_equipment/config.cpp').read_text()
    for name in ['equipmentMountRequest','equipmentLinkRequest']:
        assert re.search('class ACME_fnc_'+name+r'\s*\{allowedTargets=2;',config)
    for name in ['equipmentMountApply','equipmentMountRelease','equipmentCableVisualTick']:
        assert 'class ACME_fnc_'+name not in config
    for name in ['equipmentMountApply','equipmentMountRelease','equipmentMountRequest','equipmentLinkRequest']:
        s=(E/('fn_'+name+'.sqf')).read_text()
        assert not re.search(r'\b(addItem|addItemCargoGlobal|createVehicle|removeItem|deleteVehicle|execVM|compile)\b',s)
        assert 'if (canSuspend)' in s
    s=(E/'fn_equipmentCableVisualTick.sqf').read_text()
    assert 'ropeCreate' not in s and 'remoteExec' not in s
    assert 'if (!hasInterface)' in s and 'true]' in s


def test_old_release_packet_cannot_undock_a_new_mount_episode():
    execute(setup()+'''
      _remote=true;_caller=7;
      [_actor,_mount,_device,true,0] call ACME_fnc_equipmentMountRequest;
      [_actor,_mount,_device,false,1] call ACME_fnc_equipmentMountRequest;
      [_actor,_mount,_device,true,1] call ACME_fnc_equipmentMountRequest;
      [_actor,_mount,_device,false,1] call ACME_fnc_equipmentMountRequest;
      [(_device getVariable ["ACME_eq_mounted",false]) && {(_device getVariable "ACME_eq_mountEpoch")==2},"old release undocked a newer episode"] call _check;
    ''')


def test_old_mount_packet_cannot_reclaim_released_mount_and_fresh_request_still_works():
    execute(setup()+'''
      _remote=true;_caller=7;
      [_actor,_mount,_device,true,0] call ACME_fnc_equipmentMountRequest;
      [_actor,_mount,_device,false,1] call ACME_fnc_equipmentMountRequest;
      [_actor,_mount,_device,true,0] call ACME_fnc_equipmentMountRequest;
      [!(_device getVariable ["ACME_eq_mounted",true]),"old mount packet reclaimed station"] call _check;
      [_actor,_mount,_device,true,1] call ACME_fnc_equipmentMountRequest;
      [_device getVariable ["ACME_eq_mounted",false],"new mount request blocked by retired episode"] call _check;
    ''')


def test_old_unplug_packet_cannot_disconnect_a_new_usb_episode():
    execute(usb_setup()+'''
      _remote=true;_caller=7;
      [_actor,_ls,_pro,true,0] call ACME_fnc_equipmentLinkRequest;
      [_actor,_ls,objNull,false,1] call ACME_fnc_equipmentLinkRequest;
      [_actor,_ls,_pro,true,2] call ACME_fnc_equipmentLinkRequest;
      [_actor,_ls,objNull,false,1] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",objNull]) isEqualTo _pro && {(_ls getVariable "ACME_eq_usbEpoch")==3},"old unplug disconnected a newer USB episode"] call _check;
    ''')


def test_automatic_usb_break_retires_old_remote_connect_context():
    execute(usb_setup()+'''
      _remote=true;_caller=7;[_actor,_ls,_pro,true,0] call ACME_fnc_equipmentLinkRequest;
      _linkRange=3;[_ls] call ACME_fnc_equipmentMonitorTick;
      _linkRange=1;[_actor,_ls,_pro,true,1] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",objNull]) isEqualTo objNull,"retired connect context reapplied after a broken cable"] call _check;
      [_actor,_ls,_pro,true,2] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",objNull]) isEqualTo _pro,"fresh connect could not follow cable break"] call _check;
    ''')


def test_staged_restore_objects_cannot_be_claimed_as_inventory_during_rollback():
    s=(E/'fn_equipmentRequest.sqf').read_text()
    s=re.sub(r'values (_\w+)',r'((keys \1) apply {\1 get _x})',s)
    execute(setup()+'ACME_fnc_equipmentRequest={'+convert(s)+'''};
      _device setVariable ["ACME_eq_restoreStaged",true];
      [_actor,_patient,"pro","pickup",false,[],_device] call ACME_fnc_equipmentRequest;
      [(_actor getVariable ["ACME_equipmentWorldPending",""])=="","staged object admitted an inventory grant"] call _check;
    ''')


def test_mounted_inventory_pickup_releases_mount_and_grants_exactly_once():
    from test_b308_patient_equipment import setup as request_setup
    execute(setup()+request_setup()+'''
      [_deviceFixture,_mount,"pro"] call ACME_fnc_equipmentMountApply;
      [_medic,_patient,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==1 && {(_mount getVariable ["ACME_eq_device",_mount]) isEqualTo objNull},"pickup did not release mount before transfer"] call _check;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==2,"duplicate inventory delivery granted another monitor"] call _check;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;(_acks select 0) call ACME_fnc_equipmentAck;
      [_deleted==1 && {_stock==2},"pickup acknowledgement duplicated or lost mounted monitor"] call _check;
    ''')


def test_tiny_idle_cable_motion_does_not_retransform_every_segment():
    execute(visual_setup()+'''
      _visualSpecs=[["ecg",_patient,true]];call ACME_fnc_equipmentCableVisualTick;
      private _count=count _commands;
      _toPoint=_toPoint vectorAdd [0.001,0,0];call ACME_fnc_equipmentCableVisualTick;
      [count _commands==_count,"submillimetre idle motion retransformed all cable segments"] call _check;
      _toPoint=_toPoint vectorAdd [0.003,0,0];call ACME_fnc_equipmentCableVisualTick;
      [count _commands==_count+24,"visible endpoint motion did not update existing segments"] call _check;
      [_visualSpawns==8,"endpoint motion recreated cable objects"] call _check;
    ''')


@pytest.mark.parametrize('endpoint',['mount','usb'])
def test_owned_vehicle_or_nonhuman_actor_cannot_impersonate_an_on_foot_operator(endpoint):
    execute((setup() if endpoint=='mount' else usb_setup())+'''
      _actorIsHuman=false;
    '''+('[_actor,_mount,_device,true] call ACME_fnc_equipmentMountRequest;' if endpoint=='mount' else '[_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;')+'''
      [!(_device getVariable ["ACME_eq_mounted",false]) && {_connections==0},"nonhuman actor admitted physical interaction"] call _check;
    ''')
