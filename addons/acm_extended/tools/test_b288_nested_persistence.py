"""Execute worn-nested checkpoints against the real opaque ledger and importer.

Native cargo, locality, profile flush and CBA transport remain fixtures. The
production source-funded import, grant wait, recursive schema and ledger run.
"""
from test_b288_inventory_persistence import setup as inventory_setup
from test_b288_equipment_persistence import source as equipment_source
from test_b279_inventory_ledger import adapted
from test_menu_death_lifecycle import F, execute


def setup():
    code = inventory_setup() + r'''
    private _wornVest="Vest_A";private _wornContainer=missionNamespace;
    private _rootUniform=objNull;private _rootBackpack=objNull;
    private _testInterface=false;
    private _populateCalls=0;
    _wornContainer setVariable ["children",[["Pocket",_receiver]]];
    _receiver setVariable ["children",[]];
    ACME_fnc_vialCapacity={10};
    ACME_fnc_coolerBagVolume={params ["_class"];if ((_class find "ACM_BloodBag_")==0 || {(_class find "ACM_FreshBloodBag_")==0}) then {500} else {0}};
    ace_common_fnc_getCountOfItem={0};
    ACME_fnc_coolerSnapshot={[1,"holder",[]]};
    ACME_fnc_coolerSnapshotValid={params ["_s"];_s isEqualTo [1,"holder",[]]};
    ACME_fnc_coolerRestore={true};
    ACME_fnc_carrierCargoPopulate={_populateCalls=_populateCalls+1;true};
    ACME_fnc_carrierCargoSnapshot={params ["_o"];
        if (_o isEqualTo objNull) exitWith {[[],[],[],[]]};
        private _children=(_o getVariable ["children",[]]) apply {[_x select 0,false,[_x select 1] call ACME_fnc_carrierCargoSnapshot]};
        [_o getVariable ["items",[]],[_o] call _nativePairs,[],_children]
    };
    '''
    code += 'ACME_fnc_carrierCargoEqual={' + adapted((F / 'fn_carrierCargoEqual.sqf').read_text()) + '};'
    code += ''.join(adapted(equipment_source(n)) for n in [
        'ventDeviceFields', 'openVialStoreCommit', 'equipmentCargoValid',
        'equipmentCargoSnapshot', 'equipmentCargoRestore', 'equipmentSnapshotValid',
        'equipmentSnapshot', 'equipmentRestore',
    ])
    return code


def test_worn_nested_syringe_import_waits_for_actual_grant_and_keeps_identity_and_exact_dose():
    execute(setup() + r'''
    private _row=["Lidocaine",3,1.25,"Nested syringe",0.75,[["Lidocaine",1.25]],"dilutionB13","red","line1","line2","line3","nested-source","flush","inventoryB279"];
    [_receiver,"syringe",[["nested-source",_row]]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    private _oldNative=+(_receiver getVariable "native");
    private _saved=[_medic] call ACME_fnc_equipmentSnapshot;
    [count _saved==6 && {count (_saved select 5)==1},"worn nested syringe metadata omitted"] call _check;
    private _node=(_saved select 5) select 0;
    [(_node select 0)==1 && {(_node select 1)=="Pocket"}
        && {count (_node select 2 select 1 select 1)==1},"nested slot or payload lost"] call _check;
    [!([_medic,_saved] call ACME_fnc_equipmentRestore),"enqueue was treated as an actual native grant"] call _check;
    [(_receiver getVariable "native") isEqualTo [],"saved source tuple was not exchanged"] call _check;
    [isNil {_medic getVariable "ACME_equipmentRestoreReceipt"},"whole checkpoint completed before nested grant"] call _check;
    call _flush;
    [([_medic,_saved] call ACME_fnc_equipmentRestore),"settled nested grant did not complete import"] call _check;
    private _now=+(_receiver getVariable "native");
    [count _now==1 && {_now isNotEqualTo _oldNative},"nested carrier was duplicated or not remapped"] call _check;
    private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_now select 0 select 0],[]];
    [(_record select 3) isEqualTo _receiver && {(_record select 5)=="held"},"nested custody belongs to deleted/wrong holder"] call _check;
    private _actual=+(_record select 2 select 1);_actual set [11,"nested-source"];
    [_actual isEqualTo _row,"nested syringe dose, components or label changed"] call _check;
    private _sequence=missionNamespace getVariable "ACME_inventoryTokenSequence";
    [([_medic,_saved] call ACME_fnc_equipmentRestore),"completed nested replay rejected"] call _check;call _flush;
    [(_receiver getVariable "native") isEqualTo _now && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==_sequence}
        && {_populateCalls==0},"nested replay refilled cargo or issued another identity"] call _check;
    private _again=[_medic] call ACME_fnc_equipmentSnapshot;
    [count _again==6 && {count (_again select 5)==1},"restored nested custody could not be saved again"] call _check;
    ''')


def test_missing_or_duplicated_nested_physical_source_is_rejected_before_any_exchange():
    execute(setup() + r'''
    private _row=["Lidocaine",3,1.25,"Nested syringe",0.75,[["Lidocaine",1.25]],"dilutionB13","red","line1","line2","line3","nested-source","flush","inventoryB279"];
    [_receiver,"syringe",[["nested-source",_row]]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    private _saved=[_medic] call ACME_fnc_equipmentSnapshot;
    (_saved select 5) pushBack (+((_saved select 5) select 0));
    private _before=+(_receiver getVariable "native");
    [!([_medic,_saved] call ACME_fnc_equipmentRestore),"one physical child funded duplicate metadata"] call _check;
    [(_receiver getVariable "native") isEqualTo _before && {count _queue==0}
        && {_populateCalls==0},"failed complete-child binding mutated native custody"] call _check;
    ''')
