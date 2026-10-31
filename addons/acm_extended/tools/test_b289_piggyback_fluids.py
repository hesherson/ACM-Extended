"""Exercise unrestricted plain-fluid selection and exact owner piggyback custody.

The checked-out eligibility, workflow, reserve/retry/attach/ACK, native carrier
creation and secondary-priority code execute. Native config, UI, inventory and
transport remain explicit boundaries; this does not certify Arma rendering.
"""
import re

import pytest

from test_b275_piggyback import helpers
from test_b275_piggyback_owner import owner_function, owner_setup
from test_b156_procedure_supplies import supply_setup
from test_menu_death_lifecycle import execute, read
from test_b230_prepared_infusion_transaction import adapted


FLUIDS = ("Saline", "Plasma", "PlasmaLyte", "Blood", "FreshBlood", "Ringer", "HTS")


@pytest.mark.parametrize("primary", FLUIDS)
@pytest.mark.parametrize("candidate", FLUIDS)
def test_plain_fluid_selection_accepts_every_pair_of_supported_fluid_types(primary, candidate):
    execute(helpers() + f'''
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        _primary set [0,"{primary}"];
        _map set ["leftarm",[_primary,_neighbor]];
        [[_patient,"leftarm",true,0,"{candidate}",false] call ACME_fnc_piggybackEligible,
            "plain fluid classes were required to match"] call _check;
    ''')


@pytest.mark.parametrize("primary,candidate,infusion", [
    ("Saline", "FBTK", False), ("FBTK", "Saline", False),
    ("Saline", "ACME_SalineY", False), ("ACME_SalineY", "Saline", False),
    ("Saline", "ACME_Propofol", False), ("ACME_Propofol", "Saline", False),
    ("Saline", "ACME_Empty", False), ("Saline", "ACME_EmptySaline", False),
    ("Blood", "Saline", True), ("Plasma", "Saline", True),
    ("Saline", "Blood", True), ("Saline", "Plasma", True),
])
def test_plain_fluid_relaxation_does_not_convert_special_hardware_or_medication_carriers(primary, candidate, infusion):
    execute(helpers() + f'''
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        _primary set [0,"{primary}"];
        _map set ["leftarm",[_primary,_neighbor]];
        [!([_patient,"leftarm",true,0,"{candidate}",{str(infusion).lower()}] call ACME_fnc_piggybackEligible),
            "special hardware or medication compatibility was relaxed"] call _check;
    ''')


@pytest.mark.parametrize("primary", ("Saline", "Plasma", "Blood", "FreshBlood"))
def test_workflow_captures_the_live_primary_when_an_empty_line_marker_precedes_it(primary):
    source = read("piggybackWorkflow").replace("findDisplay 86000", "objNull")
    execute(helpers() + "ACME_fnc_piggybackWorkflow={" + adapted(source) + r'''};
        ACME_fnc_togglePreparedSets={};ACME_fnc_transfusionFilterInventory={};
        ACME_fnc_updateTransfusionControls={};
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
    ''' + f'_primary set [0,"{primary}"];'+r'''
        _map set ["leftarm",[["ACME_Empty",0,1,0,true,-1,0,-1,"empty-marker"],_primary,_neighbor]];
        [["start"] call ACME_fnc_piggybackWorkflow,"usable fluid primary refused workflow"] call _check;
        private _intent=missionNamespace getVariable ["ACME_piggybackPending",[]];
        [(_intent select 4)=="primary","workflow captured the empty marker as primary"] call _check;
        [_notices isEqualTo [],"usable fluid line displayed a rejection"] call _check;
    ''')


