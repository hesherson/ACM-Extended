"""Execute the checked-out vial lease and volume code with engine boundaries mocked.

Object/inventory/config/transport/UI operations are stand-ins. SQF scopes,
request timing, acknowledgement matching and ledger arithmetic are production
code. These tests do not simulate real network delivery or inventory replication.
"""
from pathlib import Path
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute

F = ROOT / 'addons/acm_extended/functions'


def source(name):
    return (F / ('fn_' + name + '.sqf')).read_text()


def map_defaults(text):
    """Only replace unsupported HASHMAP getOrDefault, retaining real maps/keys/set/get."""
    ts=lex(text); pairs=matching(ts); reverse={v:k for k,v in pairs.items()}
    edits=[]
    for i,t in enumerate(ts):
        if t.kind!='ident' or t.value!='getOrDefault':continue
        assert ts[i+1].value=='[' and i+1 in pairs
        end=pairs[i+1]; start=i-1
        if ts[start].value in (')',']'):start=reverse[start]
        left=text[ts[start].offset:t.offset].strip()
        right=text[ts[i+1].offset:ts[end].offset+1]
        edits.append((ts[start].offset,ts[end].offset+1,'(['+left+','+right+'] call _mapDefault)'))
    for start,end,new in reversed(edits):text=text[:start]+new+text[end:]
    return text


def code(text):
    for old,new in {
        'hasInterface':'_interface', 'serverTime':'_serverTime',
        'isNull ACE_player':'(ACE_player isEqualTo objNull)',
        'local _medic':'_medicLocal', 'local _holder':'_holderLocal',
        'alive _holder':'_holderAlive', 'alive _leaseMedic':'_leaseMedicAlive',
        'objectParent _medic':'_medicVehicle', 'objectParent _holder':'_holderVehicle',
        '_medic distance _holder':'_distance', 'netId _holder':'"holder"',
        '_holder isKindOf "CAManBase"':'_holderPerson',
        'findDisplay 84000':'_drawDisplay',
    }.items():text=text.replace(old,new)
    # Only finite numeric inputs are supplied in this module.
    text=re.sub(r'\bfinite (_\w+)',r'(\1 call _finite)',text)
    text=text.replace('finite (_x select 1)','((_x select 1) call _finite)')
    # This VM retains an explicitly nil namespace slot after setVariable. Arma
    # removes it; preserve getVariable's default after a source lease release.
    text=text.replace('_holder getVariable ["ACME_vialLease",[objNull,"",0]]',
                      '([_holder,"ACME_vialLease",[objNull,"",0]] call _namespaceDefault)')
    text=text.replace('_holder removeItem _consumeClass;', '[_holder,_consumeClass] call _removeItem;')
    text=text.replace('_holder addItemCargoGlobal [_consumeClass, -1];','[_holder,_consumeClass] call _removeItem;')
    text=re.sub(r'configFile >> "ACM_Medication" >> "Concentration" >> (_\w+)',r'\1',text)
    text=text.replace('getNumber (_cfg >> "volume")','([_cfg,"volume"] call _configNumber)')
    text=text.replace('getNumber (_cfg >> "concentration")','([_cfg,"concentration"] call _configNumber)')
    return adapt(map_defaults(text))


def function(name):return 'ACME_fnc_'+name+'={'+code(source(name))+'};\n'


