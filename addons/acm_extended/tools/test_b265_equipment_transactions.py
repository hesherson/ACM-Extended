"""B265: execute equipment transactions; only engine inventory/UI is adapted.

No test claims to render third-party uniforms or emulate actual network delivery.
Cargo cases reuse the native-cargo fixture and production snapshot/round-trip code.
"""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, ROOT
import test_b218_carrier_inventory as cargo

F = ROOT / 'addons/acm_extended/functions'

def src(name):
    return (F / ('fn_' + name + '.sqf')).read_text()

def weapon_setup(name='hangBagRestoreWeapons'):
    s = src(name)
    s = s.replace('netId _medic', '"medic"')
    s = re.sub(r'_medic setUnitPos ([^;]+);', r'_testStance=\1;', s)
    s = s.replace('getUnitLoadout _medic', '(+_loadout)')
    s = s.replace('primaryWeapon _medic', '((_loadout select 0) param [0, ""])')
    s = s.replace('secondaryWeapon _medic', '((_loadout select 1) param [0, ""])')
    s = re.sub(r'_medic removeWeapon ([^;]+);', r'[_medic, \1] call _removeWeapon;', s)
    s = s.replace('_medic addWeapon _weapon;', '[_weapon] call _addWeapon;')
    s = re.sub(r'_medic addWeaponItem (\[[^;]+\]);', r'\1 call _addWeaponItem;', s)
    # B269 production adds narrow container suppression. These retained tests
    # carry only an incompatible spare; native autoload itself is exercised in
    # test_b269_hang_bag_magazines, with explicit class/round cargo adapters.
    s = s.replace('compatibleMagazines _weapon', '([])')
    s = s.replace('uniformContainer _medic', 'objNull').replace('vestContainer _medic', 'objNull').replace('backpackContainer _medic', 'objNull')
    s = s.replace('magazinesAmmoCargo _container', '([])')
    s = re.sub(r'_container addMagazineAmmoCargo (\[[^;]+\]);', r'\1 call _noCargo;', s)
    s = s.replace('removeAllPrimaryWeaponItems _medic;', '[0] call _removeDefaultItems;')
    s = s.replace('removeAllSecondaryWeaponItems _medic;', '[1] call _removeDefaultItems;')
    s = s.replace('getArray (configFile >> "CfgWeapons" >> _weapon >> "muzzles")', '["this", "GL"]')
    return r'''
        private _loadout=[[],[],[],["U_Custom",[["seal",2]]],["V_Custom",[["Spare",1,11]]],["B_Custom",[]],"H_Custom","G_Custom",[],[]];
        private _rifle=["Rifle","suppressor","laser","scope",["Mag_A",7],["Grenade",1],"bipod"];
        private _launcher=["Launcher","","","sight",["Rocket",1],[],""];
        private _denied=[]; private _removedWeapons=[]; private _adds=0;
        private _noCargo={};
        private _removeDefaultItems={params ["_i"]; private _slot=+(_loadout select _i); {_slot set [_x,""];} forEach [1,2,3,6]; _loadout set [_i,_slot];};
        private _weaponIndex={params ["_w"]; [0,1] select (_w=="Launcher");};
        private _addWeapon={
            params ["_w"]; private _i=[_w] call _weaponIndex; _adds=_adds+1;
            _loadout set [_i,[_w,"","","",[],[],""]];
        };
        private _addWeaponItem={
            params ["_w","_part"]; private _i=[_w] call _weaponIndex;
            private _slot=+(_loadout select _i);
            if (_part isEqualType []) then {
                private _muzzle=_part param [2,"this"];
                _slot set [[4,5] select (_muzzle=="GL"), _part select [0,2]];
            } else {
                if (_part in _denied) exitWith {};
                private _index=switch (_part) do {case "suppressor":{1};case "laser":{2};case "bipod":{6};default{3};};
                _slot set [_index,_part];
            };
            _loadout set [_i,_slot];
        };
        private _removeWeapon={
            params ["_u","_w"]; _removedWeapons pushBack _w;
            _loadout set [[_w] call _weaponIndex,[]];
        };
        private _messages=[];
        ace_common_fnc_displayTextStructured={_messages pushBack _this;};
        ACME_fnc_providerAnimation={_this select 1};
        ACME_fnc_medicAnimationPrep={0}; ACME_fnc_doAnimHeld={};
    ''' + 'ACME_fnc_' + name + '={' + adapt(s) + '};'