def fluid_owner_setup():
    # Extend the explicit config boundary with real fluid action names exercised
    # by the used-bag catalogue below; native creation/identity logic still runs.
    base = owner_setup().replace(
        '["SalineIV_100","SalineIV_500","MagnesiumBag"]',
        '["SalineIV_100","SalineIV_500","MagnesiumBag","PlasmaIV_500","BloodIV_ON_500","PlasmaLyteIV_500"]')
    return base + r'''
        private _thermal=[];private _warmers=[];private _warmed=false;
        private _bloodCompatible=true;private _bloodChecks=[];private _generatedBloodType=0;
        private _configuredDonorType=-1;
        ACME_fnc_lineWarmer={_warmers pushBack _this;_warmed};
        ACME_fnc_bloodThermalStateCommit={_thermal pushBack _this;};
        ACM_circulation_fnc_generateBloodType={
            _generatedBloodType=_generatedBloodType+1;
            (_this select 0) setVariable ["ACM_circulation_BloodType",0];
        };
        ACM_circulation_fnc_isBloodTypeCompatible={_bloodChecks pushBack _this;_bloodCompatible};
        ACM_circulation_fnc_getFreshBloodEntry={[]};
        _patient setVariable ["ACM_circulation_BloodType",0];
        // Preserve the real factory; only the standard native bloodtype config
        // scalar is supplied by this fixture instead of Arma's config database.
        private _configuredFactory=ace_medical_treatment_fnc_ivBagLocal;
        ace_medical_treatment_fnc_ivBagLocal={
            private _ret=_this call _configuredFactory;
            private _bags=call _stock;
            if (count _bags>2 && {!(_this select 6)}) then {
                (_bags select ((count _bags)-1)) set [5,_configuredDonorType];
            };
            _ret
        };
        _prepared=[];_ownerArgs set [10,[]];
    ''' + owner_function("freshBloodResolve")


@pytest.mark.parametrize("primary,secondary", [
    ("Saline", "Plasma"), ("Plasma", "Saline"), ("PlasmaLyte", "Ringer"),
    ("Blood", "Plasma"), ("Blood", "Saline"), ("Saline", "Blood"),
    ("Plasma", "Blood"), ("FreshBlood", "Saline"),
])
@pytest.mark.parametrize("return_mode", ("normal", "nil"))
def test_owner_attaches_exact_cross_fluid_secondary_once_and_retains_priority(primary, secondary, return_mode):
    execute(fluid_owner_setup() + f'''
        _primary set [0,"{primary}"];_configuredType="{secondary}";
        _set set [8,{('"blood"' if secondary == 'Blood' else '"premixed"')}];
        _set set [9,73];_returnMode="{return_mode}";call _reserve;
        call _send;
        [call _ack select 3,"owner rejected distinct plain fluids"] call _check;
        private _bags=call _stock;private _secondary=_bags select 2;
        [count _bags==3 && {{(_secondary select 0)=="{secondary}"}}
            && {{(_secondary select 1)==73}} && {{(_secondary select 6)==73}},
            "secondary lost its actual fluid or exact remaining volume"] call _check;
        [(_bags select 0) isEqualTo _primary && {{(_bags select 1) isEqualTo _neighbor}},
            "piggyback changed another physical bag"] call _check;
        [[_patient,"leftarm",true,0,"primary"] call ACME_fnc_piggybackFlow isEqualTo [true,false],
            "new secondary did not hold the primary"] call _check;
        [[_patient,"leftarm",true,0,_secondary select 8] call ACME_fnc_piggybackFlow isEqualTo [false,true],
            "actual secondary UID did not receive priority"] call _check;
        _secondary set [1,0];
        [[_patient,"leftarm",true,0,"primary"] call ACME_fnc_piggybackFlow isEqualTo [false,false],
            "primary remained held after secondary depletion"] call _check;
        call _send;
        [_factoryCalls==1 && {{count _logs==1}} && {{count (call _stock)==3}},
            "exact request replay created or logged another secondary"] call _check;
        [call _entries isEqualTo [_oldMed],"plain fluid manufactured a medication entry"] call _check;
    ''')


