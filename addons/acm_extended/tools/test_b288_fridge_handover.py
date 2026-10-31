"""Execute fridge stock funding through the generic machine-fenced delivery.

Native cargo, ownership and transport are fixture boundaries. Old/new private
decision maps are separate; native inventory can precede public receipt arrival.
"""
from test_b216_fridge import setup, source
from test_menu_death_lifecycle import ROOT, adapt, execute


def start():
    return setup()+r'''
        CBA_missionTime=100;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _bridge="fridge:one:7:1";
        private _journal={(missionNamespace getVariable "ACME_resourceReturns") get _bridge};
        private _serverOnly={
            while {_resourceServerMessages isNotEqualTo []} do {
                private _wire=_resourceServerMessages deleteAt 0;
                _machineOwner=2;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","server"];
                _wire call ACME_fnc_resourceReturnBroker;
            };
        };
    '''


def missing_receipt_handover():
    return r'''
        private _oldPacket=+(_resourcePackets deleteAt 0);
        _oldPacket call ACME_fnc_resourceReturnReceive;
        private _oldDecisions=missionNamespace getVariable "ACME_resourceReturnDecisions";
        _resourceServerMessages=[];
        _player setVariable ["ACME_resourceReturnReceived",createHashMap];
        _player setVariable ["ACME_bf_deliveryReceipts",createHashMap];
        _player setVariable ["ACME_bf_receivedTokens",[]];
        _requestOwnerSim=8;_machineOwner=8;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-B"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",createHashMap];
        missionNamespace setVariable ["ACME_resourceReturnProgress",createHashMap];
        _oldPacket call ACME_fnc_resourceReturnReceive;
        [_given isEqualTo [[_player,"ON"]] && {(_player getVariable "fixtureItems") isEqualTo ["ON"]},"new owner replay placed a second ordinary blood bag"] call _check;
        CBA_missionTime=103;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _query=(_resourceQueries select {(_x select 0)=="ACME_resourceReturnQuery"}) select 0;
    '''


def test_native_bag_before_receipt_replication_waits_for_original_machine_then_settles_once():
    execute(start()+missing_receipt_handover()+r'''
        [count _resourcePackets==0 && {((call _journal) select 4)=="ready"},"migration dispatched a new native write before proving the old result"] call _check;
        _playerLocal=false;_machineOwner=7;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-A"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",_oldDecisions];
        (_query select 1) call ACME_fnc_resourceReturnQuery;call _serverOnly;
        call ACME_fnc_bloodFridgeTick;
        [((call _journal) select 4)=="delivered" && {count _given==1}
            && {((missionNamespace getVariable "ACME_bf_serverGrants") get "one:7:1" select 3)=="delivered"},"original private proof failed to settle exactly one stock-funded delivery"] call _check;
        [count (_player getVariable "ACME_bf_pendingGrants")==0 && {count (_player getVariable "ACME_resourceReturnPending")==0},"proved delivery left a false persistence fence"] call _check;
    ''')


def test_missing_original_process_keeps_funding_held_without_new_owner_rematerialization():
    execute(start()+missing_receipt_handover()+r'''
        _machineOwner=7;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","replacement-connection"];
        (_query select 1) call ACME_fnc_resourceReturnQuery;call _serverOnly;
        call ACME_fnc_bloodFridgeTick;
        [((call _journal) select 4)=="ready" && {count _given==1}
            && {count (_player getVariable "ACME_bf_pendingGrants")==1}
            && {count (_player getVariable "ACME_resourceReturnPending")==1},"reused machine address guessed an old outcome or lost held stock"] call _check;
    ''')


