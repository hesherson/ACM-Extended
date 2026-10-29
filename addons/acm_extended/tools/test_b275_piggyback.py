"""Execute connected-line identity, custody, priority and service decisions.

SQF-VM runs the checked-out helpers and service workers. Object locality, UI,
network transport, perfusion and inventory primitives are explicit boundaries.
These fixtures do not certify native Arma input or dedicated-server behavior.
"""
import re

import pytest

from test_b156_procedure_supplies import primitives
from test_b227_line_service_and_assessments import basic, service_setup, src
from test_historical_core_boundaries import block_at
from test_historical_medication_rows import iteration_scopes
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b230_prepared_infusion_transaction import inventory_boundary


def fn(name):
    source = src(name).replace('isNull ACE_player', '(ACE_player isEqualTo objNull)').replace('local ACE_player', 'true')
    source = source.replace('canSuspend', 'false')
    source = source.replace('_medic distance _p', '_distance')
    if name == 'piggybackRecover':
        source = source.replace('private _held = _y;', 'private _held = _escrow get _x;').replace('forEach _escrow;', 'forEach keys _escrow;')
    if name == 'fluidCommit':
        source = source.replace('linearConversion [0.01, 50, _totalMl, 1, 10, true]', '([0.01, 50, _totalMl, 1, 10, true] call _linear)')
    if name == 'ivBagsCommit':
        source = source.replace('private _line = _y;', 'private _line = _lines get _x;').replace('forEach _lines;', 'forEach keys _lines;')
    if name == 'clinicalBagMove':
        source = source.replace('values _moves', '(keys _moves apply {_moves get _x})')
        source = source.replace('== _originIV', 'isEqualTo _originIV')
    for variable in ('_lines', '_bags'):
        source = source.replace(', ' + variable + ', _public]', ', ' + variable + ']')
    return 'ACME_fnc_' + name + '={' + source + '};'


def helpers():
    return basic() + r'''
        ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
        private _flowRate=2;
        _hasY=false;
        ACM_circulation_fnc_getIVFlowRate={_flowRate};
        private _key="leftarm#true#0";
        private _primary=["Saline",420,1,0,true,-1,500,-1,"primary"];
        private _secondary=["Saline",100,1,0,true,-1,100,-1,"secondary"];
        private _neighbor=["Plasma",300,1,1,true,-1,500,-1,"neighbor"];
        private _map=createHashMapFromArray [["leftarm",[_primary,_secondary,_neighbor]]];
        _patient setVariable ["ACM_circulation_IV_Bags",_map];
        _patient setVariable ["ACM_circulation_FluidBagsFlow_IV",[[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]];
        _patient setVariable ["ACM_circulation_FluidBagsFlow_IO",[1,1,1,1,1,1]];
        _patient setVariable ["ACME_PiggybackLines",createHashMapFromArray [[_key,["primary","secondary",_liveEpoch]]]];
    ''' + "".join(fn(name) for name in (
        "piggybackLine", "piggybackRole", "piggybackFlow", "piggybackEligible",
        "lineWarmer", "lineWarmerRate",
    ))


@pytest.mark.parametrize("cause", ["valid", "epoch", "missing", "iv", "site", "uid", "duplicate"])
def test_piggyback_relation_requires_both_distinct_physical_uids_at_the_exact_access(cause):
    change = {
        "valid": "",
        "epoch": "_liveEpoch=2;",
        "missing": "(_map get \"leftarm\") deleteAt 1;",
        "iv": "_secondary set [4,false];",
        "site": "_secondary set [3,1];",
        "uid": "_secondary set [8,\"replacement\"];",
        "duplicate": "_secondary set [8,\"primary\"];",
    }[cause]
    execute(helpers() + change + r'''
        private _line=[_patient,"leftarm",true,0] call ACME_fnc_piggybackLine;
    ''' + f'[(_line isEqualTo []) isEqualTo {str(cause != "valid").lower()},"stale/ambiguous relation survived"] call _check;' + r'''
        [[_patient,"leftarm",true,1] call ACME_fnc_piggybackLine isEqualTo [],"neighbor access inherited relation"] call _check;
        [[_patient,"leftarm",false,0] call ACME_fnc_piggybackLine isEqualTo [],"IO inherited IV relation"] call _check;
    ''')


