"""Execute personal/removed-carrier checkpoint code.

Native cargo/locality/config and opaque-ledger transport use explicit fixture
boundaries. Production validation, snapshots, restore journaling, recursive cargo
matching, and the existing live carrier transfer execute in SQF-VM. This does not
certify Arma replication, capacity physics, or a mission persistence adapter.
"""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import execute, read, namespace_public_arguments
from test_b218_carrier_inventory import setup, cargo_source
from test_historical_vial_execution import map_defaults


def source(name):
    s = read(name)
    s = s.replace('canSuspend', 'false').replace('local _holder', 'true').replace('local _container', 'true')
    s = s.replace('local _provider', '_presentationLocal')
    s = s.replace('hasInterface', '_testInterface')
    # SQF-VM lacks finite; ordinary fixture scalars are finite. Type/range checks remain production code.
    s = re.sub(r'\bfinite (_\w+)', r'(\1 == \1)', s)
    s = re.sub(r'\bfinite (\([^()]*\))', r'(\1 == \1)', s)
    s = s.replace('vest _holder', '_wornVest').replace('getPosATL _holder', '[0,0,0]')
    s = s.replace('vestContainer _holder', '_wornContainer').replace('uniformContainer _holder', '_rootUniform').replace('backpackContainer _holder', '_rootBackpack')
    s = s.replace('createVehicle ["ACME_RemovedCarrierCargo",[0,0,0],[],0,"CAN_COLLIDE"]', '"GroundWeaponHolder" createVehicle [0,0,0]')
    s = s.replace('_cargo allowDamage false;', '')
    # VM numeric HashMap-key overload is absent; preserve lookup identity as strings.
    s = s.replace('_registry getOrDefault [_x param [7,-1],[]]', '(if (str (_x param [7,-1]) in _registry) then {_registry get str (_x param [7,-1])} else {[]})')
    s = re.sub(r'\beveryContainer (_\w+)', r'(\1 getVariable ["children",[]])', s)
    s = s.replace('isClass (configFile >> "CfgWeapons" >> _vest)', '(_vest == "Vest_A")')
    return f'ACME_fnc_{name}={{'+namespace_public_arguments(map_defaults(s))+'};\n'


def harness():
    return setup()+r'''
        _wornVest=""; deleteVehicle _wornContainer; _wornContainer=objNull;
        private _deviceCount=1; private _rootUniform=objNull; private _rootBackpack=objNull;
        private _testInterface=false;
        private _presentationLocal=true;
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _restoreRefused=false;
        private _restoreCalls=0;
        private _grantPending=false;
        private _reconcileCalls=0;
        ACME_fnc_inventoryLedgerReconcile={_reconcileCalls=_reconcileCalls+1;};
        ace_common_fnc_getCountOfItem={_deviceCount};
        ACME_fnc_vialCapacity={params ["_med"]; if (_med in ["Morphine","Ketamine"]) then {10} else {0}};
        ACME_fnc_coolerBagVolume={params ["_class"];if ((_class find "ACM_BloodBag_")==0 || {(_class find "ACM_FreshBloodBag_")==0}) then {500} else {0}};
        ACME_fnc_inventorySnapshot={params ["_object"]; if (_grantPending) exitWith {[]}; _object getVariable ["test_inventory",[1,[]]]};
        ACME_fnc_inventorySnapshotValid={params ["_s"]; _s isEqualType [] && {count _s==2} && {(_s select 0) isEqualTo 1} && {(_s select 1) isEqualType []}};
        ACME_fnc_inventoryRestore={_restoreCalls=_restoreCalls+1; !_restoreRefused};
        ACME_fnc_coolerSnapshot={params ["_object"]; _object getVariable ["test_coolers",[1,"holder",[]]]};
        ACME_fnc_coolerSnapshotValid={params ["_s"]; _s isEqualType [] && {count _s==3} && {(_s select 0) isEqualTo 1} && {(_s select 1) isEqualTo "holder"} && {(_s select 2) isEqualType []}};
        ACME_fnc_coolerRestore={!_restoreRefused};
    '''+''.join(source(n) for n in ('ventDeviceFields','openVialStoreCommit','equipmentCargoSnapshot','equipmentCargoValid','equipmentCargoRestore','equipmentSnapshotValid','equipmentSnapshot','equipmentRestore'))+r'''
        private _emptyTree=[[[],[],[],[]],[1,[]],[1,"holder",[]],[]];
        private _equipment=[1,[["Morphine",1.25]],[["used_1","Blood",243.5,1,2,500,"Blood B+",-1]],[["ACME_vent_battery",17.5],["ACME_vent_mode","SIMV VC PS"],["ACME_vent_alertInvIE",false]],[]];
    '''


