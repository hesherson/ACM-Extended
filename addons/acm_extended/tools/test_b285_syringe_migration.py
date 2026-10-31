"""Execute syringe delivery across independent old/new-owner and server views.

Production journal, inventory claim, return and patient receipt decisions run.
The fixture keeps three namespace stores and separately cloned provider object
projections; neither an event nor a public write implicitly replicates state.
Native cargo, locality, clocks, CBA transport and UI remain engine boundaries.
This does not certify native Arma replication or dedicated-server acceptance.
"""
import re

import pytest

from b282_locality_fixture import vm_primitives
from test_b279_inventory_ledger import FUNCTIONS, adapted as inventory_adapter
from test_historical_medication_rows import iteration_scopes
from test_menu_death_lifecycle import F, execute


def source(name):
    return (F / f"fn_{name}.sqf").read_text()


def adapted(text, *, deletion_fixture=False):
    # Substitute dynamic engine boundaries before the historical generic adapter
    # can turn locality, server identity or client identity into constants.
    for old, new in {
        "missionNamespace": "_machineSpace",
        "isServer": "_onServer",
        "hasInterface": "_hasInterface",
        "clientOwner": "_machineOwner",
        "serverTime": "_serverTime",
        "findDisplay 84000": "objNull",
        "local _owner": "_providerLocal",
        "local _medic": "_providerLocal",
        "local _patient": "_patientLocal",
        "local ACE_player": "_providerLocal",
        "owner _owner": "_providerOwner",
        "owner _medic": "_providerOwner",
        "owner _patient": "_patientOwner",
        "alive _owner": "_alive",
        "objectParent _owner": "objNull",
        "netId _medic": '"provider"',
    }.items():
        text = re.sub(r"(?<!\w)" + re.escape(old) + r"\b", lambda _: new, text)
    # Arma retains omitted typed strings; this VM can instead produce nil.
    text = re.sub(r'(\["_\w+",""),\[""\](\])', r"\1\2", text)
    text = text.replace('values (_j get "batches")', '((_j get "batches") call _values)')
    text = text.replace('isNull (_data select 2)', '((_data select 2) isEqualTo objNull)')
    text = text.replace('owner (_args select 0)', '_patientOwner')
    if deletion_fixture:
        # Historical fixtures also reuse this adapter. The explicit deletion
        # boundary and its counters belong only to this multi-machine fixture.
        text = text.replace('isNull _patient', '(_patientDeleted || {_patient isEqualTo objNull})')
        text = text.replace('_patient getVariable ["ACME_medicationReceiptsB14",createHashMap]',
                            '([_patient,createHashMap] call _readPatientReceipts)')
        text = re.sub(r'_patient setVariable \["ACME_medicationReceiptsB14",\s*_receipts,\s*(true|false)\];',
                      '[_patient,_receipts] call _writePatientReceipts;', text)
    text = text.replace('getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _source >> "concentration")',
                        '([_source,"concentration"] call _configNumber)')
    text = vm_primitives(text).replace("call _localityMapDefault", "call _mapDefault")
    text = text.replace("call _localityFinite", "call _finite")
    return inventory_adapter(iteration_scopes(text))


def function(name):
    return f"ACME_fnc_{name}={{" + adapted(source(name), deletion_fixture=True) + "};\n"


