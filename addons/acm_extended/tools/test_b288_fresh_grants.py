"""Execute funded fresh donor grants with independent captured-machine decisions.

Native inventory/readback, transport and owner IDs are fixture boundaries. This
does not certify native Arma packet ordering or dedicated-server persistence.
"""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute
from test_historical_vial_execution import map_defaults
from test_historical_medication_rows import iteration_scopes


def source(name):
    text=(ROOT/f'addons/circulation/functions/fnc_{name}.sqf').read_text()
    for old,new in {
        'canSuspend':'false','clientOwner':'_machineOwner','local _medic':'_medicLocal',
        'owner _recipient':'_ownerNum',
        'uniformItems _medic':'(_medic getVariable ["nativeItems",[]])',
        'vestItems _medic':'[]','backpackItems _medic':'[]',
        'nearestObject [_medic,"WeaponHolder"]':'_ground',
        'itemCargo _near':'(_near getVariable ["nativeItems",[]])',
        'itemCargo _holder':'(_holder getVariable ["nativeItems",[]])',
        '(_result select 1) isEqualType objNull':'true',
        '_medic isEqualType objNull':'(_medic isEqualType profileNamespace || {_medic isEqualTo objNull})',
        '_donor isEqualType objNull':'(_donor isEqualType profileNamespace || {_donor isEqualTo objNull})',
    }.items():text=text.replace(old,new)
    text=re.sub(r'\bfinite (\([^\n]*?\)|_\w+)',r'(\1 call _finite)',text)
    return adapt(map_defaults(iteration_scopes(text)),'circulation')


def fixture():
    code=r'''
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _finite={_this isEqualType 0};
        private _machineOwner=7;private _medicLocal=true;
        private _ground=parsingNamespace;
        private _giveWorks=true;private _giveGround=false;private _fixtureUnknown=false;
        private _nativeAdds=[];private _packets=[];private _queries=[];private _serverMessages=[];
        private _typeReads=0;
        _medic setVariable ["nativeItems",[]];_ground setVariable ["nativeItems",[]];
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","nonce-A"];
        missionNamespace setVariable ["ACME_syringeDeliveryMachines",createHashMapFromArray [["7","nonce-A"],["8","nonce-B"]]];
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMap];
        ACM_circulation_fnc_generateBloodType={_typeReads=_typeReads+1;0};
        ACM_circulation_fnc_formatFluidBagName={format ["ACM_FreshBloodBag_%1",_this select 1]};
        ace_common_fnc_addToInventory={
            _nativeAdds pushBack _this;
            if (_fixtureUnknown) exitWith {nil};
            private _destination=if (_giveGround) then {_ground} else {_medic};
            if (_giveWorks) then {private _items=+(_destination getVariable ["nativeItems",[]]);_items pushBack (_this select 1);_destination setVariable ["nativeItems",_items];};
            [!_giveGround,_destination]
        };
        CBA_fnc_targetEvent={if ((_this select 0)=="ACM_circulation_receiveFreshBloodBag") then {_packets pushBack (_this select 1)};};
        CBA_fnc_ownerEvent={_queries pushBack (_this select 1)};
        CBA_fnc_globalEvent={};CBA_fnc_localEvent={};
        CBA_fnc_serverEvent={_serverMessages pushBack _this};
        CBA_missionTime=100;
        private _facts=["freshV1",true,70,2];
        private _request="fresh-request-one";
        private _args=[_medic,_patient,500,_request,_facts];
        private _fund={private _funded=createHashMap;_funded set [_request,[_medic,500,+_facts]];_patient setVariable ["ACME_txRemoveFunded",_funded];};
        private _journal={(missionNamespace getVariable "ACM_circulation_FreshBloodGrants") get _request};
        private _flushServer={while {count _serverMessages>0} do {private _m=_serverMessages deleteAt 0;[if ((_m select 0)=="ACM_circulation_freshBloodGrantAck") then {"ack"} else {"decision"},_m select 1] call ACM_circulation_fnc_freshBloodGrant;};};
    '''
    for name in ['generateFreshBloodEntry','freshBloodGrant','receiveFreshBloodBag','freshBloodGrantQuery']:
        code+='ACM_circulation_fnc_'+name+'={'+source(name)+'};'
    code+='ACME_fnc_syringeDeliveryCopy={'+adapt((ROOT/'addons/acm_extended/functions/fn_syringeDeliveryCopy.sqf').read_text())+'};'
    return code