def test_personal_virtual_contents_survive_restart_and_repeat_does_not_refill():
    execute(harness()+r'''
        [[_equipment] call ACME_fnc_equipmentSnapshotValid,"valid personal schema rejected"] call _check;
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"restore rejected"] call _check;
        [((_patient getVariable "ACME_infusion_openVials") get "Morphine")==1.25,"partial vial changed"] call _check;
        [((_patient getVariable "ACME_usedBags") select 0 select 2)==243.5,"used bag changed"] call _check;
        [(_patient getVariable "ACME_vent_battery")==17.5,"battery reset"] call _check;
        private _saved=[_patient] call ACME_fnc_equipmentSnapshot;
        [[_saved] call ACME_fnc_equipmentSnapshotValid,"roundtrip invalid"] call _check;
        private _vials=_patient getVariable "ACME_infusion_openVials"; _vials set ["Morphine",0.25];
        _patient setVariable ["ACME_usedBags",[]];
        _patient setVariable ["ACME_vent_battery",5];
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"repeat rejected"] call _check;
        [((_patient getVariable "ACME_infusion_openVials") get "Morphine")==0.25,"repeat refilled vial"] call _check;
        [(_patient getVariable "ACME_usedBags") isEqualTo [],"repeat recreated bag"] call _check;
        [(_patient getVariable "ACME_vent_battery")==5,"repeat recharged battery"] call _check;
    ''')


@pytest.mark.parametrize('field,value',[(0,'2'),(1,'[["Morphine",-1]]'),(1,'[["Unknown",1]]'),(1,'[["Morphine",1],["Morphine",2]]'),(2,'[["used","Blood",600,1,0,500,"Blood",-1]]'),(2,'[["used","Blood",100,"IV",0,500,"Blood",-1]]'),(3,'[["ACME_vent_battery",101]]'),(3,'[["ACME_vent_battery","full"]]'),(3,'[["ACME_vent_fake",1]]'),(3,'[["ACME_vent_mode",false]]'),(4,'["untrusted","Vest_A",[]]')])
def test_malformed_metadata_has_no_inventory_or_virtual_side_effect(field,value):
    execute(harness()+f'_equipment set [{field},{value}];'+r'''
        _patient setVariable ["ACME_usedBags",[["sentinel"]]];
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"invalid metadata restored"] call _check;
        [(_patient getVariable "ACME_usedBags") isEqualTo [["sentinel"]],"invalid metadata changed virtual state"] call _check;
        [_restoreCalls==0,"invalid metadata touched native ledger"] call _check;
        [isNull (_patient getVariable ["ACME_carrierCargo",objNull]),"invalid metadata spawned cargo"] call _check;
    ''')


@pytest.mark.parametrize('context',['ACME_chestAccess_vestLoadout','ACME_CS_vestLoadout','ACME_headElev_vestLoadout'])
def test_removed_carrier_preserves_actual_cargo_and_rejoins_live_restore(context):
    execute(harness()+f'_savedVar="{context}";'+r'''
        private _native=[["live_medication"],[["partial_mag",7]],[["rifle","","","",["mag",4],[],""]],[]];
        private _tree=[_native,[1,[]],[1,"holder",[]],[]];
        _equipment set [4,[_savedVar,"Vest_A",_tree]];
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"removed carrier restore rejected"] call _check;
        [isNull (_patient getVariable ["ACME_carrierCargo",objNull]),"completed custody left a duplicate holder"] call _check;
        [_wornVest=="Vest_A","vest shell lost"] call _check;
        [[_native,[_wornContainer] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual,"returned vest changed supplies"] call _check;
        [(_patient getVariable [_savedVar,["bad"]]) isEqualTo [],"terminated workspace retained active saved record"] call _check;
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"receipt after settlement rejected"] call _check;
        [isNull (_patient getVariable ["ACME_carrierCargo",objNull]),"repeat recreated settled cargo"] call _check;
    ''')