@pytest.mark.parametrize("volume", [0, .005, .01, .011, 100])
def test_secondary_holds_primary_until_depleted_and_roles_remain_distinct(volume):
    execute(helpers() + f'_secondary set [1,{volume}];' + r'''
        [[_patient,"leftarm","primary"] call ACME_fnc_piggybackRole=="Primary","primary label lost"] call _check;
        [[_patient,"leftarm","secondary"] call ACME_fnc_piggybackRole=="Secondary","secondary label lost"] call _check;
        [[_patient,"leftarm","neighbor"] call ACME_fnc_piggybackRole=="","neighbor incorrectly labeled"] call _check;
        private _primaryFlow=[_patient,"leftarm",true,0,"primary"] call ACME_fnc_piggybackFlow;
        private _secondaryFlow=[_patient,"leftarm",true,0,"secondary"] call ACME_fnc_piggybackFlow;
    ''' + f'[_primaryFlow isEqualTo [{str(volume > .01).lower()},false],"primary priority wrong"] call _check;' + r'''
        [_secondaryFlow isEqualTo [false,true],"secondary role changed with remaining volume"] call _check;
        [[_patient,"leftarm",true,1,"neighbor"] call ACME_fnc_piggybackFlow isEqualTo [false,false],"neighbor was held"] call _check;
    ''')


@pytest.mark.parametrize("primary,candidate,infusion,want", [
    ("Saline", "Saline", False, True), ("Saline", "Saline", True, True),
    ("Saline", "Plasma", False, False), ("Saline", "Blood", False, False),
    ("Plasma", "Plasma", False, True), ("Plasma", "Saline", True, False),
    ("PlasmaLyte", "PlasmaLyte", False, True),
    ("Blood", "Blood", False, False), ("FreshBlood", "Saline", False, False),
    ("FBTK", "Saline", False, False), ("ACME_Propofol", "Saline", True, False),
    ("Saline", "ACME_Propofol", True, False), ("ACME_SalineY", "Saline", False, False),
])
def test_candidate_filter_matches_owner_compatibility_rules(primary, candidate, infusion, want):
    # Keep historical case IDs while updating the intentionally relaxed B289
    # plain-fluid contract. Medicated saline and special apparatus stay gated.
    if not infusion and (primary, candidate) in {
        ("Saline", "Plasma"), ("Saline", "Blood"),
        ("Blood", "Blood"), ("FreshBlood", "Saline"),
    }:
        want = True
    execute(helpers() + f'''
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        _primary set [0,"{primary}"];
        _map set ["leftarm",[_primary,_neighbor]];
        private _accepted=[_patient,"leftarm",true,0,"{candidate}",{str(infusion).lower()}] call ACME_fnc_piggybackEligible;
        [_accepted isEqualTo {str(want).lower()},"candidate bypassed compatibility gate"] call _check;
    ''')


@pytest.mark.parametrize("cause", ["y", "job", "duplicate", "empty", "stopped", "detached", "unplugged", "medicated", "noaccess"])
def test_piggyback_cannot_start_on_a_busy_or_unusable_primary(cause):
    change = {
        "y": "_hasY=true;",
        "job": '_patient setVariable ["ACME_yFlushJobs",createHashMapFromArray [[_key,[1]]]];',
        "duplicate": '_map set ["leftarm",[_primary,+_primary,_neighbor]];',
        "empty": "_primary set [1,0];",
        "stopped": "_flowRate=0;",
        "detached": '_patient setVariable ["ACME_detachedBags",["primary"]];',
        "unplugged": '_patient setVariable ["ACME_IV_DisconnectedBagUIDs",["primary"]];',
        "medicated": 'private _e=[];_e set [23,"primary"];_patient setVariable ["ACME_infusion_BagMedications",[_e]];',
        "noaccess": "_accessValid=false;",
    }[cause]
    execute(helpers() + r'''
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        _map set ["leftarm",[_primary,_neighbor]];
    ''' + change + f'''
        [([_patient,"leftarm",true,0,"Saline",false] call ACME_fnc_piggybackEligible) isEqualTo {str(cause == "stopped").lower()},"blocked primary or closed-clamp attachment resolved incorrectly"] call _check;
    ''')