def setup():
    return '''
        private _interface=true; private _serverTime=10;
        private _holderLocal=true; private _medicLocal=true;
        private _holderAlive=true; private _leaseMedicAlive=true;
        private _holderPerson=true; private _drawDisplay=objNull;
        private _medicVehicle=objNull; private _holderVehicle=objNull;
        private _inventoryCounts=createHashMapFromArray [["ACM_Vial_Ketamine",2]];
        private _stockWrites=0; private _inventoryDebits=0;
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _mapDefault={params ["_map","_args"]; _args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _namespaceDefault={params ["_space","_key","_default"]; private _value=_space getVariable _key;
            if (isNil "_value") then {_default} else {_value}};
        private _configNumber={params ["_med","_field"]; if (_med=="Ketamine") then {if (_field=="volume") then {10} else {50}} else {0}};
        private _removeItem={params ["_holder","_item"]; _inventoryCounts set [_item,(_inventoryCounts get _item)-1]; _inventoryDebits=_inventoryDebits+1;};
        ACME_fnc_vialCapacity={[_this select 0,"volume"] call _configNumber};
        ACME_fnc_vialItemCount={[_inventoryCounts,[_this select 1,0]] call _mapDefault};
        ACME_fnc_openVialStoreCommit={params ["_h","_map"]; _h setVariable ["ACME_infusion_openVials",_map]; _stockWrites=_stockWrites+1;};
        ACME_fnc_ownerDispatch={_events pushBack _this;};
        _patient setVariable ["ACME_infusion_openVials",createHashMap];
        _medic setVariable ["ACME_infusion_openVials",createHashMap];
    ''' + ''.join(function(n) for n in ('vialClass','infusionVialVolume','vialTake','vialRefund','vialRefundLocal','vialLeaseEnsure','vialLeaseResult','vialLeaseCommit','vialLeaseRelease'))


@pytest.mark.parametrize('refresh',[0.0,0.016,0.2,1.49])
def test_pending_lease_waits_for_ack_without_replacing_token_or_spamming_claims(refresh):
    execute(setup()+'''
        [!([_medic,_patient] call ACME_fnc_vialLeaseEnsure),"unacknowledged holder accepted"] call _check;
        private _pending=+(missionNamespace getVariable ["ACME_vialLeasePending",[]]);
    '''+f'_nowTime=10+{refresh};'+'''
        [!([_medic,_patient] call ACME_fnc_vialLeaseEnsure),"pending holder accepted"] call _check;
        [count _events==1,"pending refresh sent another claim"] call _check;
        [(missionNamespace getVariable ["ACME_vialLeasePending",[]]) isEqualTo _pending,"pending token was replaced"] call _check;
        [_patient,_pending select 1,true,14,""] call ACME_fnc_vialLeaseResult;
        [[_medic,_patient] call ACME_fnc_vialLeaseEnsure,"valid acknowledgement did not unlock source"] call _check;
        [count _events==1,"acknowledgement immediately caused another claim"] call _check;
    ''')


@pytest.mark.parametrize('operation',['vialTake','vialRefund'])
@pytest.mark.parametrize('lease',['[]','[_patient,"",14]','[_patient,"token",10]','[_medic,"token",14]'])
def test_unleased_shared_source_cannot_be_debited_or_refunded(operation,lease):
    execute(setup()+f'missionNamespace setVariable ["ACME_vialLeaseAccepted",{lease}];'+
        f'private _okResult=[_patient,"Ketamine",2] call ACME_fnc_{operation};'+'''
        [!_okResult,"unleased mutation accepted"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"unleased mutation changed inventory"] call _check;
    ''')


@pytest.mark.parametrize('person',[True,False])
@pytest.mark.parametrize('holder_alive',[True,False])
def test_valid_shared_lease_allows_exact_debit_and_refund_for_people_and_vehicle_inventory(person,holder_alive):
    execute(setup()+f'_holderPerson={str(person).lower()}; _holderAlive={str(holder_alive).lower()};'+'''
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[_patient,"token",14]];
        private _start=[_patient,"Ketamine"] call ACME_fnc_infusionVialVolume;
        [[_patient,"Ketamine",2] call ACME_fnc_vialTake,"valid shared draw rejected"] call _check;
        private _after=[_patient,"Ketamine"] call ACME_fnc_infusionVialVolume;
        [_inventoryDebits==1 && {abs (_start-_after-2)<0.000001},"draw created or lost solution"] call _check;
        [[_patient,"Ketamine",2] call ACME_fnc_vialRefund,"valid shared refund rejected"] call _check;
        [abs (([_patient,"Ketamine"] call ACME_fnc_infusionVialVolume)-_start)<0.000001,"refund changed total solution"] call _check;
        [_inventoryDebits==1,"refund fabricated sealed vial"] call _check;
    ''')


@pytest.mark.parametrize('operation',['vialTake','vialRefund'])
def test_original_provider_self_inventory_stays_valid_after_control_switch(operation):
    execute(setup()+'''
        ACE_player=_patient;
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[]];
    '''+f'private _result=[_medic,"Ketamine",2,_medic] call ACME_fnc_{operation};'+'''
        [_result,"original provider self transaction treated as an unleased foreign inventory"] call _check;
        [_stockWrites==1,"original provider transaction lost"] call _check;
    ''')