def test_unresolved_record_cannot_remove_newly_equipped_weapons():
    execute(weapon_setup('hangBagPrep')+r'''
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,_launcher]];
        _loadout set [0,["NewRifle","","","",["NewMag",9],[],""]];
        private _before=str _loadout;
        [_medic] call ACME_fnc_hangBagPrep;
        [str _loadout==_before && {_removedWeapons isEqualTo []},"new weapon deleted behind an old snapshot"] call _check;
        [!(_medic getVariable ["ACME_hang_Raising",false]),"rejected prep changed the episode"] call _check;
        [count _messages==1,"unresolved equipment rejection was silent"] call _check;
    ''')


def test_repeated_prep_does_not_resnapshot_or_remove_twice():
    execute(weapon_setup('hangBagPrep')+r'''
        _medic setVariable ["ACME_hang_Raising",true];
        _medic setVariable ["ACME_hang_PrepToken",77];
        _loadout set [0,+_rifle];
        [_medic] call ACME_fnc_hangBagPrep;
        [(_medic getVariable ["ACME_hang_PrepToken",-1])==77 && {_removedWeapons isEqualTo []},"duplicate prep owned a new transaction"] call _check;
    ''')


def test_partial_restore_retries_only_its_unchanged_weapon():
    execute(weapon_setup()+r'''
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,[]]];
        _denied=["scope"];
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"partial restore reported success"] call _check;
        [(_loadout select 0 select 4) isEqualTo ["Mag_A",7],"partial ammo changed"] call _check;
        _denied=[];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"unchanged partial weapon could not finish"] call _check;
        [(_loadout select 0) isEqualTo _rifle && {_adds==1},"retry recreated weapon or altered ammo"] call _check;
        [(_loadout select 3) isEqualTo ["U_Custom",[["seal",2]]],"uniform changed"] call _check;
        [(_loadout select 4) isEqualTo ["V_Custom",[["Spare",1,11]]],"spare cargo changed"] call _check;
    ''')


def test_retries_never_refill_a_fired_partially_restored_gun():
    execute(weapon_setup()+r'''
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,[]]];
        _denied=["scope"];
        [_medic] call ACME_fnc_hangBagRestoreWeapons;
        (_loadout select 0) set [4,["Mag_A",3]];
        _denied=[];
        private _before=str _loadout;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"externally changed partial gun was overwritten"] call _check;
        [str _loadout==_before && {_adds==1},"retry refilled fired ammunition"] call _check;
    ''')


def test_successful_slot_is_not_restored_again_while_other_slot_is_pending():
    execute(weapon_setup()+r'''
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,_launcher]];
        _loadout set [1,["ForeignLauncher","","","",[],[],""]];
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"foreign weapon was overwritten"] call _check;
        [((_medic getVariable ["ACME_hang_savedWeaponSlots",[]]) select 0) isEqualTo [],"restored rifle not settled separately"] call _check;
        _loadout set [0,[]]; _loadout set [1,[]];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"pending launcher failed to restore"] call _check;
        [(_loadout select 0) isEqualTo [] && {(_loadout select 1) isEqualTo _launcher},"old rifle resurrected after the player removed it"] call _check;
        [isNil {_medic getVariable "ACME_hang_savedWeaponSlots"},"settled snapshot retained"] call _check;
    ''')


@pytest.mark.parametrize('raising,pending,allowed',[(False,False,True),(True,True,True),(False,True,False)])
def test_menu_gate_does_not_cancel_its_own_inflight_launcher(raising,pending,allowed):
    s=src('hangBagCanStart').replace('objectParent _medic','objNull')
    s=s.replace('values _ivBags', '(keys _ivBags apply {_ivBags get _x})')
    execute('ACME_fnc_hangBagCanStart={'+adapt(s)+'};'+f'''
        _medic setVariable ["ACME_hang_Raising",{str(raising).lower()}];
        _medic setVariable ["ACME_hang_savedWeaponSlots",{('[[],[]]' if pending else '[]')}];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["Saline",100]]]]];
        [([_medic,_patient] call ACME_fnc_hangBagCanStart)=={str(allowed).lower()},"wrong pending equipment gate"] call _check;
    ''')