@pytest.mark.parametrize("warmed", (False, True))
def test_blood_secondary_preserves_native_compatibility_and_thermal_effects_once(warmed):
    execute(fluid_owner_setup() + f'''
        _configuredType="Blood";_set set [8,"blood"];_set set [7,true];
        _configuredDonorType=2;_bloodCompatible=false;_warmed={str(warmed).lower()};
        _patient setVariable ["ACM_circulation_BloodType",-1];call _reserve;
        call _send;call _send;
        [call _ack select 3,"plain blood secondary was refused"] call _check;
        [_generatedBloodType==1 && {{_bloodChecks isEqualTo [[0,2]]}},
            "staged blood lost native compatibility check or replayed it"] call _check;
        [count (_events select {{(_x select 0)=="ACM_circulation_handleHemolyticReaction"}})==1,
            "blood compatibility reaction was missing or replayed"] call _check;
        [count _thermal==1 && {{count _warmers==1}},"blood thermal effects were missing or replayed"] call _check;
        [((_thermal select 0) select 1)=={str(warmed).lower()}
            && {{((_thermal select 0) select 2)=={str(not warmed).lower()}}},
            "blood ignored the exact line warmer or cold-source state"] call _check;
    ''')


@pytest.mark.parametrize("metadata,action,allowed", [
    ('["freshV1",true,80,2]', 'FreshBloodBag_500_7', True),
    ('["freshV1",false,80,5]', 'FreshBloodBag_250_7', True),
    ('["freshV1",true,80,9]', 'FreshBloodBag_500_7', False),
    ('["unresolvedFreshV1"]', 'FreshBloodBag_500_7', False),
    ('[]', 'FreshBloodBag_500_7', False),
    ('["freshV1",true,80,2]', 'FreshBloodBag_100_7', False),
    ('["freshV1",true,80,2]', 'FreshBloodBag_500_007', False),
])
def test_fresh_blood_secondary_carries_immutable_donor_metadata_or_rejects_without_debit(metadata, action, allowed):
    execute(fluid_owner_setup() + f'''
        _configuredType="FreshBlood";
        _set set [2,"{action}"];_set set [8,"blood"];_set set [9,77];_set set [10,0];
        _set set [11,{metadata}];call _reserve;
        call _send;
        [(call _ack select 3) isEqualTo {str(allowed).lower()},"fresh donor validation result wrong"] call _check;
    ''' + (r'''
        private _secondary=(call _stock) select 2;
        [(_secondary select 0)=="FreshBlood" && {(_secondary select 1)==77},"fresh secondary lost fluid or exact volume"] call _check;
        [(_secondary select 10) isEqualTo (_set select 11),"immutable donor metadata was not carried onto the bag"] call _check;
        [(_secondary select 5)==((_set select 11) select 3),"fresh donor blood type rebound to a different record"] call _check;
        [(_secondary select 7)==7,"fresh bag lost source identifier"] call _check;
    ''' if allowed else r'''
        call _assertUnchanged;
        [_factoryCalls==0,"unknown or malformed donor metadata reached native creation"] call _check;
    '''))


def request_chain_setup():
    request = read("piggybackAttachRequest").replace("findDisplay 86000", "objNull")
    request = request.replace("serverTime", "_serverTime")
    request = request.replace('getText (configFile >> "ace_medical_treatment" >> "IV" >> _action >> "type")', '_configuredType')
    request = re.sub(r'\bvalues (_\w+)', r'(keys \1 apply {\1 get _x})', request)
    retry = read("piggybackRetry").replace("local _provider", "true")
    recover = read("piggybackRecover").replace("private _held = _y;", "private _held = _escrow get _x;").replace("forEach _escrow;", "forEach keys _escrow;")
    return fluid_owner_setup() + r'''
        _medic setVariable ["ACME_piggybackEscrow",createHashMap];
        _medic setVariable ["ACME_preparedIVSets",[_set]];
        _medic setVariable ["ACME_infusion_PreparedBags",[]];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
        missionNamespace setVariable ["ACME_piggybackPending",[_patient,"leftarm",true,0,"primary",1]];
        missionNamespace setVariable ["ACME_piggybackRequests",createHashMap];
        ACME_fnc_ownerDispatch={(_this select 2) call ACME_fnc_piggybackAttachLocal;};
        ACME_fnc_piggybackWorkflow={};ACME_fnc_updateTransfusionControls={};
        ACME_fnc_reopenTransfusion={};
    ''' + "ACME_fnc_piggybackAttachRequest={" + adapted(request) + "};" + \
        "ACME_fnc_piggybackRetry={" + adapted(retry) + "};" + \
        "ACME_fnc_piggybackRecover={" + adapted(recover) + "};" + \
        "ACME_fnc_piggybackAttachAck={" + adapted(read("piggybackAttachAck").replace("local _provider", "true")) + "};"


