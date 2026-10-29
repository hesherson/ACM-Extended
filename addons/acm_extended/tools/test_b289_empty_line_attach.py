"""Run installed-line attachment through real supply and prepared custody.

Native config/control handles, cargo, the bag factory and message transport are
explicit boundaries. Source debit, token issue/claim/settlement, line topology,
owner preflight and exact prepared-set acknowledgements execute production SQF.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from test_b156_procedure_supplies import primitives, supply_setup
from test_b279_inventory_ledger import adapted, setup as ledger_setup
from test_menu_death_lifecycle import adapt, execute, read


@pytest.fixture(autouse=True)
def reject_native_boundary_warnings(monkeypatch):
    run = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = run(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def mass_selector():
    from test_menu_death_lifecycle import ROOT
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    variants = re.findall(r'class (ACME_(?:PreparedIVSet|UnspikedBag)_M\w+): \w+ \{ mass = ([\d.]+); \};', config)
    masses = ",".join(f'["{name}",{mass}]' for name, mass in variants)
    text = read("inventoryLedgerClass")
    text = text.replace('getNumber (configFile >> "CfgWeapons" >> _line >> "ItemInfo" >> "mass")', '0.1')
    text = text.replace('getNumber (configFile >> "CfgWeapons" >> _x >> "ItemInfo" >> "mass")', '([_x]call _sourceMass)')
    text = text.replace('configFile >> "CfgMagazines" >> _class', '_class')
    text = text.replace('isClass _cfg', '(_cfg in _carrierMass)')
    text = text.replace('getNumber (_cfg >> "mass")', '(_carrierMass get _cfg)')
    return f'''
        private _carrierMass=createHashMapFromArray [{masses}];
        private _unknownMass=false;
        private _sourceMass={{params ["_class"];
            if (_unknownMass) exitWith {{5.03}};
            if ((_class find "ACM_FreshBloodBag_500")==0) exitWith {{12.9}};
            if ((_class find "ACM_FreshBloodBag_250")==0) exitWith {{6.7}};
            5
        }};
        ACME_fnc_inventoryLedgerClass={{''' + adapted(text) + '};'


def compiled(name):
    text = read(name).replace("canSuspend", "false")
    text = re.sub(r'\blocal _m\b', '_providerLocal', text)
    text = text.replace("findDisplay 86000", "_displayFixture")
    text = text.replace("objectParent ACE_player", "objNull")
    text = text.replace("netId _medic", '"medic"')
    text = text.replace("netId _target", '"patient"')
    text = text.replace("netId _patient", '"patient"')
    text = text.replace("_medic distance _target", "_distance")
    text = text.replace("_medic distance _patient", "_distance")
    text = text.replace("_medic distance _donor", "_distance")
    text = re.sub(r'_display displayCtrl \d+', 'objNull', text)
    text = re.sub(r'lbCurSel _setList', '-1', text)
    text = re.sub(r'_setList lbData _row', '""', text)
    text = re.sub(r'getText \(configFile >> "CfgWeapons" >> _class >> "displayName"\)', '"Fixture fluid"', text)
    text = text.replace('getText (_cfg >> "type")', '_fixtureType')
    text = text.replace('getNumber (_cfg >> "volume")', '_fixtureVolume')
    text = text.replace('private _cfg = configFile >> "ace_medical_treatment" >> "IV" >> _action;', 'private _cfg = configNull;')
    text = text.replace('getText (configFile >> "ace_medical_treatment" >> "IV" >> _bloodAction >> "type")', '_fixtureType')
    text = text.replace('finite _id', '(_id isEqualType 0)')
    text = re.sub(r'finite \((_entry|_inline) select (\d+)\)', r'((\1 select \2) isEqualType 0)', text)
    return f'ACME_fnc_{name}={{' + adapted(text) + '};'


def setup():
    return supply_setup() + ledger_setup() + r'''
        private _fixtureType="Saline";private _fixtureVolume=500;
        private _providerLocal=true;
        private _displayFixture=missionNamespace;
        private _accessLive=true;private _isY=false;private _factoryFails=false;
        private _untils=[];private _ownerPackets=[];private _resultPackets=[];
        private _factoryCalls=0;private _factoryArgs=[];private _notices=[];private _triage=[];private _logs=[];private _thermal=[];
        ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
        ACME_fnc_transfusionAccessValid={_accessLive};
        ACME_fnc_isYLineAccess={_isY};
        ACM_circulation_fnc_getAccessType={1};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",7]};
        ACME_fnc_clinicalNotice={_notices pushBack _this;};
        ACME_fnc_updateTransfusionControls={};
        ACME_fnc_controlledProvider={_medic};
        ACME_fnc_carrierSupplyTake={[objNull,"",false,objNull]};
        ACME_fnc_itemTake={params ["_u","_c"];
            private _stock=+(_u getVariable ["fixtureStock",[]]);
            private _i=_stock find _c;
            if (_i<0) exitWith {false};
            _stock deleteAt _i;_u setVariable ["fixtureStock",_stock];
            _debits pushBack [_u,_c];true
        };
        ACME_fnc_ivBagsCommit={params ["_p","_map"];_p setVariable ["ACM_circulation_IV_Bags",_map];true};
        ACME_fnc_yLinesCommit={};ACME_fnc_resumeSiteFlow={};
        ACME_fnc_lineWarmer={false};ACME_fnc_bloodThermalStateCommit={_thermal pushBack _this;};
        ACME_fnc_reopenTransfusion={};
        ACM_circulation_fnc_updateActiveFluidBags={};
        ace_medical_treatment_fnc_addToTriageCard={_triage pushBack _this;};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        ACM_circulation_fnc_getFreshBloodEntry={
            params ["_id"];private _registry=missionNamespace getVariable ["fixtureFresh",createHashMap];
            if (_id in _registry) then {_registry get _id} else {[]}
        };
        missionNamespace setVariable ["fixtureFresh",createHashMap];
        missionNamespace setVariable ["ACME_infusion_premixedByType",createHashMap];
        ACM_circulation_Fluids_Array=["SalineBag","BloodBag","PlasmaBag","PlasmaLyteBag"];
        ACM_circulation_Fluids_Array_Data=["SalineIV_500","BloodIV_500","PlasmaIV_500","PlasmaLyteIV_500"];
        ACM_circulation_TransfusionMenu_Target=_patient;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
        ACM_circulation_TransfusionMenu_SelectIV=true;
        ACM_circulation_TransfusionMenu_Selected_AccessSite=0;
        ACM_circulation_TransfusionMenu_Selected_Inventory=0;
        private _mark=["leftarm","front",0,0,"hub",0,"cath",16,0,0,"upper",false,0,0,"ivhub-one",[true,true,true,true],[]];
        _patient setVariable ["ACME_IV_Marks",[_mark]];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMap];
        _patient setVariable ["ACME_clinicalEpoch",7];
        _patient setVariable ["ACME_YLines",[]];
        _patient setVariable ["ACME_yFlushJobs",createHashMap];
        _patient setVariable ["ACME_preparedHangResults",createHashMap];
        _medic setVariable ["ACME_lineBagPending",[]];
        _medic setVariable ["ACME_providerLocalityEpoch",0];
        _medic setVariable ["fixtureStock",["SalineBag","ACME_IVLine"]];
        _patient setVariable ["fixtureStock",[]];
        uiNamespace setVariable ["ACME_preparedListMode",false];
        missionNamespace setVariable ["ACME_piggybackPending",[]];
        missionNamespace setVariable ["ACME_preparedHangPending",createHashMap];
        private _selected=[_patient,"leftarm",true,0,"ivhub-one",7];
        ACME_fnc_getSelectedIVLineContext={
            if (([_selected select 0,_selected select 1,_selected select 2,_selected select 3,_selected select 4]call ACME_fnc_ivLineSlot) isEqualTo []) exitWith {[]};
            if ((_selected select 5)!=([_selected select 0]call ACME_fnc_clinicalEpoch)) exitWith {[]};
            +_selected
        };
        CBA_fnc_waitUntilAndExecute={_untils pushBack _this;};
        CBA_fnc_targetEvent={
            if ((_this select 0)=="ACME_preparedHangResult") then {_resultPackets pushBack (_this select 1);}
            else {_replies pushBack (_this select 1);};
        };
        ACME_fnc_ownerDispatch={
            if ((_this select 1)=="preparedHang") then {_ownerPackets pushBack (_this select 2);};
        };
        ace_medical_treatment_fnc_ivBagLocal={
            params ["_p","_part","_action","_access","_iv","_site"];
            _factoryCalls=_factoryCalls+1;
            _factoryArgs pushBack +_this;
            if (_factoryFails) exitWith {""};
            private _uid=format ["bag:%1",_factoryCalls];
            private _map=_p getVariable ["ACM_circulation_IV_Bags",createHashMap];
            private _bags=+([_map,[_part,[]]]call _mapDefault);
            private _bag=[_fixtureType,_fixtureVolume,_access,_site,_iv,-1,_fixtureVolume,-1,_uid];
            if (_fixtureType=="FreshBlood") then {_bag set [9,_fixtureVolume];_bag set [10,+(_this param [9,[]])];};
            _bags pushBack _bag;
            _map set [_part,_bags];_p setVariable ["ACM_circulation_IV_Bags",_map];_uid
        };
        private _runUntil={
            private _job=_untils deleteAt 0;
            if ((_job select 2)call (_job select 0)) then {(_job select 2)call (_job select 1);}
            else {_untils pushBack _job;};
        };
        private _deliverOwner={private _packets=+_ownerPackets;_ownerPackets=[];
            {_x call ACME_fnc_preparedHangCommit;}forEach _packets;};
        private _deliverResult={private _packets=+_resultPackets;_resultPackets=[];
            {_x call ACME_fnc_preparedHangResult;}forEach _packets;};
        private _complete={call _flush;call _runUntil;call _flush;call _deliverOwner;call _deliverResult;call _flush;};
        private _bags={(_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) get "leftarm"};
    ''' + mass_selector() + ''.join(compiled(name) for name in (
        "ivSiteIndex", "ivLineSlot", "transfusionTakeSelected", "freshBloodResolve",
        "attachBagToLine", "hangPreparedSet", "preparedHangCommit", "preparedHangResult"
    ))


@pytest.mark.parametrize("change,available", [
    ("", True),
    ("_accessLive=false;", False),
    ("_isY=true;", False),
    ('(_mark select 15)set [3,false];', False),
    ('_mark set [14,"replacement"];', False),
    ('_mark set [17,"replacement-line"];', False),
    ('_mark set [17,123];', False),
    ('_patient setVariable ["ACME_IV_Marks",[_mark,+_mark]];', False),
    ('_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",0,1,0,true,-1,500,-1,"spent"]]]]];', False),
    ('_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",500,1,1,true,-1,500,-1,"neighbor"]]]]];', True),
    ('_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",500,1,0,true,-1,500,-1,"detached"]]]]];_patient setVariable ["ACME_IV_DisconnectedBagUIDs",["detached"]];', True),
])
def test_slot_requires_one_current_installed_empty_line(change, available):
    execute(setup() + change + f'''
        private _slot=[_patient,"leftarm",true,0,"ivhub-one"]call ACME_fnc_ivLineSlot;
        [(_slot isNotEqualTo [])=={str(available).lower()},"empty-line identity/topology was resolved incorrectly"]call _check;
        [([_patient,"leftarm",false,0]call ACME_fnc_ivLineSlot) isEqualTo [],"IO incorrectly advertised an installed IV-line slot"]call _check;
    ''')


@pytest.mark.parametrize("kind,item,action", [
    ("Saline", "SalineBag", "SalineIV_500"),
    ("Blood", "BloodBag", "BloodIV_500"),
    ("Plasma", "PlasmaBag", "PlasmaIV_500"),
    ("PlasmaLyte", "PlasmaLyteBag", "PlasmaLyteIV_500"),
])
def test_direct_attach_debits_one_selected_bag_and_reuses_the_installed_line(kind, item, action):
    execute(setup() + f'''
        _fixtureType="{kind}";
        _medic setVariable ["fixtureStock",["{item}","ACME_IVLine"]];
        [["{item}","{action}","ivhub-one"]call ACME_fnc_attachBagToLine,"valid direct attach did not start"]call _check;
        [(_medic getVariable "fixtureStock") isEqualTo ["ACME_IVLine"],"direct attach charged another line or failed its exact bag debit"]call _check;
        [count _debits==1 && {{count _ownerPackets==0}} && {{_factoryCalls==0}},"bag hung before certified prepared custody"]call _check;
        [((_medic getVariable "ACME_preparedIVSets")select 0 select 8)=="bagOnly","conversion fabricated a carried administration set"]call _check;
        call _flush;
        private _sid=(_medic getVariable "ACME_preparedIVSets")select 0 select 0;
        private _token=(missionNamespace getVariable "ACME_inventoryLedgerIndex")get ("prepared:"+_sid);
        private _carrier=(missionNamespace getVariable (format ["ACME_inventoryToken_%1",_token]))select 8;
        [(_carrier find "ACME_UnspikedBag_")==0 && {{(_carrierMass get _carrier)==5}},"bag-only custody included an unpaid tube or extra tube mass"]call _check;
        call _complete;
        [_factoryCalls==1 && {{count (call _bags)==1}} && {{((call _bags)select 0 select 1)==500}},"direct attach did not produce exactly one correctly sized bag"]call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [] && {{(_medic getVariable "native") isEqualTo []}},"consumed prepared custody survived successful hang"]call _check;
        [(_medic getVariable "ACME_lineBagPending") isEqualTo [],"owner outcome did not retire the exact busy input"]call _check;
        [((call _bags)select 0 select 11)=="bagOnly","hung bag lost its no-tubing provenance"]call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_selected set [1,"rightarm"];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_patient setVariable ["ACME_clinicalEpoch",8];',
    '(_mark select 15)set [3,false];',
])
def test_changed_context_before_inventory_confirmation_never_hangs_a_new_target(change):
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
    ''' + change + r'''
        call _flush;call _runUntil;
        [_factoryCalls==0 && {count _ownerPackets==0},"obsolete input auto-hung into changed context"]call _check;
        [count _debits==1 && {count (_medic getVariable "ACME_preparedIVSets")==1},"changed context lost source-funded bag contents"]call _check;
        [(_medic getVariable "fixtureStock") isEqualTo ["ACME_IVLine"],"changed context refunded a second native bag"]call _check;
    ''')


@pytest.mark.parametrize("change", [
    '(_mark select 15)set [3,false];',
    '_mark set [14,"replacement"];',
    '_mark set [17,"same-hub-new-line"];',
    '_patient setVariable ["ACME_clinicalEpoch",8];',
    '_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Plasma",200,1,0,true,-1,500,-1,"someone-else"]]]]];',
    '_factoryFails=true;',
])
def test_owner_rejection_returns_one_prepared_bag_without_native_source_duplication(change):
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        call _flush;call _runUntil;call _flush;
        [count _ownerPackets==1,"fixture failed to queue certified owner request"]call _check;
    ''' + change + r'''
        call _deliverOwner;call _deliverResult;call _flush;
        [count (_medic getVariable "ACME_preparedIVSets")==1 && {count (_medic getVariable "native")==1},"owner refusal lost or duplicated prepared custody"]call _check;
        [count _debits==1 && {(_medic getVariable "fixtureStock") isEqualTo ["ACME_IVLine"]},"owner refusal refunded a duplicate loose bag or line"]call _check;
        [(_medic getVariable "ACME_lineBagPending") isEqualTo [],"refusal left the input permanently busy"]call _check;
    ''')


def test_repeat_click_and_replayed_owner_delivery_never_duplicate_source_or_bag():
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        [!(["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine),"repeated click started another conversion"]call _check;
        call _flush;call _runUntil;call _flush;
        private _packet=+(_ownerPackets select 0);_ownerPackets pushBack _packet;
        call _deliverOwner;call _deliverResult;call _flush;
        [_factoryCalls==1 && {count _debits==1} && {count (call _bags)==1},"owner replay or repeated click duplicated a bag"]call _check;
    ''')


def test_missing_bag_or_wrong_class_action_pair_consumes_nothing():
    execute(setup() + r'''
        [!(["SalineBag","BloodIV_500","ivhub-one"]call ACME_fnc_attachBagToLine),"mismatched class/action was accepted"]call _check;
        _medic setVariable ["fixtureStock",["ACME_IVLine"]];
        [!(["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine),"missing selected bag was fabricated"]call _check;
        [count _debits==0 && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []},"failed conversion created unfunded custody"]call _check;
    ''')


def test_fresh_bag_retains_portable_donor_metadata_before_owner_hang():
    execute(setup() + r'''
        _fixtureType="FreshBlood";
        missionNamespace setVariable ["fixtureFresh",createHashMapFromArray [[17,[objNull,500,2,true,3]]]];
        _medic setVariable ["fixtureStock",["ACM_FreshBloodBag_500_17","ACME_IVLine"]];
        [["ACM_FreshBloodBag_500_17","FreshBloodBag_500_17","ivhub-one"]call ACME_fnc_attachBagToLine,"fresh bag conversion refused valid donor metadata"]call _check;
        [((_medic getVariable "ACME_preparedIVSets")select 0 select 11) isEqualTo ["freshV1",true,3,2],"prepared donor bag lost portable provenance"]call _check;
        missionNamespace setVariable ["fixtureFresh",createHashMapFromArray [[17,[objNull,500,0,false,100]]]];
        call _complete;
        [_factoryCalls==1 && {count _debits==1},"fresh bag failed its certified single hang"]call _check;
        [((call _bags)select 0 select 10) isEqualTo ["freshV1",true,3,2],"reused donor registry replaced immutable bag metadata"]call _check;
    ''')


def test_unknown_exact_native_mass_is_refused_before_any_source_debit():
    execute(setup() + r'''
        _unknownMass=true;
        [!(["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine),"unknown bag-only native mass was silently replaced by an equipped carrier"]call _check;
        [count _debits==0 && {(_medic getVariable "fixtureStock") isEqualTo ["SalineBag","ACME_IVLine"]},"mass rejection consumed a source item"]call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [],"mass rejection created unfunded custody"]call _check;
    ''')


def test_bag_only_manual_retry_still_requires_an_actual_installed_line():
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        call _flush;
        _selected set [1,"rightarm"];call _runUntil;
        _selected set [1,"leftarm"];
        (_mark select 15)set [3,false];
        private _sid=(_medic getVariable "ACME_preparedIVSets")select 0 select 0;
        [_sid]call ACME_fnc_hangPreparedSet;
        [count _ownerPackets==0 && {_factoryCalls==0},"manual bag-only retry invented an IV line"]call _check;
        [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_preparedIVSets")==1},"refused manual retry lost or consumed the bag"]call _check;
    ''')


def test_old_owner_call_without_optional_line_uid_cannot_equip_a_bag_only_record():
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        call _flush;call _runUntil;call _flush;
        private _packet=+(_ownerPackets select 0);_packet resize 10;
        _ownerPackets=[_packet];
        private _pending=missionNamespace getVariable "ACME_preparedHangPending";
        private _record=_pending get (_packet select 2);_record set [1,_packet];
        (_mark select 15)set [3,false];
        call _deliverOwner;call _deliverResult;call _flush;
        [_factoryCalls==0 && {count (_medic getVariable "native")==1},"omitting optional line UID bypassed real-line requirement or lost bag"]call _check;
    ''')


def test_cooled_blood_retains_thermal_handling_even_when_product_has_no_tubing():
    execute(setup() + r'''
        _fixtureType="Blood";
        _medic setVariable ["fixtureStock",["BloodBag","ACME_IVLine"]];
        ["BloodBag","BloodIV_500","ivhub-one",true]call ACME_fnc_attachBagToLine;
        call _complete;
        [count _thermal==1 && {(_thermal select 0 select 2)},"bag-only blood lost its cold-blood thermal state"]call _check;
    ''')


@pytest.mark.parametrize("volume", [250, 500])
def test_fresh_id_zero_uses_the_real_base_item_and_keeps_donor_metadata(volume):
    execute(setup() + f'''
        _fixtureType="FreshBlood";_fixtureVolume={volume};
        missionNamespace setVariable ["fixtureFresh",createHashMapFromArray [[0,[objNull,{volume},2,true,3]]]];
        _medic setVariable ["fixtureStock",["ACM_FreshBloodBag_{volume}","ACME_IVLine"]];
        [["ACM_FreshBloodBag_{volume}","FreshBloodBag_{volume}_0","ivhub-one"]call ACME_fnc_attachBagToLine,"first donor bag's real base item was rejected"]call _check;
        [(_medic getVariable "fixtureStock") isEqualTo ["ACME_IVLine"] && {{count _debits==1}},"first donor bag debit charged a tube or a second item"]call _check;
        [((_medic getVariable "ACME_preparedIVSets")select 0 select 11) isEqualTo ["freshV1",true,3,2],"first donor bag lost immutable metadata"]call _check;
        call _complete;
        [_factoryCalls==1 && {{((call _bags)select 0 select 1)=={volume}}},"first donor bag did not attach at its actual volume"]call _check;
        [((call _bags)select 0 select 10) isEqualTo ["freshV1",true,3,2],"first donor bag arrived without donor metadata"]call _check;
    ''')


def test_detached_old_bag_does_not_block_a_new_paid_empty_line():
    execute(setup() + r'''
        private _old=["Plasma",200,1,0,true,-1,500,-1,"old-detached"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_old]]]];
        _patient setVariable ["ACME_IV_DisconnectedBagUIDs",["old-detached"]];
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        call _complete;
        [_factoryCalls==1 && {count (call _bags)==2},"detached old bag blocked a current installed line"]call _check;
        [((call _bags)select 0) isEqualTo _old,"new attach changed a detached bag's exact remaining contents"]call _check;
    ''')


def test_selected_patient_inventory_is_debited_without_taking_the_medics_bag_or_line():
    execute(setup() + r'''
        ACM_circulation_TransfusionMenu_Selected_Inventory=1;
        _medic setVariable ["fixtureStock",["SalineBag","ACME_IVLine"]];
        _patient setVariable ["fixtureStock",["SalineBag"]];
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        [(_patient getVariable "fixtureStock") isEqualTo [] && {(_medic getVariable "fixtureStock") isEqualTo ["SalineBag","ACME_IVLine"]},"direct attach consumed the wrong inventory or another line"]call _check;
        call _complete;
        [_factoryCalls==1 && {count _debits==1},"patient-funded bag failed its single certified hang"]call _check;
    ''')


def test_origin_busy_preview_retires_when_provider_locality_moves_away():
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        _providerLocal=false;
        call _runUntil;
        [(_medic getVariable "ACME_lineBagPending") isEqualTo [],"origin presentation busy state survived provider ownership loss"]call _check;
        [_factoryCalls==0 && {count _debits==1},"ownership loss submitted or duplicated patient work"]call _check;
    ''')


def test_origin_busy_timer_can_retire_after_provider_moves_away_during_owner_request():
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        call _flush;call _runUntil;call _flush;
        [count _ownerPackets==1 && {(_medic getVariable "ACME_lineBagPending") isNotEqualTo []},"fixture did not retain busy owner request"]call _check;
        _providerLocal=false;
        private _timer=_waits select 0;(_timer select 1)call (_timer select 0);
        [(_medic getVariable "ACME_lineBagPending") isEqualTo [],"timeout could latch the old client's busy state after away/back ownership"]call _check;
        [count _ownerPackets==1 && {count _debits==1},"busy cleanup replayed or canceled certified custody"]call _check;
    ''')


@pytest.mark.parametrize("who", ["_patient", "_medic"])
def test_checkpoint_after_carrier_grant_cancels_auto_hang_without_consuming_custody(who):
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        call _flush;
    ''' + f'{who} setVariable ["ACME_persistenceFrozen",true];' + r'''
        call _runUntil;call _flush;
        [_factoryCalls==0 && {count _ownerPackets==0},"automatic hang crossed a coordinated save freeze"]call _check;
        [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_preparedIVSets")==1},"checkpoint lost source-funded bag-only custody"]call _check;
        [count _debits==1 && {(_medic getVariable "fixtureStock") isEqualTo ["ACME_IVLine"]},"checkpoint duplicate-refunded or consumed a line"]call _check;
    ''')


@pytest.mark.parametrize("who", ["_patient", "_medic"])
def test_owner_save_freeze_refuses_new_admission_but_returns_the_exact_bag(who):
    execute(setup() + r'''
        ["SalineBag","SalineIV_500","ivhub-one"]call ACME_fnc_attachBagToLine;
        call _flush;call _runUntil;call _flush;
        [count _ownerPackets==1,"fixture did not queue the certified hang"]call _check;
    ''' + f'{who} setVariable ["ACME_persistenceFrozen",true];' + r'''
        call _deliverOwner;call _deliverResult;call _flush;
        [_factoryCalls==0,"owner mutated bag topology during a coordinated save freeze"]call _check;
        [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_preparedIVSets")==1},"frozen owner admission lost exact prepared custody"]call _check;
    ''')
