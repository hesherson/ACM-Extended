"""Execute deployed-device persistence SQF; object creation/geometry/RPC are explicit native boundaries."""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_b288_clinical_persistence import ref_setup
from test_historical_vial_execution import map_defaults

E = ROOT / 'addons/acme_equipment/functions'


def source(name):
    s = (E / f'fn_{name}.sqf').read_text()
    s = s.replace('isRemoteExecuted', '_remote').replace('canSuspend','false')
    s = s.replace('isNull attachedTo _o','((_o getVariable ["fixtureAttached",objNull]) isEqualTo objNull)')
    s = s.replace('isNull (_bindings getOrDefault [_id,objNull])', '((_bindings getOrDefault [_id,objNull]) isEqualTo objNull)')
    s = s.replace('isNull (_patient getVariable ["ACME_eq_"+_kind,objNull])', '((_patient getVariable ["ACME_eq_"+_kind,objNull]) isEqualTo objNull)')
    s = re.sub(r'!finite (_\w+)', r'!(\1 isEqualType 0)', s)
    s = s.replace('(_state select 1) isEqualTypeAll false', '((_state select 1) findIf {!(_x isEqualType false)}) < 0')
    s = re.sub(r'(_\w+) isEqualTypeAll (""|false|0)',
               r'((\1) findIf {!(_x isEqualType \2)}) < 0', s)
    s = s.replace('createVehicle [_class,ASLToAGL _pos,[],0,"CAN_COLLIDE"]', '[_class,_pos] call _spawn')
    s = s.replace('_o setVectorDirAndUp [_dir,_up]', '_o setVariable ["fixtureOrientation",[_dir,_up]]')
    s = s.replace('_o setPosASL _pos', '_o setVariable ["fixturePosition",_pos]')
    s = s.replace('getPosASL _o', '(_o getVariable ["fixturePosition",[100,200,1000]])')
    s = s.replace('vectorDir _o', '((_o getVariable ["fixtureOrientation",[[0,1,0],[0,0,1]]]) select 0)')
    s = s.replace('vectorUp _o', '((_o getVariable ["fixtureOrientation",[[0,1,0],[0,0,1]]]) select 1)')
    s = s.replace('getPosASL _patient', '[100,200,1000]').replace('objectParent _patient', 'objNull')
    s = s.replace('_link isKindOf "ACME_TempusPro"', '_externalPro')
    s = s.replace('_patient isKindOf "CAManBase"', '_human')
    s = s.replace('_x distance _link', '_linkDistance')
    s = s.replace('deleteVehicle _x', '_deleted pushBack _x')
    s = s.replace('[_x,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select (_kind == "ls"),_patient]',
                  '_feeds pushBack [_x,_patient,_kind]')
    return adapt(map_defaults(s))


def setup():
    return ref_setup() + '''
      private _remote=false;private _ready=true;private _failAt=-1;private _spawns=[];
      private _deleted=[];private _feeds=[];private _linkDistance=1;private _externalPro=true;private _human=true;
      private _pool=[missionNamespace,parsingNamespace];
      private _spawn={params ["_class","_pos"];private _index=count _spawns;
        _spawns pushBack [_class,_pos];if (_index==_failAt) exitWith {objNull};_pool select _index};
      ACME_fnc_persistenceJournalsReady={_ready};
      ACME_fnc_tempusLsChargeClear={params ["_o"];_o setVariable ["acme_tempusls_armed",false];_o setVariable ["acme_tempusls_charge",[]];_o setVariable ["acme_tempusls_charging",[]]};
      ACME_fnc_ventDeviceFields={["ACME_vent_battery","ACME_vent_mode"]};
      CBA_fnc_addPerFrameHandler={17};
      ["bind",_patient,"patient-A"] call ACME_fnc_clinicalObjectRef;
      private _null=["0:0","",""];
      private _pat=["7:1","mission-A","patient-A"];
      private _state=[true,[true,false,true,false,true],true,false];
      private _row=["device-A","pro",[100,200,1000],[0,1,0],[0,0,1],true,_pat,_state,_null,[]];
      private _save=[1,[_row]];
    ''' + ''.join('ACME_fnc_' + n + '={' + source(n) + '};' for n in (
        'equipmentWorldSchema', 'equipmentWorldSnapshot', 'equipmentWorldCaptureValid', 'equipmentWorldRestore'))


