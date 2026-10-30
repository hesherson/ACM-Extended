"""Execute capture refusal while a provider still owns funded eye-shield escrow.

Actual clinical snapshot and native serializer failure branches, inventory save
and local/world preflight run; object/world enumeration and JSON are explicit
engine boundaries. No unresolved supply metadata is serialized as equipment.
"""
import pytest

from test_b291_medmash_phys import persistence_setup, wrapped
from test_b271_ptx_stability import execute
from test_b288_inventory_persistence import setup as inventory_setup
from test_b288_world_persistence import setup as world_setup
from test_b288_world_journals import setup as journal_setup
from test_menu_death_lifecycle import ROOT, adapt, execute as menu_execute
from test_b291_ocular_integration import function as ocular_function


def setup():
    readiness = wrapped('medmashSnapshotReady').replace('allUnits', '_units').replace('allDeadMen', '_dead')
    return persistence_setup() + r'''
        private _units=[];private _dead=[];
        private _request=[_patient,_medic,"shield-1",7,0,0,0,150,[],7,0,[7,0]];
    ''' + readiness


@pytest.mark.parametrize('dead_provider', [False, True])
def test_patient_medical_capture_waits_for_another_providers_unsettled_funding(dead_provider):
    execute(setup() + f'_{"dead" if dead_provider else "units"}=[_medic];' + r'''
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[_request]];
        [([_patient] call ACME_fnc_clinicalSnapshot) isEqualTo [],"patient captured across another actor's unsettled supply"] call _check;
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[]];
        [([_patient] call ACME_fnc_clinicalSnapshot) isNotEqualTo [],"terminal shield settlement permanently blocked medical capture"] call _check;
    ''')


def test_unrelated_patients_medical_snapshot_is_not_blocked_by_another_shield_request():
    execute(setup() + r'''
        _units=[_medic];_request set [0,_medic];
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[_request]];
        [([_patient] call ACME_fnc_clinicalSnapshot) isNotEqualTo [],"unrelated patient capture was globally blocked"] call _check;
    ''')


def test_medical_serializer_returns_existing_failure_sentinel_instead_of_empty_success_payload():
    text=(ROOT/'addons/core/overrides/fnc_serializeState.sqf').read_text()
    tail=text[text.index('private _clinicalSnapshot ='):]
    execute(setup() + r'''
        private _deletions=0;
        CBA_fnc_deleteNamespace={_deletions=_deletions+1;};
        CBA_fnc_encodeJSON={"valid-json-boundary"};
        private _serialize={private _state=missionNamespace;private _unit=_patient;
    ''' + adapt(tail) + r'''
        };
        _units=[_medic];_medic setVariable ["ACM_ophthalmology_shieldBindings",[_request]];
        [(call _serialize)=="" && {_deletions==1},"busy clinical snapshot was encoded as a successful empty medical state"] call _check;
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[]];
        [(call _serialize)=="valid-json-boundary" && {_deletions==2},"settled capture did not return to normal serializer path"] call _check;
    ''')


def test_actor_own_binding_blocks_medical_snapshot_and_transient_escrow_is_never_saved():
    execute(setup() + r'''
        _patient setVariable ["ACM_ophthalmology_shieldBindings",[_request]];
        [([_patient] call ACME_fnc_clinicalSnapshot) isEqualTo [],"actor's own reservation omitted"] call _check;
        _patient setVariable ["ACM_ophthalmology_shieldBindings",[]];
        _patient setVariable ["ACM_ophthalmology_shieldFunding_shield_1",[_request,"settled"]];
        private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
        private _names=(_snapshot select 1) apply {_x select 0};
        [!(("ACM_ophthalmology_shieldBindings" in _names) || {"ACM_ophthalmology_shieldFunding_shield_1" in _names}),"runtime funding/receipt metadata leaked into clinical persistence"] call _check;
    ''')


def test_native_inventory_checkpoint_refuses_live_shield_binding_then_recovers_after_settlement():
    menu_execute(inventory_setup() + r'''
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[["unsettled"]]];
        [([_medic] call ACME_fnc_inventorySnapshot) isEqualTo [],"unsettled shield reservation allowed inventory checkpoint"] call _check;
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[]];
        [([_medic] call ACME_fnc_inventorySnapshot) isEqualTo [1,[]],"settled shield binding permanently blocked native inventory checkpoint"] call _check;
    ''')


def test_local_equipment_preflight_refuses_provider_binding_until_settled():
    menu_execute(world_setup() + r'''
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[["unsettled"]]];
        [!([_medic] call ACME_fnc_persistenceReady),"provider could checkpoint funded escrow"] call _check;
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[]];
        [[_medic] call ACME_fnc_persistenceReady,"settled source permanently blocked checkpoint readiness"] call _check;
    ''')


