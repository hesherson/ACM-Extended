"""Execute donor persistence and canonical bag flow; native time/codec are boundaries."""
import re

import pytest

from test_menu_death_lifecycle import F, ROOT, adapt, execute
from test_historical_vial_execution import map_defaults
from test_b275_piggyback import delivery_setup, native_bag_worker
from test_historical_medication_rows import iteration_scopes
from test_b230_prepared_infusion_transaction import setup as native_setup


def source(name):
    text = (F / f'fn_{name}.sqf').read_text()
    text = re.sub(r'\bfinite (\([^\n]*?\)|_\w+)', r'(\1 call _finite)', text)
    text = text.replace('values _grants', '(keys _grants apply {_grants get _x})')
    return adapt(map_defaults(iteration_scopes(text)))


def setup():
    return r'''
    private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    CBA_missionTime=7200;
    ACME_fnc_clinicalCodec={params ["_v",["_encode",true]];if (_encode) then {["O","donor","old-session",""]} else {objNull}};
    ACME_fnc_clinicalEncodedValid={params ["_v"];_v isEqualType [] && {count _v in [2,4]} && {(_v select 0)=="O"}};
    ACM_circulation_fnc_getFreshBloodEntry={params ["_id"];private _registry=missionNamespace getVariable ["ACM_circulation_FreshBloodList",createHashMap];if (_id in _registry) then {_registry get _id} else {[]}};
    missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[3,[objNull,500,0,true,3600]]]];
    ''' + 'ACM_circulation_fnc_restoreFreshBloodRegistry={' + adapt((ROOT / 'addons/circulation/functions/fnc_restoreFreshBloodRegistry.sqf').read_text(), 'circulation') + '};' + '\n'.join('ACME_fnc_'+n+'={'+source(n)+'};' for n in [
        'freshBloodResolve','freshBloodSnapshotValid','freshBloodSnapshot','freshBloodRestore'])


def test_registry_restart_preserves_id_donor_age_and_offline_policy():
    execute(setup()+r'''
    private _saved=[] call ACME_fnc_freshBloodSnapshot;
    [_saved isEqualTo [1,[[3,["O","donor","old-session",""],500,0,true,3600]]],"bad portable donor snapshot"] call _check;
    missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[0,[objNull,250,0,true,0]]]];
    CBA_missionTime=12;
    [[_saved,100] call ACME_fnc_freshBloodRestore,"startup restore failed"] call _check;
    private _row=[3] call ACM_circulation_fnc_getFreshBloodEntry;
    [(_row select 4)==-3688 && {(_row select 3)} && {(_row select 2)==0},"restart refreshed donor age/type/alive"] call _check;
    CBA_missionTime=30;
    [[_saved,100] call ACME_fnc_freshBloodRestore,"idempotent replay refused"] call _check;
    [(([3] call ACM_circulation_fnc_getFreshBloodEntry) select 4)==-3688,"replay reset freshness clock"] call _check;
    ''')


def test_conflicting_live_registry_is_never_overwritten():
    execute(setup()+r'''
    private _saved=[] call ACME_fnc_freshBloodSnapshot;
    private _before=str (missionNamespace getVariable "ACM_circulation_FreshBloodList");
    [!([_saved] call ACME_fnc_freshBloodRestore),"live donor ID overwritten"] call _check;
    [str (missionNamespace getVariable "ACM_circulation_FreshBloodList")==_before,"rejected restore mutated registry"] call _check;
    ''')


def test_registry_save_refuses_pending_or_uncertain_funded_donor_product():
    execute(setup()+r'''
    private _grant=[_medic,_patient,500,"request",[],"pending"];
    missionNamespace setVariable ["ACM_circulation_FreshBloodGrants",createHashMapFromArray [["request",_grant]]];
    [([] call ACME_fnc_freshBloodSnapshot) isEqualTo [],"snapshot omitted a funded donor product"] call _check;
    _grant set [5,"uncertain"];
    [([] call ACME_fnc_freshBloodSnapshot) isEqualTo [],"snapshot treated uncertain delivery as settled"] call _check;
    _grant set [5,"delivered"];
    [([] call ACME_fnc_freshBloodSnapshot) isNotEqualTo [],"settled product blocked registry export"] call _check;
    ''')