def legacy_setup():
    s=cargo.setup()
    s=s.replace('getNumber (configFile >> "CfgVehicles" >> _item >> "isBackpack") > 0','(_item=="Pack")')
    s=s.replace('getText (configFile >> "CfgWeapons" >> _item >> "ItemInfo" >> "containerClass") != ""','(_item=="Pocket")')
    s=s.replace('isClass (configFile >> "CfgMagazines" >> _item)','(_item in ["Mag_A","Mag_B"])')
    s=s.replace('getNumber (configFile >> "CfgMagazines" >> _item >> "count")','30')
    # Pinned SQF-VM does not implement finite. Only this engine numeric
    # boundary is adapted; production shape/count/range rejection executes.
    s=s.replace('finite (_mag select 1)', '((_mag select 1) call _finite)')
    s=re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', s)
    return 'private _finite={_this isEqualType 0 && {abs _this < 1e30}};' + s+r'''
        _wornVest=""; deleteVehicle _wornContainer; _wornContainer=objNull;
        private _gun=["Rifle","silencer","pointer","optic",["Mag_A",9],["Grenade",1],"bipod"];
    '''


def test_legacy_weapons_and_duplicate_partial_magazines_round_trip():
    execute(legacy_setup()+r'''
        _saved=["Vest_A",[["seal",2],["seal",1],["Mag_A",2,7],["Mag_A",1,4],[_gun,2]]];
        [[_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore,"valid legacy weapon/cargo rejected"] call _check;
        private _expected=[["seal","seal","seal"],[["Mag_A",7],["Mag_A",7],["Mag_A",4]],[_gun,_gun],[]];
        [[_expected,[_wornContainer] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual,"legacy weapon/partial ammo lost or refilled"] call _check;
        [_legacyWrites==0,"uniform was rebuilt for legacy restore"] call _check;
    ''')


@pytest.mark.parametrize('nested',[
    '[["Pocket",[["seal",2],["Mag_A",1,6]]],1]',
    '["Pocket",[["seal",2],["Mag_A",1,6]]]',
])
def test_legacy_nested_containers_preserve_contents(nested):
    execute(legacy_setup()+f'_saved=["Vest_A",[{nested}]];'+r'''
        [[_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore,"nested container rejected"] call _check;
        private _expected=[[],[],[],[["Pocket",false,[["seal","seal"],[["Mag_A",6]],[],[]]]]];
        [[_expected,[_wornContainer] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual,"nested contents changed"] call _check;
    ''')


@pytest.mark.parametrize('rows', ['["bad"]','[["seal",-1]]','[[["BadWeapon"],1]]','[["NotContainer",[["seal",1]]]]','[["seal",1,"bad"]]'])
def test_unsupported_legacy_input_is_rejected_before_replacing_any_equipment(rows):
    execute(legacy_setup()+f'_saved=["Vest_A",{rows}];'+r'''
        private _before=str _saved;
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"malformed legacy input reported success"] call _check;
        [_wornVest=="" && {str _saved==_before} && {!(_patient getVariable [_savedVar+"Settled",false])},"invalid import discarded source evidence"] call _check;
    ''')


def test_legacy_populate_rejection_keeps_snapshot_unsettled():
    execute(legacy_setup()+r'''
        _saved=["Vest_A",[["seal",2]]]; _addItem={};
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"lost cargo was marked restored"] call _check;
        [_wornVest=="" && {!(_patient getVariable [_savedVar+"Settled",false])},"failed cargo left partial equipment or consumed evidence"] call _check;
    ''')


@pytest.mark.parametrize('state,lease',[('off','current'),('removing','current'),('restoring','new')])
def test_late_replace_timeout_cannot_touch_another_equipment_state(state,lease):
    s=src('manualPlateCarrierAutoReturn')
    # Stop at the provider lookup: all rejection paths must return before any
    # provider, posture, gear, or activity-log mutation is attempted.
    s=s[:s.index('private _provider =')]+ '_touched=true; true'
    execute('ACME_fnc_manualPlateCarrierAutoReturn={'+adapt(s)+'};'+f'''
        private _touched=false;
        _patient setVariable ["ACME_manualPlateCarrierState","{state}"];
        _patient setVariable ["ACME_manualPlateCarrierLease","{lease}"];
        [!([_patient,"replace-timeout","current"] call ACME_fnc_manualPlateCarrierAutoReturn),"stale return was accepted"] call _check;
        [!_touched,"stale replacement touched equipment"] call _check;
    ''')