@pytest.mark.parametrize("kind,rate,expected", [
    ("Saline", 0, 0), ("Saline", 60, 60), ("Saline", 300, 200),
    ("ACME_SalineY", 300, 200), ("Plasma", 0, 0), ("Plasma", 60, 60),
    ("Plasma", 150, 100), ("Blood", 90, 90), ("Blood", 250, 250),
])
def test_shared_downstream_warmer_caps_only_the_exact_access_and_never_raises_flow(kind, rate, expected):
    execute(helpers() + f'''
        _patient setVariable ["ACME_lineWarmers",createHashMapFromArray [[_key,true]]];
        private _value=[_patient,"leftarm",true,0,"{kind}",{rate}] call ACME_fnc_lineWarmerRate;
        [abs (_value-{expected})<.001,"fluid warmer cap wrong"] call _check;
        private _neighborRate=[_patient,"leftarm",true,1,"{kind}",{rate}] call ACME_fnc_lineWarmerRate;
        [_neighborRate=={rate},"neighbor warmer rate changed"] call _check;
        [count (_patient getVariable "ACME_lineWarmers")==1,"reader created another warmer for connected branch"] call _check;
    ''')


def escrow_setup():
    return basic() + inventory_boundary() + r'''
        private _set=["set1","ACM_SalineBag_100","SalineIV_100","","",objNull,"Saline",false,"saline",100,0];
        private _prep=["set1","ACM_SalineBag_100","SalineIV_100","TXA",1000,0,20,60,1,100,100,0,objNull,objNull,[],"set1",100];
        private _args=[_medic,_patient,"request1","set1","leftarm",true,0,"primary",1,_set,_prep,100];
        private _fingerprint=[_medic,"set1","leftarm",true,0,"primary",1,+_set,+_prep,100];
        private _requests=createHashMapFromArray [["request1",[_args,100,false]]];
        missionNamespace setVariable ["ACME_piggybackRequests",_requests];
        _medic setVariable ["ACME_preparedIVSets",[]];
        _medic setVariable ["ACME_infusion_PreparedBags",[]];
        _medic setVariable ["ACME_piggybackEscrow",createHashMapFromArray [["set1",["request1",_patient,1,_set,_prep,100,_args]]]];
        private _clamps=[];private _refresh=0;
        ACME_fnc_piggybackWorkflow={};
        ACME_fnc_queueInfusionClamp={_clamps pushBack _this;};
        ACME_fnc_updateTransfusionControls={_refresh=_refresh+1;};
    ''' + fn("piggybackRecover") + fn("piggybackAttachAck")


@pytest.mark.parametrize("accepted", [False, True])
@pytest.mark.parametrize("workflow_open", [False, True])
def test_replayed_attachment_ack_settles_escrow_once_and_respects_current_workflow(accepted, workflow_open):
    execute(escrow_setup() + f'''
        _patient setVariable ["ACME_piggybackResults",createHashMapFromArray [["request1",[{str(accepted).lower()},"","dose1",100,_fingerprint]]]];
        missionNamespace setVariable ["ACME_piggybackPending",{('[_patient,"leftarm",true,0,"primary",1]' if workflow_open else '[]')}];
        private _reply=[_patient,"request1","set1",{str(accepted).lower()},"","dose1"];
        _reply call ACME_fnc_piggybackAttachAck;_reply call ACME_fnc_piggybackAttachAck;
        [count (_medic getVariable "ACME_piggybackEscrow")==0,"escrow never settled"] call _check;
        [count (_medic getVariable "ACME_preparedIVSets")=={int(not accepted)},"staged set lost/duplicated"] call _check;
        [count (_medic getVariable "ACME_infusion_PreparedBags")=={int(not accepted)},"prepared infusion lost/duplicated"] call _check;
        [count _clamps=={int(accepted and workflow_open)} && {{_refresh==1}},"duplicate ACK or closed workflow reopened popup"] call _check;
        if (!{str(accepted).lower()}) then {{
          [(_medic getVariable "ACME_preparedIVSets" select 0) isEqualTo _set,"refund changed exact staged record"] call _check;
          [(_medic getVariable "ACME_infusion_PreparedBags" select 0) isEqualTo _prep,"refund changed exact infusion record"] call _check;
        }};
    ''')