def setup():
    names = list(FUNCTIONS) + [
        "syringeDeliveryDelta", "syringeDeliveryClaim", "syringeDeliveryCopy",
        "syringeDeliveryBroker", "syringeDeliveryTick", "syringeDeliveryServerTick",
        "syringeDeliveryDoseValid", "syringeDeliveryRequest", "syringeDeliveryRecover",
        "syringeDeliveryReply", "narcStoreCommit", "medicationLineLocal",
        "hardcorePushRetire",
        "skInventoryInjectClaim",
        "syringeDeliveryMachine", "syringeDeliveryPatientQuery",
    ]
    return r'''
    private _serverSpace=missionNamespace;
    private _oldSpace=profileNamespace;
    private _newSpace=parsingNamespace;
    private _machineSpace=_oldSpace;
    private _machineName="";
    private _machineOwner=7;
    private _providerOwner=7;
    private _patientOwner=9;
    private _providerLocal=true;
    private _patientLocal=false;
    private _onServer=false;
    private _hasInterface=true;
    private _serverTime=10;
    private _holder=missionNamespace;
    private _serverEvents=[];
    private _targetEvents=[];
    private _patientEvents=[];
    private _ownerEvents=[];
    private _patientDeleted=false;
    private _deletedReceiptReads=0;
    private _deletedReceiptWrites=0;
    private _readPatientReceipts={params ["_object","_default"];
        if (_patientDeleted) then {_deletedReceiptReads=_deletedReceiptReads+1;};
        _object getVariable ["ACME_medicationReceiptsB14",_default]};
    private _writePatientReceipts={params ["_object","_receipts"];
        if (_patientDeleted) then {_deletedReceiptWrites=_deletedReceiptWrites+1;};
        _object setVariable ["ACME_medicationReceiptsB14",_receipts];};
    private _deliveredMg=0;
    private _mapDefault={params ["_map","_args"]; _args params ["_key","_default"];
        if (_key in _map) then {_map get _key} else {_default}};
    private _values={private _map=_this; (keys _map) apply {_map get _x}};
    private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    private _copy={
        params ["_value"];
        if (_value isEqualType []) exitWith {_value apply {[_x] call _copy}};
        if (_value isEqualType createHashMap) exitWith {
            private _map=_value;
            createHashMapFromArray ((keys _map) apply {[_x,[_map get _x] call _copy]})
        };
        _value
    };
    private _providerFields=[
        ["native",[]],["ACME_narcStore",[]],["ACME_inventoryEscrow",createHashMap],
        ["ACME_inventoryPending",createHashMap],["ACME_inventoryRequests",createHashMap],
        ["ACME_inventoryPayloadCache",createHashMap],["ACME_inventoryMutations",createHashMap],
        ["ACME_inventoryAdoptions",createHashMap],["ACME_inventoryIncoming",createHashMap],
        ["ACME_inventoryPlacement",createHashMap],["ACME_syringeInventoryHidden",[]],
        ["ACME_medicationEscrow",createHashMap],["ACME_medicationAckSettling",createHashMap],
        ["ACME_syringeDeliverySessions",createHashMap],["ACME_syringeDeliveryRecoveryPeriod",[]],
        ["ACME_equipmentKitEpoch",0],["ACME_providerLocalityEpoch",0],
        ["ACME_preparedIVSets",[]],["ACME_infusion_PreparedBags",[]]
    ];
    private _worlds=createHashMap;
    {
        private _world=createHashMap;
        {_world set [_x select 0,[_x select 1] call _copy];} forEach _providerFields;
        _worlds set [_x,_world];
    } forEach ["old","new","server","patientA","patientB"];
    private _decisionWorlds=createHashMap;
    private _patientWorlds=createHashMap;
    private _machineNonces=createHashMapFromArray [["old","machine7"],["new","machine8"],["server","machine2"],["patientA","machine9"],["patientB","machine10"]];
    private _patientFields=[["ACME_medicationReceiptsB14",createHashMap],["ACME_pendingFlush",[]]];
    {
        _decisionWorlds set [_x,createHashMap];
        private _world=createHashMap;
        {_world set [_x select 0,[_x select 1] call _copy];} forEach _patientFields;
        _patientWorlds set [_x,_world];
    } forEach ["old","new","server","patientA","patientB"];
    private _saveProvider={
        if (_machineName!="") then {
            private _world=_worlds get _machineName;
            {_world set [_x select 0,[_medic getVariable [_x select 0,_x select 1]] call _copy];} forEach _providerFields;
            _decisionWorlds set [_machineName,[_machineSpace getVariable ["ACME_syringeDeliveryPatientDecisions",createHashMap]] call _copy];
            _machineNonces set [_machineName,_machineSpace getVariable ["ACME_syringeDeliveryMachineNonce",""]];
            private _patientWorld=_patientWorlds get _machineName;
            {_patientWorld set [_x select 0,[_patient getVariable [_x select 0,_x select 1]] call _copy];} forEach _patientFields;
        };
    };
    private _switch={
        params ["_next"];
        call _saveProvider;
        _machineName=_next;
        _machineSpace=switch (_next) do {case "server":{_serverSpace};case "new":{_newSpace};case "patientB":{_newSpace};default{_oldSpace}};
        _machineOwner=switch (_next) do {case "server":{2};case "new":{8};case "patientA":{9};case "patientB":{10};default{7}};
        _onServer=_next=="server";
        _hasInterface=!_onServer;
        _providerLocal=_machineOwner==_providerOwner;
        _patientLocal=_machineOwner==_patientOwner;
        private _world=_worlds get _next;
        {_medic setVariable [_x select 0,[_world get (_x select 0)] call _copy];} forEach _providerFields;
        _machineSpace setVariable ["ACME_syringeDeliveryMachineNonce",_machineNonces get _next];
        _machineSpace setVariable ["ACME_syringeDeliveryPatientDecisions",[_decisionWorlds get _next] call _copy];
        private _patientWorld=_patientWorlds get _next;
        {_patient setVariable [_x select 0,[_patientWorld get (_x select 0)] call _copy];} forEach _patientFields;
    };
    private _replicateProvider={
        params ["_from","_to",["_fields",[]]];
        call _saveProvider;
        private _fromWorld=_worlds get _from;
        private _toWorld=_worlds get _to;
        if (_fields isEqualTo []) then {_fields=_providerFields apply {_x select 0};};
        {_toWorld set [_x,[_fromWorld get _x] call _copy];} forEach _fields;
        if (_machineName==_to) then {
            {_medic setVariable [_x select 0,[_toWorld get (_x select 0)] call _copy];} forEach _providerFields;
        };
    };
    private _replicateToken={
        params ["_to","_token"];
        private _space=if (_to=="old") then {_oldSpace} else {_newSpace};
        private _key=format ["ACME_inventoryToken_%1",_token];
        _space setVariable [_key,[_serverSpace getVariable [_key,[]]] call _copy];
        _space setVariable ["ACME_inventoryLedgerIndex",[_serverSpace getVariable ["ACME_inventoryLedgerIndex",createHashMap]] call _copy];
    };
    CBA_fnc_serverEvent={_serverEvents pushBack [_this select 0,[_this select 1] call _copy,_machineOwner];};
    CBA_fnc_targetEvent={_targetEvents pushBack [_this select 0,[_this select 1] call _copy,_this select 2];};
    CBA_fnc_ownerEvent={_ownerEvents pushBack [_this select 0,[_this select 1] call _copy,_this select 2];};
    CBA_fnc_waitAndExecute={_waits pushBack _this;};
    ACME_fnc_ownerDispatch={_patientEvents pushBack ([_this] call _copy);};
    ACME_fnc_ownerRegister={};
    ACME_fnc_clinicalEpoch={0};
    ACME_fnc_medicationLineIdentity={[0,1,1]};
    ACME_fnc_medicationRouteAllowed={true};
    ACME_fnc_medicationLineBloodBusy={false};
    ACME_fnc_medicationLineFraction={1};
    ACME_fnc_medicationLeak={};
    ACME_fnc_ioPainResponse={};
    ACME_fnc_hardcorePushOverlay={};
    ace_medical_treatment_fnc_medicationLocal={_deliveredMg=_deliveredMg+(_this select 3);};
    ace_medical_treatment_fnc_addToTriageCard={};
    private _configNumber={params ["_source","_field"]; if (_source=="Ketamine") then {50} else {0}};
    ACME_fnc_inventoryLedgerNative={params ["_owner",["_kind",""]];
        (_owner getVariable ["native",[]]) select {_kind=="" || {(_x select 1)==_kind}}};
    private _addNative={params ["_owner","_class","_token"];
        private _native=+(_owner getVariable ["native",[]]);
        _native pushBack [_token,["prepared","syringe"] select ((_class find "ACME_PreparedSyringe")==0)];
        _owner setVariable ["native",_native];};
    ace_common_fnc_removeSpecificMagazine={params ["_owner","_class","_token"];
        private _native=+(_owner getVariable ["native",[]]);
        private _at=_native findIf {(_x select 0)==_token};
        if (_at<0) exitWith {false};
        _native deleteAt _at; _owner setVariable ["native",_native]; true};
    ACME_fnc_skInventoryReconcile={};
    ["old"] call _switch;
    ''' + "".join(function(name) for name in names) + r'''
    ["server"] call _switch;
    {[_x,format ["machine%1",_x]] call ACME_fnc_syringeDeliveryMachine;} forEach [2,7,8,9,10];
    ["old"] call _switch;
    private _drainServer={
        ["server"] call _switch;
        while {count _serverEvents>0} do {
            private _event=_serverEvents deleteAt 0;
            if ((_event select 0)=="ACME_inventoryBroker") then {(_event select 1) call ACME_fnc_inventoryLedgerBroker;};
            if ((_event select 0)=="ACME_syringeDelivery") then {(_event select 1) call ACME_fnc_syringeDeliveryBroker;};
        };
    };
    private _deliverInventoryReplies={
        params ["_to"];
        [_to] call _switch;
        private _keep=[];
        {
            if ((_x select 0)=="ACME_inventoryReply") then {(_x select 1) call ACME_fnc_inventoryLedgerReply;}
            else {_keep pushBack _x;};
        } forEach _targetEvents;
        _targetEvents=_keep;
    };
    private _deliverDeliveryReplies={
        params ["_to"];
        [_to] call _switch;
        private _pending=+_targetEvents; _targetEvents=[];
        {
            if ((_x select 0)=="ACME_syringeDeliveryReply") then {(_x select 1) call ACME_fnc_syringeDeliveryReply;}
            else {_targetEvents pushBack _x;};
        } forEach _pending;
    };
    private _sid="migration-syringe";
    private _request="migration-claim";
    private _session="migration-session";
    private _row=["Ketamine",3,2,"label",0,[["Ketamine",2]],"compoundB13","none","","","",_sid,"","inventoryB279"];
    private _token=0;
    private _fund={
        ["old"] call _switch;
        _medic setVariable ["ACME_narcStore",[[_row] call _copy]];
        [_medic,"syringe",[[_sid,_row]]] call ACME_fnc_inventoryLedgerCommit;
        ["old","server"] call _replicateProvider;
        call _drainServer;
        _token=(_serverSpace getVariable "ACME_inventoryLedgerIndex") get ("syringe:"+_sid);
        ["old",_token] call _replicateToken;
        ["old"] call _deliverInventoryReplies;
        [(_medic getVariable "native") isEqualTo [[_token,"syringe"]],"funding did not materialize one exact native syringe"] call _check;
    };
    private _claim={
        call _fund;
        [_medic,"syringe",_sid,_request] call ACME_fnc_inventoryLedgerReserve;
        private _escrow=_medic getVariable "ACME_inventoryEscrow";
        private _held=+(_escrow get _request);
        _held set [6,["syringeDeliveryB285",_machineOwner]];
        _escrow set [_request,_held]; _medic setVariable ["ACME_inventoryEscrow",_escrow];
        [_medic,_request,{},[],true] call ACME_fnc_inventoryLedgerClaim;
        ["old","server"] call _replicateProvider;
        call _drainServer;
    };
    private _send={
        params ["_mode",["_data",[]],["_from",7]];
        ["server"] call _switch;
        [_mode,_medic,_request,_from,_data] call ACME_fnc_syringeDeliveryBroker;
    };
    private _begin={
        ["begin",[_session,"push",_patient,"leftarm",0,[0,1,1],0]] call _send;
    };
    private _delta=[0.25,0,[[0,"Ketamine",0.25]]];
    private _wire={
        params ["_id",["_volume",0.25]];
        private _slice=[_volume,0,[[0,"Ketamine",_volume]]];
        private _meta=["hcPush",_session,_sid,_slice];
        [_patient,_medic,0,_id,"administer","leftarm",[["Ketamine_IV",50*_volume,true,"label",1,true,["hcPush",3,_session,750]]],0,[0,1,1],_meta]
    };
    private _batch={
        params ["_id",["_volume",0.25]];
        private _args=[_id,_volume] call _wire;
        ["batch",[_session,_id,_args,[_volume,0,[[0,"Ketamine",_volume]]]]] call _send;
        _args
    };
    private _receipt={
        params ["_id","_accepted",["_reason","terminal"]];
        ["receipt",[_session,_id,_id,_patient,_accepted,_reason],_patientOwner] call _send;
    };
    private _record={_serverSpace getVariable [format ["ACME_inventoryToken_%1",_token],[]]};
    private _journal={(_serverSpace getVariable ["ACME_syringeDeliveries",createHashMap]) get _request};
    private _remaining={((call _journal) get "row") select 2};
    '''