def test_query_before_unseen_attempt_permits_new_owner_and_fences_late_aba_packet():
    execute(start()+r'''
        private _oldPacket=+(_resourcePackets deleteAt 0);
        _requestOwnerSim=8;_machineOwner=8;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-B"];
        CBA_missionTime=103;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _query=(_resourceQueries select {(_x select 0)=="ACME_resourceReturnQuery"}) select 0;
        _machineOwner=7;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-A"];
        (_query select 1) call ACME_fnc_resourceReturnQuery;call _serverOnly;
        private _oldDecisions=missionNamespace getVariable "ACME_resourceReturnDecisions";
        _machineOwner=8;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-B"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",createHashMap];
        missionNamespace setVariable ["ACME_resourceReturnProgress",createHashMap];
        CBA_missionTime=106;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _newPacket=+(_resourcePackets deleteAt 0);
        _newPacket call ACME_fnc_resourceReturnReceive;call _serverOnly;
        _machineOwner=7;_requestOwnerSim=7;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-A"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",_oldDecisions];
        _player setVariable ["ACME_resourceReturnReceived",createHashMap];
        _player setVariable ["ACME_bf_deliveryReceipts",createHashMap];
        _oldPacket call ACME_fnc_resourceReturnReceive;
        [count _given==1 && {(_player getVariable "fixtureItems") isEqualTo ["ON"]}
            && {((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0},"late ABA delivery duplicated one stock-funded product"] call _check;
    ''')


def test_legacy_give_is_presentation_only_before_and_after_real_generic_delivery():
    execute(start()+r'''
        for "_i" from 1 to 4 do {[_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;};
        [count _given==0 && {count _reaches==0},"uncertified legacy Give materialized inventory or took over presentation"] call _check;
        call _flushResources;call ACME_fnc_bloodFridgeTick;
        for "_i" from 1 to 20 do {[_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;};
        [count _given==1 && {(_player getVariable "fixtureItems") isEqualTo ["ON"]},"legacy presentation replay materialized another item"] call _check;
    ''')


def test_source_debit_failure_retains_stock_and_never_funds_generic_delivery():
    raw=source('bloodFridgeTakeOwner').replace(
        '_anchor setVariable ["ACME_bf_stock", [_stock] call ACME_fnc_syringeDeliveryCopy];',
        'nil;')
    # Only the native object-variable write is a failed engine boundary; the
    # production pre-debit journal, source readback and grant admission execute.
    assert 'nil;' in raw
    execute(setup()+'ACME_fnc_bloodFridgeTakeOwner={'+raw+'};'+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        [((_anchor getVariable "ACME_bf_stock") select 0 select 1)==1 && {count _resourcePackets==0}
            && {count (missionNamespace getVariable ["ACME_resourceReturns",createHashMap])==0},"failed source decrement funded an item"] call _check;
        [((missionNamespace getVariable "ACME_bf_serverGrants") get "one:7:1" select 3)=="failed"
            && {count (_player getVariable "ACME_bf_pendingGrants")==0},"proved unchanged source retained false pending custody"] call _check;
    ''')


def test_uncertain_stock_write_keeps_deep_frozen_audit_without_minting_or_saving():
    raw=source('bloodFridgeTakeOwner').replace(
        '_anchor setVariable ["ACME_bf_stock", [_stock] call ACME_fnc_syringeDeliveryCopy];',
        '_anchor setVariable ["ACME_bf_stock",[["ON",4],["A",2]]];')
    assert '[["ON",4]' in raw
    execute(setup()+'ACME_fnc_bloodFridgeTakeOwner={'+raw+'};'+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _grant=(missionNamespace getVariable "ACME_bf_serverGrants") get "one:7:1";
        private _audit=_grant select 7;
        private _current=_anchor getVariable "ACME_bf_stock";
        (_current select 0) set [1,99];
        [(_grant select 3)=="stockUncertain" && {count _resourcePackets==0}
            && {(_audit select 0 select 0 select 1)==1} && {(_audit select 1 select 0 select 1)==0}
            && {(_audit select 2 select 0 select 1)==4},"uncertain source lost immutable before/expected/observed evidence or minted inventory"] call _check;
        [count (_player getVariable "ACME_bf_pendingGrants")==1,"uncertain source allowed an incomplete checkpoint"] call _check;
    ''')