def test_pending_timeout_releases_old_claim_and_rejects_its_late_ack():
    execute(setup()+'''
        [_medic,_patient] call ACME_fnc_vialLeaseEnsure;
        private _first=+(missionNamespace getVariable ["ACME_vialLeasePending",[]]);
        _nowTime=11.5;
        [_medic,_patient] call ACME_fnc_vialLeaseEnsure;
        private _second=+(missionNamespace getVariable ["ACME_vialLeasePending",[]]);
        [count _events==3,"timed-out claim not replaced with release then claim"] call _check;
        [(((_events select 1) select 2) select 1)=="release","old claim not released"] call _check;
        [_patient,_first select 1,true,14,""] call ACME_fnc_vialLeaseResult;
        [(missionNamespace getVariable ["ACME_vialLeaseAccepted",[]]) isEqualTo [],"stale acknowledgement acquired source"] call _check;
        [_patient,_second select 1,true,15.5,""] call ACME_fnc_vialLeaseResult;
        [[_medic,_patient] call ACME_fnc_vialLeaseEnsure,"current acknowledgement rejected"] call _check;
    ''')


def test_lease_renewal_uses_same_token_and_bounded_cadence():
    execute(setup()+'''
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[_patient,"accepted",14]];
        missionNamespace setVariable ["ACME_vialLeaseRenewAt",11.5];
        [[_medic,_patient] call ACME_fnc_vialLeaseEnsure,"active lease lost"] call _check;
        [count _events==0,"premature renewal"] call _check;
        _nowTime=11.5; _serverTime=11.5;
        [[_medic,_patient] call ACME_fnc_vialLeaseEnsure,"renewal blocked valid lease"] call _check;
        [_patient,"accepted",true,15.5,""] call ACME_fnc_vialLeaseResult;
        _nowTime=11.6;
        [[_medic,_patient] call ACME_fnc_vialLeaseEnsure,"renewed lease lost"] call _check;
        [count _events==1 && {(((_events select 0) select 2) select 2)=="accepted"},"renewal replaced token or flooded"] call _check;
    ''')


def test_release_clears_local_pending_and_late_ack_cannot_reopen_it():
    execute(setup()+'''
        [_medic,_patient] call ACME_fnc_vialLeaseEnsure;
        private _pending=+(missionNamespace getVariable ["ACME_vialLeasePending",[]]);
        [_medic] call ACME_fnc_vialLeaseRelease;
        [_patient,_pending select 1,true,14,""] call ACME_fnc_vialLeaseResult;
        [(missionNamespace getVariable ["ACME_vialLeaseAccepted",[]]) isEqualTo [],"late reply reopened closed source"] call _check;
        [(missionNamespace getVariable ["ACME_vialLeasePending",[]]) isEqualTo [],"release retained pending"] call _check;
    ''')


def test_owner_rejects_competing_provider_and_stale_release_cannot_clear_winner():
    execute(setup()+'''
        [_patient,_medic,"claim","first"] call ACME_fnc_vialLeaseCommit;
        [_patient,missionNamespace,"claim","second"] call ACME_fnc_vialLeaseCommit;
        private _lease=_patient getVariable ["ACME_vialLease",[]];
        [(_lease select 1)=="first","second provider stole live lease"] call _check;
        [_patient,missionNamespace,"release","second"] call ACME_fnc_vialLeaseCommit;
        [(_patient getVariable ["ACME_vialLease",[]]) isEqualTo _lease,"stale release removed live lease"] call _check;
        _serverTime=14;
        [_patient,missionNamespace,"claim","second"] call ACME_fnc_vialLeaseCommit;
        [((_patient getVariable ["ACME_vialLease",[]]) select 1)=="second","expired lease could not be acquired"] call _check;
        [_patient,_medic,"release","first"] call ACME_fnc_vialLeaseCommit;
        [((_patient getVariable ["ACME_vialLease",[]]) select 1)=="second","late original release removed new lease"] call _check;
    ''')