def test_fixture_keeps_server_old_owner_and_new_owner_projections_independent():
    execute(setup() + r'''
    ["old"] call _switch;
    _medic setVariable ["ACME_narcStore",[[_row] call _copy]];
    _oldSpace setVariable ["ACME_HCMedPushJob",createHashMapFromArray [["session","old-only"]]];
    ["new"] call _switch;
    [(_medic getVariable "ACME_narcStore") isEqualTo [],"new owner inherited unreplicated old row"] call _check;
    [count (_machineSpace getVariable ["ACME_HCMedPushJob",createHashMap])==0,"new owner shared old controller"] call _check;
    ["old","new",["ACME_narcStore"]] call _replicateProvider;
    ["new"] call _switch;
    private _new=(_medic getVariable "ACME_narcStore") select 0;
    _new set [2,1];
    ["old"] call _switch;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==2,"new owner mutated aliased old row"] call _check;
    ["server"] call _switch;
    [(_medic getVariable "ACME_narcStore") isEqualTo [],"server observed implicit provider replication"] call _check;
    ''')


def test_accepted_claim_creates_canonical_journal_before_lost_client_continuation():
    execute(setup() + r'''
    call _claim;
    private _j=call _journal;
    [count _j>0 && {(_j get "state")=="awaitBegin"},"accepted claim lacks durable awaiting-begin journal"] call _check;
    [(_j get "initial") isEqualTo _row && {(_j get "row") isEqualTo _row},"claim journal changed funded syringe"] call _check;
    [count _patientEvents==0 && {count (_oldSpace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap])==0},"claim dispatched patient work or fabricated live controller"] call _check;
    // The private continuation disappears with the old machine. The new owner
    // starts without any old owner row, controller, escrow or callbacks.
    _oldSpace setVariable ["ACME_inventoryCallbacks",createHashMap];
    _providerOwner=8;
    ["recover",[],8] call _send;
    [((call _journal) get "state")=="ready" && {call _remaining==2},"orphan recovery lost original funded remainder"] call _check;
    [count _patientEvents==0,"orphan recovery invented a medication delivery"] call _check;
    ["begin",[_session,"push",_patient,"leftarm",0,[0,1,1],0],8] call _send;
    [((call _journal) get "state")=="ready" && {count _patientEvents==0},"late begin restarted recovered orphan"] call _check;
    ''')


def test_begin_is_exact_idempotent_and_cannot_replace_the_patient_or_session():
    execute(setup() + r'''
    call _claim; call _begin;
    private _revision=(call _journal) get "revision";
    call _begin;
    [((call _journal) get "revision")==_revision && {((call _journal) get "state")=="active"},"duplicate begin created a second session"] call _check;
    ["begin",["replacement","push",_medic,"rightarm",1,[1,1,1],0]] call _send;
    [((call _journal) get "session")==_session && {((call _journal) get "binding" select 2) isEqualTo _patient},"changed begin replaced immutable patient binding"] call _check;
    [count _patientEvents==0 && {call _remaining==2},"begin delivered or debited medication"] call _check;
    ''')


def test_server_reserves_exact_slice_before_synchronous_patient_callback():
    execute(setup() + r'''
    call _claim; call _begin;
    private _observed=false;
    ACME_fnc_ownerDispatch={
        private _j=call _journal;
        private _batch=(_j get "batches") get "slice-a";
        _observed=(_batch select 3)=="pending" && {abs (((_j get "row") select 2)-1.75)<0.000001};
        _patientEvents pushBack ([_this] call _copy);
        ["slice-a",true] call _receipt;
    };
    ["slice-a"] call _batch;
    [_observed && {count _patientEvents==1},"patient callback preceded durable canonical reservation"] call _check;
    [(((call _journal) get "batches") get "slice-a" select 3)=="accepted", "synchronous patient decision was overwritten"] call _check;
    [abs (call _remaining-1.75)<0.000001,"synchronous decision lost canonical dose debit"] call _check;
    ''')