@pytest.mark.parametrize('kind,cls', [('pro','ACME_TempusPro'),('ls','ACME_TempusLS'),('accu','ACME_AccuvacRescue')])
def test_restore_exact_transform_and_patient_without_inventory_grants(kind, cls):
    execute(setup() + f'''
      _row set [1,"{kind}"];
      private _r=[_save] call ACME_fnc_equipmentWorldRestore;
      [_r select 0,"valid restore refused"] call _check;
      [(_spawns select 0) isEqualTo ["{cls}",[100,200,1000]],"wrong model or elevated transform"] call _check;
      [(missionNamespace getVariable ["fixtureOrientation",[]]) isEqualTo [[0,1,0],[0,0,1]],"orientation lost"] call _check;
      [(_patient getVariable ["ACME_eq_{kind}",objNull]) isEqualTo missionNamespace,"patient slot missing"] call _check;
      [(missionNamespace getVariable ["ACME_eq_manual",false]),"manual placement marker lost"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_row set [0,""];', '_row set [1,"arbitrary_class"];', '_row set [2,[1,2]];',
    '_row set [3,[0,0,0]];', '_row set [4,[0,1,0]];', '_row set [5,0];',
    '_row set [6,["7:1","old",""]];', '_state set [0,1];',
    '_state set [1,[true]];', '_row set [8,["x","old","foreign"]];',
    '_row set [9,["script"]];', '(_save select 1) pushBack +_row;',
    '_save set [0,2];', '_save set [1,"bad"];'
])
def test_schema_rejects_malformed_payload_before_creation(change):
    execute(setup() + change + '''
      [!([_save] call ACME_fnc_equipmentWorldSchema),"malformed schema accepted"] call _check;
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0) && {count _spawns==0},"invalid payload created equipment"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_remote=true;', '_ready=false;',
    'missionNamespace setVariable ["ACME_eqPending",createHashMapFromArray [["pending",true]]];',
    'missionNamespace setVariable ["ACME_eqDevices",[parsingNamespace]];',
    '["bind",_medic,"device-A"] call ACME_fnc_clinicalObjectRef;',
    '_pat set [2,"missing-patient"];_pat set [1,"old"];',
    '_patient setVariable ["ACME_eq_pro",parsingNamespace];',
])
def test_restore_conflicts_and_unsettled_transfers_fail_before_creation(change):
    execute(setup() + change + '''
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0),"unsafe restore accepted"] call _check;
      [count _spawns==0,"preflight conflict allocated equipment"] call _check;
    ''')


def test_restart_rebinds_stable_patient_instead_of_recycled_netid():
    execute(setup() + '''
      missionNamespace setVariable ["ACME_clinicalPersistenceSession","mission-B"];
      _nativeIds set ["7:1",_medic];
      private _r=[_save] call ACME_fnc_equipmentWorldRestore;
      [_r select 0,"stable restart refused"] call _check;
      [(missionNamespace getVariable ["acme_tempus_pat",objNull]) isEqualTo _patient,"recycled net ID became patient"] call _check;
      [count _feeds==1 && {((_feeds select 0) select 1) isEqualTo _patient},"feed did not target rebound owner"] call _check;
    ''')


