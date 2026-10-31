"""Conserve installed-line provenance through real return/save/rehang code.

Native inventory, gear containers, config lookups and network transport are
explicit fixture boundaries. Source funding, canonical products, receiver
idempotence, save/restore schemas and owner rehang decisions run production SQF.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from test_b288_equipment_persistence import harness
from test_historical_medication_rows import iteration_scopes
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import execute, namespace_public_arguments, read


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def function(name):
    text = read(name)
    for old, new in {
        "canSuspend": "false", "isServer": "true", "clientOwner": "7",
        "serverTime": "_serverTime", "toLowerANSI": "toLower",
        "local _patient": "true", "local _p": "true",
        "alive _medic": "_alive", "alive _patient": "_patientAlive",
        "owner _provider": "7", "owner _recipient": "7",
        "netId _medic": '"medic"', "netId _patient": '"patient"',
        "_medic distance _patient": "_distance", "_medic distance _p": "_distance",
        'isClass (configFile >> "CfgWeapons" >> _class)': '(_class != "Invalid")',
        'isClass (configFile >> "CfgWeapons" >> _value)': '(_value != "Invalid")',
    }.items():
        text = text.replace(old, new)
    # These fixtures supply finite ordinary values; retain production type and
    # range guards while replacing only SQF-VM's missing native finite command.
    text = re.sub(r"\bfinite (_\w+|\([^()]*\))", r"(\1 call _finite)", text)
    return f"ACME_fnc_{name}={{" + namespace_public_arguments(map_defaults(iteration_scopes(text))) + "};\n"


def fixture():
    return harness() + r'''
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _serverTime=100;private _liveEpoch=1;private _lineLive=true;
        private _packets=[];private _serverMessages=[];private _notices=[];
        private _line=["leftarm","front",.5,.5,"hub","","",16,-1,1,"upper",0,1,0,"hub",[true,true,true,true],[],"paid-line"];
        ACE_player=_medic;
        _deviceCount=0;_testInterface=false;
        CBA_missionTime=100;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","machineA"];
        missionNamespace setVariable ["ACME_syringeDeliveryMachines",createHashMapFromArray [["7","machineA"]]];
        ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
        ACME_fnc_clinicalEpoch={_liveEpoch};
        ACME_fnc_clinicalNotice={_notices pushBack _this;};
        ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
        ACME_fnc_ivBagsCommit={params ["_p","_map"];_p setVariable ["ACM_circulation_IV_Bags",_map];true};
        ACME_fnc_transfusionAccessValid={_lineLive};
        ACME_fnc_isYLineAccess={false};
        ACME_fnc_ivSiteIndex={0};
        ACME_fnc_resumeSiteFlow={};ACME_fnc_lineWarmer={false};
        ACM_circulation_fnc_getAccessType={1};ACM_circulation_fnc_hasIV={_lineLive};
        ACM_circulation_fnc_hasIO={false};ACM_circulation_fnc_updateActiveFluidBags={};
        ACM_circulation_fnc_getReturnVolume={params ["_ml"];floor (_ml/250)*250};
        ACM_circulation_fnc_formatFluidBagName={params ["_type","_volume"];format ["%1_%2",_type,_volume]};
        ace_common_fnc_isAwake={true};ace_common_fnc_getName={"Medic"};
        CBA_fnc_serverEvent={_serverMessages pushBack _this;};
        CBA_fnc_targetEvent={if ((_this select 0)=="ACME_resourceReturnDelivery") then {_packets pushBack (_this select 1);};};
        CBA_fnc_ownerEvent={
            private _name=_this select 0;
            if (_name=="ACME_resourceReturnSourceAdmitted") then {["admitted",_this select 1] call ACME_fnc_resourceReturnSource;};
            if (_name=="ACME_resourceReturnSourceDelivered") then {["delivered",_this select 1] call ACME_fnc_resourceReturnSource;};
        };
        ACME_fnc_ownerDispatch={
            if ((_this select 1)=="resourceReturnCleanup") then {["cleanup",_this select 2] call ACME_fnc_resourceReturnSource;};
        };
        private _flushServer={while {count _serverMessages>0} do {
            private _message=_serverMessages deleteAt 0;
            if ((_message select 0)=="ACME_resourceReturn") then {(_message select 1) call ACME_fnc_resourceReturnBroker;};
        };};
        _patient setVariable ["ACME_IV_Marks",[_line]];
        _medic setVariable ["ACME_usedBags",[]];
    ''' + "".join(function(name) for name in (
        "resourceReturnBroker", "resourceReturnProducts", "resourceReturnProductsValid",
        "transfusionPullCommit", "rehangUsedBagCommit", "ivLineSlot", "clinicalFreshBlood", "clinicalBagMove", "piggybackLine",
    ))


@pytest.mark.parametrize("fresh", [False, True])
def test_source_funded_pull_delivery_restart_and_rehang_preserve_bag_only_marker(fresh):
    kind = "FreshBlood" if fresh else "Saline"
    blood = 2 if fresh else -1
    metadata = '["freshV1",true,70,2]' if fresh else "[]"
    execute(fixture() + f'''
        private _bag=["{kind}",183.25,1,0,true,{blood},500,-1,"source-bag",500,{metadata},"bagOnly"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_bag]]]];
        [[_patient,_medic,"leftarm","source-bag",0,[],1,"pull",100] call ACME_fnc_transfusionPullCommit,
            "paid-line bag pull was rejected"] call _check;
        [((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") isEqualTo [],
            "pull did not debit the original native bag"] call _check;
        call _flushServer;
        [count _packets==1,"source-funded product did not reach the certified receiver"] call _check;
        private _packet=[_packets select 0] call ACME_fnc_syringeDeliveryCopy;
        _packet call ACME_fnc_resourceReturnReceive;call _flushServer;
        _packet call ACME_fnc_resourceReturnReceive;call _flushServer;
        private _used=_medic getVariable "ACME_usedBags";
        [count _used==1 && {{(_used select 0 select 2)==183.25}} && {{(_used select 0 select 9)=="bagOnly"}},
            "return lost volume/provenance or duplicated the pulled bag"] call _check;
        [((((missionNamespace getVariable "ACME_resourceReturns") get "pull") select 4)=="delivered"),
            "certified recipient did not settle its source funding"] call _check;
        private _saved=[_medic] call ACME_fnc_equipmentSnapshot;
        [[_saved] call ACME_fnc_equipmentSnapshotValid,"marked used bag could not be saved"] call _check;
        [(_saved select 2 select 0 select 9)=="bagOnly","save omitted bag-only ownership"] call _check;
        CBA_missionTime=1000;
        _medic setVariable ["ACME_usedBags",[]];_medic setVariable ["ACME_equipmentKitEpoch",1];
        [[_medic,_saved] call ACME_fnc_equipmentRestore,"marked used bag could not be restored"] call _check;
        private _restored=+((_medic getVariable "ACME_usedBags") select 0);
        [(_restored select 9)=="bagOnly" && {{(_restored select 2)==183.25}},
            "restart lost bag-only provenance or exact volume"] call _check;
        _medic setVariable ["ACME_usedBags",[]];
        [[_patient,_medic,"leftarm",true,0,_restored select 0,_restored,1,"rehang",false,100,"paid-line"] call ACME_fnc_rehangUsedBagCommit,
            "marked used bag could not reconnect to its installed line"] call _check;
        private _native=((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") select 0;
        [(_native select 11)=="bagOnly" && {{(_native select 1)==183.25}},
            "rehang invented a line or changed fluid volume"] call _check;
        [(_patient getVariable "ACME_IV_Marks") isEqualTo [_line],
            "pull/rehang removed or duplicated installed apparatus"] call _check;
        private _clinical=[_patient getVariable "ACM_circulation_IV_Bags","snapshot"] call ACME_fnc_clinicalFreshBlood;
        private _back=[_clinical,"restore"] call ACME_fnc_clinicalFreshBlood;
        [((_back get "leftarm") select 0 select 11)=="bagOnly",
            "native medical save/restore lost bag-only provenance"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_lineLive=false;', '_line set [17,"replacement-line"];_patient setVariable ["ACME_IV_Marks",[_line]];',
    '_patient setVariable ["ACME_IV_Marks",[]];',
])
def test_marked_used_bag_cannot_rehang_without_its_current_installed_line(change):
    execute(fixture() + r'''
        private _record=["used","Saline",183.25,1,-1,500,"Saline",-1,[],"bagOnly"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[]]]];
    ''' + change + r'''
        [!([_patient,_medic,"leftarm",true,0,"used",_record,1,"rehang",false,100,"paid-line"] call ACME_fnc_rehangUsedBagCommit),
            "marked used bag created a free line at a removed or replaced apparatus"] call _check;
        [((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") isEqualTo [],
            "refused rehang created a native bag"] call _check;
    ''')


def test_marked_used_bag_cannot_bypass_line_selection_with_legacy_rehang_arguments():
    execute(fixture() + r'''
        private _record=["used","Saline",183.25,1,-1,500,"Saline",-1,[],"bagOnly"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[]]]];
        [!([_patient,_medic,"leftarm",true,0,"used",_record,1,"rehang",false,100] call ACME_fnc_rehangUsedBagCommit),
            "legacy request bypassed bag-only installed-line requirement"] call _check;
    ''')


@pytest.mark.parametrize("tail", ['"ownLine"', 'false', '[]'])
def test_return_and_equipment_schemas_reject_unknown_ownership_tail(tail):
    execute(fixture() + f'''
        private _row=["used","Saline",183.25,1,-1,500,"Saline",-1,[],{tail}];
        [!([[ ["used",_row] ]] call ACME_fnc_resourceReturnProductsValid),
            "canonical return accepted an unknown line-ownership tag"] call _check;
        [!([[1,[],[_row],[],[]]] call ACME_fnc_equipmentSnapshotValid),
            "equipment save accepted an unknown line-ownership tag"] call _check;
    ''')


def test_nonfresh_marker_requires_empty_reserved_fresh_metadata_slot():
    execute(fixture() + r'''
        private _row=["used","Saline",183.25,1,-1,500,"Saline",-1,["unexpected"],"bagOnly"];
        [!([[ ["used",_row] ]] call ACME_fnc_resourceReturnProductsValid),
            "nonfresh marked return accepted arbitrary reserved metadata"] call _check;
        [!([[1,[],[_row],[],[]]] call ACME_fnc_equipmentSnapshotValid),
            "nonfresh marked save accepted arbitrary reserved metadata"] call _check;
    ''')


@pytest.mark.parametrize("mode", ["snapshot", "restore"])
@pytest.mark.parametrize("kind,metadata", [
    ("Saline", 'false'), ("Saline", 'nil'), ("Saline", '["unexpected"]'),
    ("FreshBlood", 'false'), ("FreshBlood", 'nil'),
])
def test_native_bag_only_marker_rejects_malformed_reserved_metadata(mode, kind, metadata):
    execute(fixture() + f'''
        private _bag=["{kind}",183.25,1,0,true,2,500,-1,"bag",500,[],"bagOnly"];
        _bag set [10,{metadata}];
        private _map=createHashMapFromArray [["leftarm",[_bag]]];
        private _before=str _map;
        [([_map,"{mode}"] call ACME_fnc_clinicalFreshBlood) isEqualTo [],
            "native bag-only marker accepted malformed reserved metadata"] call _check;
        [str _map==_before,"rejected normalization changed live bag custody"] call _check;
    ''')


@pytest.mark.parametrize("mode", ["snapshot", "restore"])
@pytest.mark.parametrize("fresh", [False, True])
def test_native_normalization_preserves_foreign_tail_without_claiming_its_schema(mode, fresh):
    kind = "FreshBlood" if fresh else "Saline"
    tag = "freshV1" if mode == "snapshot" else "freshAgeV1"
    metadata = f'["{tag}",true,70,2]' if fresh else '["foreign-reserved-value"]'
    execute(fixture() + f'''
        private _bag=["{kind}",183.25,1,0,true,2,500,-1,"bag",500,{metadata},"foreign-tail",["foreign-extension",17]];
        private _map=createHashMapFromArray [["leftarm",[_bag]]];
        private _before=str _map;
        private _normalized=[_map,"{mode}"] call ACME_fnc_clinicalFreshBlood;
        [_normalized isEqualType createHashMap,"foreign metadata blocked clinical normalization"] call _check;
        private _row=(_normalized get "leftarm") select 0;
        [(_row select [11,2]) isEqualTo (_bag select [11,2]),
            "normalization truncated or interpreted another bag extension"] call _check;
        [str _map==_before,"snapshot/restore changed live bag custody"] call _check;
    ''')


@pytest.mark.parametrize("field", [7, 8, 9])
def test_marked_row_may_not_contain_nil_padding(field):
    execute(fixture() + f'''
        private _row=["used","Saline",183.25,1,-1,500,"Saline",-1,[],"bagOnly"];
        _row set [{field},nil];
        [!([[ ["used",_row] ]] call ACME_fnc_resourceReturnProductsValid),
            "canonical return accepted nil marker padding"] call _check;
        [!([[1,[],[_row],[],[]]] call ACME_fnc_equipmentSnapshotValid),
            "equipment save accepted nil marker padding"] call _check;
    ''')


def test_ordinary_native_remove_returns_only_the_bag_item_without_an_extra_line():
    execute(fixture() + r'''
        private _bag=["Saline",499,1,0,true,-1,500,-1,"bag",500,[],"bagOnly"];
        private _result=["remove",_patient,"remove",[_bag]] call ACME_fnc_resourceReturnProducts;
        [(_result select 0) && {(_result select 1) isEqualTo [["item","Saline_250"]]},
            "native Remove changed into a line-bearing return"] call _check;
    ''')


def test_legacy_used_return_schema_still_accepts_its_original_eight_fields():
    execute(fixture() + r'''
        private _row=["legacy","Saline",183.25,1,-1,500,"Saline",-1];
        [[[["used",_row]]] call ACME_fnc_resourceReturnProductsValid,
            "legacy line-bearing used product lost compatibility"] call _check;
    ''')


@pytest.mark.parametrize("bag_only", [False, True])
def test_used_fill_retains_original_capacity_without_refilling(bag_only):
    tail = ',"bagOnly"' if bag_only else ""
    execute(fixture() + f'''
        private _bag=["Saline",120,1,0,true,-1,120,-1,"used-fill",500,[]{tail}];
        private _result=["pull",_patient,"pull",[_bag]] call ACME_fnc_resourceReturnProducts;
        [(_result select 0),"used-fill return was rejected"] call _check;
        private _row=(_result select 1 select 0) select 1;
        [(_row select 2)==120 && {{(_row select 5)==500}},
            "used-fill return shrank manufacturer capacity or refilled its contents"] call _check;
    ''')


def test_bag_only_move_cannot_invent_a_line_at_a_bare_destination():
    execute(fixture() + r'''
        private _bag=["Saline",183.25,1,0,true,-1,500,-1,"source-bag",500,[],"bagOnly"];
        private _map=createHashMapFromArray [["leftarm",[_bag]],["rightarm",[]]];
        _patient setVariable ["ACM_circulation_IV_Bags",_map];
        [_patient,_medic,"source-bag","reserve","leftarm",true,0,1,"move"] call ACME_fnc_clinicalBagMove;
        [count (_patient getVariable ["ACME_bagMoves",createHashMap])==0,
            "bag-only source reserved an implicit administration-set move"] call _check;
        // A previously queued legacy reservation must also be refused before
        // group placement when a fresh replica reveals bag-only provenance.
        _patient setVariable ["ACME_bagMoves",createHashMapFromArray [["source-bag",["leftarm",_bag,_medic,100,1,"move"]]]];
        [_patient,_medic,"source-bag","place","rightarm",true,0,1,"move"] call ACME_fnc_clinicalBagMove;
        [(_patient getVariable "ACM_circulation_IV_Bags") isEqualTo _map,
            "queued bag-only move detached source or invented destination tubing"] call _check;
        [count (_patient getVariable ["ACME_bagMoves",createHashMap])==0,
            "refused bag-only move retained its reservation"] call _check;
    ''')