@pytest.mark.parametrize("first_accepted,second_accepted", [(True, True), (True, False), (False, True), (False, False)])
def test_migration_reordered_duplicate_decisions_use_canonical_row_and_restore_unsent_tail(first_accepted, second_accepted):
    expected = 2 - 0.25 * first_accepted - 0.25 * second_accepted
    execute(setup() + r'''
    call _claim; call _begin;
    // Only the old owner observes the extra 0.25 mL visual tail. It is not a
    // registered patient batch and must never be replayed after migration.
    ["old"] call _switch;
    private _advanced=[_row] call _copy; _advanced set [2,1.25]; _advanced set [5,[["Ketamine",1.25]]];
    _medic setVariable ["ACME_narcStore",[_advanced]];
    _oldSpace setVariable ["ACME_HCMedPushJob",createHashMapFromArray [["session",_session],["unsentDelta",_delta],["flowing",true]]];
    ["slice-a"] call _batch; ["slice-b"] call _batch;
    [count _patientEvents==2 && {abs (call _remaining-1.5)<0.000001},"canonical batches did not reserve two exact slices"] call _check;
    _providerOwner=8;
    ["recover",[],8] call _send;
    [((call _journal) get "state")=="stopping", "migration released source while patient decisions were unknown"] call _check;
    ''' + f'["slice-b",{str(second_accepted).lower()}] call _receipt;' + r'''
    [((call _journal) get "state")=="stopping", "first terminal decision forgave another pending slice"] call _check;
    ''' + f'["slice-a",{str(first_accepted).lower()}] call _receipt;' +
        f'["slice-b",{str(not second_accepted).lower()},"changed duplicate"] call _receipt;' +
        f'["slice-a",{str(first_accepted).lower()},"duplicate"] call _receipt;' +
        f'private _expected={expected};' + r'''
    private _final=(call _journal) get "row";
    [abs ((_final select 2)-_expected)<0.000001 && {abs ((_final select 5 select 0 select 1)-_expected)<0.000001},"migration lost or duplicated accepted/rejected/unsent drug"] call _check;
    [((call _journal) get "state")=="ready" && {count _patientEvents==2},"migration resumed flow or replayed the unsent visual tail"] call _check;
    ["new"] call _switch;
    [(_medic getVariable "ACME_narcStore") isEqualTo [] && {count (_machineSpace getVariable ["ACME_HCMedPushJob",createHashMap])==0},"server settlement depended on a shared old-owner row/controller"] call _check;
    ''')


@pytest.mark.parametrize("change", ["wire", "delta", "session"])
def test_duplicate_batch_identity_cannot_change_immutable_delivery_or_debit(change):
    mutations = {
        "wire": 'private _doses=+(_wireArgs select 6); private _dose=+(_doses select 0); _dose set [1,999]; _doses set [0,_dose]; _wireArgs set [6,_doses];',
        "delta": '_again set [3,[0.5,0,[[0,"Ketamine",0.5]]]];',
        "session": '_again set [0,"foreign-session"];',
    }
    execute(setup() + r'''
    call _claim; call _begin;
    private _wireArgs=["slice-a"] call _batch;
    private _again=[_session,"slice-a",[_wireArgs] call _copy,[_delta] call _copy];
    _wireArgs=_again select 2;
    ''' + mutations[change] + r'''
    ["batch",_again] call _send;
    [count _patientEvents==1 && {abs (call _remaining-1.75)<0.000001},"changed duplicate dispatched or debited a second dose"] call _check;
    ["slice-a",false] call _receipt;
    [abs (call _remaining-2)<0.000001,"changed duplicate poisoned original exact rejection refund"] call _check;
    ''')


def test_old_owner_cannot_register_new_slices_after_migration_or_restart_stopped_session():
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    _providerOwner=8;
    ["slice-b"] call _batch;
    [count _patientEvents==1 && {count ((call _journal) get "batches")==1},"old owner delivered new medication after migration"] call _check;
    ["recover",[],8] call _send;
    _providerOwner=7;
    ["slice-c"] call _batch;
    call _begin;
    [count _patientEvents==1 && {((call _journal) get "state")=="stopping"},"away-and-back owner identity revived a closed session"] call _check;
    ["slice-a",true] call _receipt;
    [((call _journal) get "state")=="ready" && {abs (call _remaining-1.75)<0.000001},"old-owner fencing discarded a previously registered patient decision"] call _check;
    ''')


def test_lease_expiry_retries_exact_pending_request_without_forgiving_unknown_delivery():
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _first=[(_patientEvents select 0)] call _copy;
    _providerOwner=8;
    CBA_missionTime=1000;
    ["server"] call _switch;
    call ACME_fnc_syringeDeliveryServerTick;
    call ACME_fnc_syringeDeliveryServerTick;
    [((call _journal) get "state")=="stopping" && {abs (call _remaining-1.75)<0.000001},"lease expiry refunded an uncertain patient dose"] call _check;
    [count _patientEvents==2 && {(_patientEvents select 1) isEqualTo _first},"server retry changed request identity or sent more than its cadence"] call _check;
    private _settles=_targetEvents select {(_x select 0)=="ACME_syringeDeliveryReply" && {(_x select 1 select 0)=="settle"}};
    [count _settles==0 && {(call _record select 5)=="reserved"},"missing patient ACK released usable syringe stock"] call _check;
    CBA_missionTime=1005;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _patientEvents==3 && {(_patientEvents select 2) isEqualTo _first},"later retry was discarded or reidentified"] call _check;
    ''')


def test_patient_owner_change_holds_uncertain_slice_then_accepts_replicated_exact_receipt():
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    _patientOwner=10;
    _providerOwner=8;
    CBA_missionTime=100;
    ["server"] call _switch;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _patientEvents==1 && {((call _journal) get "state")=="stopping"},"new patient owner received uncertain systemic replay"] call _check;
    [abs (call _remaining-1.75)<0.000001,"missing transferred receipt refunded uncertain drug"] call _check;
    _patient setVariable ["ACME_medicationReceiptsB14",createHashMapFromArray [["slice-a",[true,"accepted on original patient owner"]]]];
    call ACME_fnc_syringeDeliveryServerTick;
    [((call _journal) get "state")=="ready" && {abs (call _remaining-1.75)<0.000001},"replicated exact patient receipt failed to settle original debit"] call _check;
    [count _patientEvents==1,"receipt reconciliation reapplied patient physiology"] call _check;
    ''')


@pytest.mark.parametrize("postmortem", [False, True])
def test_production_patient_delivery_is_once_and_unknown_new_owner_cannot_apply(postmortem):
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _args=(_patientEvents select 0) select 2;
    _patientOwner=10;
    ["patientB"] call _switch;
    _args call ACME_fnc_medicationLineLocal;
    [_deliveredMg==0 && {count (_patient getVariable ["ACME_medicationReceiptsB14",createHashMap])==0},"unknown new patient owner applied an uncertain dose"] call _check;
    _patientOwner=9;
    ["patientA"] call _switch;
    ''' + f'_patientAlive={str(not postmortem).lower()};' + r'''
    _args call ACME_fnc_medicationLineLocal;
    _args call ACME_fnc_medicationLineLocal;
    ''' + f'[_deliveredMg=={0 if postmortem else 12.5},"duplicate patient delivery changed systemic medication"] call _check;' + r'''
    private _receiptMap=_patient getVariable ["ACME_medicationReceiptsB14",createHashMap];
    [count _receiptMap==1 && {((_receiptMap get "slice-a") select 0)},"production patient path failed to persist one terminal decision"] call _check;
    call _drainServer;
    [abs (call _remaining-1.75)<0.000001 && {(((call _journal) get "batches") get "slice-a" select 3)=="accepted"},"patient decision failed to terminate original source debit"] call _check;
    ''')