def test_restore_replay_never_repositions_or_duplicates_or_revives_retired_device():
    execute(setup() + '''
      [_save] call ACME_fnc_equipmentWorldRestore;
      missionNamespace setVariable ["fixturePosition",[1,2,3]];
      private _r=[_save] call ACME_fnc_equipmentWorldRestore;
      [(_r select 0) && {count _spawns==1},"retry duplicated equipment"] call _check;
      [(missionNamespace getVariable "fixturePosition") isEqualTo [1,2,3],"retry rewound live placement"] call _check;
      // A deleted/picked-up object is objNull at the native boundary.
      private _journal=missionNamespace getVariable "ACME_eqWorldImport";
      (_journal select 1) set [0,objNull];
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0) && {count _spawns==1},"retired world item respawned"] call _check;
    ''')


def test_import_journal_does_not_alias_callers_mutable_array():
    execute(setup() + '''
      [_save] call ACME_fnc_equipmentWorldRestore;
      _row set [2,[1,2,3]];
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0),"caller changed durable import evidence"] call _check;
      [count _spawns==1,"changed payload spawned again"] call _check;
    ''')


def test_failed_second_creation_rolls_back_without_bindings_or_patient_slots():
    execute(setup() + '''
      private _second=+_row;_second set [0,"device-B"];_second set [1,"ls"];
      (_save select 1) pushBack _second;_failAt=1;
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0),"partial creation reported success"] call _check;
      [count _deleted==1,"staged device was not rolled back"] call _check;
      [isNil {missionNamespace getVariable "ACME_persistenceId"},"failed batch published device binding"] call _check;
      [(_patient getVariable ["ACME_eq_pro",objNull]) isEqualTo objNull,"failed batch took patient slot"] call _check;
      [isNil {missionNamespace getVariable "ACME_eqWorldImport"},"failed batch became committed import"] call _check;
    ''')


def test_pair_graph_binds_after_all_devices_exist_and_ls_is_disarmed():
    execute(setup() + '''
      private _second=+_row;_second set [0,"device-B"];_second set [1,"ls"];
      _second set [8,["0:0","old","device-A"]];(_save select 1) pushBack _second;
      parsingNamespace setVariable ["acme_tempusls_armed",true];
      parsingNamespace setVariable ["acme_tempusls_pace",[true,100,200,true]];
      [([_save] call ACME_fnc_equipmentWorldRestore) select 0,"pair batch failed"] call _check;
      [(parsingNamespace getVariable ["acme_tempusls_link",objNull]) isEqualTo missionNamespace,"pair was not rebound"] call _check;
      [!(parsingNamespace getVariable ["acme_tempusls_armed",true]),"shock rearmed"] call _check;
      [(parsingNamespace getVariable ["acme_tempusls_pace",[]]) isEqualTo [false,70,0,false],"pacing resumed"] call _check;
      [(parsingNamespace getVariable ["acme_tempusls_st","bad"])=="","browser therapy state restored"] call _check;
      [count _feeds==2,"observation feeds not rebuilt exactly once"] call _check;
    ''')


def test_world_capture_and_final_validation_detect_movement_or_busy_transfer():
    execute(setup() + '''
      [_save] call ACME_fnc_equipmentWorldRestore;
      private _capture=call ACME_fnc_equipmentWorldSnapshot;
      [_capture isNotEqualTo [],"capture failed"] call _check;
      [[_capture] call ACME_fnc_equipmentWorldCaptureValid,"unchanged capture invalidated"] call _check;
      missionNamespace setVariable ["fixturePosition",[101,200,1000]];
      [!([_capture] call ACME_fnc_equipmentWorldCaptureValid),"movement was missed"] call _check;
      missionNamespace setVariable ["ACME_eq_busy",true];
      [(call ACME_fnc_equipmentWorldSnapshot) isEqualTo [],"busy world snapshot accepted"] call _check;
    ''')


def test_empty_world_is_valid_but_unbound_device_is_failed_capture():
    execute(setup() + '''
      [(call ACME_fnc_equipmentWorldSnapshot) isEqualTo [2,[]],"empty world confused with failure"] call _check;
      missionNamespace setVariable ["ACME_eqDevices",[parsingNamespace]];
      parsingNamespace setVariable ["ACME_eq_kind","pro"];
      [(call ACME_fnc_equipmentWorldSnapshot) isEqualTo [],"unbound device silently omitted"] call _check;
    ''')


