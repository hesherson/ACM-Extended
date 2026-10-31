"""B267: executed owner kit/carrier retirement with real cargo algorithms.

Native createVehicle/equipment/position/locality and network scheduling are
explicit adapters. Live cargo objects and metadata remain the SAME objects.
This does not render uniforms or emulate Arma's network/inventory scheduler.
"""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute, adapt, namespace_public_arguments
import test_b218_carrier_inventory as cargo

F=ROOT/'addons/acm_extended/functions'
def src(name):
    if name in ('carrierKitChanged','carrierRetireToWorld','carrierLegacySnapshot'):
        return (ROOT/'addons/core/functions'/f'fnc_{name}.sqf').read_text().split('#include "..\\script_component.hpp"',1)[-1]
    return (F/f'fn_{name}.sqf').read_text()

def retired_source(name):
    s=src(name)
    s=s.replace('local _patient','_ownerLocal').replace('serverTime','_clock')
    s=s.replace('getPosATL _patient','[0,0,0]').replace('getPosATL _archive','[0,0,0]')
    s=s.replace('netId _archive','"archive"')
    s=s.replace('createVehicle ["GroundWeaponHolder_Scripted", [0,0,0], [], 0, "CAN_COLLIDE"]','(call _createHolder)')
    s=s.replace('_shell addItemCargoGlobal [_class, 1];','[_shell, [_class, 1]] call _addItem;')
    s=s.replace('detach _x;', '_detached pushBack _x;')
    return 'ACM_core_fnc_'+name+'={'+namespace_public_arguments(s)+'};'

def setup():
    s=cargo.setup().replace('_class in ["Pocket","Pack"]','_class in ["Pocket","Pack","Vest_A"]')
    # Pinned VM lacks finite; adapt only this numeric engine boundary.
    s=s.replace('finite (_mag select 1)', '((_mag select 1) call _finite)')
    s=re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', s)
    s='private _finite={_this isEqualType 0 && {abs _this < 1e30}};'+s
    return s+r'''
        private _ownerLocal=true; private _clock=100; private _newHolders=[];
        private _failCreate=false; private _detached=[]; private _released=[]; private _lowered=[];
        private _createHolder={
            if (_failCreate) exitWith {objNull};
            private _h="GroundWeaponHolder" createVehicle [0,0,0]; _newHolders pushBack _h; _h
        };
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
        ACME_fnc_patientAnimRelease={_released pushBack _this;};
        ACME_fnc_headElevateStop={_lowered pushBack _this;};
    '''+retired_source('carrierRetireToWorld')+retired_source('carrierKitChanged')

def custody(context='ACME_chestAccess_vestLoadout'):
    return f'_savedVar="{context}";'+r'''
        _saved=["Vest_A",[["SPENT",99]]];
        private _live=[ ["seal","seal"], [["Mag_A",7]],
            [["Rifle","silencer","laser","optic",["Mag_A",9],["Grenade",1],"bipod"]],
            [["Pocket",false,[["nested"],[["Mag_B",2]],[],[]]]]];
        [_wornContainer,_live] call ACME_fnc_carrierCargoPopulate;
    '''+cargo.remove()+r'''
        _patient setVariable [_savedVar,+_saved];
        _cargo setVariable ["thirdPartyPersistentId","do-not-copy-or-clear"];
        private _contents=str ([_cargo] call ACME_fnc_carrierCargoSnapshot);
        // The external setter has ALREADY applied this unrelated new kit.
        _wornVest="NewCarrier";
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        _patient setVariable ["ACME_manualPlateCarrierState","off"];
        _patient setVariable ["ACME_manualPlateCarrierLease","old-manual"];
        _patient setVariable ["ACME_chestAccess_leases",createHashMapFromArray [["old-manual",[_medic,1,"manualplatecarrier"]]]];
    '''