def test_respawn_has_no_direct_whole_unit_write_and_rechecks_its_deferred_snapshot():
    s=(ROOT/'addons/evacuation/functions/fnc_onRespawn.sqf').read_text()
    assert 'setUnitLoadout' not in s
    assert 'CBA_fnc_getLoadout' in s and 'CBA_fnc_setLoadout' in s
    assert '(getUnitLoadout _unit) isNotEqualTo _before' in s
    assert 'ACM_evacuation_loadoutEpoch' in s
    assert '!local _unit' in s and '!alive _unit' in s


@pytest.mark.parametrize('mutation', [
    '', '_isLocal=false;', '_unitAlive=false;', '_playerUnit=false;',
    '_loadout set [3,["U_Arsenal",[]]];',
    '_unit setVariable ["ACM_evacuation_loadoutEpoch",999];',
    '_unit setVariable ["ENH_savedLoadout",[]];',
])
def test_deferred_respawn_uses_cba_metadata_and_never_clobbers_successor(mutation):
    s=(ROOT/'addons/evacuation/functions/fnc_onRespawn.sqf').read_text()
    s=s.replace('local _unit','_isLocal').replace('alive _unit','_unitAlive')
    s=s.replace('isPlayer _unit','_playerUnit').replace('isMultiplayer','true')
    s=s.replace('getUnitLoadout _unit','(+_loadout)')
    execute(r'''
        private _unit=profileNamespace;
        private _isLocal=true; private _unitAlive=true; private _playerUnit=true;
        private _queued=[]; private _writes=[];
        private _loadout=[[],[],[],["U_Initial",[]],[],[],"","",[],[]];
        private _wanted=[[],[],[],["U_Preset",[]],[],[],"","",[],[]];
        private _metadata=createHashMapFromArray [["supportedMod",["gloves","sleeves"]]];
        _unit setVariable ["ENH_savedLoadout",_wanted];
        CBA_fnc_execNextFrame={_queued pushBack _this;};
        CBA_fnc_getLoadout={[+_loadout,_metadata]};
        CBA_fnc_setLoadout={_writes pushBack _this;};
    '''+'ACM_evacuation_fnc_onRespawn={'+adapt(s,component='evacuation')+'};'+r'''
        [_unit,objNull] call ACM_evacuation_fnc_onRespawn;
        [count _queued==1,"respawn did not defer exactly one checked restore"] call _check;
    '''+mutation+r'''
        ((_queued select 0) select 1) call ((_queued select 0) select 0);
    '''+(r'''
        [count _writes==1,"valid respawn restore was lost"] call _check;
        private _write=_writes select 0;
        [(_write select 1 select 0) isEqualTo _wanted,"wrong saved kit applied"] call _check;
        [(_write select 1 select 1) isEqualTo _metadata,"CBA metadata bypassed"] call _check;
        [!(_write select 2),"respawn refilled partially loaded magazines"] call _check;
    ''' if not mutation else
        '[count _writes==0,"stale respawn overwrote the current unit/kit"] call _check;'))


@pytest.mark.parametrize('rows', [
    '[[["Rifle","","","",["Mag_A",-1],[],""],1]]',
    '[[["Rifle","","","",["Mag_A",9],[],""],1,"extra"]]',
    '[["Mag_A",1,5,"extra"]]',
    '[[["Pocket",[["seal",10000]]],10000]]',
])
def test_legacy_invalid_magazines_and_expansion_are_rejected(rows):
    execute(legacy_setup()+f'_saved=["Vest_A",{rows}];'+r'''
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"unsafe legacy data accepted"] call _check;
        [_wornVest=="","validation ran after gear mutation"] call _check;
    ''')


def test_legacy_duplicate_counts_must_all_survive_population():
    execute(legacy_setup()+r'''
        _saved=["Vest_A",[["seal",1],["seal",1]]];
        _addItem={
            params ["_container","_spec"];
            if ((_container getVariable ["items",[]]) isEqualTo []) then {
                _container setVariable ["items",[_spec select 0]];
            };
        };
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"partial duplicate quantities accepted"] call _check;
        [_wornVest=="" && {!(_patient getVariable [_savedVar+"Settled",false])},"lost duplicate settled original cargo"] call _check;
    ''')