@pytest.mark.parametrize("cause", ["patient", "set", "request"])
def test_wrong_attachment_ack_cannot_consume_or_restore_someone_elses_prepared_set(cause):
    patient = "missionNamespace" if cause == "patient" else "_patient"
    set_id = "other" if cause == "set" else "set1"
    request_id = "other" if cause == "request" else "request1"
    execute(escrow_setup() + f'''
        _patient setVariable ["ACME_piggybackResults",createHashMapFromArray [["request1",[false,"","",100,_fingerprint]]]];
        [{patient},"{request_id}","{set_id}",false] call ACME_fnc_piggybackAttachAck;
        [count (_medic getVariable "ACME_piggybackEscrow")==1 && {{_refresh==0}},"foreign ACK settled current reservation"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [],"foreign ACK invented a refund"] call _check;
    ''')


@pytest.mark.parametrize("cause", ["missing", "outcome", "dose", "fingerprint"])
def test_unproved_ack_keeps_physical_escrow_reserved_until_owner_certificate_arrives(cause):
    change = {
        "missing": '_patient setVariable ["ACME_piggybackResults",createHashMap];',
        "outcome": '_certificate set [0,true];',
        "dose": '_certificate set [2,"other-dose"];',
        "fingerprint": '_fingerprint set [5,"other-primary"];',
    }[cause]
    execute(escrow_setup() + r'''
        private _certificate=[false,"","",100,_fingerprint];
        _patient setVariable ["ACME_piggybackResults",createHashMapFromArray [["request1",_certificate]]];
    ''' + change + r'''
        [_patient,"request1","set1",false] call ACME_fnc_piggybackAttachAck;
        [count (_medic getVariable "ACME_piggybackEscrow")==1,"unproved ACK spent/refunded physical custody"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [] && {_refresh==0},"unproved ACK leaked a staged bag"] call _check;
    ''')


@pytest.mark.parametrize("warm,physical,want_per_second", [(False, 10, 5), (True, 10, 200 / 60), (True, 1, 1), (True, 0, 0)])
def test_priming_opens_exact_line_but_finishes_only_after_actual_capped_saline_delivery(warm, physical, want_per_second):
    execute(service_setup() + f'''
        [100,false,false,500] call _init;
        _patient setVariable ["ACM_circulation_FluidBagsFlow_IO",[1,0,1,1,1,1]];
        _patient setVariable ["ACME_lineWarmers",createHashMapFromArray [[_key,{str(warm).lower()}]]];
        _admissionRate={physical};
        ["prime","once"] call _request;
        [((_patient getVariable "ACM_circulation_FluidBagsFlow_IO") select 1)==1,"valid priming never opened service path"] call _check;
        [!((_patient getVariable "ACME_YLinePrimed") get _key),"line marked primed before delivery"] call _check;
        [1] call _advance;
        [abs (_credited-{want_per_second})<.001,"prime ignored access/warmer rate"] call _check;
        [!((_patient getVariable "ACME_YLinePrimed") get _key),"partial prime opened blood path"] call _check;
        [{30 if physical else 10}] call _advance;
    ''' + (r'''
        [abs (_credited-25)<.001 && {abs (call _stock-75)<.001},"prime did not settle exactly 25 mL"] call _check;
        [(_patient getVariable "ACME_YLinePrimed") get _key,"completed delivery did not prime line"] call _check;
        [((_patient getVariable "ACM_circulation_FluidBagsFlow_IO") select 0)==1 && {((_patient getVariable "ACM_circulation_FluidBagsFlow_IO") select 2)==1},"prime changed another access"] call _check;
    ''' if physical else r'''
        [_credited==0 && {call _stock==100},"occluded prime drained fluid"] call _check;
        [!((_patient getVariable "ACME_YLinePrimed") get _key),"occluded line became primed"] call _check;
    '''))