@pytest.mark.parametrize("fresh_kit", [False, True])
@pytest.mark.parametrize("stale_row", [False, True])
def test_new_owner_canonical_recovery_waits_for_certificate_and_places_or_discards_one_token(fresh_kit, stale_row):
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    ["slice-a",true] call _receipt;
    _providerOwner=8;
    ["recover",[],8] call _send;
    private _settles=_targetEvents select {(_x select 0)=="ACME_syringeDeliveryReply" && {(_x select 1 select 0)=="settle"}};
    private _settleArgs=(_settles select ((count _settles)-1)) select 1;
    _targetEvents=[];
    ["new"] call _switch;
    ''' + ('private _stale=[_row] call _copy; _stale set [2,1.25]; _stale set [5,[["Ketamine",1.25]]]; _medic setVariable ["ACME_narcStore",[_stale]];' if stale_row else '') + r'''
    ''' + ('_medic setVariable ["ACME_equipmentKitEpoch",1]; _medic setVariable ["ACME_narcStore",[[_row] call _copy]];' if fresh_kit else '') + r'''
    private _unrelated=createHashMapFromArray [["medic",_patient],["session","unrelated"],["flowing",true]];
    _machineSpace setVariable ["ACME_HCMedPushJob",_unrelated];
    _machineSpace setVariable ["ACME_HCMedPushPFH",123];
    uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
    private _retireCalls=0;
    ACME_fnc_hardcorePushRetire={_retireCalls=_retireCalls+1;};
    _settleArgs call ACME_fnc_syringeDeliveryReply;
    [count (_medic getVariable "native")==0 && {count (_medic getVariable "ACME_inventoryEscrow")==0},"reply outran missing certificate and materialized custody"] call _check;
    ["new",_token] call _replicateToken;
    _settleArgs call ACME_fnc_syringeDeliveryReply;
    _settleArgs call ACME_fnc_syringeDeliveryReply;
    ["new","server"] call _replicateProvider;
    call _drainServer;
    ["new",_token] call _replicateToken;
    ["new"] call _deliverInventoryReplies;
    ["new"] call _deliverInventoryReplies;
    [_retireCalls==0 && {(_machineSpace getVariable "ACME_HCMedPushJob") isEqualTo _unrelated}
        && {(_machineSpace getVariable "ACME_HCMedPushPFH")==123} && {uiNamespace getVariable "ACME_SK_InjectionBusy"},"recovered receipt modified unrelated current controller/UI"] call _check;
    [count (_medic getVariable "ACME_inventoryEscrow")==0 && {((call _journal) get "state")=="settled"},"canonical return failed to close exact source custody"] call _check;
    ''' + (r'''
    [count (_medic getVariable "native")==0 && {(call _record select 5)=="spent"},"fresh kit was replenished by old source token"] call _check;
    [(_medic getVariable "ACME_narcStore") isEqualTo [_row],"old canonical dose rewrote replacement kit"] call _check;
    ''' if fresh_kit else r'''
    [(_medic getVariable "native") isEqualTo [[_token,"syringe"]] && {(call _record select 5)=="held"},"canonical migration return lost or duplicated exact carrier"] call _check;
    private _left=(_medic getVariable "ACME_narcStore") select 0;
    [abs ((_left select 2)-1.75)<0.000001 && {abs ((_left select 5 select 0 select 1)-1.75)<0.000001},"canonical migration replacement lost exact accepted dose"] call _check;
    '''))


def test_stop_manifest_preserves_batch_when_stop_overtakes_original_delivery_packet():
    execute(setup() + r'''
    call _claim; call _begin;
    private _args=["slice-a"] call _wire;
    private _batchData=[_session,"slice-a",_args,_delta];
    ["stop",[_session,"manual",[_batchData]]] call _send;
    [count _patientEvents==1 && {((call _journal) get "state")=="stopping"}
        && {abs (call _remaining-1.75)<0.000001},"STOP overtook batch and returned medication before exact dispatch"] call _check;
    ["batch",_batchData] call _send;
    ["stop",[_session,"manual",[_batchData]]] call _send;
    [count _patientEvents==1,"late original batch or duplicate STOP redelivered manifest dose"] call _check;
    ["slice-a",true] call _receipt;
    [((call _journal) get "state")=="ready" && {abs (call _remaining-1.75)<0.000001},"manifest dose failed to terminate canonical source"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["push", "inject"])
def test_unfunded_dose_is_terminal_rejection_without_patient_dispatch_or_source_loss(kind):
    execute(setup() + r'''
    call _claim;
    ''' + f'["begin",[_session,"{kind}",_patient,"leftarm",0,[0,1,1],0]] call _send;' + r'''
    private _args=["slice-a"] call _wire;
    _args set [6,[["Ketamine_IV",999,true,"unfunded",1,true,[]]]];
    ["batch",[_session,"slice-a",_args,_delta]] call _send;
    [count _patientEvents==0 && {call _remaining==2},"unfunded dose reached patient or reduced canonical source"] call _check;
    [((call _journal) get "state")=="ready" && {(((call _journal) get "batches") get "slice-a" select 3)=="rejected"},"invalid batch left phantom pending patient debt"] call _check;
    ''')


def test_hosted_synchronous_begin_delivery_stop_settlement_and_native_placement_do_not_reenter():
    execute(setup() + r'''
    _providerOwner=2; _patientOwner=2;
    ["server"] call _switch;
    _hasInterface=true;
    ACE_player=_medic;
    private _directEvents=0;
    CBA_fnc_serverEvent={
        _directEvents=_directEvents+1;
        if (_directEvents>50) exitWith {[false,"synchronous server transport recursively reentered settlement"] call _check;};
        if ((_this select 0)=="ACME_inventoryBroker") then {(_this select 1) call ACME_fnc_inventoryLedgerBroker;};
        if ((_this select 0)=="ACME_syringeDelivery") then {(_this select 1) call ACME_fnc_syringeDeliveryBroker;};
    };
    CBA_fnc_targetEvent={
        _directEvents=_directEvents+1;
        if (_directEvents>50) exitWith {[false,"synchronous client reply recursively reentered settlement"] call _check;};
        if ((_this select 0)=="ACME_inventoryReply") then {(_this select 1) call ACME_fnc_inventoryLedgerReply;};
        if ((_this select 0)=="ACME_syringeDeliveryReply") then {(_this select 1) call ACME_fnc_syringeDeliveryReply;};
    };
    ACME_fnc_ownerDispatch={
        _patientEvents pushBack ([_this] call _copy);
        (_this select 2) call ACME_fnc_medicationLineLocal;
    };
    _medic setVariable ["ACME_narcStore",[[_row] call _copy]];
    [_medic,"syringe",[[_sid,_row]]] call ACME_fnc_inventoryLedgerCommit;
    _token=(_machineSpace getVariable "ACME_inventoryLedgerIndex") get ("syringe:"+_sid);
    [_medic,"syringe",_sid,_request] call ACME_fnc_inventoryLedgerReserve;
    private _escrow=_medic getVariable "ACME_inventoryEscrow";
    private _held=_escrow get _request;
    _held set [6,["syringeDeliveryB285",2]]; _escrow set [_request,_held];
    private _claimed=false;
    [_medic,_request,{_claimed=_this select 0;},[],true] call ACME_fnc_inventoryLedgerClaim;
    [_claimed,"synchronous claim continuation did not receive exact certificate"] call _check;
    private _began=false;
    ["begin",_medic,_request,[_session,"push",_patient,"leftarm",0,[0,1,1],0],{_began=_this select 0;},[]] call ACME_fnc_syringeDeliveryRequest;
    [_began,"synchronous begin lost or duplicated its continuation"] call _check;
    private _args=["slice-a"] call _wire;
    ["batch",_medic,_request,[_session,"slice-a",_args,_delta]] call ACME_fnc_syringeDeliveryRequest;
    [_deliveredMg==12.5 && {count _patientEvents==1},"synchronous batch/receipt failed exact one patient dose"] call _check;
    private _handler=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
    _machineSpace setVariable ["ACME_HCMedPushPFH",_handler];
    _machineSpace setVariable ["ACME_HCMedPushJob",createHashMapFromArray [
        ["medic",_medic],["patient",_patient],["session",_session],["stableId",_sid],
        ["inventoryRequest",_request],["syringeDelivery",true],["flowing",false]]];
    uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
    uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
    ["stop",_medic,_request,[_session,"manual"]] call ACME_fnc_syringeDeliveryRequest;
    [((call _journal) get "state")=="settled" && {(call _record select 5)=="held"},"synchronous final return did not terminate journal and token"] call _check;
    [(_medic getVariable "native") isEqualTo [[_token,"syringe"]] && {count (_medic getVariable "ACME_inventoryEscrow")==0},"synchronous final return lost or duplicated carrier"] call _check;
    [abs (((_medic getVariable "ACME_narcStore") select 0 select 2)-1.75)<0.000001,"synchronous canonical row lost accepted dose"] call _check;
    [count (_machineSpace getVariable "ACME_HCMedPushJob")==0 && {!((_handlers select _handler) select 2)}
        && {!(uiNamespace getVariable "ACME_SK_InjectionBusy")} && {!(uiNamespace getVariable "ACME_SK_CarouselBusy")},"synchronous final reply retained old worker/UI"] call _check;
    [_directEvents<50 && {_deliveredMg==12.5},"synchronous final reply recursed or redelivered physiology"] call _check;
    ''')