def test_registry_import_refuses_inflight_grant_even_before_a_donor_id_exists():
    execute(setup()+r'''
    private _saved=[] call ACME_fnc_freshBloodSnapshot;
    missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMap];
    missionNamespace setVariable ["ACM_circulation_FreshBloodGrants",createHashMapFromArray [["request",[_medic,_patient,500,"request",[],"awaitProof"]]]];
    [!([_saved] call ACME_fnc_freshBloodRestore),"startup import overwrote registry during grant admission"] call _check;
    [count (missionNamespace getVariable "ACM_circulation_FreshBloodList")==0,"refused import published saved donors"] call _check;
    ''')


@pytest.mark.parametrize('bad',[
    '[]','nil','[1,nil]','[nil,[]]','[2,[]]','[1,[[513,["O",""],500,0,true,0]]]','[1,[[3,["O",""],500,0,true,-1]]]',
    '[1,[[3,["O",""],500,0,true,0],[3,["O",""],250,0,false,0]]]',
    '[1,[[3,["V",1],500,0,true,0]]]','[1,[[3,["O",""],500,0,1,0]]]',
    '[1,[[3,["O",""],-1,0,true,0]]]','[1,[[3,["O",""],500,0,true,nil]]]',
    '[1,[[3,["O",""],500,8,true,0]]]',
])
def test_malformed_registry_snapshot_rejected_before_mutation(bad):
    execute(setup()+f'private _bad={bad};'+r'''
    private _before=str (missionNamespace getVariable "ACM_circulation_FreshBloodList");
    [!([_bad] call ACME_fnc_freshBloodSnapshotValid),"bad snapshot accepted"] call _check;
    [!([_bad] call ACME_fnc_freshBloodRestore),"bad import accepted"] call _check;
    [str (missionNamespace getVariable "ACM_circulation_FreshBloodList")==_before,"malformed import changed registry"] call _check;
    ''')


@pytest.mark.parametrize('marker',['["freshMissingV1"]','["freshV1",true,"bad",0]','["freshAgeV1",true,300,0]'])
def test_fenced_bag_never_falls_back_to_reused_registry_id(marker):
    execute(setup()+f'private _marker={marker};'+r'''
    [([3,_marker] call ACME_fnc_freshBloodResolve) isEqualTo [],"stale metadata fell back to unrelated donor"] call _check;
    ''')


def test_inline_freshness_wins_over_reused_native_id():
    execute(setup()+r'''
    private _row=[3,["freshV1",false,-100,2]] call ACME_fnc_freshBloodResolve;
    [_row isEqualTo [objNull,0,2,false,-100],"inline donor metadata replaced by live donor registry"] call _check;
    ''')


def test_canonical_flow_holds_unknown_fresh_bag_and_preserves_capacity_tail():
    execute(delivery_setup(group=False,kind="FreshBlood")+setup()+native_bag_worker()+r'''
    private _map=_patient getVariable "ACM_circulation_IV_Bags";
    _map set ["leftarm",[["FreshBlood",300,1,0,true,0,500,3,"primary",500,["freshMissingV1"]]]];
    private _before=str (_map get "leftarm");
    private _result=call _integrate;
    [str (_result select 0)==_before,"unknown fresh bag drained or lost metadata"] call _check;
    [(_result select 4)==0,"unknown fresh bag credited blood"] call _check;
    ''')


def test_canonical_flow_preserves_manufacturer_capacity_on_running_bag():
    execute(delivery_setup(group=False,kind="Saline")+native_bag_worker()+r'''
    private _map=_patient getVariable "ACM_circulation_IV_Bags";
    _map set ["leftarm",[["Saline",300,1,0,true,-1,500,-1,"primary",500]]];
    private _result=call _integrate;
    private _row=(_result select 0) select 0;
    [(_row select 1)<300 && {(_row select 9)==500},"flow lost capacity extension"] call _check;
    ''')


