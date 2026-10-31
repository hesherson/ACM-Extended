"""Run disposable IV accessories through real reservation and owner transactions.

Native inventory and display handles are explicit stand-ins. The production
Take/Bind/Scope/Start/Commit/Reply/Refund functions execute together, including
exact donor provenance, retries and cancellation. No native Arma acceptance is
claimed by this fixture.
"""
import json

import pytest

import test_menu_death_lifecycle as lifecycle
from medication_inventory import subtree
from test_b156_procedure_supplies import supply_setup
from test_b232_iv_finish import SETUP, START_SETUP, rules, source, start_source
from test_menu_death_lifecycle import ROOT, execute


ACCESSORIES = {
    "extension": ("ACME_IVExtension", [False, False, False, False], 0),
    "dressing": ("ACME_Tegaderm", [True, True, False, False], 2),
    "line": ("ACME_IVLine", [True, True, True, False], 3),
    "lock": ("ACME_SalineLock", [False, False, False, False], 4),
}


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def fixture(action):
    item, state, _ = ACCESSORIES[action]
    return SETUP + rules() + START_SETUP + supply_setup() + \
        "ACME_fnc_ivFinishStart={" + start_source() + "};" + r'''
        // Hit testing is a native UI boundary here; the real planner still
        // authorizes this exact seated hub before any inventory is debited.
        ACME_fnc_ivFinishTarget={[_row]};
        // Native getOrDefault is adapted without SQF-VM's warning for a nil
        // temporary; inventory policy and receipt decisions stay unchanged.
        _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        // These supply fixtures have no hung bags. External bag/rope teardown
        // has separate production-chain coverage in the field-IV suite.
        ACME_fnc_ivAccessoryUnplug={
            [count (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap])==0,
                "inventory fixture unexpectedly detached a hung bag"] call _check;
            true
        };
        _d setVariable ["ACME_IV_FinishActive",[]];
        _medic setVariable ["ACME_IV_FinishPending",[]];
        _medic setVariable ["fixtureStock",[]];
        _patient setVariable ["fixtureStock",[]];
        private _lastOwnerRequest=[];
        private _beginRequest={
            private _request=_events select 0;
            _lastOwnerRequest=[_patient]+(_request select 2);
            _lastOwnerRequest call ACME_fnc_ivFinishCommit;
        };
        private _ack={
            private _reply=call _lastReply;
            _reply call ACME_fnc_ivFinishReply;
        };
        private _finishRequest={
            private _request=+_lastOwnerRequest;
            _request set [2,"finish"];
            _request set [8,[]];
            _request call ACME_fnc_ivFinishCommit;
        };
    ''' + f'''
        _row set [15,{json.dumps(state).lower()}];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        private _item="{item}";
        private _start={{[0.5,0.5,"{action}"] call ACME_fnc_ivFinishStart;}};
    '''


@pytest.mark.parametrize("action", ACCESSORIES)
@pytest.mark.parametrize("donor", ["medic", "patient", "vehicle"])
def test_actual_item_is_reserved_once_and_successful_owner_completion_does_not_refund(action, donor):
    _, _, state_index = ACCESSORIES[action]
    stock = {
        "medic": '_medic setVariable ["fixtureStock",[_item]];',
        "patient": '_patient setVariable ["fixtureStock",[_item]];',
        "vehicle": '_medic setVariable ["fixtureParent",missionNamespace];missionNamespace setVariable ["fixtureCargo",[_item]];',
    }[donor]
    expected_donor = "_patient" if donor == "patient" else "_medic"
    execute(fixture(action) + stock + r'''
        call _start;call _start;
        [count _debits==1 && {count _events==1},"accessory did not debit exactly once before owner request"] call _check;
        private _held=(_medic getVariable "ACME_IV_FinishPending") select 6;
        [count _held==4 && {(_held select 1)==_item},"pending procedure lost exact physical accessory"] call _check;
    ''' + f'''[(_held select 0) isEqualTo {expected_donor},"accessory charged the wrong donor"] call _check;''' + r'''
        call _beginRequest;call _ack;call _ack;
        _lastOwnerRequest call ACME_fnc_ivFinishCommit;
        _serverTime=102;call _finishRequest;call _finishRequest;call _ack;
        [count _debits==1 && {count _refunds==0},"successful or duplicate callbacks recreated an accessory"] call _check;
        [count (missionNamespace getVariable "ACME_supplyReceipts")==0
            && {(_medic getVariable "ACME_IV_SupplyBindings") isEqualTo []},"used accessory retained a reusable reservation"] call _check;
    ''' + f'''[(call _getState) select {state_index},"paid accessory was not installed"] call _check;''')