def test_mutating_original_registered_arguments_cannot_change_a_retry_or_rejection_refund():
    execute(setup() + r'''
    call _claim; call _begin;
    private _args=["slice-a"] call _batch;
    private _original=[(_patientEvents select 0)] call _copy;
    private _dose=(_args select 6) select 0; _dose set [1,999];
    private _meta=_args select 9; (_meta select 3) set [0,2];
    _providerOwner=8; CBA_missionTime=100;
    ["server"] call _switch;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _patientEvents==2 && {(_patientEvents select 1) isEqualTo _original},"caller mutation rewrote immutable retry wire"] call _check;
    ["slice-a",false] call _receipt;
    [call _remaining==2 && {((call _journal) get "row" select 5) isEqualTo [["Ketamine",2]]},"caller mutation changed exact canonical rejection refund"] call _check;
    ''')


def test_production_normal_injection_continuation_waits_for_begin_before_private_debit_and_dispatch():
    execute(setup() + r'''
    call _claim;
    ["old",_token] call _replicateToken;
    ["old"] call _deliverInventoryReplies;
    private _remainingRow=[_row] call _copy;
    _remainingRow set [2,1.75]; _remainingRow set [5,[["Ketamine",1.75]]];
    private _doses=[["Ketamine_IV",12.5,true,"label",1,true,[]]];
    private _continuation=[_medic,_patient,"leftarm",_doses,0,_row,_remainingRow,[],_request,[]];
    [true,_continuation] call ACME_fnc_skInventoryInjectClaim;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==2 && {count _patientEvents==0},"ordinary injection debited or delivered before certified BEGIN"] call _check;
    call _drainServer;
    [count _patientEvents==0 && {((call _journal) get "state")=="active"},"BEGIN alone dispatched ordinary injection"] call _check;
    ["old"] call _deliverDeliveryReplies;
    [abs (((_medic getVariable "ACME_narcStore") select 0 select 2)-1.75)<0.000001 && {count _patientEvents==0},"certified normal continuation did not debit exact private source"] call _check;
    ["old","server"] call _replicateProvider;
    call _drainServer;
    [count _patientEvents==1 && {((call _journal) get "state")=="stopping"}
        && {abs (call _remaining-1.75)<0.000001},"ordinary injection failed durable exact batch and close"] call _check;
    private _args=(_patientEvents select 0) select 2;
    ["patientA"] call _switch;
    _args call ACME_fnc_medicationLineLocal;
    _args call ACME_fnc_medicationLineLocal;
    [_deliveredMg==12.5,"ordinary injection duplicate redelivered physiology"] call _check;
    call _drainServer;
    [((call _journal) get "state")=="ready" && {abs (call _remaining-1.75)<0.000001},"ordinary injection patient receipt did not settle canonical source"] call _check;
    ''')


def test_claim_event_overtaking_delivery_marker_publication_cannot_succeed_without_journal():
    execute(setup() + r'''
    call _fund;
    [_medic,"syringe",_sid,_request] call ACME_fnc_inventoryLedgerReserve;
    // Only the original six-field Reserve publication reaches the server.
    ["old","server"] call _replicateProvider;
    [_medic,_request,{},[],true] call ACME_fnc_inventoryLedgerClaim;
    private _wire=(_serverEvents select 0) select 1;
    call _drainServer;
    [count _targetEvents==0 && {(call _record select 5)=="held"}
        && {count (_serverSpace getVariable ["ACME_syringeDeliveries",createHashMap])==0},"claim outran intent publication and succeeded without durable delivery authority"] call _check;
    ["old","server"] call _replicateProvider;
    ["server"] call _switch;
    _wire call ACME_fnc_inventoryLedgerBroker;
    [count _targetEvents==1 && {(_targetEvents select 0 select 1 select 6)}
        && {((call _journal) get "state")=="awaitBegin"},"durable retry after marker replication failed one certified journal admission"] call _check;
    ''')