def test_owner_preflight_uses_native_cleanup_to_recover_delayed_terminal_binding():
    menu_execute(world_setup() + ocular_function('shieldSource') + r'''
        private _medicLocal=true;private _serverClock=100;
        private _receipt=[_medic,"kat_eyecovers","item","source:7:1"];
        private _request=[_patient,_medic,"r",7,0,0,0,150,_receipt,7,0,[7,0]];
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[_request]];
        _medic setVariable ["ACM_ophthalmology_shieldFunding_source_7_1",[_request,"sent"]];
        [!([_medic] call ACME_fnc_persistenceReady),"native cleanup retired an unproved funding decision"] call _check;
        _medic setVariable ["ACM_ophthalmology_shieldFunding_source_7_1",[_request,"settled"]];
        [[_medic] call ACME_fnc_persistenceReady,"lost terminal cleanup event permanently blocked owner checkpoint"] call _check;
        [(_medic getVariable "ACM_ophthalmology_shieldBindings") isEqualTo [],"native terminal cleanup did not retire exact binding"] call _check;
    ''')


@pytest.mark.parametrize('dead_provider', [False, True])
def test_world_checkpoint_refuses_any_provider_binding_until_settled(dead_provider):
    menu_execute(journal_setup() + f'_{"dead" if dead_provider else "units"}=[_medic];' + r'''
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[["unsettled"]]];
        [!([] call ACME_fnc_persistenceJournalsReady),"world checkpoint omitted provider shield funding"] call _check;
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[]];
        [[] call ACME_fnc_persistenceJournalsReady,"terminal settlement kept global checkpoint blocked"] call _check;
    ''')


def test_malformed_nonempty_provider_binding_cannot_silently_disappear_from_patient_capture():
    execute(setup() + r'''
        _units=[_medic];_medic setVariable ["ACM_ophthalmology_shieldBindings",[[]]];
        [([_patient] call ACME_fnc_clinicalSnapshot) isEqualTo [],"malformed pending binding was treated as known settled"] call _check;
    ''')


@pytest.mark.parametrize('boundary', ['medical','inventory','local','world'])
def test_patient_owned_incoming_custody_fences_capture_after_provider_and_source_machine_are_gone(boundary):
    if boundary == 'medical':
        prefix, run = setup(), execute
        actor, probe, rejected = '_patient', '[_patient] call ACME_fnc_clinicalSnapshot', 'isEqualTo []'
    elif boundary == 'inventory':
        prefix, run = inventory_setup(), menu_execute
        actor, probe, rejected = '_medic', '[_medic] call ACME_fnc_inventorySnapshot', 'isEqualTo []'
    elif boundary == 'local':
        prefix, run = world_setup(), menu_execute
        actor, probe, rejected = '_medic', '[_medic] call ACME_fnc_persistenceReady', 'isEqualTo false'
    else:
        prefix, run = journal_setup()+'_units=[_patient];', menu_execute
        actor, probe, rejected = '_patient', '[] call ACME_fnc_persistenceJournalsReady', 'isEqualTo false'
    run(prefix + f'''
        missionNamespace setVariable ["ACM_ophthalmology_shieldPending",createHashMap];
        {actor} setVariable ["ACM_ophthalmology_shieldIncoming",createHashMapFromArray [["receipt",[objNull,objNull]]]];
        [(({probe}) {rejected}),"patient custody vanished when source actor/process disappeared"] call _check;
        {actor} setVariable ["ACM_ophthalmology_shieldIncoming",createHashMap];
        [!(({probe}) {rejected}),"terminal patient custody closure permanently blocked capture"] call _check;
    ''')


@pytest.mark.parametrize('boundary', ['medical','inventory','local','world'])
def test_private_source_ledger_blocks_capture_after_original_actor_disappears_and_recovers_when_settled(boundary):
    if boundary == 'medical':
        prefix, run = setup(), execute
        probe, rejected = '[_patient] call ACME_fnc_clinicalSnapshot', 'isEqualTo []'
    elif boundary == 'inventory':
        prefix, run = inventory_setup(), menu_execute
        probe, rejected = '[_medic] call ACME_fnc_inventorySnapshot', 'isEqualTo []'
    elif boundary == 'local':
        prefix, run = world_setup(), menu_execute
        probe, rejected = '[_medic] call ACME_fnc_persistenceReady', 'isEqualTo false'
    else:
        prefix, run = journal_setup(), menu_execute
        probe, rejected = '[] call ACME_fnc_persistenceJournalsReady', 'isEqualTo false'
    run(prefix + r'''
        missionNamespace setVariable ["ACM_ophthalmology_shieldPending",createHashMapFromArray [["orphaned",[objNull,objNull]]]];
    ''' + f'[((({probe})) {rejected}),"deleted source actor hid unresolved funding from capture"] call _check;'
        + r'''
        missionNamespace setVariable ["ACM_ophthalmology_shieldPending",createHashMap];
    ''' + f'[!((({probe}) {rejected})),"terminal private settlement permanently blocked capture"] call _check;')
