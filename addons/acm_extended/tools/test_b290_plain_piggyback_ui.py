"""Execute card dispatch and a loose plain-fluid secondary through owner ACK.

Native controls/config/inventory receipts are explicit engine boundaries. The
production selection, funded preparation, delayed admission and physical owner
attachment run; these tests do not certify native Arma rendering or transport.
"""
import pytest

from test_b156_procedure_supplies import primitives
from test_b274_transfusion_preparation import stage_setup
from test_b280_transfusion_native_input import input_setup
from test_b275_piggyback import helpers
from test_b289_piggyback_fluids import request_chain_setup, used_stage_setup
from test_menu_death_lifecycle import adapt, execute, read


def card_source(name):
    source = read(name).replace("findDisplay 86000", "_display")
    source = source.replace("_display displayCtrl 86145", "_setList")
    source = source.replace("lbCurSel _list", "_setRow")
    source = source.replace("lbCurSel _setList", "_setRow")
    source = source.replace("_list lbData _row", "(_setRows select _row)")
    source = source.replace("_setList lbData _row", "(_setRows select _row)")
    source = source.replace("ctrlShown _list", "_nativeListVisible")
    return "ACME_fnc_" + name + "={" + primitives(adapt(source)) + "};"


def card_setup():
    return request_chain_setup() + r'''
        private _display=missionNamespace;private _setList=uiNamespace;
        private _setRow=0;private _setRows=["set1"];
        // Card surfaces hide backing lists while retaining their selections.
        private _nativeListVisible=false;
        uiNamespace setVariable ["ACME_preparedListMode",true];
        private _staleInfusion=["stale-infusion"];
        ACME_fnc_getSelectedPreparedInfusion={[-1,_staleInfusion]};
    ''' + card_source("piggybackWorkflow") + card_source("hangPreparedSet") + card_source("givePreparedBag")


@pytest.mark.parametrize("invocation", [
    '["add"] call ACME_fnc_piggybackWorkflow',
    '[] call ACME_fnc_hangPreparedSet',
    '[uiNamespace] call ACME_fnc_hangPreparedSet',
    '["set1"] call ACME_fnc_hangPreparedSet',
])
def test_hidden_plain_saline_card_dispatches_its_exact_set_instead_of_a_stale_infusion(invocation):
    execute(card_setup() + invocation + r''';
        [call _ack select 3,"hidden plain saline card was ignored"] call _check;
        [count (call _stock)==3 && {_factoryCalls==1},"plain selected set never reached physical owner attachment"] call _check;
        [(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo []
            && {call _entries isEqualTo [_oldMed]},"plain fluid required or created medication"] call _check;
        (call _ack) call ACME_fnc_piggybackAttachAck;
        [count _inventorySettlements==1 && {(_inventorySettlements select 0 select 2)},"plain set custody did not settle"] call _check;
    ''')


def test_give_infusion_cannot_accidentally_attach_the_hidden_plain_set_selection():
    execute(card_setup() + r'''
        uiNamespace setVariable ["ACME_preparedListMode",true];
        [] call ACME_fnc_givePreparedBag;
        [_factoryCalls==0 && {(_medic getVariable "ACME_preparedIVSets") isEqualTo [_set]},
            "Give Infusion reused the independently selected hidden plain set"] call _check;
    ''')


@pytest.mark.parametrize("line", [False, True])
def test_plain_saline_card_offers_connect_piggyback_only_with_a_real_branch_line(line):
    execute(input_setup() + helpers() + r'''
        _map set ["leftarm",[_primary,_neighbor]];
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        private _targetBodyPart="leftarm";private _flIV=true;private _flSite=0;
        _selectingPiggyback=true;_selectedAccessValid=true;
        uiNamespace setVariable ["ACME_preparedListMode",false];
        _selection=0;_rowData=["ACM_SalineBag_500|SalineIV_500"];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
    ''' + f'_medic setVariable ["fixtureStock",{("[\"ACM_SalineBag_500\",\"ACME_IVLine\"]" if line else "[\"ACM_SalineBag_500\"]")}];' + r'''
        call ACME_fnc_updateTransfusionControls;
        [_spikeText=="Connect Piggyback","plain fluid still offered the medication preparation path"] call _check;
    ''' + f'[_spikeEnabled isEqualTo {str(line).lower()},"secondary action ignored real branch-line stock"] call _check;')