@pytest.mark.parametrize('context',['ACME_chestAccess_vestLoadout','ACME_CS_vestLoadout','ACME_headElev_vestLoadout'])
def test_full_kit_change_preserves_same_live_inventory_and_retires_old_custody(context):
    execute(setup()+custody(context)+r'''
        [[_patient] call ACM_core_fnc_carrierKitChanged,"kit retirement rejected"] call _check;
        [!isNull _cargo && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"live items, partial ammo or nested cargo changed"] call _check;
        [(_cargo getVariable ["thirdPartyPersistentId",""])=="do-not-copy-or-clear","mod container metadata lost"] call _check;
        [_wornVest=="NewCarrier" && {_legacyWrites==0},"replacement kit overwritten"] call _check;
        [isNull (_patient getVariable ["ACME_carrierCargo",_patient]),"retired box still tied to casualty"] call _check;
        [isNull ([_patient] call ACME_fnc_carrierInventoryGet),"new patient can spend old kit as worn gear"] call _check;
        [(_cargo getVariable ["ACME_carrierRetired",false]),"recovery record not retained"] call _check;
        [count _newHolders==1 && {_cargo getVariable ["ACME_carrierRetiredShellCreated",false]},"expected exactly one recoverable old carrier shell"] call _check;
        [(_patient getVariable ["ACME_manualPlateCarrierState","wrong"])=="","old manual watchdog retained ownership"] call _check;
        [(_patient getVariable [_savedVar,[1]]) isEqualTo [],"stale saved vest not retired"] call _check;
    ''')

def test_borrowed_semifowler_carrier_returns_one_shell_not_two():
    execute(setup()+custody()+r'''
        _patient setVariable ["ACME_headElev_vestLoadout",+_saved];
        _patient setVariable ["ACME_headElev_vestRemoved",true];
        _patient setVariable ["ACME_headElev_manualCarrierBorrowed",true];
        _patient setVariable ["ACME_headElevated",true];
        [[_patient] call ACM_core_fnc_carrierKitChanged,"borrowed carrier not retired"] call _check;
        [count _newHolders==1 && {count _lowered==1},"borrowed alias duplicated carrier or failed to retire unsupported posture"] call _check;
        [_wornVest=="NewCarrier" && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"head support overwrote current kit/contents"] call _check;
    ''')

@pytest.mark.parametrize('empty_new_kit',[False,True])
def test_duplicate_boundaries_never_duplicate_carrier_or_rewear_old_slot(empty_new_kit):
    execute(setup()+custody()+('_wornVest="";' if empty_new_kit else '')+r'''
        [_patient] call ACM_core_fnc_carrierKitChanged;
        _patient setVariable ["ACME_equipmentKitEpoch",2];
        [_patient] call ACM_core_fnc_carrierKitChanged;
        [count _newHolders==1,"duplicate loadout events duplicated old wearable gear"] call _check;
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"old snapshot was reused after kit boundary"] call _check;
        [_legacyWrites==0 && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"retired inventory was reapplied"] call _check;
    ''')

def test_failed_shell_creation_keeps_current_contents_and_recovery_evidence():
    execute(setup()+custody()+r'''
        _failCreate=true;
        [[_patient] call ACM_core_fnc_carrierKitChanged,"live box could not be independently retained"] call _check;
        [!isNull _cargo && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"shell failure lost current supplies"] call _check;
        [(_cargo getVariable ["ACME_carrierRetiredRecord",[]]) select 1 isEqualTo _saved,"shell failure lost saved class/recovery record"] call _check;
        [!(_cargo getVariable ["ACME_carrierRetiredShellCreated",false]),"shell failure reported success"] call _check;
        [_wornVest=="NewCarrier","shell failure used patient as scratch loadout"] call _check;
    ''')

def test_failed_shell_cargo_round_trip_never_deletes_live_supplies_or_visual():
    execute(setup()+custody()+r'''
        private _prop="GroundWeaponHolder" createVehicle [0,0,0];
        _patient setVariable ["ACME_chestAccess_vestProp",_prop];
        _addItem={};
        [_patient] call ACM_core_fnc_carrierKitChanged;
        [!isNull _prop && {!isNull _cargo} && {count _detached==1},"failed wearable staging deleted original evidence"] call _check;
        [str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents,"failed shell changed original live cargo"] call _check;
    ''')