def test_failed_ledger_restore_retains_exact_staged_cargo_for_retry():
    execute(harness()+r'''
        private _native=[["live"],[["opaque",4]],[],[]];
        _equipment set [4,["ACME_CS_vestLoadout","Vest_A",[_native,[1,[]],[1,"holder",[]],[]]]];
        _restoreRefused=true;
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"failed ledger marked restored"] call _check;
        private _cargo=_patient getVariable "ACME_carrierCargo";
        [!isNull _cargo,"funding holder destroyed"] call _check;
        [_cargo getVariable ["ACME_carrierClosing",false],"incomplete carrier offered to treatment"] call _check;
        [isNil {_patient getVariable "ACME_usedBags"},"virtual stores applied before native completion"] call _check;
        _restoreRefused=false;
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"funded retry failed"] call _check;
        [isNull (_patient getVariable ["ACME_carrierCargo",objNull]),"completed retry retained live holder"] call _check;
        [_wornVest=="Vest_A","completed retry lost vest"] call _check;
    ''')


def test_destroyed_live_carrier_saves_only_empty_shell():
    execute(harness()+r'''
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[["stale",99]]]];
        _patient setVariable ["ACME_CS_vestLoadoutLive",true];
        private _saved=[_patient] call ACME_fnc_equipmentSnapshot;
        [(_saved select 4 select 2 select 0) isEqualTo [[],[],[],[]],"destroyed carrier refilled historical supplies"] call _check;
    ''')


def test_attached_ventilator_settings_are_not_overwritten_by_empty_carried_metadata():
    execute(harness()+r'''
        _patient setVariable ["ACME_vent_connected",true];
        _patient setVariable ["ACME_vent_battery",12.3];
        _equipment set [3,[]];
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"empty carried metadata rejected attached patient"] call _check;
        [(_patient getVariable "ACME_vent_battery")==12.3,"attached ventilator reset by gear restore"] call _check;
    ''')


@pytest.mark.parametrize('busy',['ACME_medicationEscrow','ACME_syringeDeliverySessions'])
def test_pending_owner_transaction_prevents_equipment_snapshot(busy):
    execute(harness()+f'_patient setVariable ["{busy}",createHashMapFromArray [["pending",[]]]];'+r'''
        [([_patient] call ACME_fnc_equipmentSnapshot) isEqualTo [],"busy owner produced apparently complete snapshot"] call _check;
    ''')


def test_recursive_cargo_match_survives_engine_child_reordering():
    execute(harness()+r'''
        private _a=[["A"],[],[],[]]; private _b=[["B"],[],[],[]];
        private _native=[[],[],[],[["Pocket",false,_a],["Pocket",false,_b]]];
        private _ta=[_a,[1,[]],[1,"holder",[]],[]]; private _tb=[_b,[1,[]],[1,"holder",[]],[]];
        private _tree=[_native,[1,[]],[1,"holder",[]],[_ta,_tb]];
        private _cargo="GroundWeaponHolder" createVehicle [0,0,0];
        [_cargo,_native] call ACME_fnc_carrierCargoPopulate;
        private _children=_cargo getVariable "children"; reverse _children; _cargo setVariable ["children",_children];
        [[_cargo,_tree] call ACME_fnc_equipmentCargoRestore,"reordered children rejected"] call _check;
        [_restoreCalls==3,"recursive ledgers omitted"] call _check;
    ''')


def test_returned_vest_enrolls_recreated_nested_container_custody():
    execute(harness()+r'''
        private _leafNative=[["nested_supply"],[["opaque",4]],[],[]];
        private _childNative=[[],[],[],[["Pocket",false,_leafNative]]];
        private _native=[[],[],[],[["Pocket",false,_childNative]]];
        private _leaf=[_leafNative,[1,[]],[1,"holder",[]],[]];
        private _child=[_childNative,[1,[]],[1,"holder",[]],[_leaf]];
        private _tree=[_native,[1,[]],[1,"holder",[]],[_child]];
        _equipment set [4,["ACME_CS_vestLoadout","Vest_A",_tree]];
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"nested vest restore failed"] call _check;
        private _newChild=(_wornContainer getVariable "children") select 0 select 1;
        private _newLeaf=(_newChild getVariable "children") select 0 select 1;
        private _tracked=missionNamespace getVariable ["ACME_inventoryTracked",[]];
        [_newChild in _tracked && {_newLeaf in _tracked},"recreated child custody was never enrolled"] call _check;
        [_reconcileCalls==3,"nested children did not enter adoption reconciliation"] call _check;
    ''')