@pytest.mark.parametrize('millilitres',[-1,0,21])
def test_invalid_or_unfunded_draw_cannot_change_either_ledger_or_physical_vials(millilitres):
    execute(setup()+f'private _result=[_medic,"Ketamine",{millilitres}] call ACME_fnc_vialTake;'+'''
        [!_result && {_inventoryDebits==0} && {_stockWrites==0},"invalid draw consumed source"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==20,"invalid draw changed stock"] call _check;
    ''')


def test_partial_vial_is_used_first_and_explicit_multivial_transaction_conserves_solution():
    execute(setup()+'''
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",2.5]]];
        [[_medic,"Ketamine",1] call ACME_fnc_vialTake,"partial draw failed"] call _check;
        [_inventoryDebits==0 && {([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==21.5},"partial vial not used first"] call _check;
        [[_medic,"Ketamine",15] call ACME_fnc_vialTake,"funded multi-vial transaction failed"] call _check;
        [_inventoryDebits==2 && {abs (([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)-6.5)<0.000001},"multi-vial volume not conserved"] call _check;
        [[_medic,"Ketamine",15] call ACME_fnc_vialRefund,"multi-vial rollback failed"] call _check;
        [abs (([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)-21.5)<0.000001,"refund volume wrong"] call _check;
        [_inventoryDebits==2,"rollback created a sealed vial"] call _check;
    ''')


def session_setup():
    return setup()+function('vialSession')+'''
        private _display=missionNamespace;
        _drawDisplay=_display;
        ACME_fnc_vialHolder={_medic};
    '''


def test_partial_vial_precedes_sealed_and_next_vial_needs_deliberate_selection():
    execute(session_setup()+'''
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",2.5]]];
        private _first=["limit","Ketamine",0,_display] call ACME_fnc_vialSession;
        [_first==2.5,"initial binding skipped opened vial"] call _check;
        private _early=["select","Ketamine",1,_display] call ACME_fnc_vialSession;
        [_early==2.5,"early click unlocked extra stock"] call _check;
        private _exhausted=["preview","Ketamine",2.5,_display] call ACME_fnc_vialSession;
        [(_exhausted select 0)==0 && {(_exhausted select 3)==2.5},"preview rolled over automatically"] call _check;
        private _next=["select","Ketamine",2.5,_display] call ACME_fnc_vialSession;
        [_next==12.5,"explicit click failed to unlock exactly one vial"] call _check;
        [_inventoryDebits==0 && {_stockWrites==0},"UI session consumed source before commit"] call _check;
    ''')


def test_repeated_limit_and_preview_never_unlock_another_vial():
    execute(session_setup()+'''
        for "_i" from 1 to 20 do {
            private _limit=["limit","Ketamine",10,_display] call ACME_fnc_vialSession;
            private _preview=["preview","Ketamine",10,_display] call ACME_fnc_vialSession;
            [_limit==10 && {(_preview select 0)==0} && {(_preview select 3)==10},"read-only refresh advanced the vial"] call _check;
        };
        private _next=["select","Ketamine",10,_display] call ACME_fnc_vialSession;
        [_next==20,"deliberate second selection failed"] call _check;
        [(["select","Ketamine",20,_display] call ACME_fnc_vialSession)==20,"selection invented third vial"] call _check;
    ''')


def test_session_missing_or_unacknowledged_holder_exposes_no_usable_volume():
    execute(session_setup()+'''
        ACME_fnc_vialHolder={objNull};
        [(["limit","Ketamine",0,_display] call ACME_fnc_vialSession)==0,"missing holder exposes volume"] call _check;
        [(["preview","Ketamine",0,_display] call ACME_fnc_vialSession) isEqualTo [0,0,0,0],"missing holder exposes a vial"] call _check;
        [_inventoryDebits==0 && {_stockWrites==0},"missing-holder read wrote inventory"] call _check;
    ''')


def test_existing_micro_residual_policy_is_unchanged_and_does_not_create_solution():
    execute(setup()+'''
        [[_medic,"Ketamine",9.99] call ACME_fnc_vialTake,"endpoint draw failed"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==10,"discardable residual policy changed"] call _check;
        [_inventoryDebits==1,"endpoint consumed another vial"] call _check;
    ''')