def native_bag_worker():
    """Extract the complete canonical per-bag integration statement, not copied algebra."""
    source = (ROOT / "addons/circulation/functions/fnc_getBloodVolumeChange.sqf").read_text()
    anchor = "_fluidBagsBodyPart = _fluidBagsBodyPart apply "
    assert source.count(anchor) == 1
    start = source.index(anchor)
    source = anchor + block_at(source, start + len(anchor)) + ";"
    for macro, boundary in (
        ("HAS_TOURNIQUET_APPLIED_ON(_unit,_partIndex)", "false"),
        ("GET_IO_FLOW_X(_unit,_partIndex)", "_openFlow"),
        ("GET_IV_FLOW_X(_unit,_partIndex,_accessSite)", "_openFlow"),
        ("GET_IV_COMPLICATIONS_FLOW_X(_unit,_partIndex,_accessSite)", "0"),
        ("GET_IV_COMPLICATIONS_PAIN_X(_unit,_partIndex,_accessSite)", "0"),
        ("GET_BLOODTYPE(_unit)", "0"),
    ):
        source = source.replace(macro, boundary)
    # SQF-VM only implements select [start,length]; supply native tail length.
    source = source.replace('_x select [9]', '_x select [9,count _x]')
    source = source.replace('private _acmeBagIndex = _forEachIndex;', '_fixtureBagIndex=_fixtureBagIndex+1;private _acmeBagIndex=_fixtureBagIndex;')
    source = primitives(adapt(iteration_scopes(source), "circulation"))
    return r'''
        private _integrate={
            private _unit=_patient;private _targetBodyPart="leftarm";private _partIndex=2;
            private _fluidBagsBodyPart=(_patient getVariable "ACM_circulation_IV_Bags") get "leftarm";
            private _IVFlowMultiplier=1;private _IOFlowMultiplier=1;
            private _activeBagTypesIO=[1,1,1,1,1,1];
            private _activeBagTypesIV=[[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]];
            private _fluidPerfusionOpen=_perfusing;private _bloodBagsPresent=false;
            private _coldFlag=false;private _coldFrac=0;private _coolDrop=0;
            private _warmthAdd=0;private _warmerTempPerLiter=.8;
            private _bloodVolume=5;private _bloodVolumeChange=0;private _plasmaVolumeChange=0;
            private _salineVolumeChange=0;private _plateletCountChange=0;
            private _transfusedBloodVolumeChange=0;private _reactionBloodVolumeChange=0;
            private _freshBloodEffectiveness=0;private _transfusionPain=0;
            private _updateCountBodyPartArray=[];private _fixtureBagIndex=-1;
    ''' + source + r'''
            private _map=_patient getVariable "ACM_circulation_IV_Bags";
            _map set ["leftarm",_fluidBagsBodyPart];
            _patient setVariable ["ACM_circulation_IV_Bags",_map];
            [_fluidBagsBodyPart,_warmthAdd,_salineVolumeChange,_plasmaVolumeChange,_bloodVolumeChange]
        };
    '''


def delivery_setup(group=True, kind="Saline", warm=True):
    rate = (ROOT / "addons/circulation/functions/fnc_getIVFlowRate.sqf").read_text()
    rate = primitives(adapt(rate, "circulation"))
    return helpers() + r'''
        private _deltaT=1;private _openFlow=1;private _fraction=1;private _perfusing=true;
        private _delivery=[];private _drive=[];private _leaks=[];
        ace_medical_ivFlowRate=1;ACM_circulation_IVComplications=false;
        ACM_IO_FAST1_M=4;ACM_IO_EZ_M=3;
        ACME_infusion_premixedByType=createHashMap;
        ACME_circ_activePatients=[];
        ACME_infusion_minPulseDose=createHashMap;ACME_infusion_pulseInterval=1;
        ACME_fnc_aajtOccludes={false};
        ACME_fnc_pressureLevel={1};
        ACME_fnc_medicationLineFraction={_fraction};
        ACME_fnc_setVarNetApprox=ACME_fnc_setVarNet;
        private _linear={params ["_lo","_hi","_value","_a","_b",["_clamp",false]];private _f=(_value-_lo)/(_hi-_lo);if (_clamp) then {_f=(_f max 0) min 1;};_a+(_b-_a)*_f;};
        ACME_fnc_medicationDriveAdd={_drive pushBack _this;};
        ACME_fnc_medicationLeak={_leaks pushBack _this;};
        ace_medical_treatment_fnc_medicationLocal={_delivery pushBack _this;};
        ACME_fnc_infusionMedicationStateCommit={params ["_p","_entries"];_p setVariable ["ACME_infusion_BagMedications",_entries];true};
        _patient setVariable ["ACM_circulation_IV_Placement",[[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]];
        _patient setVariable ["ACME_hang_flowMult",4];
        _patient setVariable ["ACME_piCuffs",createHashMapFromArray [["primary",[1]],["secondary",[1]]]];
        _patient setVariable ["ACME_infusion_BagMedications",[]];
    ''' + f'''
        _primary set [0,"{kind}"];
        _secondary set [0,"{kind}"];
        _patient setVariable ["ACME_lineWarmers",createHashMapFromArray [[_key,{str(warm).lower()}]]];
        _map set ["leftarm",{('[_primary,_secondary]' if group else '[_primary]')}];
    ''' + ("" if group else '_patient setVariable ["ACME_PiggybackLines",createHashMap];') + \
        "ACM_circulation_fnc_getIVFlowRate={" + rate + "};" + \
        "".join(fn(name) for name in ("fluidCommit", "infusionFlow", "infusionDeliver", "infusionRetire")) + native_bag_worker()