@pytest.mark.parametrize("accepted", [False, True])
def test_fresh_kit_while_patient_decision_pending_preserves_retry_and_consumes_old_source(accepted):
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _wireBefore=[(_patientEvents select 0)] call _copy;
    _providerOwner=8;
    ["new"] call _switch;
    _medic setVariable ["ACME_equipmentKitEpoch",1];
    _medic setVariable ["ACME_narcStore",[[_row] call _copy]];
    ["new","server"] call _replicateProvider;
    ["server"] call _switch;
    CBA_missionTime=100;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _patientEvents==2 && {(_patientEvents select 1) isEqualTo _wireBefore}
        && {((call _journal) get "state")=="stopping"},"kit reset discarded pending exact patient retry or released unknown source"] call _check;
    ''' + f'["slice-a",{str(accepted).lower()}] call _receipt;' + r'''
    private _settles=_targetEvents select {(_x select 0)=="ACME_syringeDeliveryReply" && {(_x select 1 select 0)=="settle"}};
    private _settle=(_settles select ((count _settles)-1)) select 1;
    _targetEvents=[];
    ["new",_token] call _replicateToken;
    ["new"] call _switch;
    _settle call ACME_fnc_syringeDeliveryReply;
    ["new","server"] call _replicateProvider;
    call _drainServer;
    ["new",_token] call _replicateToken;
    ["new"] call _deliverInventoryReplies;
    [(_medic getVariable "ACME_narcStore") isEqualTo [_row] && {count (_medic getVariable "native")==0},"old pending patient decision replenished or rewrote fresh kit"] call _check;
    [(call _record select 5)=="spent" && {((call _journal) get "state")=="settled"},"old source failed terminal consumed accounting after kit reset"] call _check;
    [count (_medic getVariable "ACME_inventoryEscrow")==0,"old pending source retained an endless reset blocker"] call _check;
    ''')


def test_missing_patient_machine_nonce_holds_source_until_machine_registration_allows_dispatch():
    execute(setup() + r'''
    call _claim; call _begin;
    private _machines=_serverSpace getVariable "ACME_syringeDeliveryMachines";
    _machines deleteAt "9";
    ["slice-a"] call _batch;
    [count _patientEvents==0 && {abs (call _remaining-1.75)<0.000001},"unregistered patient machine received an uncertified incarnation dose"] call _check;
    CBA_missionTime=100;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _patientEvents==0 && {((call _journal) get "state")=="stopping"},"missing machine hello was interpreted as dose rejection"] call _check;
    [9,"machine9"] call ACME_fnc_syringeDeliveryMachine;
    CBA_missionTime=101;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _patientEvents==1 && {(_patientEvents select 0 select 2 select 9 select 6)=="machine9"},"registered exact machine incarnation failed to release one pending request"] call _check;
    private _args=(_patientEvents select 0) select 2;
    ["patientA"] call _switch;
    _args call ACME_fnc_medicationLineLocal;
    call _drainServer;
    [_deliveredMg==12.5 && {((call _journal) get "state")=="ready"}
        && {abs (call _remaining-1.75)<0.000001},"registered pending dose failed terminal exact delivery"] call _check;
    ''')


def test_query_before_original_packet_tombstones_absent_delivery_before_refund_and_blocks_late_aba():
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _lateArgs=[(_patientEvents select 0 select 2)] call _copy;
    _providerOwner=8; _patientOwner=10; CBA_missionTime=100;
    ["server"] call _switch;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _ownerEvents==1 && {(_ownerEvents select 0 select 2)==9},"uncertain ownership transfer did not query captured original machine"] call _check;
    private _query=(_ownerEvents select 0) select 1;
    ["patientA"] call _switch;
    _query call ACME_fnc_syringeDeliveryPatientQuery;
    private _decision=[_machineSpace getVariable "ACME_syringeDeliveryPatientDecisions",["slice-a",[]]] call _mapDefault;
    [count _decision==3 && {!(_decision select 1)} && {count (_patient getVariable ["ACME_medicationReceiptsB14",createHashMap])==0},"negative proof lacked private tombstone or wrote remote patient state"] call _check;
    call _drainServer;
    [call _remaining==2 && {((call _journal) get "state")=="ready"},"original machine negative proof failed exact source recovery"] call _check;
    _patientOwner=9;
    ["patientA"] call _switch;
    _lateArgs call ACME_fnc_medicationLineLocal;
    _lateArgs call ACME_fnc_medicationLineLocal;
    call _drainServer;
    [_deliveredMg==0 && {call _remaining==2}
        && {(((call _journal) get "batches") get "slice-a" select 3)=="rejected"},"late A-B-A packet delivered a dose after its source refund"] call _check;
    ''')


def test_private_accepted_decision_survives_object_receipt_loss_and_proves_query_without_refund():
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _args=[(_patientEvents select 0 select 2)] call _copy;
    ["patientA"] call _switch;
    _args call ACME_fnc_medicationLineLocal;
    [_deliveredMg==12.5,"original patient execution failed"] call _check;
    _serverEvents=[]; // The original acceptance ACK is lost at the transport boundary.
    _patient setVariable ["ACME_medicationReceiptsB14",createHashMap];
    _providerOwner=8; _patientOwner=10; CBA_missionTime=100;
    ["server"] call _switch;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _ownerEvents==1 && {abs (call _remaining-1.75)<0.000001},"lost replicated receipt was guessed rejected before original-machine proof"] call _check;
    private _query=(_ownerEvents select 0) select 1;
    ["patientA"] call _switch;
    [count (_patient getVariable ["ACME_medicationReceiptsB14",createHashMap])==0,"fixture implicitly replicated deleted object receipt"] call _check;
    _query call ACME_fnc_syringeDeliveryPatientQuery;
    call _drainServer;
    [abs (call _remaining-1.75)<0.000001 && {((call _journal) get "state")=="ready"},"private original acceptance was incorrectly source-refunded"] call _check;
    _patientOwner=9;
    ["patientA"] call _switch;
    _patient setVariable ["ACME_medicationReceiptsB14",createHashMap];
    _args call ACME_fnc_medicationLineLocal;
    [_deliveredMg==12.5,"private accepted receipt loss permitted duplicate systemic exposure"] call _check;
    ''')


def test_accepted_private_decision_is_committed_before_reentrant_medication_effect_callback():
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _args=[(_patientEvents select 0 select 2)] call _copy;
    ["patientA"] call _switch;
    private _observed=false;
    ace_medical_treatment_fnc_medicationLocal={
        private _decision=[_machineSpace getVariable ["ACME_syringeDeliveryPatientDecisions",createHashMap],["slice-a",[]]] call _mapDefault;
        _observed=count _decision==3 && {_decision select 1};
        [_medic,_request,_session,"slice-a","slice-a",_patient,9,"machine9"] call ACME_fnc_syringeDeliveryPatientQuery;
        _deliveredMg=_deliveredMg+(_this select 3);
    };
    _args call ACME_fnc_medicationLineLocal;
    call _drainServer;
    [_observed && {_deliveredMg==12.5} && {abs (call _remaining-1.75)<0.000001},"effect callback queried before private acceptance commit and refunded delivered source"] call _check;
    [(((call _journal) get "batches") get "slice-a" select 3)=="accepted", "reentrant query replaced committed patient acceptance"] call _check;
    ''')