@pytest.mark.parametrize('slot,root', [(0,'_rootUniform'),(1,'_wornContainer'),(2,'_rootBackpack')])
def test_worn_nested_snapshot_records_physical_slot_and_waits_for_unsettled_custody(slot,root):
    execute(harness()+f'{root}="GroundWeaponHolder" createVehicle [0,0,0];'+r'''
        private _native=[[],[],[],[["Pocket",false,[["nested_supply"],[],[],[]]]]];
        '''+f'[{root},_native] call ACME_fnc_carrierCargoPopulate;'+r'''
        private _saved=[_patient] call ACME_fnc_equipmentSnapshot;
        [count _saved==6 && {count (_saved select 5)==1},"worn child metadata omitted"] call _check;
        private _entry=(_saved select 5) select 0;
        '''+f'[(_entry select 0)=={slot},"worn child assigned wrong slot"] call _check;'+r'''
        [(_entry select 1)=="Pocket" && {(_entry select 2 select 0 select 0) isEqualTo ["nested_supply"]},"worn child physical source changed"] call _check;
        _grantPending=true;
        [([_patient] call ACME_fnc_equipmentSnapshot) isEqualTo [],"unsettled nested custody silently omitted"] call _check;
    ''')


@pytest.mark.parametrize('bag', ['ACM_BloodBag_ON_500','ACM_FreshBloodBag_500_17'])
def test_nested_loose_blood_is_refused_without_an_exposure_metadata_slot(bag):
    execute(harness()+r'''
        _wornContainer="GroundWeaponHolder" createVehicle [0,0,0];
        '''+f'private _native=[[],[],[],[["Pocket",false,[["{bag}"],[],[],[]]]]];'+r'''
        [_wornContainer,_native] call ACME_fnc_carrierCargoPopulate;
        [([_patient] call ACME_fnc_equipmentSnapshot) isEqualTo [],"nested blood exposure was silently omitted"] call _check;
        private _child=(_wornContainer getVariable "children") select 0 select 1;
        '''+f'private _tree=[[["{bag}"],[],[],[]],[1,[]],[1,"holder",[]],[]];'+r'''
        [!([_tree] call ACME_fnc_equipmentCargoValid),"unsupported looseblood tree validated"] call _check;
        [!([_child,_tree] call ACME_fnc_equipmentCargoRestore),"unsupported looseblood tree imported"] call _check;
        [_restoreCalls==0,"unsupported looseblood metadata mutated ledger"] call _check;
    ''')


@pytest.mark.parametrize('work', ['y_build','spike','native_remove'])
def test_inflight_materialization_or_uncertain_native_remove_prevents_checkpoint(work):
    action={
        'y_build':'_testInterface=true;ACE_player=_patient;missionNamespace setVariable ["ACME_yBuildingActive",1];',
        'spike':'_testInterface=true;ACE_player=_patient;missionNamespace setVariable ["ACME_spikingActive",["blood",1]];',
        'native_remove':'_patient setVariable ["ACME_txRemoveRecovery",createHashMapFromArray [["pending",[]]]];',
    }[work]
    execute(harness()+action+r'''
        [([_patient] call ACME_fnc_equipmentSnapshot) isEqualTo [],"inflight temporary materialization saved as a full native item"] call _check;
    ''')


@pytest.mark.parametrize('name,epoch_index', [('ACME_txPullPending',2),('ACME_yDiscardPending',2),('ACME_txRemoveContexts',3)])
@pytest.mark.parametrize('stale', ['delivered','new_incarnation','nonlocal','deleted'])
def test_resource_free_stale_ui_context_does_not_permanently_block_checkpoint(name,epoch_index,stale):
    changes={
        'delivered':'_patient setVariable ["ACME_resourceReturnReceived",createHashMapFromArray [["old",[[],"delivered"]]]];',
        'new_incarnation':'_patient setVariable ["ACME_providerLocalityEpoch",2];',
        'nonlocal':'_presentationLocal=false;',
        'deleted':'_context set [0,objNull];',
    }[stale]
    execute(harness()+r'''
        _testInterface=true;ACE_player=_patient;
        private _context=[_patient,_medic];
        '''+(' _context pushBack "body";' if epoch_index==3 else '')+r'''
        _context pushBack 0;
        '''+changes+f'uiNamespace setVariable ["{name}",createHashMapFromArray [["old",_context]]];'+r'''
        uiNamespace setVariable ["ACME_txRemovePending","old"];
        private _snapshot=[_patient] call ACME_fnc_equipmentSnapshot;
        [[_snapshot] call ACME_fnc_equipmentSnapshotValid,"stale presentation context blocked checkpoint"] call _check;
        '''+f'[count (uiNamespace getVariable "{name}")==0,"stale presentation context was never retired"] call _check;'+
        ('[uiNamespace getVariable "ACME_txRemovePending"=="","stale Remove button marker remained active"] call _check;' if name=='ACME_txRemoveContexts' else '')+r'''
    ''')


