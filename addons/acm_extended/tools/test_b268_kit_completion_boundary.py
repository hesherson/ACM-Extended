"""B268: completed setters, rather than Arsenal button reports, retire a kit.

The installed production CBA/native handlers, equipment/carrier retirement,
live cargo algorithms, Hang Bag stop, and medication writers execute in SQF-VM.
Only engine inventory/locality/UI and the external ACE/CBA event producer are
adapters. This does not emulate Arma's replication or inventory scheduler.

ACE event adapter provenance (supplied ACE3-master snapshot):
  addons/arsenal/functions/fnc_buttonImport.sqf, lines 29-34, 50-62, 94
  SHA256 1c3ae188a025cfdd4a529a32db754e87956d03a13e8db7cc3a7d060f22fc7649
  addons/arsenal/functions/fnc_buttonLoadoutsLoad.sqf, lines 38, 68-69
  SHA256 96b4508f934122019d83cdba2d0723457cd0191a096a5f4ccbe98430f0ce43b6
The import accepts a parsed array, wraps length 10, applies only length 2,
then emits loadoutImported even when no setter ran (including []). Saved
loads apply the CBA setter before onLoadoutLoad. The adapter preserves these
branches; the tests have no dependency on the external attachment directory.
"""
import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b212_prone_providers import hang_setup
from test_b267_carrier_kit_boundary import setup as carrier_setup, custody


def production(name, core=False):
    """Adapt engine boundaries while retaining the whole production function."""
    source = ((ROOT / 'addons/core/functions' / f'fnc_{name}.sqf').read_text()
              if core else read(name))
    source = source.replace('hasInterface', '_interface').replace('is3DEN', '_editor')
    source = source.replace('local _unit', '_localUnit').replace('local _owner', '_localUnit')
    source = source.replace('canSuspend', 'false')
    source = source.replace('player addEventHandler', '_nativeEH pushBack')
    source = source.replace(', _public]', ']')
    # These fixtures retain real VM objects; the shared namespace adapter's
    # typed-object conversion is unnecessary at this engine boundary.
    source = source.replace('objNull, [objNull]', 'objNull')
    return adapt(source)