def fresh_setup():
    # Retain production loose-bag preparation and the real request/owner/ACK
    # chain. Native config, UI and exact physical carrier receipts are fixtures.
    source = stage_setup().replace(
        'getText(configFile >> "ace_medical_treatment" >> "IV" >> _action >> "type")',
        '([_action] call _fluidType)')
    return source + request_chain_setup() + r'''
        _configuredVolume=500;_configuredType="Saline";
        _medic setVariable ["ACME_preparedIVSets",[]];
        _medic setVariable ["ACME_infusion_PreparedBags",[]];
        _medic setVariable ["fixtureStock",["ACM_SalineBag_500","ACME_IVLine"]];
        _rowData=["ACM_SalineBag_500|SalineIV_500"];
        ace_common_fnc_addToInventory={params ["_u","_item"];
            private _stock=+(_u getVariable ["fixtureStock",[]]);_stock pushBack _item;_u setVariable ["fixtureStock",_stock];_refunds pushBack [_u,_item];
        };
        private _nativeReady=false;
        ACME_fnc_inventoryLedgerPossessed={params ["_m","_kind","_sid"];
            _nativeReady && {_kind=="prepared"} && {((_m getVariable ["ACME_preparedIVSets",[]]) findIf {(_x select 0)==_sid})>=0}
        };
        // Preparation refreshes use the provider UI without rebuilding fixtures.
        ACME_fnc_togglePreparedSets={uiNamespace setVariable ["ACME_preparedListMode",_this select 0];};
        private _prepare={
            [] call ACME_fnc_transfusionSpikeOrAdd;
            private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
        };
        private _poll={private _job=_waits select 0;
            if ((_job select 1) call (_job select 2)) then {(_job select 1) call (_job select 0);};
        };
    '''