@pytest.mark.parametrize('name', ['ACME_txPullPending','ACME_yDiscardPending','ACME_txRemoveContexts'])
def test_current_undelivered_ui_request_stays_busy_and_does_not_change_funding(name):
    execute(harness()+r'''
        _testInterface=true;ACE_player=_patient;
        private _context=[_patient,_medic];
        '''+(' _context pushBack "body";' if name=='ACME_txRemoveContexts' else '')+r'''
        _context pushBack 0;
        '''+f'uiNamespace setVariable ["{name}",createHashMapFromArray [["live",_context]]];'+r'''
        _patient setVariable ["ACME_resourceReturnReceived",createHashMapFromArray [["live",[[],"uncertain"]]]];
        private _funding=createHashMapFromArray [["live",["source-certificate"]]];
        _patient setVariable ["ACME_resourceReturnSourcePending",_funding];
        [([_patient] call ACME_fnc_equipmentSnapshot) isEqualTo [],"current uncertain request stopped blocking"] call _check;
        '''+f'[count (uiNamespace getVariable "{name}")==1,"current request was discarded"] call _check;'+r'''
        [(_patient getVariable "ACME_resourceReturnSourcePending") isEqualTo _funding,"UI retirement altered source funding"] call _check;
    ''')


def test_other_local_actor_presentation_does_not_block_unrelated_holder_or_erase_receipt():
    execute(harness()+r'''
        _testInterface=true;ACE_player=_patient;
        private _context=[_medic,_patient,0];
        uiNamespace setVariable ["ACME_txPullPending",createHashMapFromArray [["other",_context]]];
        [[[_patient] call ACME_fnc_equipmentSnapshot] call ACME_fnc_equipmentSnapshotValid,"another local actor's UI blocked this holder"] call _check;
        [count (uiNamespace getVariable "ACME_txPullPending")==1,"unrelated live context was erased"] call _check;
    ''')


@pytest.mark.parametrize('name,context', [
    ('ACME_txRemoveContexts','[_patient,_medic]'),
    ('ACME_txPullPending','[_patient,_medic,0,"invalid-extra"]'),
    ('ACME_yDiscardPending','[_patient,_medic,0,"invalid-extra"]'),
])
def test_ui_context_shape_that_no_result_can_settle_is_retired_without_touching_resources(name,context):
    execute(harness()+r'''
        _testInterface=true;ACE_player=_patient;
        '''+f'uiNamespace setVariable ["{name}",createHashMapFromArray [["invalid",{context}]]];'+r'''
        [[[_patient] call ACME_fnc_equipmentSnapshot] call ACME_fnc_equipmentSnapshotValid,"unsettleable presentation context blocked checkpoint"] call _check;
        '''+f'[count (uiNamespace getVariable "{name}")==0,"unsettleable presentation context was retained"] call _check;'+r'''
        [isNil {_patient getVariable "ACME_resourceReturnReceived"},"presentation cleanup invented a resource decision"] call _check;
    ''')


@pytest.mark.parametrize('name', ['ACME_usedRehangPending','ACME_yRefillPending'])
def test_escrow_owning_ui_maps_are_never_retired_with_presentation_contexts(name):
    execute(harness()+r'''
        _testInterface=true;ACE_player=_patient;_presentationLocal=false;
        uiNamespace setVariable ["ACME_txPullPending",createHashMapFromArray [["old",[objNull,_patient,0]]]];
        private _escrow=createHashMapFromArray [["source",["used-row",183.25,"native-funding"]]];
        '''+f'uiNamespace setVariable ["{name}",_escrow];'+r'''
        [([_patient] call ACME_fnc_equipmentSnapshot) isEqualTo [],"resource escrow was treated as presentation"] call _check;
        [count (uiNamespace getVariable "ACME_txPullPending")==0,"stale resource-free context was not retired"] call _check;
        '''+f'[(uiNamespace getVariable "{name}") isEqualTo _escrow,"resource-bearing pending data was erased"] call _check;'+r'''
    ''')