def test_world_inventory_survives_patient_deletion():
    execute(setup()+custody()+r'''
        [_patient] call ACM_core_fnc_carrierKitChanged;
        deleteVehicle _patient;
        [!isNull _cargo && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"despawn deleted retired physical inventory"] call _check;
        [!isNull (_cargo getVariable ["ACME_carrierRetiredShell",objNull]),"despawn deleted independent shell"] call _check;
    ''')

def test_no_live_holder_does_not_resurrect_historical_supplies():
    execute(setup()+custody()+r'''
        deleteVehicle _cargo;
        [_patient] call ACM_core_fnc_carrierKitChanged;
        [count _newHolders==2,"deleted live box prevented independent shell/recovery record"] call _check;
        [([_newHolders select 0] call ACME_fnc_carrierCargoSnapshot) isEqualTo [[],[],[],[]],"deleted/spent supplies resurrected from stale snapshot"] call _check;
        [_wornVest=="NewCarrier","missing old box touched new kit"] call _check;
    ''')

def test_nonowner_cannot_retire_carrier():
    execute(setup()+custody()+r'''
        _ownerLocal=false;
        [!([_patient] call ACM_core_fnc_carrierKitChanged),"nonowner accepted retirement"] call _check;
        [(_patient getVariable ["ACME_carrierCargo",objNull]) isEqualTo _cargo && {count _newHolders==0},"nonowner touched old inventory"] call _check;
    ''')

def test_foreign_holder_is_not_modified_or_deleted():
    execute(setup()+custody()+r'''
        _cargo setVariable ["ACME_carrierPatient",_medic];
        [!([_patient] call ACM_core_fnc_carrierKitChanged),"foreign inventory was adopted"] call _check;
        [(_cargo getVariable ["ACME_carrierPatient",objNull]) isEqualTo _medic && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"foreign holder mutated"] call _check;
        [_wornVest=="NewCarrier" && {count _newHolders==0},"foreign holder caused new gear writes"] call _check;
    ''')

def test_kit_change_cancels_only_carrier_tokens_and_preserves_completed_interventions():
    execute(setup()+custody()+r'''
        _patient setVariable ["ACME_chestAccess_vestBusy","vest:old"];
        _patient setVariable ["ACME_CS_vestBusy","cs:old"];
        _patient setVariable ["ACME_chestAccess_vestPFH",13];
        _patient setVariable ["ACME_CS_ProcedureTokens",["viewer1","viewer2"]];
        _patient setVariable ["ACME_CS_PreparationToken","viewer1"];
        _patient setVariable ["ACME_patientAnimLock",["CPR","another-owner"]];
        _patient setVariable ["ACME_thora_tube_left",true];
        _patient setVariable ["ACME_CS_seals",["existing seal"]];
        _patient setVariable ["ACME_headElev_startEpoch",7];
        [_patient] call ACM_core_fnc_carrierKitChanged;
        [_released isEqualTo [[_patient,"vest:old"],[_patient,"cs:old"]],"unrelated patient animation token was released"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[1]]) isEqualTo [],"old viewer membership remained live"] call _check;
        [((_patient getVariable ["ACME_CS_ClosedTokens",[]]) apply {_x select 0}) isEqualTo ["viewer1","viewer2"],"old Begin retries could reopen retired equipment session"] call _check;
        [_patient getVariable ["ACME_thora_tube_left",false],"kit change removed tube"] call _check;
        [(_patient getVariable ["ACME_CS_seals",[]]) isEqualTo ["existing seal"],"kit change erased applied chest seal"] call _check;
        [(_patient getVariable ["ACME_headElev_startEpoch",0])==8,"old head-position continuation not invalidated"] call _check;
    ''')

@pytest.mark.parametrize('operation', ['chestAccessVestEvent','chestSealPatientBegin','manualPlateCarrier','headElevStart'])
def test_old_owner_request_is_rejected_after_kit_boundary(operation):
    s=src('ownerDispatch').split('switch (_operation) do {',1)[0]+'_admitted=_admitted+1;'
    s=s.replace('local _patient','_isLocal')
    execute('ACME_fnc_ownerDispatch={'+adapt(s)+'};'+r'''
        private _isLocal=false; private _admitted=0;
        _patient setVariable ["ACME_equipmentKitEpoch",3];
    '''+f'[_patient,"{operation}",[]] call ACME_fnc_ownerDispatch;'+r'''
        private _packet=(_events select 0) select 1;
        [_packet select 4==3,"owner request did not carry original kit"] call _check;
        _patient setVariable ["ACME_equipmentKitEpoch",4]; _isLocal=true;
        _packet call ACME_fnc_ownerDispatch;
        [_admitted==0,"old owner request acquired replacement gear"] call _check;
    ''')