@pytest.mark.parametrize("action", ACCESSORIES)
def test_no_inventory_item_stops_the_actual_ui_start_before_any_owner_request(action):
    execute(fixture(action) + r'''
        private _before=str (_patient getVariable "ACME_IV_Marks");
        call _start;
        [count _debits==0 && {count _events==0},"empty stock still started a free accessory procedure"] call _check;
        [(_medic getVariable "ACME_IV_FinishPending") isEqualTo [],"missing stock locked the UI"] call _check;
        [str (_patient getVariable "ACME_IV_Marks")==_before,"missing accessory changed the catheter"] call _check;
    ''')


@pytest.mark.parametrize("action", ACCESSORIES)
@pytest.mark.parametrize("receipt", ["[]", '[_medic,"ACM_SalineFlush_10",objNull,"wrong-item"]'])
def test_owner_endpoint_refuses_missing_or_wrong_accessory_receipts(action, receipt):
    execute(fixture(action) + f'''
        [_patient,_medic,"begin","ivhub:7:1","{action}","unfunded",7,130,{receipt}] call ACME_fnc_ivFinishCommit;
        [!((call _lastReply) select 4),"unfunded accessory passed the owner gate"] call _check;
        [(call _getRow select 16) isEqualTo [],"unfunded accessory created an active job"] call _check;
    ''')


@pytest.mark.parametrize("action", ACCESSORIES)
@pytest.mark.parametrize("full_inventory", [False, True])
def test_cancel_before_owner_begin_refunds_the_original_item_once_even_with_late_begin(action, full_inventory):
    execute(fixture(action) + r'''
        _patient setVariable ["fixtureStock",[_item]];
        private _ground=[];
    ''' + (r'''
        // ACE's full-inventory spill is the native placement boundary. The
        // production refund still chooses the original donor and original item.
        ace_common_fnc_addToInventory={params ["_donor","_class"];
            _ground pushBack [_donor,_class];_refunds pushBack [_donor,_class];};
    ''' if full_inventory else "") + r'''
        call _start;
        [] call ACME_fnc_ivFinishAbort;
        private _cancel=_events select 1;
        ([_patient]+(_cancel select 2)) call ACME_fnc_ivFinishCommit;call _ack;
        call _beginRequest;call _ack;
        [count _debits==1 && {count _refunds==1},"cancel/late BEGIN refunded twice or lost the accessory"] call _check;
        [(_refunds select 0) isEqualTo [_patient,_item],"refund changed original item or donor"] call _check;
        [(call _getRow select 16) isEqualTo [],"late BEGIN escaped the cancellation tombstone"] call _check;
    ''' + f'''[count _ground=={int(full_inventory)},"full inventory did not use exactly one native ground return"] call _check;''')