def test_fresh_used_bag_snapshots_donor_facts_and_normalizes_clock_without_registry_id_reuse():
    execute(harness()+r'''
        CBA_missionTime=7200;
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [["1",[_patient,500,2,false,7000]]]];
        _patient setVariable ["ACME_usedBags",[["used_fresh","FreshBlood",183,1,2,500,"Fresh blood",1]]];
        private _save=[_patient] call ACME_fnc_equipmentSnapshot;
        [(_save select 2 select 0 select 8) isEqualTo ["freshAgeV1",false,200,2],"donor age/status not captured"] call _check;
        CBA_missionTime=12;
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [["1",[_patient,1000,5,true,12]]]];
        [[_patient,_save] call ACME_fnc_equipmentRestore,"fresh used restore rejected"] call _check;
        private _bag=(_patient getVariable "ACME_usedBags") select 0;
        [(_bag select 7)==-1,"stale numeric donor ID retained"] call _check;
        [(_bag select 8) isEqualTo ["freshV1",false,-188,2],"restart freshness/donor status changed"] call _check;
        [(_bag select 2)==183,"fresh used volume changed"] call _check;
    ''')


def test_missing_fresh_donor_facts_are_saved_as_unusable_evidence_without_stale_id():
    execute(harness()+r'''
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMap];
        _patient setVariable ["ACME_usedBags",[["used_fresh","FreshBlood",183,1,2,500,"Fresh blood",1]]];
        private _save=[_patient] call ACME_fnc_equipmentSnapshot;
        [[_save] call ACME_fnc_equipmentSnapshotValid,"missing-donor evidence prevented unrelated save"] call _check;
        [(_save select 2 select 0 select 8) isEqualTo ["freshMissingV1"],"unknown donor metadata not fenced"] call _check;
        [[_patient,_save] call ACME_fnc_equipmentRestore,"missing-donor evidence not retained"] call _check;
        [((_patient getVariable "ACME_usedBags") select 0 select 7)==-1,"stale donor ID retained"] call _check;
    ''')


@pytest.mark.parametrize('blood', [-1,8,16])
def test_fresh_used_bag_out_of_domain_blood_type_is_rejected_before_restore(blood):
    execute(harness()+f'_equipment set [2,[["bad_fresh","FreshBlood",100,1,{blood},500,"Fresh blood",-1,["freshAgeV1",true,0,{blood}]]]];'+r'''
        [!([_equipment] call ACME_fnc_equipmentSnapshotValid),"out-of-domain fresh blood type validated"] call _check;
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"out-of-domain fresh blood restored"] call _check;
        [_restoreCalls==0 && {isNil {_patient getVariable "ACME_usedBags"}},"invalid fresh type mutated resources"] call _check;
    ''')


@pytest.mark.parametrize('mode', ['remove','pull','discard'])
@pytest.mark.parametrize('source_blood', [-1,8])
def test_unknown_fresh_canonical_return_can_be_saved_and_restored_only_as_unusable_evidence(mode,source_blood):
    execute(harness()+f'private _mode="{mode}";private _sourceBlood={source_blood};'+r'''
        CBA_fnc_serverEvent={_events pushBack _this;};
        CBA_missionTime=7200;
        private _provider=_patient;private _source=_medic;
        private _bag=["FreshBlood",183.25,4,0,false,_sourceBlood,500,17,"unknown-fresh",500,["freshMissingV1"]];
        private _canonical=[_mode,_source,"unknown-cleanup",[_bag]] call ACME_fnc_resourceReturnProducts;
        [_canonical select 0,"unknown fresh cleanup was refused by canonical products"] call _check;
        private _products=_canonical select 1;
        private _args=[_provider,_source,"unknown-cleanup",_products];
        [["stage",_args] call ACME_fnc_resourceReturnSource,"source stage rejected"] call _check;
        [["funded",_args] call ACME_fnc_resourceReturnSource,"source funding rejected"] call _check;
        [_provider,_source,"unknown-cleanup",_products,7,"machineA",1] call ACME_fnc_resourceReturnReceive;
        [_provider,_source,"unknown-cleanup",_products,7,"machineA",1] call ACME_fnc_resourceReturnReceive;
        [["delivered",["unknown-cleanup",[7,"machineA"]]] call ACME_fnc_resourceReturnSource,"delivered source did not settle"] call _check;
        private _used=_provider getVariable "ACME_usedBags";
        [count _used==1 && {(_used select 0 select 2)==183.25} && {(_used select 0 select 4)==-1}
            && {(_used select 0 select 8) isEqualTo ["freshMissingV1"]},"canonical cleanup lost, cloned or refreshed unknown donor evidence"] call _check;
        private _saved=[_provider] call ACME_fnc_equipmentSnapshot;
        [[_saved] call ACME_fnc_equipmentSnapshotValid,"inert unknown fresh product permanently blocked checkpoint"] call _check;
        _provider setVariable ["ACME_usedBags",[]];
        CBA_missionTime=12;
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[17,[_source,500,2,true,12]]]];
        [[_provider,_saved] call ACME_fnc_equipmentRestore,"inert unknown fresh product could not be restored"] call _check;
        private _restored=(_provider getVariable "ACME_usedBags") select 0;
        [_restored isEqualTo (_used select 0),"unknown fresh evidence changed across restart"] call _check;
        [([17,_restored select 8,_restored select 4] call ACME_fnc_freshBloodResolve) isEqualTo [],"restored unknown evidence bound reused donor ID"] call _check;
        private _again=[_provider] call ACME_fnc_equipmentSnapshot;
        [(_again select 2) isEqualTo (_saved select 2),"unknown donor fence changed on subsequent save"] call _check;
    ''')