def test_loose_saline_onto_saline_uses_one_branch_line_then_autoattaches_without_medication():
    execute(fresh_setup() + r'''
        call _prepare;
        private _set=(_medic getVariable "ACME_preparedIVSets") select 0;
        [(_set select 8)=="saline" && {(_set select 2)=="SalineIV_500"},"ordinary fluid was converted into a medication infusion"] call _check;
        [(_medic getVariable "fixtureStock") isEqualTo [] && {count _debits==1},"plain secondary did not use exactly its bag and one branch line"] call _check;
        [count _waits==1 && {_factoryCalls==0},"secondary was attached before prepared carrier custody"] call _check;
        call _poll;
        [_factoryCalls==0 && {count (_medic getVariable "ACME_piggybackEscrow")==0},"unregistered carrier was reserved"] call _check;
        _nativeReady=true;call _poll;
        [call _ack select 3,"plain saline secondary failed after native receipt"] call _check;
        private _bags=call _stock;private _secondary=_bags select 2;
        [count _bags==3 && {(_secondary select 0)=="Saline"} && {(_secondary select 1)==500},"wrong plain fluid or volume attached"] call _check;
        [call _entries isEqualTo [_oldMed] && {ACME_infusion_activePatients isEqualTo []},"plain secondary created a medication effect/worker"] call _check;
        [([_patient,"leftarm",true,0,"primary"] call ACME_fnc_piggybackFlow) isEqualTo [true,false],"secondary did not hold the original primary"] call _check;
        (call _ack) call ACME_fnc_piggybackAttachAck;
        [count _inventorySettlements==1 && {_factoryCalls==1},"owner acknowledgement duplicated the source or bag"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    'missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",missionNamespace];',
    'missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",1];',
    'missionNamespace setVariable ["ACME_piggybackPending",[]];',
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_primary set [8,"replacement-primary"];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
    '_patient setVariable ["ACME_persistenceFrozen",true];',
])
def test_delayed_plain_secondary_stays_carried_when_workflow_or_provider_period_changes(change):
    execute(fresh_setup() + r'''
        call _prepare;private _carried=+(_medic getVariable "ACME_preparedIVSets");
    ''' + change + r'''
        _nativeReady=true;call _poll;
        [_factoryCalls==0 && {(_medic getVariable "ACME_preparedIVSets") isEqualTo _carried}
            && {count (_medic getVariable "ACME_piggybackEscrow")==0},"delayed plain bag redirected or lost custody"] call _check;
    ''')


def test_failed_plain_preparation_returns_both_real_sources_and_does_not_schedule_an_attachment():
    execute(fresh_setup() + r'''
        ACME_fnc_preparedInventoryCommit={false};
        call _prepare;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [] && {count _waits==0}
            && {_factoryCalls==0},"failed carrier commit created or scheduled a secondary"] call _check;
        [([_medic,"ACM_SalineBag_500"] call ace_common_fnc_getCountOfItem)==1
            && {([_medic,"ACME_IVLine"] call ace_common_fnc_getCountOfItem)==1},"failed commit lost fluid or real line"] call _check;
        [count (missionNamespace getVariable ["ACME_supplyReceipts",createHashMap])==0,"failed preparation leaked source receipts"] call _check;
    ''')


@pytest.mark.parametrize("key", ["ACME_equipmentKitEpoch", "ACME_providerLocalityEpoch"])
def test_provider_period_change_during_spiking_cannot_consume_the_new_periods_stock(key):
    execute(fresh_setup() + r'''
        [] call ACME_fnc_transfusionSpikeOrAdd;
    ''' + f'_medic setVariable ["{key}",1];' + r'''
        private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
        [(_medic getVariable "fixtureStock") isEqualTo ["ACM_SalineBag_500","ACME_IVLine"]
            && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []}
            && {_debits isEqualTo []} && {count _waits==0},"old spike consumed a replacement provider periods equipment"] call _check;
    ''')


def test_old_spike_callback_cannot_clear_a_new_preparation_session_or_debit_its_sources():
    execute(fresh_setup() + r'''
        [] call ACME_fnc_transfusionSpikeOrAdd;
        private _replacement=["ACM_SalineBag_500",999,"new-spike-session"];
        missionNamespace setVariable ["ACME_spikingActive",_replacement];
        private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
        [(missionNamespace getVariable "ACME_spikingActive") isEqualTo _replacement
            && {_debits isEqualTo []} && {(_medic getVariable "fixtureStock") isEqualTo ["ACM_SalineBag_500","ACME_IVLine"]},
            "stale preparation callback cleared or consumed the newer session"] call _check;
    ''')


def test_cancel_then_restart_at_the_same_access_cannot_inherit_an_old_autoattach():
    execute(fresh_setup() + card_source("piggybackWorkflow") + r'''
        call _prepare;private _carried=+(_medic getVariable "ACME_preparedIVSets");
        private _oldIntent=+(missionNamespace getVariable "ACME_piggybackPending");
        ["cancel"] call ACME_fnc_piggybackWorkflow;
        ["start"] call ACME_fnc_piggybackWorkflow;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo _oldIntent,"fixture did not restart the same patient/line tuple"] call _check;
        _nativeReady=true;call _poll;
        [_factoryCalls==0 && {(_medic getVariable "ACME_preparedIVSets") isEqualTo _carried},"old secondary attached into a later identical workflow"] call _check;
    ''')


def test_used_secondary_also_requires_its_original_workflow_generation():
    execute(used_stage_setup() + r'''
        private _display=missionNamespace;
        ACME_fnc_togglePreparedSets={};ACME_fnc_transfusionFilterInventory={};
    ''' + card_source("piggybackWorkflow") + r'''
        [["used1"] call ACME_fnc_piggybackStageUsed,"fixture could not stage used secondary"] call _check;
        private _carried=+(_medic getVariable "ACME_preparedIVSets");
        private _oldIntent=+(missionNamespace getVariable "ACME_piggybackPending");
        ["cancel"] call ACME_fnc_piggybackWorkflow;
        ["start"] call ACME_fnc_piggybackWorkflow;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo _oldIntent,"fixture did not restart same access"] call _check;
        _nativeReady=true;call _pollStage;
        [_factoryCalls==0 && {(_medic getVariable "ACME_preparedIVSets") isEqualTo _carried},"old used secondary attached into later identical workflow"] call _check;
    ''')


def test_old_owner_ack_settles_exact_custody_without_cancelling_a_restarted_identical_workflow():
    execute(card_setup() + r'''
        _returnMode="wrong-type";
        ACME_fnc_togglePreparedSets={};ACME_fnc_transfusionFilterInventory={};
        ["set1"] call ACME_fnc_piggybackAttachRequest;
        private _acknowledgement=call _ack;
        // A rejected receipt can arrive after a new choice at the same primary.
        private _intent=+(missionNamespace getVariable "ACME_piggybackPending");
        ["cancel"] call ACME_fnc_piggybackWorkflow;
        ["start"] call ACME_fnc_piggybackWorkflow;
        _acknowledgement call ACME_fnc_piggybackAttachAck;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo _intent
            && {(missionNamespace getVariable "ACME_piggybackWorkflowGeneration")==2},"old acknowledgement cancelled a newer same-line workflow"] call _check;
        [count _inventorySettlements==1 && {!(_inventorySettlements select 0 select 2)}
            && {count (_medic getVariable "ACME_piggybackEscrow")==0},"old receipt did not settle its exact bag custody"] call _check;
    ''')