@pytest.mark.parametrize("action", ACCESSORIES)
def test_missing_binding_waits_for_replication_and_retries_without_another_debit(action):
    execute(fixture(action) + r'''
        _medic setVariable ["fixtureStock",[_item]];call _start;
        private _binding=+(_medic getVariable "ACME_IV_SupplyBindings");
        _medic setVariable ["ACME_IV_SupplyBindings",[]];
        call _beginRequest;
        [count _events==1 && {(call _getRow select 16) isEqualTo []},"unreplicated binding was treated as accepted or rejected"] call _check;
        _medic setVariable ["ACME_IV_SupplyBindings",_binding];
        // Ownership handover has no copy of the origin's private receipt maps.
        missionNamespace setVariable ["ACME_supplyReceipts",createHashMap];
        missionNamespace setVariable ["ACME_IV_SupplyScopes",createHashMap];
        _lastOwnerRequest call ACME_fnc_ivFinishCommit;
        [((call _lastReply) select 4) && {count (call _getRow select 16)>0},"owner did not recover the replicated exact scope"] call _check;
        [count _debits==1,"binding retry charged another physical accessory"] call _check;
    ''')


@pytest.mark.parametrize("action", ACCESSORIES)
@pytest.mark.parametrize("change", [
    "_testClinicalEpoch=8;",
    "_hasIV=false;",
    '_row set [14,"replacement-hub"];_patient setVariable ["ACME_IV_Marks",[_row]];',
])
def test_changed_access_before_owner_begin_refunds_one_real_reserved_item(action, change):
    execute(fixture(action) + r'''
        _patient setVariable ["fixtureStock",[_item]];call _start;
    ''' + change + r'''
        call _beginRequest;call _ack;call _ack;
        [count _debits==1 && {count _refunds==1},"changed catheter lost or duplicated its accessory reservation"] call _check;
        [(_refunds select 0) isEqualTo [_patient,_item],"changed catheter refunded a different item or donor"] call _check;
        [(_patient getVariable "fixtureStock") isEqualTo [_item],"rejected accessory did not return to its original stock"] call _check;
        [(call _getRow select 16) isEqualTo [],"replaced or unavailable access accepted an old accessory request"] call _check;
    ''')


@pytest.mark.parametrize("action", ACCESSORIES)
def test_lost_owner_result_never_speculatively_duplicates_the_reserved_accessory(action):
    execute(fixture(action) + r'''
        _medic setVariable ["fixtureStock",[_item]];call _start;
        private _pending=+(_medic getVariable "ACME_IV_FinishPending");
        call _beginRequest;
        _serverTime=133;
        [_medic,_pending select 1] call ACME_fnc_ivFinishRetry;
        [_medic,_pending select 1] call ACME_fnc_ivFinishRetry;
        [count _debits==1 && {count _refunds==0},"unknown owner result recreated a potentially used accessory"] call _check;
        [count (missionNamespace getVariable "ACME_supplyReceipts")==0
            && {(_medic getVariable "ACME_IV_FinishPending") isEqualTo []},"unknown result retained a reusable debit or UI lock"] call _check;
    ''')