def setup(interface=True):
    hang = hang_setup().replace('objNull, [profileNamespace]', 'objNull')
    return carrier_setup() + hang + custody() + r'''
        private _interface=true; private _editor=false; private _localUnit=true;
        private _registered=createHashMapFromArray [
            ["CBA_loadoutSet",[]],["ACME_equipmentKitReplaced",[]],
            ["ace_arsenal_onLoadoutLoad",[]],["ace_arsenal_onLoadoutLoadExtended",[]],
            ["ace_arsenal_loadoutImported",[]]
        ]; private _nativeEH=[];
        private _installed=0; private _setters=0;
        private _kitCalls=[]; private _resets=[]; private _claims=[];
        CBA_fnc_addEventHandler={
            params ["_event","_handler"];
            private _handlers=+(_registered get _event);
            _handlers pushBack _handler; _registered set [_event,_handlers];
            _installed=_installed+1; _installed
        };
        private _emit={
            params ["_event","_args"];
            {_args call _x;} forEach (_registered get _event);
        };
        private _native={
            params ["_event","_args"];
            {if ((_x select 0)==_event) then {_args call (_x select 1);};} forEach _nativeEH;
        };
        ACME_fnc_ownerDispatch={_claims pushBack _this;};
        ACME_fnc_vialLeaseRelease={};
        missionNamespace setVariable ["ACME_HCMedPushJob",createHashMap];
        missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",[]];
        ACE_player=_medic;
        missionNamespace setVariable ["ace_arsenal_center",_patient];
        // A parked carrier is still the patient's live supply source before a
        // completed setter. The historical snapshot contains spent supplies.
        _wornVest="";
        _patient setVariable ["ACME_hang_Active",true];
        _patient setVariable ["ACME_hang_Claimed",true];
        _patient setVariable ["ACME_hang_Raising",true];
        _patient setVariable ["ACME_hang_Start",10];
        _patient setVariable ["ACME_hang_PFH",7];
        _patient setVariable ["ACME_hang_Patient",_medic];
        _patient setVariable ["ACME_hang_weaponKitEpoch",1];
        _patient setVariable ["ACME_hang_savedWeaponSlots",[["OLD_RIFLE"],[]]];
        _patient setVariable ["ACME_hang_weaponRestoreOwned",[["partial"],[]]];
        _patient setVariable ["ACME_narcStore",[["prepared",["calcium",2]]]];
        _patient setVariable ["ACME_narcStoreSerial",7];
        _patient setVariable ["ACME_infusion_openVials",createHashMapFromArray [["calcium",1.96]]];
        _medic setVariable ["ACME_equipmentKitEpoch",40];
        _medic setVariable ["ACME_hang_savedWeaponSlots",[["VIEWER_RIFLE"],[]]];
        _medic setVariable ["ACME_narcStore",[["viewer-syringe",["ketamine",1]]]];
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["ketamine",0.5]]];
        private _snapshot={
            params ["_unit"];
            [
                _unit getVariable ["ACME_equipmentKitEpoch",0],
                _unit getVariable ["ACME_hang_savedWeaponSlots",[]],
                _unit getVariable ["ACME_hang_weaponRestoreOwned",[]],
                _unit getVariable ["ACME_hang_Active",false],
                _unit getVariable ["ACME_hang_Start",-1],
                _unit getVariable ["ACME_hang_Raising",false],
                _unit getVariable ["ACME_narcStore",[]],
                _unit getVariable ["ACME_narcStoreSerial",0],
                str (_unit getVariable ["ACME_infusion_openVials",createHashMap]),
                _unit getVariable ["ACME_manualPlateCarrierState",""],
                _unit getVariable ["ACME_manualPlateCarrierLease",""],
                _unit getVariable [_savedVar,[]]
            ]
        };
        private _before=[_patient] call _snapshot;
        private _viewerBefore=[_medic] call _snapshot;
        private _unchanged={
            [([_patient] call _snapshot) isEqualTo _before,"button/no-setter event reset kit, hang or medication custody"] call _check;
            [(_patient getVariable ["ACME_carrierCargo",objNull]) isEqualTo _cargo,"button/no-setter event orphaned parked carrier"] call _check;
            [([_patient] call ACME_fnc_carrierInventoryGet) isEqualTo _cargo,"button/no-setter event disabled live supplies"] call _check;
            [str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents,"button/no-setter event changed partial ammo or nested supplies"] call _check;
            [count _newHolders==0 && {count _claims==0} && {count _kitCalls==0} && {count _resets==0},"button/no-setter event performed teardown"] call _check;
            [([_medic] call _snapshot) isEqualTo _viewerBefore,"viewer's kit was altered"] call _check;
        };
    ''' + f'_interface={str(interface).lower()};' + r'''
        private _installCore={
    ''' + production('registerEquipmentKitRuntime', core=True) + r'''};
        private _equipmentChanged={
    ''' + production('equipmentKitChanged', core=True) + r'''};
        ACM_core_fnc_equipmentKitChanged={
            _kitCalls pushBack (_this select 0); _this call _equipmentChanged
        };
        ACME_fnc_narcStoreCommit={
    ''' + production('narcStoreCommit') + r'''};
        ACME_fnc_openVialStoreCommit={
    ''' + production('openVialStoreCommit') + r'''};
        private _reset={
    ''' + production('resetPersonalMedicationKit') + r'''};
        ACME_fnc_resetPersonalMedicationKit={
            _resets pushBack (_this select 0); _this call _reset
        };
        call _installCore;
    ''' + production('registerSyringeLifecycleRuntime') + r'''
        // External producer: CBA completion reports the edited unit only
        // after the setter has applied its physical kit.
        private _complete={
            params ["_unit","_loadout"];
            _setters=_setters+1;
            _unit setVariable ["ACME_testPhysicalLoadout",_loadout];
            if (_unit isEqualTo _patient) then {_wornVest="FreshCarrier";};
            ["CBA_loadoutSet",[_unit,_loadout,createHashMap]] call _emit;
        };
        private _clipboard={
            params ["_parsed",["_importList",false]];
            if !(_parsed isEqualType []) exitWith {};
            if !(_importList && {_editor}) then {
                if (count _parsed==10) then {_parsed=[_parsed,createHashMap];};
                if (count _parsed==2) then {[_patient,_parsed] call _complete;};
            };
            ["ace_arsenal_loadoutImported",[objNull,_importList && {_editor}]] call _emit;
        };
        private _saved={
            private _loadout=+_this;
            [_patient,_loadout] call _complete;
            ["ace_arsenal_onLoadoutLoad",[_loadout,"Saved kit"]] call _emit;
            ["ace_arsenal_onLoadoutLoadExtended",[[_loadout,createHashMap],"Saved kit"]] call _emit;
        };
        private _retiredOnce={
            params [["_epoch",2],["_count",1]];
            [(_patient getVariable ["ACME_equipmentKitEpoch",0])==_epoch,"completion advanced wrong number of kit generations"] call _check;
            private _expected=[];
            for "_i" from 1 to _count do {_expected pushBack _patient;};
            [_kitCalls isEqualTo _expected && {_resets isEqualTo _expected},"completion did not retire edited unit exactly once"] call _check;
            [isNull (_patient getVariable ["ACME_carrierCargo",objNull]) && {count _newHolders==1},"completion failed to independently retain one old carrier"] call _check;
            [!isNull _cargo && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"completion lost live carrier supplies"] call _check;
            [(_cargo getVariable ["thirdPartyPersistentId",""])=="do-not-copy-or-clear","completion erased foreign container metadata"] call _check;
            [isNil {_patient getVariable "ACME_hang_savedWeaponSlots"} && {isNil {_patient getVariable "ACME_hang_weaponRestoreOwned"}},"completed kit retained old weapon snapshots"] call _check;
            [!(_patient getVariable ["ACME_hang_Active",true]) && {!(_patient getVariable ["ACME_hang_Raising",true])},"completed kit retained old held bag"] call _check;
            [(_patient getVariable ["ACME_narcStore",[1]]) isEqualTo [] && {count (_patient getVariable ["ACME_infusion_openVials",createHashMapFromArray [["wrong",1]]])==0},"completed kit retained prepared syringes/open vial remnants"] call _check;
            [(_patient getVariable ["ACME_narcStoreSerial",-1])==0,"completed kit retained serial"] call _check;
            [([_medic] call _snapshot) isEqualTo _viewerBefore,"completion reset viewer rather than edited unit"] call _check;
            [_restores==0 && {_legacyWrites==0} && {count _moves==0} && {count _stances==0},"completion reapplied old weapons/loadout or pose"] call _check;
        };
    '''