def test_reused_engine_owner_id_with_new_nonce_cannot_deny_old_unknown_delivery():
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _args=[(_patientEvents select 0 select 2)] call _copy;
    _providerOwner=8; _patientOwner=10; CBA_missionTime=100;
    ["server"] call _switch;
    [9,"replacement9"] call ACME_fnc_syringeDeliveryMachine;
    call ACME_fnc_syringeDeliveryServerTick;
    private _query=(_ownerEvents select 0) select 1;
    ["patientA"] call _switch;
    _machineSpace setVariable ["ACME_syringeDeliveryMachineNonce","replacement9"];
    _machineSpace setVariable ["ACME_syringeDeliveryPatientDecisions",createHashMap];
    _query call ACME_fnc_syringeDeliveryPatientQuery;
    [count _serverEvents==0 && {count (_machineSpace getVariable "ACME_syringeDeliveryPatientDecisions")==0},"new connection using old owner ID denied an unknown original-machine dose"] call _check;
    _patientOwner=9; _patientLocal=true;
    _args call ACME_fnc_medicationLineLocal;
    [_deliveredMg==0 && {count _serverEvents==0},"reused owner ID executed old-incarnation dose"] call _check;
    ["server"] call _switch;
    [abs (call _remaining-1.75)<0.000001 && {((call _journal) get "state")=="stopping"}
        && {(((call _journal) get "batches") get "slice-a" select 8)=="machine9"},"new machine hello rewrote prior source authority or refunded uncertain delivery"] call _check;
    ''')


@pytest.mark.parametrize("executed", [False, True])
def test_deleted_patient_recovers_from_captured_machine_private_proof_without_object_access_or_replay(executed):
    execute(setup() + r'''
    call _claim; call _begin;
    ["slice-a"] call _batch;
    private _args=[(_patientEvents select 0 select 2)] call _copy;
    ["patientA"] call _switch;
    ''' + ('_args call ACME_fnc_medicationLineLocal;' if executed else '') + r'''
    _serverEvents=[]; // The acceptance packet is lost if execution happened.
    _patient setVariable ["ACME_medicationReceiptsB14",createHashMap];
    // The namespace preserves one logical engine object reference in every
    // saved wire/fingerprint; the native null boundary now reports its deletion.
    _patientDeleted=true;
    _providerOwner=8; CBA_missionTime=100;
    ["server"] call _switch;
    call ACME_fnc_syringeDeliveryServerTick;
    [count _ownerEvents==1 && {(_ownerEvents select 0 select 2)==9},"deleted patient skipped available captured-machine proof"] call _check;
    if (count _ownerEvents==1) then {
        private _query=(_ownerEvents select 0) select 1;
        ["patientA"] call _switch;
        _query call ACME_fnc_syringeDeliveryPatientQuery;
        call _drainServer;
    };
    ''' + f'private _expectedRemaining={1.75 if executed else 2}; private _expectedMg={12.5 if executed else 0};' + r'''
    [abs (call _remaining-_expectedRemaining)<0.000001 && {((call _journal) get "state")=="ready"},"deleted patient private proof failed exact terminal source accounting"] call _check;
    [count _patientEvents==1 && {_deliveredMg==_expectedMg},"deleted patient proof replayed physiology"] call _check;
    ["patientA"] call _switch;
    _args call ACME_fnc_medicationLineLocal;
    [_deletedReceiptReads==0 && {_deletedReceiptWrites==0} && {_deliveredMg==_expectedMg},"deleted patient proof accessed removed object state or replayed dose"] call _check;
    ''')


def test_deleted_patient_without_registered_machine_is_proven_undispatched_and_refunds_once():
    execute(setup() + r'''
    call _claim; call _begin;
    private _machines=_serverSpace getVariable "ACME_syringeDeliveryMachines";
    _machines deleteAt "9";
    private _args=["slice-a"] call _batch;
    [count _patientEvents==0 && {abs (call _remaining-1.75)<0.000001},"unknown machine unexpectedly received packet before deletion"] call _check;
    _patientDeleted=true; _providerOwner=8; CBA_missionTime=100;
    ["server"] call _switch;
    call ACME_fnc_syringeDeliveryServerTick;
    [call _remaining==2 && {((call _journal) get "state")=="ready"}
        && {(((call _journal) get "batches") get "slice-a" select 3)=="rejected"},"provably undispatched deleted-patient batch retained or lost source"] call _check;
    [count _ownerEvents==0 && {count _patientEvents==0} && {_deliveredMg==0}
        && {_deletedReceiptReads==0} && {_deletedReceiptWrites==0},"undispatched deletion queried fabricated authority, accessed removed patient or delivered medication"] call _check;
    // A later hello cannot turn a terminal never-dispatched request into a dose.
    [9,"machine9"] call ACME_fnc_syringeDeliveryMachine;
    CBA_missionTime=110;
    call ACME_fnc_syringeDeliveryServerTick;
    call ACME_fnc_syringeDeliveryServerTick;
    ["batch",[_session,"slice-a",_args,_delta],8] call _send;
    [call _remaining==2 && {count _ownerEvents==0} && {count _patientEvents==0}
        && {_deliveredMg==0} && {_deletedReceiptReads==0},"late machine hello or duplicate request replayed/refunded terminal deleted-patient batch"] call _check;
    ''')


@pytest.mark.parametrize("mutation", ["provider_owner", "patient_owner", "retry_owner", "stop_manifest", "private_tombstone", "accepted_commit", "query_nonce", "apply_nonce"])
def test_critical_protocol_mutations_are_rejected_by_executed_scenarios(monkeypatch, mutation):
    original = source
    replacements = {
        "provider_owner": ("syringeDeliveryBroker", "\nif (_sender != owner _medic) exitWith {false};", "\nif (false) exitWith {false};"),
        "patient_owner": ("medicationLineLocal", 'if (_journal && {(_meta param [5,-1]) != clientOwner', 'if (false && {(_meta param [5,-1]) != clientOwner'),
        "retry_owner": ("syringeDeliveryServerTick", 'if (_gone || {owner _patient != (_b select 6)}) then {', 'if (false) then {'),
        "stop_manifest": ("syringeDeliveryBroker", '} forEach (_data param [2,[],[[]]]);', '} forEach [];'),
        "private_tombstone": ("syringeDeliveryPatientQuery", '_decisions set [_id,_decision];', ''),
        "accepted_commit": ("medicationLineLocal", 'if (_journal) then {[true,"accepted"] call _remember;};', ''),
        "query_nonce": ("syringeDeliveryPatientQuery", '(missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""]) != _nonce', 'false'),
        "apply_nonce": ("medicationLineLocal", '(_meta param [6,""]) != (missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""])', 'false'),
    }
    name, old, new = replacements[mutation]
    assert old in original(name)

    def changed(function_name):
        text = original(function_name)
        return text.replace(old, new, 1) if function_name == name else text

    monkeypatch.setattr(__import__(__name__), "source", changed)
    cases = {
        "provider_owner": (test_old_owner_cannot_register_new_slices_after_migration_or_restart_stopped_session, "old owner delivered new medication"),
        "patient_owner": (lambda: test_production_patient_delivery_is_once_and_unknown_new_owner_cannot_apply(False), "unknown new patient owner applied"),
        "retry_owner": (test_patient_owner_change_holds_uncertain_slice_then_accepts_replicated_exact_receipt, "new patient owner received uncertain systemic replay"),
        "stop_manifest": (test_stop_manifest_preserves_batch_when_stop_overtakes_original_delivery_packet, "STOP overtook batch"),
        "private_tombstone": (test_query_before_original_packet_tombstones_absent_delivery_before_refund_and_blocks_late_aba, "private tombstone|late A-B-A packet"),
        "accepted_commit": (test_accepted_private_decision_is_committed_before_reentrant_medication_effect_callback, "effect callback queried before private acceptance"),
        "query_nonce": (test_reused_engine_owner_id_with_new_nonce_cannot_deny_old_unknown_delivery, "new connection using old owner ID denied"),
        "apply_nonce": (test_reused_engine_owner_id_with_new_nonce_cannot_deny_old_unknown_delivery, "reused owner ID executed"),
    }
    case, message = cases[mutation]
    with pytest.raises(AssertionError, match=message):
        case()