def test_donor_type_mismatch_fails_closed():
    execute(setup()+r'''
    [([3,["freshV1",true,7000,2],0] call ACME_fnc_freshBloodResolve) isEqualTo [],"bag/donor blood type mismatch accepted"] call _check;
    ''')


@pytest.mark.parametrize('code',['-1','8','2.5'])
def test_out_of_native_range_donor_facts_fail_closed(code):
    execute(setup()+f'private _code={code};'+r'''
    [([-1,["freshV1",true,7000,_code]] call ACME_fnc_freshBloodResolve) isEqualTo [],"unsafe donor blood type accepted"] call _check;
    ''')


def test_native_factory_prefers_saved_provenance_to_reused_numeric_donor():
    execute(native_setup()+setup()+r'''
    private _uid=[_patient,"leftarm","FreshBloodBag_500_3",1,true,0,true,false,[],["freshV1",true,-100,2]] call _nativeCarrier;
    private _bag=((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") select 0;
    [_uid!="" && {(_bag select 5)==2} && {(_bag select 9)==500} && {(_bag select 10) isEqualTo ["freshV1",true,-100,2]},"native factory rebound saved donor or dropped capacity/provenance"] call _check;
    [(([3] call ACM_circulation_fnc_getFreshBloodEntry) select 2)==0,"portable donor overwrote another live registry record"] call _check;
    ''')


def test_native_factory_rejects_missing_provenance_without_attaching_or_reaction():
    execute(native_setup()+setup()+r'''
    private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
    private _uid=[_patient,"leftarm","FreshBloodBag_500_3",1,true,0,true,false,[],["freshMissingV1"]] call _nativeCarrier;
    [_uid=="" && {str (_patient getVariable "ACM_circulation_IV_Bags")==_before},"fenced donor attached via recycled ID"] call _check;
    ''')


@pytest.mark.parametrize('action',['FreshBloodBag_500','FreshBloodBag_ABC_3','FreshBloodBag_500_999','FreshBloodBag_500_3bad'])
def test_native_factory_rejects_malformed_donor_treatment_before_any_write(action):
    execute(native_setup()+setup()+f'private _action="{action}";'+r'''
    private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
    private _uid=[_patient,"leftarm",_action,1,true,0,true,false,[],["freshV1",true,-100,2]] call _nativeCarrier;
    [_uid=="" && {str (_patient getVariable "ACM_circulation_IV_Bags")==_before},"invalid fresh action attached or mutated bag map"] call _check;
    ''')


def test_native_factory_captures_live_donor_metadata_before_registry_changes():
    execute(native_setup()+setup()+r'''
    private _uid=[_patient,"leftarm","FreshBloodBag_500_3",1,true,0,true,false] call _nativeCarrier;
    private _bag=((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") select 0;
    [_uid!="" && {(_bag select 10) isEqualTo ["freshV1",true,3600,0]},"new fresh bag omitted immutable donor facts"] call _check;
    ''')


def test_prepared_hang_rejects_fenced_donor_before_creating_or_consuming_anything():
    execute(native_setup()+setup()+'ACME_fnc_preparedHangCommit={'+source('preparedHangCommit')+'};'+r'''
    _set set [1,"ACM_FreshBloodBag_500_3"];_set set [2,"FreshBloodBag_500_3"];
    _set set [10,0];_set set [11,["freshMissingV1"]];call _store;
    ACME_fnc_inventoryLedgerCertificate={["set1",_set]};
    [_patient,_medic,"hang_fenced","set1","leftarm",true,0,1,false,[]] call ACME_fnc_preparedHangCommit;
    private _result=(_patient getVariable "ACME_preparedHangResults") get "hang_fenced";
    [!(_result select 0) && {count (_medic getVariable "ACME_preparedIVSets")==1} && {_bagWrites isEqualTo []},"fenced prepared blood was attached or consumed"] call _check;
    ''')