@pytest.mark.parametrize("legacy", [False, True])
def test_removing_and_reinstalling_a_line_on_the_same_hub_retires_the_old_slot_identity(legacy):
    slot = "ACME_fnc_ivLineSlot={" + source("ivLineSlot") + "};"
    initial = r'''
        _medic setVariable ["fixtureStock",[_item]];
        call _start;call _beginRequest;call _ack;
        _serverTime=102;call _finishRequest;call _ack;
    ''' if not legacy else r'''
        (_row select 15) set [3,true];
        _patient setVariable ["ACME_IV_Marks",[_row]];
    '''
    execute(fixture("line") + slot + r'''
        // These are native access/topology boundaries; slot resolution and
        // its physical installation identity check execute production SQF.
        ACME_fnc_transfusionAccessValid={true};
        ACME_fnc_isYLineAccess={false};
        ACM_circulation_fnc_getAccessType={16};
        ACME_infusion_bodyParts=["leftarm","rightarm","leftleg","rightleg","head"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMap];
    ''' + initial + r'''
        private _oldSlot=[_patient,"leftarm",true,1] call ACME_fnc_ivLineSlot;
        [count _oldSlot==2,"installed line did not expose its empty attachment slot"] call _check;
        private _oldUID=_oldSlot select 0;
        private _hubUID=(call _getRow) select 14;
        ["begin","removeLine","pull"] call _invoke;
        _serverTime=_serverTime+1;
        ["finish","removeLine","pull"] call _invoke;
        [([_patient,"leftarm",true,1,_oldUID] call ACME_fnc_ivLineSlot) isEqualTo [],
            "removed line retained an attachment slot"] call _check;
        [((call _getRow) param [17,""])=="","removed line retained its installed tubing identity"] call _check;
        _row=+(call _getRow);
        _medic setVariable ["fixtureStock",[_item]];
        _events=[];
        call _start;call _beginRequest;call _ack;
        _serverTime=_serverTime+2;call _finishRequest;call _ack;
        private _newSlot=[_patient,"leftarm",true,1] call ACME_fnc_ivLineSlot;
        [(call _getRow select 14)==_hubUID,"line replacement unnecessarily changed the venous catheter"] call _check;
        [count _newSlot==2 && {(_newSlot select 0)!=_oldUID},"replacement reused the old administration-line identity"] call _check;
        [([_patient,"leftarm",true,1,_oldUID] call ACME_fnc_ivLineSlot) isEqualTo [],
            "a delayed old-line attach request followed its hub onto replacement tubing"] call _check;
        [([_patient,"leftarm",true,1,_newSlot select 0] call ACME_fnc_ivLineSlot) isEqualTo _newSlot,
            "the current administration line lost its valid empty slot"] call _check;
    ''')


@pytest.mark.parametrize("item", [value[0] for value in ACCESSORIES.values()])
def test_accessory_is_a_real_registered_medical_inventory_item_with_light_positive_mass(item):
    config_path = ROOT / "addons/acm_extended/config.cpp"
    config = config_path.read_text().replace('#include "vent_battery_items.hpp"',
        (config_path.parent / "vent_battery_items.hpp").read_text())
    entry = subtree(config, "CfgWeapons")["classes"][item]
    assert entry["props"]["scope"] == 2
    assert entry["props"]["ACE_isMedicalItem"] == 1
    assert entry["classes"]["ItemInfo"]["props"]["mass"] == 0.1
    assert item in subtree(config, "CfgPatches")["classes"]["ACM_Extended"]["props"]["weapons"]
    picture = entry["props"]["picture"].lstrip("\\").replace("\\", "/")
    assert (ROOT / "addons" / picture).is_file()


def test_owner_line_generation_survives_provider_serial_reset_and_expired_receipts():
    slot = "ACME_fnc_ivLineSlot={" + source("ivLineSlot") + "};"
    execute(fixture("line") + slot + r'''
        ACME_fnc_transfusionAccessValid={true};
        ACME_fnc_isYLineAccess={false};
        ACM_circulation_fnc_getAccessType={16};
        ACME_infusion_bodyParts=["leftarm","rightarm","leftleg","rightleg","head"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMap];
        _medic setVariable ["fixtureStock",[_item]];
        call _start;call _beginRequest;call _ack;
        private _firstToken=_lastOwnerRequest select 5;
        _serverTime=102;call _finishRequest;call _ack;
        private _oldUID=([_patient,"leftarm",true,1] call ACME_fnc_ivLineSlot) select 0;
        private _hub=(call _getRow) select 14;
        ["begin","removeLine","pull"] call _invoke;
        _serverTime=103;["finish","removeLine","pull"] call _invoke;
        // A later provider ownership period can reuse its serial and native
        // client ID after the old request history expires. The patient owner
        // must retain installation generation independently of that provider.
        _serverTime=200;
        _medic setVariable ["ACME_IV_FinishSerial",0];
        missionNamespace setVariable ["ACME_supplyReceiptSerial",0];
        missionNamespace setVariable ["ACME_supplyReceipts",createHashMap];
        missionNamespace setVariable ["ACME_IV_SupplyScopes",createHashMap];
        _row=+(call _getRow);
        _medic setVariable ["fixtureStock",[_item]];
        _events=[];
        call _start;call _beginRequest;call _ack;
        [(_lastOwnerRequest select 5)==_firstToken,"fixture did not reuse the actual provider job token"] call _check;
        _serverTime=202;call _finishRequest;call _ack;
        private _current=[_patient,"leftarm",true,1] call ACME_fnc_ivLineSlot;
        [(call _getRow select 14)==_hub,"reused provider identity changed the catheter hub"] call _check;
        [count _current==2 && {(_current select 0)!=_oldUID},
            "reused provider token revived the older administration-line identity"] call _check;
        [([_patient,"leftarm",true,1,_oldUID] call ACME_fnc_ivLineSlot) isEqualTo [],
            "expired old-line request can attach to replacement tubing after token reuse"] call _check;
        [((call _getRow) param [18,0])==2,"patient owner did not retain and advance its per-hub line generation"] call _check;
    ''')