def test_funded_request_replay_allocates_and_delivers_one_immutable_donor_product():
    execute(fixture()+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        ["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        private _packet=+(_packets select 0);
        _packet call ACM_circulation_fnc_receiveFreshBloodBag;call _flushServer;
        _packet call ACM_circulation_fnc_receiveFreshBloodBag;call _flushServer;
        [(count (missionNamespace getVariable "ACM_circulation_FreshBloodList"))==1 && {count _nativeAdds==1},"replay allocated or placed duplicate blood"] call _check;
        [((call _journal) select 5)=="delivered" && {count (_medic getVariable "ACM_circulation_freshBloodPending")==0},"delivery did not settle exact journal"] call _check;
        [_typeReads==0 && {((call _journal) select 7 select [2,3]) isEqualTo [2,true,70]},"late allocation resampled donor clinical facts"] call _check;
    ''')


def test_request_overtaking_source_proof_waits_without_allocating_then_uses_original_facts():
    execute(fixture()+r'''
        ["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        [count (missionNamespace getVariable ["ACM_circulation_FreshBloodGrants",createHashMap])==0 && {count _packets==0},"unfunded request exposed a native product or authoritative journal"] call _check;
        call _fund;CBA_missionTime=400;["tick",[]] call ACM_circulation_fnc_freshBloodGrant;
        [count _packets==1 && {((call _journal) select 7 select 4)==70},"proof retry lost frozen collection timestamp"] call _check;
    ''')


def test_changed_duplicate_cannot_rebind_donor_volume_or_facts():
    execute(fixture()+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        private _before=str (call _journal);
        private _changed=+_args;_changed set [2,250];_changed set [4,["freshV1",false,99,0]];
        ["request",_changed] call ACM_circulation_fnc_freshBloodGrant;
        [str (call _journal)==_before && {count _packets==1},"changed replay replaced original donor grant"] call _check;
    ''')


@pytest.mark.parametrize('ground',[False,True])
def test_known_failed_placement_retries_one_funding_and_never_uses_a_second_ground_fallback(ground):
    execute(fixture()+f'_giveGround={str(ground).lower()};'+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        private _packet=+(_packets select 0);_giveWorks=false;
        _packet call ACM_circulation_fnc_receiveFreshBloodBag;
        [count _serverMessages==0,"failed readback acknowledged donor delivery"] call _check;
        _giveWorks=true;_packet call ACM_circulation_fnc_receiveFreshBloodBag;call _flushServer;
        [count (_medic getVariable "nativeItems")+count (_ground getVariable "nativeItems")==1,"placement retry duplicated or lost donor blood"] call _check;
        [((call _journal) select 5)=="delivered","verified native retry did not finish"] call _check;
    ''')


def test_exhausted_native_id_space_keeps_full_donor_bag_as_savable_virtual_product():
    execute(fixture()+r'''
        private _registry=createHashMap;for "_i" from 1 to 512 do {_registry set [_i,[objNull,500,0,true,0]];};
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",_registry];
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        private _packet=+(_packets select 0);_packet call ACM_circulation_fnc_receiveFreshBloodBag;call _flushServer;
        _packet call ACM_circulation_fnc_receiveFreshBloodBag;
        private _used=_medic getVariable "ACME_usedBags";
        [count _used==1 && {(_used select 0 select [1,5]) isEqualTo ["FreshBlood",500,0,2,500]},"ID exhaustion lost volume or created duplicate virtual product"] call _check;
        [(_used select 0 select 8) isEqualTo _facts && {((call _journal) select 5)=="delivered"} && {count _nativeAdds==0},"exhaustion discarded donor identity or reused native ID"] call _check;
    ''')


def test_uncertain_placement_holds_exact_product_and_never_retries_side_effect():
    execute(fixture()+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        private _packet=+(_packets select 0);_fixtureUnknown=true;
        _packet call ACM_circulation_fnc_receiveFreshBloodBag;
        _packet call ACM_circulation_fnc_receiveFreshBloodBag;
        [count _nativeAdds==1 && {count _serverMessages==0} && {((call _journal) select 5)=="ready"},"unknown placement was reminted or forgiven"] call _check;
    ''')


def test_original_machine_proof_settles_after_provider_migration_without_another_item():
    execute(fixture()+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        private _packet=+(_packets select 0);_packet call ACM_circulation_fnc_receiveFreshBloodBag;
        _serverMessages=[];_medic setVariable ["ACM_circulation_freshBloodReceived",createHashMap];
        _ownerNum=8;_medicLocal=false;CBA_missionTime=103;
        ["tick",[]] call ACM_circulation_fnc_freshBloodGrant;
        [count _queries==1 && {count _packets==1},"migration dispatched another native write without original outcome"] call _check;
        (_queries select 0) call ACM_circulation_fnc_freshBloodGrantQuery;call _flushServer;
        [((call _journal) select 5)=="delivered" && {count _nativeAdds==1},"captured private decision failed to settle"] call _check;
    ''')


def test_query_cancels_unseen_attempt_before_reassignment_and_blocks_late_aba_packet():
    execute(fixture()+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        private _oldPacket=+(_packets select 0);
        _ownerNum=8;_medicLocal=false;CBA_missionTime=103;["tick",[]] call ACM_circulation_fnc_freshBloodGrant;
        (_queries select 0) call ACM_circulation_fnc_freshBloodGrantQuery;call _flushServer;
        [((call _journal) select 13)==2 && {!((call _journal) select 12)},"unseen attempt did not leave replay fence before reassignment"] call _check;
        private _oldDecisions=missionNamespace getVariable "ACM_circulation_FreshBloodGrantDecisions";
        _machineOwner=8;_medicLocal=true;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","nonce-B"];
        missionNamespace setVariable ["ACM_circulation_FreshBloodGrantDecisions",createHashMap];
        CBA_missionTime=106;["tick",[]] call ACM_circulation_fnc_freshBloodGrant;
        (_packets select 1) call ACM_circulation_fnc_receiveFreshBloodBag;call _flushServer;
        _machineOwner=7;_ownerNum=7;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","nonce-A"];
        missionNamespace setVariable ["ACM_circulation_FreshBloodGrantDecisions",_oldDecisions];
        _medic setVariable ["ACM_circulation_freshBloodReceived",createHashMap];
        _oldPacket call ACM_circulation_fnc_receiveFreshBloodBag;
        [count _nativeAdds==1 && {((call _journal) select 6)==1},"late ABA packet reminted product or allocated a second donor ID"] call _check;
    ''')


def test_reused_owner_address_new_incarnation_cannot_cancel_old_unknown_delivery():
    execute(fixture()+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        _ownerNum=8;CBA_missionTime=103;["tick",[]] call ACM_circulation_fnc_freshBloodGrant;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","new-connection"];
        (_queries select 0) call ACM_circulation_fnc_freshBloodGrantQuery;
        [count _serverMessages==0 && {((call _journal) select 13)==1},"reused routing address denied original machine grant"] call _check;
    ''')


def test_unfunded_hints_are_bounded_expire_and_cannot_abort_a_checkpoint():
    execute(fixture()+r'''
        _medic setVariable ["ACME_persistenceFrozen",true];
        _patient setVariable ["ACME_persistenceFrozen",true];
        for "_i" from 1 to 150 do {
            private _wire=+_args;_wire set [3,format ["unknown-%1",_i]];
            ["request",_wire] call ACM_circulation_fnc_freshBloodGrant;
        };
        [count (missionNamespace getVariable "ACM_circulation_FreshBloodGrantWaiters")==128,"unfunded hints exceeded bounded admission memory"] call _check;
        [count (missionNamespace getVariable ["ACM_circulation_FreshBloodGrants",createHashMap])==0
            && {count (_medic getVariable ["ACM_circulation_freshBloodPending",createHashMap])==0}
            && {_medic getVariable "ACME_persistenceFrozen"} && {_patient getVariable "ACME_persistenceFrozen"},"unproven request acquired custody or cancelled a save"] call _check;
        CBA_missionTime=131;["tick",[]] call ACM_circulation_fnc_freshBloodGrant;
        [count (missionNamespace getVariable "ACM_circulation_FreshBloodGrantWaiters")==0
            && {(missionNamespace getVariable "ACM_circulation_FreshBloodGrantPFH")==-1},"expired unfunded hints retained recurring server work"] call _check;
    ''')


def test_positive_public_donor_receipt_survives_lost_ack_and_missing_original_process():
    execute(fixture()+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        (_packets select 0) call ACM_circulation_fnc_receiveFreshBloodBag;
        _serverMessages=[];_ownerNum=8;_machineOwner=8;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","nonce-B"];
        missionNamespace setVariable ["ACM_circulation_FreshBloodGrantDecisions",createHashMap];
        CBA_missionTime=103;["tick",[]] call ACM_circulation_fnc_freshBloodGrant;
        [((call _journal) select 5)=="delivered" && {count _nativeAdds==1},"positive donor receipt waited forever or reminted for a new owner"] call _check;
    ''')


@pytest.mark.parametrize('blood_type',[8,15,-1,2.5])
def test_invalid_native_blood_code_never_creates_a_grant_or_registry_entry(blood_type):
    execute(fixture()+f'_facts set [3,{blood_type}];'+r'''
        call _fund;["request",_args] call ACM_circulation_fnc_freshBloodGrant;
        [count _packets==0 && {count (missionNamespace getVariable "ACM_circulation_FreshBloodList")==0},"unsupported blood code created donor inventory"] call _check;
    ''')