@pytest.mark.parametrize('parsed', ['[]', '[1]', '[1,2,3]', '"not an array"'])
def test_invalid_clipboard_array_never_retires_a_live_kit(parsed):
    execute(setup() + f'[{parsed}] call _clipboard;' + r'''
        [_setters==0,"invalid clipboard unexpectedly invoked setter"] call _check;
        call _unchanged;
    ''')


@pytest.mark.parametrize('event,args', [
    ('ace_arsenal_onLoadoutLoad', '[[],"No completed setter"]'),
    ('ace_arsenal_loadoutImported', '[objNull,false]'),
    ('ace_arsenal_loadoutImported', '[objNull,true]'),
])
def test_arsenal_button_only_events_preserve_all_existing_custody(event, args):
    execute(setup() + f'for "_i" from 1 to 3 do {{["{event}",{args}] call _emit;}};' + r'''
        call _unchanged;
    ''')


@pytest.mark.parametrize('producer', [
    '[[],[],[],[],[],[],"","",[],[]] call _saved;',
    '[[[],[],[],[],[],[],"","",[],[]]] call _clipboard;',
    '[[[[],[],[],[],[],[],"","",[],[]],createHashMap]] call _clipboard;',
])
@pytest.mark.parametrize('interface,viewer_is_target', [
    (True, True), (True, False), (False, False)
], ids=['player', 'edited-local-ai', 'server-or-hc-ai'])
def test_successful_ace_sequence_retires_only_actual_unit_once(producer, interface, viewer_is_target):
    code = setup(interface=interface)
    if viewer_is_target:
        code += 'ACE_player=_patient;'
    execute(code + producer + r'''
        [_setters==1,"valid producer did not complete one setter"] call _check;
        [] call _retiredOnce;
        [count _claims==1 && {((_claims select 0) select 2) isEqualTo [_patient,10]},"completed setter did not release exact held bag once"] call _check;
        call _installCore;
        [_installed==2,"startup registered duplicate or button-based kit handlers"] call _check;
    ''')


