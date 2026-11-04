"""Execute custody checks around owner inventory delivery; native attachments/RPC are explicit boundaries."""
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute
from test_b308_patient_equipment import setup as transfer_setup
from test_b312_mounts_cables import setup as mount_setup, usb_setup

E=ROOT/'addons/acme_equipment/functions'


def setup():
    return mount_setup()+transfer_setup()+'''
      _deviceFixture setVariable ["ACME_eq_kind","pro"];
      _deviceFixture setVariable ["acme_tempus_pat",_patient];
      _deviceFixture setVariable ["ACME_eq_patient",_patient];
    '''


@pytest.mark.parametrize('kind',['pro','ls','accu'])
@pytest.mark.parametrize('claim',['stale','missing_mount','wrong_occupant','no_claim'])
def test_external_parent_is_refused_even_before_reconciler_retires_claim(kind,claim):
    changes={
        'stale':'_deviceFixture setVariable ["fixtureAttached",_medic];',
        'missing_mount':'_deviceFixture setVariable ["ACME_eq_mount",objNull];',
        'wrong_occupant':'_mount setVariable ["ACME_eq_device",_patient];',
        'no_claim':'_deviceFixture setVariable ["ACME_eq_mounted",false];',
    }
    execute(setup()+'''
      [_deviceFixture,_mount,"pro"] call ACME_fnc_equipmentMountApply;
    '''+changes[claim]+f'''
      private _parent=_deviceFixture getVariable "fixtureAttached";
      [_medic,_patient,"{kind}","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==0 && {{_stock==1}} && {{_deleted==0}},"unsupported custody admitted inventory pickup"] call _check;
      [(_deviceFixture getVariable "fixtureAttached") isEqualTo _parent,"rejected pickup detached external parent"] call _check;
      [!(_deviceFixture getVariable ["ACME_eq_busy",false]),"rejected pickup reserved device"] call _check;
    ''')


@pytest.mark.parametrize('kind',['pro','ls','accu'])
def test_takeover_during_inventory_delivery_defers_commit_and_retries_one_credit(kind):
    execute(setup()+f'''
      [_medic,_patient,"{kind}","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==1,"valid pickup refused"] call _check;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==2,"owner credit missing"] call _check;
      _deviceFixture setVariable ["ACME_eq_mounted",true];
      _deviceFixture setVariable ["ACME_eq_mount",_mount];
      _deviceFixture setVariable ["fixtureAttached",_medic];
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_deleted==0 && {{(_deviceFixture getVariable "fixtureAttached") isEqualTo _medic}},"commit deleted external carry"] call _check;
      [(_medic getVariable ["ACME_equipmentWorldPending",""])!="" && {{_deviceFixture getVariable ["ACME_eq_busy",false]}},"deferred pickup lost reservation"] call _check;
      [_medic,_patient,"{kind}"] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==1,"deferred actor reused pending credit for setup"] call _check;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==2,"retry duplicated owner credit"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [_deleted==0,"retry deleted carried device"] call _check;
      _deviceFixture setVariable ["fixtureAttached",objNull];
      (_acks select 1) call ACME_fnc_equipmentAck;(_acks select 0) call ACME_fnc_equipmentAck;
      [_deleted==1 && {{_stock==2}},"release/retry duplicated or lost device"] call _check;
      [(_medic getVariable ["ACME_equipmentWorldPending","busy"])=="","completed pickup retained reservation"] call _check;
    ''')


def test_staged_object_appearing_during_delivery_cannot_be_deleted():
    execute(setup()+'''
      [_medic,_patient,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _deviceFixture setVariable ["ACME_eq_restoreStaged",true];
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_deleted==0,"ACK deleted a staged object"] call _check;
    ''')