@pytest.mark.parametrize("kind,cap", [("Saline", 200), ("Plasma", 100)])
def test_native_drainer_and_heat_credit_use_the_actual_capped_admitted_volume(kind, cap):
    execute(delivery_setup(False, kind) + f'''
        private _result=call _integrate;
        private _remaining=(_result select 0 select 0) select 1;
        [abs ((420-_remaining)-{cap}/60)<.001,"canonical bag drainer exceeded warmer cap"] call _check;
        [abs ((_result select 1)-(({cap}/60/1000)*.8))<.001,"heat credit did not match actual admitted fluid"] call _check;
        _fraction=.25;
        _result=call _integrate;
        [abs ((_result select 1)-(({cap}/60/1000)*.8*.25))<.001,"tissue loss still warmed systemic volume"] call _check;
        _perfusing=false;
        private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
        _result=call _integrate;
        [_before==str (_patient getVariable "ACM_circulation_IV_Bags") && {{(_result select 1)==0}},"no perfusion drained or warmed fluid"] call _check;
    ''')


@pytest.mark.parametrize("kind,rate", [("Saline", 200 / 60), ("Plasma", 100 / 60)])
def test_secondary_gravity_priority_ignores_cuff_and_hang_boost_and_resumes_primary_next_tick(kind, rate):
    execute(delivery_setup(True, kind) + f'''
        _secondary set [1,{rate * 1.5}];
        private _result=call _integrate;
        [(_result select 0 select 0 select 1)==420,"held primary drained"] call _check;
        [abs ((_result select 0 select 1 select 1)-{rate * .5})<.001,"secondary ignored native gravity/warmer ceiling"] call _check;
        [abs ((_result select 1)-{rate / 1000 * .8})<.001,"only flowing secondary should add heat"] call _check;
        _result=call _integrate;
        [(_result select 0 select 0 select 1)==420 && {{(_result select 0 select 1 select 1)==0}},"depletion tick drained primary too early"] call _check;
        _result=call _integrate;
        [(_result select 0 select 0 select 1)<420 && {{(_result select 0 select 1 select 1)==0}},"completed secondary never released primary"] call _check;
        [(_result select 1)>0,"newly flowing primary was not warmed downstream"] call _check;
        [count (_patient getVariable "ACME_lineWarmers")==1,"branch transition invented another warmer"] call _check;
    ''')


@pytest.mark.parametrize("kind,factor", [("Saline", 1.2), ("Plasma", 1)])
@pytest.mark.parametrize("gauge", [1, 5, 6])
def test_unheated_secondary_uses_native_gauge_gravity_without_an_arbitrary_rate_limit(kind, factor, gauge):
    execute(delivery_setup(True, kind, False) + f'''
        (_patient getVariable "ACM_circulation_IV_Placement" select 2) set [0,{gauge}];
        private _gravity=[_patient,2,true,0,-1,"secondary",true] call ACM_circulation_fnc_getIVFlowRate;
        private _result=call _integrate;
        [abs ((100-(_result select 0 select 1 select 1))-_gravity*{factor})<.001,"secondary bypassed native gravity/gauge physics or inherited pressure/hang"] call _check;
        [(_result select 0 select 0 select 1)==420 && {{(_result select 1)==0}},"unheated held primary drained or created heat"] call _check;
        ((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm" select 1) set [1,0];
        private _primaryRate=[_patient,2,true,0,-1,"primary",false] call ACM_circulation_fnc_getIVFlowRate;
        _result=call _integrate;
        [abs ((420-(_result select 0 select 0 select 1))-_primaryRate*{factor})<.001,"empty secondary kept dividing the primary flow"] call _check;
    ''')