@pytest.mark.parametrize('marker', ['[]','["freshMissingV1","extra"]','["freshAgeV1",true,0,-1]','["freshV1",true,0,-1]','["unknown"]'])
def test_unknown_fresh_type_requires_the_exact_missing_donor_fence(marker):
    execute(harness()+f'_equipment set [2,[["bad_fresh","FreshBlood",100,1,-1,500,"Fresh blood",-1,{marker}]]];'+r'''
        [!([_equipment] call ACME_fnc_equipmentSnapshotValid),"malformed negative donor facts validated"] call _check;
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"malformed negative donor facts restored"] call _check;
        [_restoreCalls==0 && {isNil {_patient getVariable "ACME_usedBags"}},"malformed negative donor facts mutated resources"] call _check;
    ''')


def test_settled_syringe_delivery_receipt_does_not_permanently_block_saving():
    execute(harness()+r'''
        _patient setVariable ["ACME_syringeDeliverySessions",createHashMapFromArray [["old",[1,"session","settled",1,1]]]];
        [[[_patient] call ACME_fnc_equipmentSnapshot] call ACME_fnc_equipmentSnapshotValid,"settled receipt blocked save"] call _check;
    ''')


def test_carried_ventilator_metadata_requires_a_physical_device():
    execute(harness()+r'''
        _deviceCount=0;
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"unfunded carried ventilator restored"] call _check;
        [isNil {_patient getVariable "ACME_vent_battery"},"unfunded device changed battery"] call _check;
    ''')


def test_failed_carrier_return_retains_custody_and_retries_without_refilling_looted_contents():
    execute(harness()+r'''
        private _native=[["live"],[],[],[]];
        _equipment set [4,["ACME_headElev_vestLoadout","Vest_A",[_native,[1,[]],[1,"holder",[]],[]]]];
        _patient setVariable ["ACME_headElev_vestRemoved",true];
        private _normalReturn=ACME_fnc_carrierInventoryRestore;
        ACME_fnc_carrierInventoryRestore={false};
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"refused vest return completed checkpoint"] call _check;
        private _cargo=_patient getVariable "ACME_carrierCargo";
        [!isNull _cargo,"refused vest lost holder"] call _check;
        [(_cargo getVariable "ACME_carrierPatient") isEqualTo _patient,"refused vest lost association"] call _check;
        [_cargo,["live",-1]] call _addItem;
        ACME_fnc_carrierInventoryRestore=_normalReturn;
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"vest return retry failed"] call _check;
        [!(_patient getVariable ["ACME_headElev_vestRemoved",true]),"terminated head elevation kept removed flag"] call _check;
        [(_wornContainer getVariable ["items",[]]) isEqualTo [],"return retry refilled looted cargo"] call _check;
    ''')


def test_cargo_import_rejects_native_tree_mismatch_before_mutating_ledgers():
    execute(harness()+r'''
        private _cargo="GroundWeaponHolder" createVehicle [0,0,0];
        private _tree=[[["missing"],[],[],[]],[1,[]],[1,"holder",[]],[]];
        [!([_cargo,_tree] call ACME_fnc_equipmentCargoRestore),"mismatched cargo imported"] call _check;
        [_restoreCalls==0,"mismatched cargo touched ledger"] call _check;
    ''')