@pytest.mark.parametrize("primary,secondary", [("Saline", "Plasma"), ("Plasma", "Saline"), ("Blood", "Saline"), ("Saline", "Blood")])
def test_request_reserves_cross_fluid_owner_attach_and_ack_settles_exact_set_once(primary, secondary):
    execute(request_chain_setup() + f'''
        _primary set [0,"{primary}"];_configuredType="{secondary}";
        _set set [8,{('"blood"' if secondary == 'Blood' else '"premixed"')}];
        ["set1"] call ACME_fnc_piggybackAttachRequest;
        [count (call _stock)==3 && {{_factoryCalls==1}},"cross-fluid request never reached the owner attach"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [],"reserved source remained available for reuse"] call _check;
        private _reply=call _ack;
        _reply call ACME_fnc_piggybackAttachAck;_reply call ACME_fnc_piggybackAttachAck;
        [count (_medic getVariable "ACME_piggybackEscrow")==0
            && {{count (missionNamespace getVariable "ACME_piggybackRequests")==0}},
            "owner proof did not settle exact prepared custody"] call _check;
        [count _inventorySettlements==1 && {{(_inventorySettlements select 0 select 2)}},
            "duplicate ACK settled twice or refunded the attached bag"] call _check;
        [_factoryCalls==1 && {{count (call _stock)==3}},"ACK duplicated attachment"] call _check;
    ''')


@pytest.mark.parametrize("failure", ("wrong-site", "wrong-access", "wrong-type", "wrong-volume", "double"))
def test_cross_fluid_failure_returns_exact_reserved_set_after_owner_proof(failure):
    execute(request_chain_setup() + f'''
        _configuredType="Plasma";_returnMode="{failure}";
        ["set1"] call ACME_fnc_piggybackAttachRequest;
        [!(call _ack select 3),"invalid cross-fluid native carrier was accepted"] call _check;
        call _assertUnchanged;
        private _reply=call _ack;
        _reply call ACME_fnc_piggybackAttachAck;_reply call ACME_fnc_piggybackAttachAck;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [_set],
            "failed cross-fluid request did not restore the exact prepared bag once"] call _check;
        [count _inventorySettlements==1 && {{!(_inventorySettlements select 0 select 2)}},
            "rejection proof did not release reserved inventory once"] call _check;
    ''')


@pytest.mark.parametrize("kind", ("bagOnly", "yset", "propofol"))
def test_unfunded_or_special_prepared_apparatus_cannot_enter_piggyback_custody(kind):
    execute(request_chain_setup() + f'''
        _set set [8,"{kind}"];
        [!(["set1"] call ACME_fnc_piggybackAttachRequest),"unusable apparatus entered piggyback reservation"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [_set]
            && {{count (_medic getVariable "ACME_piggybackEscrow")==0}} && {{_factoryCalls==0}},
            "unusable apparatus debited or attached a bag"] call _check;
        call _reserve;call _send;
        [!(call _ack select 3) && {{_factoryCalls==0}},"owner accepted a bag without funded compatible tubing"] call _check;
    ''')


@pytest.mark.parametrize("participant", ("_patient", "_medic"))
def test_save_checkpoint_blocks_both_new_source_reservations_and_inflight_owner_mutations(participant):
    execute(request_chain_setup() + f'''
        {participant} setVariable ["ACME_persistenceFrozen",true];
        [!(["set1"] call ACME_fnc_piggybackAttachRequest),"frozen equipment accepted a new source reservation"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [_set]
            && {{count (_medic getVariable "ACME_piggybackEscrow")==0}},
            "checkpoint reservation changed source custody"] call _check;
        call _reserve;call _send;
        [!(call _ack select 3) && {{_factoryCalls==0}},"inflight owner mutation crossed a frozen checkpoint"] call _check;
    ''')