@pytest.mark.parametrize("counter", ["-1", "0.5", "16777215", '"bad"'])
def test_invalid_or_exhausted_owner_line_generation_cannot_be_reset_to_reuse_old_ids(counter):
    execute(fixture("line") + f'''
        _row set [17,"retired-line"];_row set [18,{counter}];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        _medic setVariable ["fixtureStock",[_item]];
        call _start;call _beginRequest;
        [!((call _lastReply) select 4),"invalid generation was admitted for a new line"] call _check;
        call _ack;
        [count _refunds==1 && {{(_medic getVariable "fixtureStock") isEqualTo [_item]}},
            "generation rejection lost the physical line reservation"] call _check;
        [((call _getRow) select 18) isEqualTo {counter},"bad generation was silently reset"] call _check;
        [!((call _getState) select 3) && {{(call _getRow select 16) isEqualTo []}},
            "invalid generation installed an unidentifiable line"] call _check;
    ''')


@pytest.mark.parametrize("actor", ["_patient", "_medic"])
@pytest.mark.parametrize("moment", ["before_begin", "before_finish"])
def test_checkpoint_freeze_rejects_in_transit_begin_and_interrupts_opened_line_completion(actor, moment):
    freeze = f'{actor} setVariable ["ACME_persistenceFrozen",true];'
    body = r'''
        _medic setVariable ["fixtureStock",[_item]];
        private _beforeState=str (call _getState);
        call _start;
        [count _debits==1,"fixture did not reserve a real administration line before freeze"] call _check;
    '''
    if moment == "before_begin":
        body += freeze + r'''
            call _beginRequest;
            [!((call _lastReply) select 4),"checkpoint freeze admitted a new owner job"] call _check;
            call _ack;call _ack;
            [count _refunds==1 && {(_medic getVariable "fixtureStock") isEqualTo [_item]},
                "frozen BEGIN did not refund its original unopened line exactly once"] call _check;
        '''
    else:
        body += r'''
            call _beginRequest;call _ack;
            [(_medic getVariable "fixtureStock") isEqualTo [],"accepted BEGIN did not consume its opened line"] call _check;
        ''' + freeze + r'''
            _serverTime=102;call _finishRequest;call _ack;
            [count _refunds==0 && {(_medic getVariable "fixtureStock") isEqualTo []},
                "interrupted opened line was incorrectly recreated"] call _check;
        '''
    execute(fixture("line") + body + r'''
        [str (call _getState)==_beforeState,"checkpoint freeze allowed an IV hardware mutation"] call _check;
        [(call _getRow select 16) isEqualTo [],"checkpoint freeze retained an executable job"] call _check;
        [((call _getRow) param [17,""])=="" && {((call _getRow) param [18,0])==0},
            "checkpoint freeze assigned or advanced a physical line identity"] call _check;
    ''')