def test_public_event_cannot_invoke_private_virtual_stock_admission():
    init=(ROOT/'addons/circulation/XEH_postInit.sqf').read_text()
    body=init.split('["ACME_resourceReturn", {',1)[1].split('}] call CBA_fnc_addEventHandler;',1)[0]
    execute(setup()+'private _publicHandler={'+adapt(body,'circulation')+'};'+r'''
        private _bridge="fridge:one:7:1";
        private _products=[["item","ON"]];
        missionNamespace setVariable ["ACME_bf_serverGrants",createHashMapFromArray [["one:7:1",[_player,[7,1],"ON","pending",0,_anchor,_bridge]]]];
        ["fridgeStock",[_player,_anchor,_bridge,_products]] call _publicHandler;
        [count _resourcePackets==0 && {count (missionNamespace getVariable ["ACME_resourceReturns",createHashMap])==0},"public wire accessed the server-private virtual-stock admission"] call _check;
        ["fridgeStock",[_player,_anchor,_bridge,_products]] call ACME_fnc_resourceReturnBroker;
        [count _resourcePackets==1,"private-admission fixture was not otherwise a valid server record"] call _check;
    ''')


def test_headless_recipient_delivers_without_reading_undefined_controlled_player_or_opening_ui():
    raw=source('bloodFridgeReceive')
    assert 'if (!true) exitWith' in raw
    raw=raw.replace('if (!true) exitWith','if (!false) exitWith')
    execute(setup()+'ACME_fnc_bloodFridgeReceive={'+raw+'};'+r'''
        ACE_player=nil;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        call _flushResources;call ACME_fnc_bloodFridgeTick;
        [count _given==1 && {(_player getVariable "fixtureItems") isEqualTo ["ON"]}
            && {count _reaches==0},"headless delivery touched controlled-player UI or lost the item"] call _check;
    ''')


def test_previously_accepted_grant_delivers_to_same_recipient_after_death_without_replacing_actor():
    execute(start()+r'''
        _alive=false;
        call _flushResources;call ACME_fnc_bloodFridgeTick;
        [count _given==1 && {(_given select 0 select 0) isEqualTo _player}
            && {(_player getVariable "fixtureItems") isEqualTo ["ON"]} && {count _reaches==0},"late grant moved actors, disappeared or started corpse theatre"] call _check;
    ''')


def test_deleted_recipient_parks_proved_unseen_funding_without_replacement_or_idle_poll():
    tick=source('bloodFridgeTick')
    marker='private _grant=_serverGrants get _x;'
    assert tick.count(marker)==1
    tick=tick.replace(marker,'_parkedScans=_parkedScans+1;'+marker)
    execute(start()+r'''
        private _native=(missionNamespace getVariable "ACME_bf_serverGrants") get "one:7:1";
        _native set [0,objNull];
        private _generic=call _journal;_generic set [0,objNull];
        _resourcePackets=[];
        CBA_missionTime=103;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _query=(_resourceQueries select {(_x select 0)=="ACME_resourceReturnQuery"}) select 0;
        _machineOwner=7;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-A"];
        (_query select 1) call ACME_fnc_resourceReturnQuery;call _serverOnly;
        call ACME_fnc_bloodFridgeTick;
        [((call _journal) select 4)=="orphaned" && {(_native select 3)=="orphaned"}
            && {((call _journal) select 3) isEqualTo [["item","ON"]]} && {count _given==0},"deleted recipient lost its funded product or minted for a replacement actor"] call _check;
        [(missionNamespace getVariable "ACME_bf_activeGrants") isEqualTo []
            && {((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0},"orphaned fridge grant retained idle polling or silently refunded stock"] call _check;
    '''+'private _parkedScans=0;ACME_fnc_bloodFridgeTick={'+tick+'};'+r'''
        private _queriesBefore=count _resourceQueries;
        for "_i" from 1 to 10 do {call ACME_fnc_bloodFridgeTick;};
        [_parkedScans==0 && {count _resourcePackets==0} && {count _resourceQueries==_queriesBefore}
            && {((call _journal) select 3) isEqualTo [["item","ON"]]},"parked orphan was scanned/resubmitted or lost canonical funding"] call _check;
    ''')