def test_dispatch_does_not_fence_unrelated_clinical_effects():
    s=src('ownerDispatch').split('switch (_operation) do {',1)[0]+'_admitted=_admitted+1;'
    execute('ACME_fnc_ownerDispatch={'+adapt(s)+'};'+r'''
        private _admitted=0;
        _patient setVariable ["ACME_equipmentKitEpoch",4];
        [_patient,"medicationLine",[],1,3] call ACME_fnc_ownerDispatch;
        [_admitted==1,"kit guard improperly suppressed clinical transaction"] call _check;
    ''')

def test_old_inventory_snapshot_cannot_consume_new_same_class_custody():
    execute(setup()+custody()+r'''
        [_patient] call ACM_core_fnc_carrierKitChanged;
        _wornVest="Vest_A"; _wornContainer="GroundWeaponHolder" createVehicle [0,0,0];
        private _newCargo=[_patient,_savedVar] call ACME_fnc_carrierInventoryCreate;
        private _newSaved=["Vest_A",[["different",2]]];
        _patient setVariable [_savedVar,+_newSaved];
        _wornVest="";
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"old snapshot restored newer custody"] call _check;
        [!isNull _newCargo && {(_patient getVariable ["ACME_carrierCargo",objNull]) isEqualTo _newCargo},"old callback consumed new live inventory"] call _check;
    ''')

def test_modals_capture_patient_kit_and_close_on_replacement():
    for name,prefix in [('chestSealOpen','ACME_CS'),('thoraOpen','ACME_Thora')]:
        assert f'uiNamespace setVariable ["{prefix}_PatientKitEpoch", _patient getVariable ["ACME_equipmentKitEpoch", 0]];' in src(name)
    assert 'ACME_CS_PatientKitEpoch' in src('chestSealTick')
    assert 'ACME_Thora_PatientKitEpoch' in src('thoraTick')

def test_healthy_replacement_does_not_create_carrier_or_change_clinical_state():
    execute(setup()+r'''
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        _patient setVariable ["ACME_hpmk_state","wrapped"];
        [_patient] call ACM_core_fnc_carrierKitChanged;
        [count _newHolders==0 && {_wornVest=="Vest_A"},"healthy kit replacement generated equipment"] call _check;
        [(_patient getVariable ["ACME_hpmk_state",""])=="wrapped","unrelated clinical equipment cleared"] call _check;
    ''')


def test_legacy_retirement_materializes_valid_contents_without_outfitting_patient():
    # Same production parser/populate/comparison used for B265 legacy return.
    from test_b265_equipment_transactions import legacy_setup
    base=legacy_setup().replace('"Pocket","Pack"','"Pocket","Pack","Vest_A"')
    extra=r'''
        private _ownerLocal=true; private _clock=100; private _newHolders=[]; private _detached=[];
        private _createHolder={private _h="GroundWeaponHolder" createVehicle [0,0,0]; _newHolders pushBack _h; _h};
        ACME_fnc_patientAnimRelease={};
        CBA_fnc_removePerFrameHandler={};
        _saved=["Vest_A",[["seal",2],["Mag_A",1,7],[_gun,1]]];
        _patient setVariable [_savedVar,+_saved];
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        _wornVest="FreshUniformKit";
    '''
    execute(base+extra+retired_source('carrierRetireToWorld')+retired_source('carrierKitChanged')+r'''
        [[_patient] call ACM_core_fnc_carrierKitChanged,"legacy world retirement rejected"] call _check;
        [count _newHolders==2,"legacy archive/shell not created once"] call _check;
        private _expected=[["seal","seal"],[["Mag_A",7]],[_gun],[]];
        [[_expected,[_newHolders select 0] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual,"legacy world inventory incomplete/refilled"] call _check;
        [_wornVest=="FreshUniformKit" && {_legacyWrites==0},"legacy retirement rebuilt replacement unit"] call _check;
    ''')