@pytest.mark.parametrize("ml_per_second", [0, .25, 4])
def test_medicated_secondary_uses_existing_roller_rate_and_delivers_only_secondary_dose(ml_per_second):
    admitted = min(ml_per_second, 200 / 60)
    execute(delivery_setup() + f'''
        private _entry=[];_entry resize 28;
        _entry set [0,"dose1"];_entry set [1,"leftarm"];_entry set [2,1];
        _entry set [4,0];_entry set [5,true];_entry set [9,100];_entry set [10,100];
        _entry set [11,"TXA"];_entry set [12,"TXA_IV"];_entry set [13,1000];
        _entry set [14,1000];_entry set [15,0];_entry set [16,0];
        _entry set [20,20];_entry set [21,{ml_per_second}*60*20];_entry set [22,-1];
        _entry set [23,"secondary"];_entry set [24,0];_entry set [25,0];_entry set [26,10];
        _patient setVariable ["ACME_infusion_BagMedications",[_entry]];
        private _result=call _integrate;
        [(_result select 0 select 0 select 1)==420,"medication carrier let primary drain"] call _check;
        [abs ((_result select 0 select 1 select 1)-(100-{admitted}))<.001,"secondary ignored clamp/gravity cap"] call _check;
        [abs ((_entry select 14)-(1000-{admitted*10}))<.001,"remaining dose did not match carrier drain"] call _check;
        private _delivered=0;{{_delivered=_delivered+(_x select 3);}} forEach _delivery;
        [abs (_delivered-{admitted*10})<.001,"native medication callback got wrong/doubled dose"] call _check;
        [abs ((_result select 1)-({admitted}/1000*.8))<.001,"medicated fluid warmed more than once"] call _check;
    ''')


def move_setup(kind="pib"):
    return helpers() + r'''
        ace_common_fnc_isAwake={true};
        ACM_circulation_fnc_setIVBagsState={params ["_p","_bags"];_p setVariable ["ACM_circulation_IV_Bags",_bags];true};
        ACM_circulation_fnc_getAccessType={1};
        ACM_circulation_fnc_updateActiveFluidBags={};
        ACM_circulation_fnc_setRuntimeState={};
        ACME_fnc_infusionMedicationStateCommit={params ["_p","_entries"];_p setVariable ["ACME_infusion_BagMedications",_entries];true};
        private _entry=[];_entry resize 24;_entry set [1,"leftarm"];_entry set [2,1];
        _entry set [4,0];_entry set [5,true];_entry set [23,"secondary"];
        _patient setVariable ["ACME_infusion_BagMedications",[_entry]];
        _patient setVariable ["ACME_bagMoves",createHashMap];
        _patient setVariable ["ACME_lineWarmers",createHashMapFromArray [[_key,true]]];
        private _warmerRecord=["device1",_medic,1,100];
        _patient setVariable ["ACME_lineWarmerCustody",createHashMapFromArray [[_key,_warmerRecord]]];
        private _reserve={[_patient,_medic,"secondary","reserve","leftarm",true,0,1,"move1"] call ACME_fnc_clinicalBagMove;};
        private _place={[_patient,_medic,"secondary","place","rightarm",true,0,1,"move1"] call ACME_fnc_clinicalBagMove;};
    ''' + "".join(fn(name) for name in (
        "isYLineAccess", "lineWarmerMove", "lineWarmerDetach", "piggybackLinesCommit", "ivBagsCommit", "yLinesCommit",
        "resumeSiteFlow", "detachedBagsCommit", "clinicalBagMove",
    )) + (r'''
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        _primary set [0,"Blood"];_secondary set [0,"ACME_SalineY"];
        _patient setVariable ["ACME_YLines",[_key]];
        _patient setVariable ["ACME_YLinePrimed",createHashMapFromArray [[_key,true]]];
        _patient setVariable ["ACME_YLineDirty",createHashMapFromArray [[_key,true]]];
        _patient setVariable ["ACME_YLineUnitsSinceFlush",createHashMapFromArray [[_key,2]]];
        _patient setVariable ["ACME_YLineVolSinceFlush",createHashMapFromArray [[_key,1000]]];
    ''' if kind == "y" else "")