def test_consecutive_identical_valid_loads_are_distinct_completed_kits():
    execute(setup() + r'''
        private _same=[[],[],[],[],[],[],"","",[],[]];
        _same call _saved;
        // Real use of the first fresh kit before reapplying the identical kit.
        _patient setVariable ["ACME_narcStore",[["new-prepared",["calcium",1]]]];
        _patient setVariable ["ACME_infusion_openVials",createHashMapFromArray [["calcium",0.6]]];
        _patient setVariable ["ACME_hang_savedWeaponSlots",[["FIRST_FRESH_RIFLE"],[]]];
        _same call _saved;
        [3,2] call _retiredOnce;
        [_setters==2 && {count _claims==1},"identical consecutive applications were collapsed or repeated old release"] call _check;
        [(_patient getVariable ["ACME_testPhysicalLoadout",[]]) isEqualTo _same && {_wornVest=="FreshCarrier"},"retirement altered last applied kit"] call _check;
    ''')


@pytest.mark.parametrize('event', ['CBA_loadoutSet', 'ACME_equipmentKitReplaced'])
@pytest.mark.parametrize('guard', ['_localUnit=false;', '_editor=true;'])
def test_nonowner_and_editor_completion_reports_are_ignored(event, guard):
    execute(setup(interface=False) + guard + f'["{event}",[_patient,[],createHashMap]] call _emit;' + r'''
        call _unchanged;
    ''')


def test_editor_import_of_preset_library_does_not_apply_or_retire_equipment():
    execute(setup() + r'''
        _editor=true;
        [[ ["Preset",[[],[],[],[],[],[],"","",[],[]]] ],true] call _clipboard;
        [_setters==0,"preset library import applied kit"] call _check;
        call _unchanged;
    ''')


def test_raw_setter_requires_its_explicit_completion_notification():
    execute(setup(interface=False) + r'''
        // Native setUnitLoadout has no CBA event; the external author must
        // report successful completion explicitly on the actual owner.
        _patient setVariable ["ACME_testPhysicalLoadout",["Raw replacement"]];
        _wornVest="FreshCarrier";
        call _unchanged;
        ["ACME_equipmentKitReplaced",[_patient]] call _emit;
        [] call _retiredOnce;
        [(_patient getVariable ["ACME_testPhysicalLoadout",[]]) isEqualTo ["Raw replacement"],"explicit raw-setter notification wrote over new gear"] call _check;
    ''')


@pytest.mark.parametrize('local', [True, False])
def test_native_respawn_uses_new_unit_and_preserves_viewers_kit(local):
    execute(setup() + f'_localUnit={str(local).lower()};' + r'''
        ["Respawn",[_patient,_medic]] call _native;
    ''' + ('[] call _retiredOnce;' if local else 'call _unchanged;'))


def test_completion_runtime_requires_no_ace_arsenal_runtime_or_interface():
    execute(setup(interface=False) + r'''
        ["CBA_loadoutSet",[_patient,[],createHashMap]] call _emit;
        [] call _retiredOnce;
        [count _nativeEH==0 && {_installed==2},"headless owner required Arsenal or player UI runtime"] call _check;
    ''')
