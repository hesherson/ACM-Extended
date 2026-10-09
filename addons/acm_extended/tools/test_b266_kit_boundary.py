"""B266 explicit kit replacement, executing the real Hang Bag lifecycle.

Only Arma/UI/network boundaries are mocked. Never infer a wholesale replacement
from ordinary loot, opening/closing Arsenal, or importing a preset library.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b212_prone_providers import hang_setup
from test_b265_equipment_transactions import weapon_setup

F=ROOT / "addons/acm_extended/functions"
_base_read=read

def read(name):
    if name in ['equipmentKitChanged','registerEquipmentKitRuntime']:
        return (ROOT/'addons/core/functions'/('fnc_'+name+'.sqf')).read_text()
    return _base_read(name)


def kit_code():
    s=read('equipmentKitChanged').replace('local _unit', '_localUnit')
    s=s.replace('canSuspend', 'false')
    # Carrier retirement is a separate production subsystem, covered by B267.
    return 'ACM_core_fnc_carrierKitChanged={}; ACM_core_fnc_equipmentKitChanged={'+adapt(s)+'};'


def setup():
    return hang_setup()+r'''
        private _localUnit=true;
        private _claims=[]; private _reopens=[]; private _freshKit="untouched";
        ACME_fnc_ownerDispatch={_claims pushBack _this;};
        ACM_circulation_fnc_openTransfusionMenu={_reopens pushBack _this;};
        _medic setVariable ["ACME_hang_weaponKitEpoch",0];
        _medic setVariable ["ACME_hang_savedWeaponSlots",[["OLD"],[]]];
        _medic setVariable ["ACME_hang_weaponRestoreOwned",[["partial"],[]]];
    '''+kit_code()


@pytest.mark.parametrize('claimed', [False, True])
def test_explicit_replacement_releases_only_existing_claim_without_equipment_or_pose_return(claimed):
    execute(setup()+r'''
        call _activate;
        _medic setVariable ["ACME_hang_Raising",true];
        _medic setVariable ["ACME_DP_Paused",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","hangbag"];
    '''+f'_medic setVariable ["ACME_hang_Claimed",{str(claimed).lower()}];'+r'''
        _held=[];
        [[_medic] call ACM_core_fnc_equipmentKitChanged,"explicit kit change rejected"] call _check;
        [count _held==1 && {((_held select 0) select 1)==""},"old pending/active animation reassert worker was not retired once"] call _check;
        [!(_medic getVariable ["ACME_hang_Active",true]) && {!(_medic getVariable ["ACME_hang_Raising",true])},"old hang episode remained live"] call _check;
        [isNil {_medic getVariable "ACME_hang_savedWeaponSlots"} && {isNil {_medic getVariable "ACME_hang_weaponRestoreOwned"}},"old weapon custody survived kit replacement"] call _check;
        [count _claims==1 && {(_claims select 0) isEqualTo [_patient,"hangBagRelease",[_medic,10]]},"replacement released wrong patient or epoch"] call _check;
        [_restores==0 && {count _moves==0} && {count _stances==0} && {count _reopens==0},"kit replacement restarted old equipment/pose/UI"] call _check;
        [!(_medic getVariable ["ACME_DP_Paused",true]),"retired bag kept DP paused"] call _check;
        [_freshKit=="untouched","new kit changed"] call _check;
    ''')


def test_repeated_notifications_cannot_release_patient_twice_or_restore_old_kit():
    execute(setup()+r'''
        call _activate;
        for "_i" from 1 to 3 do {[_medic] call ACM_core_fnc_equipmentKitChanged;};
        [count _claims==1 && {_restores==0},"duplicate kit events replayed release or restoration"] call _check;
        [(_medic getVariable ["ACME_equipmentKitEpoch",0])==3,"kit generations did not advance"] call _check;
    ''')


def test_remote_unit_cannot_have_its_custody_cleared_here():
    execute(setup()+r'''
        call _activate;
        private _saved=str (_medic getVariable ["ACME_hang_savedWeaponSlots",[]]);
        _localUnit=false;
        [!([_medic] call ACM_core_fnc_equipmentKitChanged),"nonowner accepted a kit replacement"] call _check;
        [_medic getVariable ["ACME_hang_Active",false],"nonowner stopped held bag"] call _check;
        [str (_medic getVariable ["ACME_hang_savedWeaponSlots",[]])==_saved && {count _claims==0},"nonowner changed equipment"] call _check;
    ''')


def test_ordinary_new_kit_does_not_clear_other_procedure_or_another_unit():
    execute(setup()+r'''
        _medic setVariable ["ACME_DP_PauseTreatmentClass","CPR"];
        _medic setVariable ["ACME_DP_Paused",true];
        _patient setVariable ["ACME_hang_savedWeaponSlots",[["PATIENT"],[]]];
        _medic setVariable ["ACME_chestAccess_vestLoadout",["V",[["current",2]]]];
        _medic setVariable ["ACME_thora_tube_left",true];
        [_medic] call ACM_core_fnc_equipmentKitChanged;
        [_medic getVariable ["ACME_DP_Paused",false],"unrelated CPR pause was retired"] call _check;
        [(_patient getVariable ["ACME_hang_savedWeaponSlots",[]]) isEqualTo [["PATIENT"],[]],"other unit kit cleared"] call _check;
        [(_medic getVariable ["ACME_chestAccess_vestLoadout",[]]) isEqualTo ["V",[["current",2]]],"live carrier inventory was erased"] call _check;
        [_medic getVariable ["ACME_thora_tube_left",false],"kit event reset clinical state"] call _check;
    ''')


def test_delayed_raise_does_not_reassert_after_new_kit():
    execute(hang_setup()+kit_code()+r'''
        private _localUnit=true;
        _stance="STAND"; _animation="standing-idle";
        [_medic] call ACME_fnc_hangBagPrep;
        [count _waits==1,"missing delayed stand-to-kneel preparation"] call _check;
        private _old=_waits select 0;
        [_medic] call ACM_core_fnc_equipmentKitChanged;
        _held=[]; _moves=[]; _stances=[];
        [_old] call _deliver;
        [count _held==0 && {count _moves==0} && {count _stances==0},"old raise reasserted after kit change"] call _check;
    ''')


def test_delayed_native_preparation_cancel_has_no_authority_after_kit_change():
    execute(hang_setup()+kit_code()+r'''
        private _localUnit=true;
        [_medic] call ACME_fnc_hangBagPrep;
        [_medic] call ACM_core_fnc_equipmentKitChanged;
        _held=[]; _moves=[]; _stances=[]; _restores=0;
        [_medic] call ACME_fnc_hangBagPrepStop;
        [count _held==0 && {count _moves==0} && {count _stances==0} && {_restores==0},"stale native cancel touched replacement kit/pose"] call _check;
    ''')


@pytest.mark.parametrize('new_kit', [False,True])
def test_delayed_lowering_teardown_checks_kit_generation(new_kit):
    execute(hang_setup()+r'''
        private _reopens=[];
        ACM_circulation_fnc_openTransfusionMenu={_reopens pushBack _this;};
        call _activate;
        _animation="acme_acts_jetscrewaidfcrouchthumbup";
        [false,_medic] call ACME_fnc_hangBagStop;
        [count _waits==1,"lowering did not queue completion"] call _check;
        private _job=_waits select 0;
        // Timeout uses the exact same production teardown as a normal exit.
        private _timeout=_job select 3;
        _moves=[]; _stances=[]; _restores=0; _waits=[];
    '''+('_medic setVariable ["ACME_equipmentKitEpoch",1];' if new_kit else '')+r'''
        (_job select 1) call _timeout;
    '''+(r'''
        [_restores==0 && {count _moves==0} && {count _stances==0} && {count _waits==0},"stale lower restored/moved/reopened over new kit"] call _check;
    ''' if new_kit else r'''
        [_restores==1 && {count _moves==1} && {count _stances==1},"normal same-kit bag lowering lost its restoration"] call _check;
    '''))


def test_already_queued_stance_and_transfusion_reopen_are_fenced_by_kit_epoch():
    execute(hang_setup()+r'''
        private _reopens=[];
        ACM_circulation_fnc_openTransfusionMenu={_reopens pushBack _this;};
        call _activate;
        [false,_medic] call ACME_fnc_hangBagStop;
        [count _waits==2,"normal cleanup did not queue stance release and menu"] call _check;
        _medic setVariable ["ACME_equipmentKitEpoch",1];
        _stances=[]; _moves=[];
        {[_x] call _deliver;} forEach (+_waits);
        [count _stances==0 && {count _moves==0} && {count _reopens==0},"old late cleanup touched new kit UI/stance"] call _check;
    ''')


@pytest.mark.parametrize('current,snapshot,allowed',[(0,0,True),(1,0,False),(2,2,True)])
def test_weapon_snapshot_must_belong_to_current_kit(current,snapshot,allowed):
    execute(weapon_setup()+f'''
        _medic setVariable ["ACME_equipmentKitEpoch",{current}];
        _medic setVariable ["ACME_hang_weaponKitEpoch",{snapshot}];
    '''+r'''
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,[]]];
        private _before=str _loadout;
    '''+f'''
        [([_medic] call ACME_fnc_hangBagRestoreWeapons)=={str(allowed).lower()},"wrong kit snapshot admitted"] call _check;
    '''+('[(_loadout select 0) isEqualTo _rifle,"current kit restore lost"] call _check;' if allowed else
        '[str _loadout==_before && {_adds==0},"stale kit wrote a weapon"] call _check;'))


def event_setup():
    s=read('registerEquipmentKitRuntime').replace('local _unit','_localUnit').replace('is3DEN','_editor')
    return r'''
        private _registered=createHashMap; private _handlerCalls=0;
        private _localUnit=true; private _editor=false;
        private _equipment=[]; private _medical=[];
        CBA_fnc_addEventHandler={_registered set [_this select 0,_this select 1];_handlerCalls=_handlerCalls+1;_handlerCalls};
        ACM_core_fnc_equipmentKitChanged={_equipment pushBack (_this select 0);};
        ACME_fnc_resetPersonalMedicationKit={_medical pushBack (_this select 0);};
    '''+'private _register={'+adapt(s)+'}; call _register;'


@pytest.mark.parametrize('event', ['CBA_loadoutSet','ACME_equipmentKitReplaced'])
@pytest.mark.parametrize('unit',['_medic','_patient'])
def test_explicit_kit_hooks_use_actual_event_unit_not_current_player(event,unit):
    execute(event_setup()+f'''
        [{unit},[],createHashMap] call (_registered get "{event}");
        [_equipment isEqualTo [{unit}] && {{_medical isEqualTo [{unit}]}},"event reset the wrong unit"] call _check;
        call _register;
        [_handlerCalls==2,"runtime installed duplicate kit event handlers"] call _check;
    ''')


@pytest.mark.parametrize('mutation',['_localUnit=false;','_editor=true;'])
def test_kit_events_ignore_other_owner_and_editor(mutation):
    execute(event_setup()+mutation+r'''
        [_medic] call (_registered get "CBA_loadoutSet");
        [count _equipment==0 && {count _medical==0},"nonowner/editor kit altered"] call _check;
    ''')


@pytest.mark.parametrize('import_list,editor,expected',[(False,False,1),(True,False,0),(False,True,0),(True,True,0)])
def test_clipboard_applied_kit_but_not_preset_list_or_editor_is_replacement(import_list,editor,expected):
    s=read('registerSyringeLifecycleRuntime').replace('player addEventHandler','_life pushBack').replace('is3DEN','_editor').replace('local _unit','_localUnit')
    execute(event_setup()+f'private _life=[]; _editor={str(editor).lower()};'+adapt(s)+f'''
        [objNull,{str(import_list).lower()}] call (_registered get "ace_arsenal_loadoutImported");
        [count _equipment=={expected} && {{count _medical=={expected}}},"import list/editor was mistaken for new equipment"] call _check;
    ''')


def test_no_ordinary_inventory_or_arsenal_close_invalidation_hook():
    s=read('registerEquipmentKitRuntime')+read('registerSyringeLifecycleRuntime')
    from source_scan import lex
    names=[t.value for t in lex(s) if t.kind=='string']
    for forbidden in ['loadout','Take','Put','InventoryClosed','ace_arsenal_displayClosed','ace_arsenal_displayOpened']:
        assert forbidden not in names


def test_medical_runtime_does_not_introduce_full_unit_loadout_setters():
    from source_scan import lex
    prohibited={'setunitloadout','cba_fnc_setloadout','bis_fnc_loadinventory','bis_fnc_loadinventoryfile'}
    hits=[]
    for file in F.glob('*.sqf'):
        for t in lex(file.read_text()):
            if t.kind=='ident' and t.value.lower() in prohibited: hits.append((file.name,t.value))
    assert hits==[]


def test_startup_registers_once_on_all_owners_not_only_ui_clients():
    prep=(ROOT/'addons/core/XEH_PREP.hpp').read_text()
    for name in ['equipmentKitChanged','registerEquipmentKitRuntime']:
        assert f'PREP({name});' in prep
    assert read('initForkStartupRuntime').count('call ACM_core_fnc_registerEquipmentKitRuntime;')==1
    from source_scan import lex
    assert not any(t.kind=='ident' and t.value=='hasInterface' for t in lex(read('registerEquipmentKitRuntime')))


@pytest.mark.parametrize('event', ['ace_arsenal_onLoadoutLoad','ace_arsenal_loadoutImported'])
@pytest.mark.parametrize('local', [True,False])
def test_arsenal_center_not_ace_player_receives_actual_kit_replacement(event,local):
    s=read('registerSyringeLifecycleRuntime').replace('player addEventHandler','_life pushBack')
    s=s.replace('is3DEN','_editor').replace('local _unit','_localUnit')
    execute(event_setup()+"private _life=[];"+adapt(s)+f"""
        missionNamespace setVariable ["ace_arsenal_center",_patient];
        _localUnit={str(local).lower()};
        [objNull,false] call (_registered get "{event}");
    """+('[ _equipment isEqualTo [_patient] && {_medical isEqualTo [_patient]},"Arsenal reset viewer instead of edited unit"] call _check;'
        if local else '[count _equipment==0 && {count _medical==0},"Arsenal changed remote kit here"] call _check;'))


def test_identical_shape_replaced_kit_invalidates_pending_respawn_write():
    from test_b265_equipment_transactions import test_deferred_respawn_uses_cba_metadata_and_never_clobbers_successor
    test_deferred_respawn_uses_cba_metadata_and_never_clobbers_successor('_unit setVariable ["ACME_equipmentKitEpoch",1];')