def test_rehang_preserves_inline_donor_facts_after_registry_disappears():
    from test_b228_line_service_network_audit import used_setup
    fixture = re.sub(r'\bfinite (\([^()]*\))', r'(\1 call _finite)', used_setup())
    execute(fixture+r'''
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMap];
        private _meta=["freshV1",false,-188,2];
        _record=["used","FreshBlood",100,4,2,500,"Fresh blood",-1,_meta];
        call _send;
        private _rows=(_patient getVariable "ACM_circulation_IV_Bags") get "body";
        [count _rows==1,"portable donor bag refused rehang"] call _check;
        [(_rows select 0 select 9)==500,"manufacturer capacity slot overwritten"] call _check;
        [(_rows select 0 select 10) isEqualTo _meta,"portable donor metadata lost on rehang"] call _check;
    ''')


@pytest.mark.parametrize('blood', [-1,2])
def test_rehang_missing_donor_fence_cannot_bind_reused_numeric_id(blood):
    from test_b228_line_service_network_audit import used_setup
    fixture = re.sub(r'\bfinite (\([^()]*\))', r'(\1 call _finite)', used_setup())
    execute(fixture+f'private _blood={blood};'+r'''
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[1,[_patient,500,2,true,0]]]];
        _record=["used","FreshBlood",100,4,_blood,500,"Fresh blood",1,["freshMissingV1"]];
        call _send;
        private _rows=(_patient getVariable "ACM_circulation_IV_Bags") get "body";
        [_rows isEqualTo [],"unknown donor fence fell through to new registry entry"] call _check;
    ''')


@pytest.mark.parametrize('mode',['pull','discard'])
def test_salvage_keeps_inline_donor_metadata(mode):
    from test_b288_native_remove import fixture
    execute(fixture()+f'private _mode="{mode}";'+r'''
        private _meta=["freshV1",false,0,2];
        _bag set [10,_meta];
        private _canonical=[_mode,_patient,"salvage",[_bag]] call ACME_fnc_resourceReturnProducts;
        [_canonical select 0,"salvage canonical facts rejected"] call _check;
        [_medic,_patient,"salvage",_canonical select 1,7,"machineA",1] call ACME_fnc_resourceReturnReceive;
        private _rows=_medic getVariable "ACME_usedBags";
        [count _rows==1 && {(_rows select 0 select 8) isEqualTo _meta},"canonical salvage lost donor data"] call _check;
    ''')


def test_enqueued_opaque_grant_keeps_holder_alive_until_owner_sees_settled_native_rows():
    execute(harness()+r'''
        _equipment set [4,["ACME_CS_vestLoadout","Vest_A",_emptyTree]];
        _grantPending=true;
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"enqueue treated as completed native grant"] call _check;
        private _cargo=_patient getVariable "ACME_carrierCargo";
        [!isNull _cargo,"pending grant recipient deleted"] call _check;
        [_wornVest=="","pending carrier returned too soon"] call _check;
        _grantPending=false;
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"settled native grant could not finish"] call _check;
        [_wornVest=="Vest_A","settled carrier not returned"] call _check;
    ''')


def test_incomplete_restore_prevents_saving_an_intermediate_equipment_checkpoint():
    execute(harness()+r'''
        _patient setVariable ["ACME_equipmentRestoreJournal",["pending",0]];
        [([_patient] call ACME_fnc_equipmentSnapshot) isEqualTo [],"intermediate restore saved"] call _check;
    ''')


def test_intentional_new_kit_can_restore_after_an_old_incomplete_journal_was_retired():
    execute(harness()+r'''
        _patient setVariable ["ACME_equipmentRestoreJournal",["old",0]];
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        [[_patient,_equipment] call ACME_fnc_equipmentRestore,"retired journal blocked new kit"] call _check;
    ''')


def test_different_same_kit_import_cannot_overwrite_incomplete_funding_evidence():
    execute(harness()+r'''
        _patient setVariable ["ACME_equipmentRestoreJournal",["other",0]];
        [!([_patient,_equipment] call ACME_fnc_equipmentRestore),"different import replaced live journal"] call _check;
        [(_patient getVariable "ACME_equipmentRestoreJournal") isEqualTo ["other",0],"incomplete journal lost"] call _check;
    ''')