def used_stage_setup():
    stage = read("piggybackStageUsed")
    stage = stage.replace('configFile >> "ace_medical_treatment" >> "IV" >> _candidateAction', '_candidateAction')
    stage = stage.replace('getNumber (_cfg >> "volume")', '((_definitions get _cfg) select 1)')
    stage = stage.replace('getNumber (_cfg >> "bloodtype")', '((_definitions get _cfg) select 2)')
    stage = stage.replace('isNumber (_cfg >> "bloodtype")', '(count (_definitions get _cfg)>2)')
    stage = stage.replace('getText (_cfg >> "type")', '((_definitions get _cfg) select 0)')
    stage = stage.replace('isClass (configFile >> "CfgWeapons" >> _class)', '(_class in _itemClasses)')
    stage = stage.replace('isClass (configFile >> "CfgWeapons" >> _candidate)', '(_candidate in _itemClasses)')
    return request_chain_setup() + supply_setup() + r'''
        private _nativeReady=false;private _commitWorks=true;private _commits=0;
        private _itemClasses=["saline100","saline500","plasma500","bloodON500","ACM_FreshBloodBag_250_7","ACM_FreshBloodBag_500_7","ACM_FreshBloodBag_250","ACM_FreshBloodBag_500"];
        private _definitions=createHashMapFromArray [
            ["SalineIV_100",["Saline",100]], ["SalineIV_500",["Saline",500]],
            ["PlasmaIV_500",["Plasma",500]], ["BloodIV_ON_500",["Blood",500,2]]];
        missionNamespace setVariable ["ACM_circulation_Fluids_Array",["saline100","saline500","plasma500","bloodON500"]];
        missionNamespace setVariable ["ACM_circulation_Fluids_Array_Data",["SalineIV_100","SalineIV_500","PlasmaIV_500","BloodIV_ON_500"]];
        ACME_fnc_preparedInventoryCommit={_commits=_commits+1;_commitWorks};
        ACME_fnc_inventoryLedgerPossessed={params ["_m","_kind","_sid"];
            _nativeReady && {_kind=="prepared"} && {((_m getVariable ["ACME_preparedIVSets",[]]) findIf {(_x select 0)==_sid})>=0}
        };
        _medic setVariable ["ACME_preparedIVSets",[]];
        _medic setVariable ["ACME_usedBags",[["used1","Saline",73,1,-1,500,"Saline"]]];
        _configuredVolume=500;
        private _pollStage={
            private _wait=_waits select 0;
            if ((_wait select 1) call (_wait select 2)) then {(_wait select 1) call (_wait select 0);};
        };
    ''' + "ACME_fnc_piggybackStageUsed={" + adapted(stage) + "};"


@pytest.mark.parametrize("type,action,meta", [
    ("Saline", "SalineIV_500", '[]'), ("Plasma", "PlasmaIV_500", '[]'),
    ("Blood", "BloodIV_ON_500", '[]'),
    ("FreshBlood", "FreshBloodBag_500_7", '["freshV1",false,80,2]'),
])
def test_used_fluid_retains_exact_volume_and_existing_tubing_then_waits_for_carrier_custody(type, action, meta):
    blood_type = 2 if type in ("Blood", "FreshBlood") else -1
    execute(used_stage_setup() + f'''
        _configuredType="{type}";
        private _used=["used1","{type}",73,1,{blood_type},500,"Used fluid",7,{meta}];
        _medic setVariable ["ACME_usedBags",[_used]];
        [["used1"] call ACME_fnc_piggybackStageUsed,"used fluid was not staged"] call _check;
        private _staged=(_medic getVariable "ACME_preparedIVSets") select 0;
        [(_staged select 2)=="{action}" && {{(_staged select 9)==73}},"staging changed the fluid action or exact volume"] call _check;
        [(_medic getVariable "ACME_usedBags") isEqualTo [] && {{_commits==1}},"staging did not move exact source once"] call _check;
        [!(["used1"] call ACME_fnc_piggybackStageUsed),"a second click reused the consumed used record"] call _check;
        call _pollStage;
        [_factoryCalls==0 && {{count (_medic getVariable "ACME_piggybackEscrow")==0}},"staging dispatched before native custody"] call _check;
        _nativeReady=true;call _pollStage;
        [call _ack select 3,"native custody did not permit exact used-fluid piggyback"] call _check;
        private _secondary=(call _stock) select 2;
        [(_secondary select 0)=="{type}" && {{(_secondary select 1)==73}}
            && {{(_secondary select 9)==500}},"used fluid volume or manufacturer capacity was lost"] call _check;
        private _reply=call _ack;_reply call ACME_fnc_piggybackAttachAck;
        [count _inventorySettlements==1 && {{(_medic getVariable "ACME_preparedIVSets") isEqualTo []}},
            "used source did not settle exactly once after owner proof"] call _check;
    ''' + (f'[(_secondary select 10) isEqualTo {meta},"used fresh donor facts were lost"] call _check;' if type == "FreshBlood" else ""))