@pytest.mark.parametrize('mounted',[False,True])
def test_vent_restore_requires_clinical_mount_and_rebuilds_funded_custody(mounted):
    execute(setup() + f'''
      _row set [1,"vent"];_row set [5,false];
      _row set [9,[_null,"uid-1",_null,_null,"uid-1"]];
      _patient setVariable ["ACME_vent_onPatient",{str(mounted).lower()}];
      _patient setVariable ["ACME_vent_battery",42];
      private _r=[_save] call ACME_fnc_equipmentWorldRestore;
      [(_r select 0) isEqualTo {str(mounted).lower()},"vent mount prerequisite ignored"] call _check;
      {'private _r=(missionNamespace getVariable "ACME_vent_custody") get "world:device-A";[(_r get "phase")=="attached","custody missing"] call _check;[(_r get "settings") isEqualTo [["ACME_vent_battery",42]],"battery/settings not retained"] call _check;' if mounted else '[count _spawns==0,"unfunded vent created"] call _check;'}
    ''')


@pytest.mark.parametrize('change', [
    '_human=false;', '_row set [8,["0:0","old","missing-Pro"]];_row set [1,"ls"];',
    '_patient setVariable ["ACME_vent_recovering",true];',
    '_row set [9,[_pat,"uid-1",["0:0","old","missing-vehicle"],_null,"uid-1"]];',
    '_row set [9,[_null,"uid-1",_null,["0:0","old","missing-operator"],"uid-1"]];',
])
def test_vent_and_pair_references_must_resolve_before_allocation(change):
    execute(setup() + '''
      _row set [1,"vent"];_row set [5,false];_row set [9,[_null,"uid-1",_null,_null,"uid-1"]];
      _patient setVariable ["ACME_vent_onPatient",true];
    ''' + change + '''
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0) && {count _spawns==0},"invalid relationship allocated equipment"] call _check;
    ''')


def test_vent_custody_preserves_supplier_vehicle_recovery_and_roundtrips():
    execute(setup() + '''
      ["bind",_medic,"supplier-A"] call ACME_fnc_clinicalObjectRef;
      private _supplier=["0:0","old","supplier-A"];
      _row set [1,"vent"];_row set [5,false];_row set [9,[_supplier,"uid-1",_supplier,_supplier,"uid-1"]];
      _patient setVariable ["ACME_vent_onPatient",true];
      [([_save] call ACME_fnc_equipmentWorldRestore) select 0,"funded vent restore refused"] call _check;
      private _r=(missionNamespace getVariable "ACME_vent_custody") get "world:device-A";
      [(_r get "supplier") isEqualTo _medic && {(_r get "recoveryOperator") isEqualTo _medic},"supplier/recovery identity lost"] call _check;
      [(_r get "supplyOrigin") isEqualTo [_medic,_medic],"original vehicle return path lost"] call _check;
      private _capture=call ACME_fnc_equipmentWorldSnapshot;
      [_capture isNotEqualTo [] && {(((_capture select 1) select 0) select 1)=="vent"},"restored vent cannot be captured"] call _check;
      ["world:device-A" == (_patient getVariable "ACME_vent_custodyId"),"native removal does not own restored custody"] call _check;
    ''')