def test_malformed_legacy_custody_remains_fenced_and_is_not_discarded():
    execute(setup()+r'''
        _saved=["Vest_A",[["bad",-2]]];
        _patient setVariable [_savedVar,+_saved];
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        [!([_patient] call ACM_core_fnc_carrierKitChanged),"invalid legacy record was silently accepted"] call _check;
        [(_patient getVariable [_savedVar,[]]) isEqualTo _saved && {count _newHolders==0},"invalid legacy recovery evidence discarded"] call _check;
        [_wornVest=="Vest_A","invalid legacy input mutated worn inventory"] call _check;
        [(_patient getVariable [_savedVar+"KitEpoch",99])!=1,"failed legacy archive could overwrite current kit later"] call _check;
    ''')


def test_already_settled_carrier_does_not_create_a_second_shell():
    execute(setup()+r'''
        _patient setVariable [_savedVar,+_saved];
        _patient setVariable [_savedVar+"Settled",true];
        [_patient] call ACM_core_fnc_carrierKitChanged;
        [count _newHolders==0,"already returned carrier was duplicated on new kit"] call _check;
    ''')


def test_unrelated_multiple_records_are_not_cleared_as_one_carrier():
    execute(setup()+r'''
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[["a",1]]]];
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_B",[["b",1]]]];
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        [!([_patient] call ACM_core_fnc_carrierKitChanged),"ambiguous carriers treated as borrowed alias"] call _check;
        [count _newHolders==0 && {count (_patient getVariable ["ACME_CS_vestLoadout",[]])==2},"one ambiguous carrier discarded"] call _check;
    ''')


def test_carrier_kit_helpers_are_native_registered_and_not_runtime_overrides():
    prep=(ROOT/'addons/core/XEH_PREP.hpp').read_text()
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    for name in ('carrierKitChanged','carrierRetireToWorld','carrierLegacySnapshot'):
        assert prep.count(f'PREP({name});')==1
        assert f'class {name} {{}};' not in cfg
    assert 'call ACM_core_fnc_carrierKitChanged;' in (ROOT/'addons/core/functions/fnc_equipmentKitChanged.sqf').read_text()


@pytest.mark.parametrize('flag',[False,True])
def test_physical_holder_always_wins_over_historical_inventory(flag):
    execute(setup()+custody()+f'_patient setVariable [_savedVar+"Live",{str(flag).lower()}];'+r'''
        [[_patient] call ACM_core_fnc_carrierKitChanged,"existing holder rejected"] call _check;
        [str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents,"bookkeeping flag caused live contents to be reset"] call _check;
        [isNull (_patient getVariable ["ACME_carrierCargo",_patient]),"live carrier not detached after retirement"] call _check;
    ''')


def test_live_holder_without_a_saved_vest_record_is_not_orphaned():
    execute(setup()+custody()+r'''
        _patient setVariable [_savedVar,[]];
        [!([_patient] call ACM_core_fnc_carrierKitChanged),"ambiguous holder was accepted"] call _check;
        [(_patient getVariable ["ACME_carrierCargo",objNull]) isEqualTo _cargo,"unclassified live supplies were orphaned"] call _check;
        [!isNull _cargo && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents} && {count _newHolders==0},"ambiguous holder contents mutated"] call _check;
    ''')


def test_borrow_flag_does_not_merge_unrelated_chestseal_and_head_carriers():
    execute(setup()+r'''
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[["a",1]]]];
        _patient setVariable ["ACME_headElev_vestLoadout",["Vest_A",[["a",1]]]];
        _patient setVariable ["ACME_headElev_manualCarrierBorrowed",true];
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        [!([_patient] call ACM_core_fnc_carrierKitChanged),"stale borrow flag merged unrelated records"] call _check;
        [count _newHolders==0 && {count (_patient getVariable ["ACME_CS_vestLoadout",[]])==2},"unrelated carrier evidence discarded"] call _check;
    ''')