@pytest.mark.parametrize("change", [
    'missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",missionNamespace];',
    'missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",1];',
    'missionNamespace setVariable ["ACME_piggybackPending",[]];',
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_primary set [8,"replacement"];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
    '_patient setVariable ["ACME_persistenceFrozen",true];',
])
def test_delayed_used_carrier_cannot_redirect_to_changed_patient_line_or_provider_period(change):
    execute(used_stage_setup() + r'''
        [["used1"] call ACME_fnc_piggybackStageUsed,"fixture could not stage used bag"] call _check;
        private _staged=+(_medic getVariable "ACME_preparedIVSets");
    ''' + change + r'''
        _nativeReady=true;call _pollStage;
        [_factoryCalls==0 && {count (_medic getVariable "ACME_piggybackEscrow")==0},
            "delayed used bag attached in a later UI/provider context"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo _staged
            && {(_medic getVariable "ACME_usedBags") isEqualTo []},
            "context retirement lost or duplicated the exact staged product"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_commitWorks=false;',
    '_medic setVariable ["ACME_usedBags",[["used1","Saline",501,1,-1,500,"bad"]]];',
    '_medic setVariable ["ACME_usedBags",[["used1","Saline","bad",1,-1,500,"bad"]]];',
    '_medic setVariable ["ACME_usedBags",[["used1","UnknownFluid",73,1,-1,500,"unknown"]]];',
    'private _used=_medic getVariable "ACME_usedBags";_used pushBack +(_used select 0);',
    '_medic setVariable ["ACME_usedBags",[["used1","FreshBlood",73,1,2,500,"bad",7,["unresolvedFreshV1"]]]];',
    '_medic setVariable ["ACME_usedBags",[["used1","Saline",73,1,-1,500,"bag only",-1,[],"bagOnly"]]];',
])
def test_failed_used_staging_preserves_exact_source_and_does_not_allocate_tubing(change):
    execute(used_stage_setup() + change + r'''
        private _before=str (_medic getVariable "ACME_usedBags");
        [!(["used1"] call ACME_fnc_piggybackStageUsed),"invalid staging succeeded"] call _check;
        [str (_medic getVariable "ACME_usedBags")==_before
            && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []},
            "failed staging lost source contents or minted a prepared product"] call _check;
        [_factoryCalls==0 && {count _waits==0} && {count _inventorySettlements==0},
            "failed staging dispatched or consumed apparatus"] call _check;
        if (((_medic getVariable "ACME_usedBags") select 0 param [9,""]) isEqualTo "bagOnly") then {
            [count _notices==1,"bag without available tubing was refused without explaining the missing IV line"] call _check;
        };
    ''')


def test_used_carrier_timeout_keeps_prepared_product_available_for_a_later_manual_retry():
    execute(used_stage_setup() + r'''
        [["used1"] call ACME_fnc_piggybackStageUsed,"fixture could not stage used bag"] call _check;
        private _staged=+(_medic getVariable "ACME_preparedIVSets");
        private _wait=_waits select 0;
        (_wait select 1) call (_wait select 3);
        [_factoryCalls==0 && {(_medic getVariable "ACME_preparedIVSets") isEqualTo _staged},
            "carrier receipt timeout discarded or attached the product"] call _check;
        [count _notices==1,"timeout omitted its retained-product explanation"] call _check;
    ''')


@pytest.mark.parametrize("alive", (False, True))
@pytest.mark.parametrize("iv", (False, True))
def test_mechanical_connection_keeps_stopped_native_flow_and_master_switch_unchanged(alive, iv):
    execute(fluid_owner_setup() + f'''
        _patientAlive={str(alive).lower()};
        _flowRate=0;_primary set [4,{str(iv).lower()}];_ownerArgs set [5,{str(iv).lower()}];
        private _ivFlow=[[0.2,0.3,0.4],[0.5,0.6,0.7],[0,0.4,0.75],[1,0.2,0.1],[0.5,0.4,0.3],[0.1,0.2,0.3]];
        private _ioFlow=[0.2,0.3,0,0.5,0.6,0.7];
        _patient setVariable ["ACM_circulation_FluidBagsFlow_IV",_ivFlow];
        _patient setVariable ["ACM_circulation_FluidBagsFlow_IO",_ioFlow];
        _patient setVariable ["ACM_circulation_IV_Bags_Active",false];
        private _ivBefore=str _ivFlow;private _ioBefore=str _ioFlow;
        call _reserve;call _send;
        [call _ack select 3,"dead patient or stopped established line refused mechanical connection"] call _check;
        [count (call _stock)==3 && {{_factoryCalls==1}},"mechanical secondary was not created exactly once"] call _check;
        [str (_patient getVariable "ACM_circulation_FluidBagsFlow_IV")==_ivBefore
            && {{str (_patient getVariable "ACM_circulation_FluidBagsFlow_IO")==_ioBefore}}
            && {{!(_patient getVariable "ACM_circulation_IV_Bags_Active")}},
            "mechanical attachment opened a stopped native line or master flow switch"] call _check;
        [_activeWrites isEqualTo [] && {{ACME_infusion_activePatients isEqualTo []}},
            "plain mechanical attachment started clinical processing"] call _check;
    ''')


def test_dead_patient_blood_attachment_does_not_generate_clinical_blood_or_thermal_effects():
    execute(fluid_owner_setup() + r'''
        _patientAlive=false;_configuredType="Blood";_set set [8,"blood"];
        _set set [7,true];_configuredDonorType=2;_bloodCompatible=false;
        _patient setVariable ["ACM_circulation_BloodType",-1];
        call _reserve;call _send;
        [call _ack select 3,"dead patient refused the mechanical blood bag"] call _check;
        [_generatedBloodType==0 && {_bloodChecks isEqualTo []} && {_thermal isEqualTo []}
            && {_warmers isEqualTo []},"dead patient attachment generated living clinical effects"] call _check;
        [count (_events select {(_x select 0)=="ACM_circulation_handleHemolyticReaction"})==0,
            "dead patient equipment attachment started a hemolytic reaction"] call _check;
    ''')


@pytest.mark.parametrize("stock", (False, True))
@pytest.mark.parametrize("commit", (False, True))
def test_bag_only_used_secondary_requires_one_real_line_and_refunds_only_a_failed_conversion(stock, commit):
    execute(used_stage_setup() + f'''
        private _used=["used1","Saline",73,1,-1,500,"bag only",-1,[],"bagOnly"];
        _medic setVariable ["ACME_usedBags",[_used]];
        _medic setVariable ["fixtureStock",{('["ACME_IVLine"]' if stock else '[]')}];
        _commitWorks={str(commit).lower()};
        private _accepted=["used1"] call ACME_fnc_piggybackStageUsed;
        [_accepted isEqualTo {str(stock and commit).lower()},"bag-only conversion ignored real tubing availability or commit result"] call _check;
        [count _debits=={int(stock)} && {{count _refunds=={int(stock and not commit)}}},
            "bag-only conversion spent/refunded the wrong number of IV lines"] call _check;
        [([_medic,"ACME_IVLine"] call ace_common_fnc_getCountOfItem)=={int(stock and not commit)},
            "bag-only conversion changed the wrong physical line stock"] call _check;
        [count (missionNamespace getVariable ["ACME_supplyReceipts",createHashMap])==0,
            "bag-only conversion left an unsettled tubing receipt"] call _check;
    ''' + (r'''
        private _sets=_medic getVariable "ACME_preparedIVSets";
        [count _sets==1 && {((_sets select 0) select 8)=="saline"}
            && {((_sets select 0) select 9)==73}
            && {(_medic getVariable "ACME_usedBags") isEqualTo []},
            "funded conversion did not preserve exact bag contents with equipped custody"] call _check;
        [!(["used1"] call ACME_fnc_piggybackStageUsed) && {count _debits==1},
            "duplicate click consumed another administration line"] call _check;
    ''' if stock and commit else r'''
        [(_medic getVariable "ACME_usedBags") isEqualTo [_used]
            && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []}
            && {count _waits==0},"failed tubing/conversion changed exact used custody"] call _check;
    '''))


def test_bad_used_donor_facts_are_rejected_before_spending_available_tubing():
    execute(used_stage_setup() + r'''
        private _used=["used1","FreshBlood",73,1,2,500,"bag only",-1,["unresolvedFreshV1"],"bagOnly"];
        _medic setVariable ["ACME_usedBags",[_used]];
        _medic setVariable ["fixtureStock",["ACME_IVLine"]];
        [!(["used1"] call ACME_fnc_piggybackStageUsed),"unresolved donor facts reached conversion"] call _check;
        [_debits isEqualTo [] && {_refunds isEqualTo []}
            && {([_medic,"ACME_IVLine"] call ace_common_fnc_getCountOfItem)==1}
            && {(_medic getVariable "ACME_usedBags") isEqualTo [_used]},
            "donor validation consumed tubing or changed exact source contents"] call _check;
    ''')


def test_used_conversion_owner_rejection_keeps_the_paid_line_with_its_equipped_prepared_bag():
    execute(used_stage_setup() + r'''
        _configuredType="Plasma";_returnMode="wrong-type";
        _medic setVariable ["ACME_usedBags",[["used1","Plasma",73,1,-1,500,"bag only",-1,[],"bagOnly"]]];
        _medic setVariable ["fixtureStock",["ACME_IVLine"]];
        [["used1"] call ACME_fnc_piggybackStageUsed,"fixture conversion failed"] call _check;
        private _staged=+(_medic getVariable "ACME_preparedIVSets");
        _nativeReady=true;call _pollStage;
        [!(call _ack select 3),"invalid owner carrier was accepted"] call _check;
        (call _ack) call ACME_fnc_piggybackAttachAck;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo _staged
            && {(_medic getVariable "ACME_usedBags") isEqualTo []}
            && {([_medic,"ACME_IVLine"] call ace_common_fnc_getCountOfItem)==0}
            && {count _debits==1} && {_refunds isEqualTo []},
            "owner rejection lost the equipped product or refunded its committed tubing"] call _check;
    ''')


@pytest.mark.parametrize("bag_only", (False, True))
def test_returned_fresh_blood_without_a_session_id_preserves_inline_donor_facts_through_piggyback(bag_only):
    marker = ',"bagOnly"' if bag_only else ''
    execute(used_stage_setup() + f'''
        _configuredType="FreshBlood";
        private _facts=["freshV1",false,80,2];
        _medic setVariable ["ACME_usedBags",[["used1","FreshBlood",73,1,2,500,"returned donor blood",-1,_facts{marker}]]];
        _medic setVariable ["fixtureStock",["ACME_IVLine"]];
        [["used1"] call ACME_fnc_piggybackStageUsed,"complete donor return required a retired mission ID"] call _check;
        private _set=(_medic getVariable "ACME_preparedIVSets") select 0;
        [(_set select 2)=="FreshBloodBag_500_0" && {{(_set select 11) isEqualTo _facts}},
            "returned donor facts were rebound or lost while forming the action"] call _check;
        _nativeReady=true;call _pollStage;
        [call _ack select 3,"owner refused portable donor facts after native custody"] call _check;
        private _secondary=(call _stock) select 2;
        [(_secondary select 10) isEqualTo _facts && {{(_secondary select 5)==2}}
            && {{(_secondary select 1)==73}},"owner attached the seed donor instead of immutable return facts"] call _check;
        [count _debits=={int(bag_only)},"returned fresh blood spent the wrong number of branch lines"] call _check;
    ''')