@pytest.mark.parametrize('change',['_linkDistance=11;','_second set [6,_null];_row set [6,_null];'])
def test_pairing_respects_distance_and_optional_unassigned_patients(change):
    execute(setup() + '''
      private _second=+_row;_second set [0,"device-B"];_second set [1,"ls"];
      _second set [8,["0:0","old","device-A"]];(_save select 1) pushBack _second;
    ''' + change + '''
      [([_save] call ACME_fnc_equipmentWorldRestore) select 0,"valid physical batch failed"] call _check;
      private _link=parsingNamespace getVariable ["acme_tempusls_link",objNull];
      [if (_linkDistance>10) then {_link isEqualTo objNull} else {_link isEqualTo missionNamespace},"pair range or unassigned policy ignored"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_row set [2,[1e8,0,0]];', '_row set [3,[0,2,0]];',
    '_row set [6,["0:0","old",""]];', '_state set [1,[true,true,true,true,1]];',
    '_row set [1,"vent"];_row set [5,false];_row set [9,[_null,"uid",_null,[],"uid"]];',
])
def test_schema_rejects_invalid_vectors_and_unportable_clockless_references(change):
    execute(setup() + change + '''
      [!([_save] call ACME_fnc_equipmentWorldSchema),"invalid portable facts accepted"] call _check;
    ''')


def test_replay_rejects_rebound_live_device_identity_without_minting():
    execute(setup() + '''
      [_save] call ACME_fnc_equipmentWorldRestore;
      ["bind",missionNamespace,"replacement-A"] call ACME_fnc_clinicalObjectRef;
      [!(([_save] call ACME_fnc_equipmentWorldRestore) select 0) && {count _spawns==1},"identity replay minted device"] call _check;
    ''')


@pytest.mark.parametrize('change',['_remote=true;','_ready=false;','missionNamespace setVariable ["ACME_eqPending",createHashMapFromArray [["transfer",true]]];'])
def test_snapshot_and_final_validation_refuse_unsettled_or_remote_capture(change):
    execute(setup() + '''
      [_save] call ACME_fnc_equipmentWorldRestore;
      private _capture=call ACME_fnc_equipmentWorldSnapshot;
    ''' + change + '''
      [(call ACME_fnc_equipmentWorldSnapshot) isEqualTo [],"unsafe capture accepted"] call _check;
      [!([_capture] call ACME_fnc_equipmentWorldCaptureValid),"unsafe final commit accepted"] call _check;
    ''')


def test_world_import_functions_are_registered_but_never_remote_whitelisted():
    config=(ROOT/'addons/acme_equipment/config.cpp').read_text()
    for n in ('equipmentWorldSchema','equipmentWorldSnapshot','equipmentWorldCaptureValid','equipmentWorldRestore'):
        assert f'class {n} {{}};' in config
        assert f'class ACME_fnc_{n}' not in config
    restore=(E/'fn_equipmentWorldRestore.sqf').read_text()
    assert not re.search(r'\b(addItem|addItemCargoGlobal|removeItem|execVM|compile)\b',restore)
    assert 'ACME_eqPending' in (ROOT/'addons/acm_extended/functions/fn_persistenceJournalsReady.sqf').read_text()


def test_capture_keeps_independent_sensor_evidence_after_live_array_changes():
    execute(setup()+'''
      [_save] call ACME_fnc_equipmentWorldRestore;
      private _capture=call ACME_fnc_equipmentWorldSnapshot;
      private _live=missionNamespace getVariable "acme_tempus_sensors";_live set [0,false];
      missionNamespace setVariable ["acme_tempus_sensors",_live];
      [((((_capture select 1) select 0) select 7) select 1) select 0,"live mutation changed saved evidence"] call _check;
      [!([_capture] call ACME_fnc_equipmentWorldCaptureValid),"sensor change did not invalidate checkpoint"] call _check;
    ''')


@pytest.mark.parametrize('operation',['setup','pickup'])
def test_patient_checkpoint_fence_blocks_setup_and_pickup(operation):
    from test_b308_patient_equipment import setup as request_setup
    execute(request_setup()+f'''
      _patient setVariable ["ACME_persistenceFrozen",true];
      _deviceFixture setVariable ["ACME_eq_patient",_patient];
      [_medic,{"_patient" if operation=='setup' else "objNull"},"accu","{operation}",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      [count _inventoryMessages==0 && {{_stock==1}},"patient checkpoint fence admitted transfer"] call _check;
    ''')