@pytest.mark.parametrize('end',['pro','ls'])
def test_pickup_unplugs_both_usb_ends_immediately_once(end):
    target='_mount' if end=='pro' else '_deviceFixture'
    execute(setup()+'''
      _deviceFixture setVariable ["ACME_eq_kind","ls"];
      _deviceFixture setVariable ["acme_tempusls_pat",_patient];
      _mount setVariable ["ACME_eq_kind","pro"];
      _mount setVariable ["acme_tempus_pat",_patient];
      _mount setVariable ["ACME_eq_patient",_patient];
      _remote=false;[_medic,_deviceFixture,_mount,true] call ACME_fnc_equipmentLinkRequest;
      [_deviceFixture getVariable ["ACME_eq_usbEpoch",0]==1,"USB setup failed"] call _check;
    '''+f'[_medic,_patient,"{end}","pickup",false,[],{target}] call ACME_fnc_equipmentRequest;'+'''
      [count _inventoryMessages==1,"pickup not admitted"] call _check;
      [(_deviceFixture getVariable ["ACME_eq_usb",_patient]) isEqualTo objNull && {(_mount getVariable ["ACME_eq_usbLs",_patient]) isEqualTo objNull},"pickup retained a physical USB port"] call _check;
      [_deviceFixture getVariable ["ACME_eq_usbEpoch",0]==2,"pickup did not retire the USB episode"] call _check;
      [_deviceFixture] call ACME_fnc_equipmentUsbRelease;
      [_deviceFixture getVariable ["ACME_eq_usbEpoch",0]==2,"duplicate cleanup retired another episode"] call _check;
    ''')


def test_stale_reverse_usb_claim_does_not_unplug_another_pair():
    execute(usb_setup()+'''
      _ls setVariable ["ACME_eq_usb",_patient];_ls setVariable ["ACME_eq_usbEpoch",9];
      _pro setVariable ["ACME_eq_usbLs",_ls];_patient setVariable ["ACME_eq_usbLs",_ls];
      [_pro] call ACME_fnc_equipmentUsbRelease;
      [(_pro getVariable ["ACME_eq_usbLs",_patient]) isEqualTo objNull,"stale reverse port not retired"] call _check;
      [(_ls getVariable "ACME_eq_usb") isEqualTo _patient && {(_patient getVariable "ACME_eq_usbLs") isEqualTo _ls},"cleanup unplugged a newer pair"] call _check;
      [_ls getVariable ["ACME_eq_usbEpoch",0]==9,"cleanup invalidated another pair's epoch"] call _check;
    ''')


def test_usb_cleanup_retires_old_packets_and_accepts_a_fresh_connection():
    execute(usb_setup()+'''
      [_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;
      [_ls] call ACME_fnc_equipmentUsbRelease;
      _remote=true;[_actor,_ls,_pro,true,1] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",_patient]) isEqualTo objNull,"retired request restored released USB"] call _check;
      [_actor,_ls,_pro,true,2] call ACME_fnc_equipmentLinkRequest;
      [(_ls getVariable ["ACME_eq_usb",objNull]) isEqualTo _pro,"fresh request could not reconnect"] call _check;
    ''')


@pytest.mark.parametrize('patient',['objNull','_patient'])
def test_unassigned_or_assigned_field_monitor_remains_pickable(patient):
    execute(setup()+f'''
      _deviceFixture setVariable ["ACME_eq_patient",{patient}];
      _deviceFixture setVariable ["acme_tempus_pat",{patient}];
      [_medic,objNull,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==1,"field monitor without canonical patient could not be picked up"] call _check;
    ''')


def test_usb_cleanup_is_local_server_only_and_keeps_wireless_pair():
    execute(usb_setup()+'''
      [_actor,_ls,_pro,true] call ACME_fnc_equipmentLinkRequest;
      _server=false;[_ls] call ACME_fnc_equipmentUsbRelease;
      [(_ls getVariable "ACME_eq_usb") isEqualTo _pro,"client unplugged server USB"] call _check;
      _server=true;[_ls] call ACME_fnc_equipmentUsbRelease;
      [(_ls getVariable ["ACME_eq_usb",_patient]) isEqualTo objNull,"server unplug failed"] call _check;
      [(_ls getVariable "acme_tempusls_link") isEqualTo _pro,"physical cleanup erased wireless pairing"] call _check;
    ''')


def test_helpers_are_registered_without_exposing_new_mutation_rpcs():
    config=(E.parent/'config.cpp').read_text()
    functions=config.split('class CfgFunctions',1)[1].split('class CfgRemoteExec',1)[0]
    remote=config.split('class CfgRemoteExec',1)[1]
    for name in ['equipmentPickupReady','equipmentUsbRelease']:
        assert 'class '+name+' {};' in functions
        assert 'ACME_fnc_'+name not in remote


@pytest.mark.parametrize('name',['equipmentRequest','equipmentAck'])
def test_scheduled_entry_runs_decisions_in_one_unscheduled_section(name):
    s=(E/f'fn_{name}.sqf').read_text()
    assert re.search(r'if \(canSuspend\) exitWith \{isNil \{[^\n]+ call ACME_fnc_'+name+r';\};\};',s)