@pytest.mark.parametrize("kind", ["pib", "y"])
def test_move_reservation_and_cancel_leave_connected_bags_and_warmer_on_source(kind):
    execute(move_setup(kind) + r'''
        private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
        call _reserve;
        [_before==str (_patient getVariable "ACM_circulation_IV_Bags"),"Move Bag detached before destination selection"] call _check;
        [count (_patient getVariable "ACME_bagMoves")==1,"move intent was not reserved"] call _check;
        [_patient,_medic,"secondary","cancel","leftarm",true,0,1,"move1"] call ACME_fnc_clinicalBagMove;
        [_before==str (_patient getVariable "ACM_circulation_IV_Bags"),"cancel/close lost connected bags"] call _check;
        [count (_patient getVariable "ACME_bagMoves")==0 && {(_events findIf {(_x select 0)=="ACME_lineWarmerReturn"})<0},"cancel lost warmer or retained intent"] call _check;
        [[_patient,"leftarm",true,0] call ACME_fnc_lineWarmer,"cancel moved downstream warmer"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["pib", "y"])
def test_owner_move_preserves_complete_group_uid_bindings_and_shared_device(kind):
    execute(move_setup(kind) + r'''
        call _reserve;call _place;
        private _bags=_patient getVariable "ACM_circulation_IV_Bags";
        private _from=_bags get "leftarm";private _to=_bags get "rightarm";
        [count _from==1 && {(_from select 0 select 8)=="neighbor"},"move took neighboring access"] call _check;
        [count _to==2 && {(_to apply {_x select 8}) isEqualTo ["primary","secondary"]},"connected group was split/lost"] call _check;
        [(_to findIf {(_x select 3)!=0 || {!(_x select 4)}})<0,"destination access binding wrong"] call _check;
        [_entry select 1=="rightarm" && {_entry select 2==1} && {_entry select 4==0} && {_entry select 5},"medication retained source index/access"] call _check;
        [!([_patient,"leftarm",true,0] call ACME_fnc_lineWarmer) && {[_patient,"rightarm",true,0] call ACME_fnc_lineWarmer},"shared warmer failed to move"] call _check;
        [((_patient getVariable "ACME_lineWarmerCustody") get "rightarm#true#0") isEqualTo _warmerRecord && {(_events findIf {(_x select 0)=="ACME_lineWarmerReturn"})<0},"movement returned/duplicated physical warmer"] call _check;
        [count (_patient getVariable "ACME_bagMoves")==0,"accepted move retained old intent"] call _check;
    ''' + (r'''
        [[_patient,"rightarm",true,0] call ACME_fnc_piggybackLine isEqualTo ["primary","secondary",1],"PiB relation failed to move with physical endpoints"] call _check;
    ''' if kind == "pib" else r'''
        [(_patient getVariable "ACME_YLines") isEqualTo ["rightarm#true#0"],"Y topology stayed at source"] call _check;
        [(_patient getVariable "ACME_YLinePrimed") get "rightarm#true#0","moved primed Y line required priming again"] call _check;
        [(_patient getVariable "ACME_YLineDirty") get "rightarm#true#0","moved Y lost required flush state"] call _check;
        [((_patient getVariable "ACME_YLineUnitsSinceFlush") get "rightarm#true#0")==2 && {((_patient getVariable "ACME_YLineVolSinceFlush") get "rightarm#true#0")==1000},"moved Y reset transfusion history"] call _check;
    '''))


@pytest.mark.parametrize("cause", ["noaccess", "occupied", "service", "warmer", "oldtoken"])
def test_rejected_destination_keeps_original_connected_assembly(cause):
    change = {
        "noaccess": "_accessValid=false;",
        "occupied": '_map set ["rightarm",[["Saline",100,1,0,true,-1,100,-1,"other"]]];',
        "service": '_patient setVariable ["ACME_yFlushJobs",createHashMapFromArray [[_key,[1]]]];',
        "warmer": '(_patient getVariable "ACME_lineWarmers") set ["rightarm#true#0",true];',
        "oldtoken": 'private _movesNow=_patient getVariable "ACME_bagMoves";(_movesNow get "secondary") set [5,"successor"];',
    }[cause]
    execute(move_setup() + r'''
        call _reserve;
    ''' + change + r'''
        private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
        call _place;
        [_before==str (_patient getVariable "ACM_circulation_IV_Bags"),"rejected place changed physical bag custody"] call _check;
        [[_patient,"leftarm",true,0] call ACME_fnc_lineWarmer && {(_events findIf {(_x select 0)=="ACME_lineWarmerReturn"})<0},"rejected move moved/returned source warmer"] call _check;
        [count (_patient getVariable "ACME_bagMoves")==1,"old/rejected callback consumed successor move intent"] call _check;
    ''')
