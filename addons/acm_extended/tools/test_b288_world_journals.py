"""Execute server-wide checkpoint refusal, including deleted actors' journals."""
import pytest

from test_menu_death_lifecycle import F, adapt, execute
from test_historical_vial_execution import map_defaults


def setup():
    text = (F / 'fn_persistenceJournalsReady.sqf').read_text()
    for name in ('_map', '_deliveries', '_vents', '_boxes'):
        text = text.replace('values '+name, '(keys '+name+' apply {'+name+' get _x})')
    text = text.replace('allUnits', '_units').replace('allDeadMen', '_dead')
    return '''
    private _units=[];private _dead=[];
    private _mapDefault={params ["_m","_a"];_a params ["_k","_d"];if (_k in _m) then {_m get _k} else {_d}};
    '''+'ACME_fnc_persistenceJournalsReady={'+adapt(map_defaults(text))+'};'


@pytest.mark.parametrize('name,row',[
    ('ACME_resourceReturns','[objNull,objNull,"r",[],"ready"]'),
    ('ACME_resourceReturns','[objNull,objNull,"r",[],"orphaned"]'),
    ('ACM_circulation_FreshBloodGrants','[objNull,objNull,500,"r",[],"ready"]'),
    ('ACME_bf_serverGrants','[objNull,"ON",[7,1],"pending"]'),
    ('ACME_coolerBoxReceipts','["draw",objNull,"blood",0,objNull,[],0,false]'),
])
def test_pending_product_blocks_world_checkpoint_after_both_actors_deleted(name,row):
    execute(setup()+f'missionNamespace setVariable ["{name}",createHashMapFromArray [["r",{row}]]];'+r'''
    [!([] call ACME_fnc_persistenceJournalsReady),"deleted actors hid pending funding from world save"] call _check;
    ''')


@pytest.mark.parametrize('phase',['reserved','packing','packingAbort'])
def test_unsettled_native_token_blocks_world_save_without_a_live_owner(phase):
    execute(setup()+f'''
    missionNamespace setVariable ["ACME_inventoryLedgerIndex",createHashMapFromArray [["cooler:sid",17]]];
    missionNamespace setVariable ["ACME_inventoryToken_17",["cooler","sid",[],objNull,"r","{phase}",1]];
    [!([] call ACME_fnc_persistenceJournalsReady),"unsettled native token omitted"] call _check;
    ''')


def test_settled_history_and_attached_device_do_not_block_checkpoint():
    execute(setup()+r'''
    missionNamespace setVariable ["ACME_resourceReturns",createHashMapFromArray [["r",[objNull,objNull,"r",[],"delivered"]]]];
    missionNamespace setVariable ["ACM_circulation_FreshBloodGrants",createHashMapFromArray [["r",[objNull,objNull,500,"r",[],"delivered"]]]];
    missionNamespace setVariable ["ACME_bf_serverGrants",createHashMapFromArray [["r",[objNull,"ON",[7,1],"delivered"]]]];
    missionNamespace setVariable ["ACME_syringeDeliveries",createHashMapFromArray [["r",createHashMapFromArray [["state","settled"]]]]];
    missionNamespace setVariable ["ACME_vent_custody",createHashMapFromArray [["r",createHashMapFromArray [["phase","attached"]]]]];
    missionNamespace setVariable ["ACME_coolerBoxReceipts",createHashMapFromArray [["r",["draw",objNull,"blood",0,objNull,[],0,true]]]];
    [[] call ACME_fnc_persistenceJournalsReady,"settled history blocked checkpoint"] call _check;
    ''')


@pytest.mark.parametrize('name,row',[
    ('ACME_syringeDeliveries','createHashMapFromArray [["state","active"]]'),
    ('ACME_vent_custody','createHashMapFromArray [["phase","returning"]]'),
    ('ACME_resourceReturns','"malformed"'),
])
def test_other_server_journals_fail_closed(name,row):
    execute(setup()+f'missionNamespace setVariable ["{name}",createHashMapFromArray [["r",{row}]]];'+r'''
    [!([] call ACME_fnc_persistenceJournalsReady),"unsettled/malformed server journal accepted"] call _check;
    ''')


def test_public_supply_binding_on_corpse_blocks_world_checkpoint():
    execute(setup()+r'''
    _dead=[_patient];
    _patient setVariable ["ACME_IV_SupplyBindings",createHashMapFromArray [["r",[]]]];
    [!([] call ACME_fnc_persistenceJournalsReady),"corpse supply binding omitted from save preflight"] call _check;
    ''')
