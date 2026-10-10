"""B230 actual prepared attach/register/ACK execution with explicit engine boundaries.

Config, object locality, transport, inventory UI and native publication are stand-ins.
The production carrier factory, before/after resolver, mixture math, transaction and
ACK state machines execute. These are not native Arma or real packet delivery tests.
"""
from pathlib import Path
import re
import subprocess
import pytest
from test_menu_death_lifecycle import ROOT, F, adapt, execute
from test_historical_vial_execution import map_defaults

BASE = "4f4c6403ad12eb8f248c332da800b22c9847bdba"


def raw(name, baseline=False):
    path = f"addons/acm_extended/functions/fn_{name}.sqf"
    if baseline:
        return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)
    return (ROOT / path).read_text()


def adapted(text):
    text = text.replace("canSuspend", "false")
    text = text.replace('_entry param [14, [], [[]]]', '(if (count _entry<=14) then {[]} else {_entry param [14, [], [[]]]})')
    # This VM mishandles typed param defaults for absent array elements.
    text = re.sub(r'(\b_\w+) param \[8, "", \[""\]\]', r'([\1, 8] call _stringUid)', text)
    text = text.replace("values _results", "((keys _results) apply {_results get _x})")
    text = text.replace("local _patient", "_patientLocal")
    text = text.replace('netId _medic', '"medic"')
    text = text.replace('configFile >> "ACM_Medication" >> "Medications" >> _class', '_class')
    text = text.replace('isClass (_class)', '(_class in _validClasses)')
    text = text.replace('configFile >> "ace_medical_treatment" >> "IV" >> _action', '_action')
    text = text.replace('getText (_action >> "type")', '_configuredType')
    text = text.replace('getText (_cfg >> "type")', '_configuredType')
    text = text.replace('getNumber (_cfg >> "volume")', '_configuredVolume')
    text = text.replace('isClass _cfg', '(_cfg in ["SalineIV_100","SalineIV_500","MagnesiumBag"])')
    text = re.sub(r'\bfinite (\([^\n;]+?\)|_\w+)', r'(\1 call _finite)', text)
    # Arma's HashMap key/value iteration is absent in this SQF-VM.
    text = text.replace('{private _part = _x; private _idx = _y findIf',
                        '{private _part = _x; private _y = _map get _x; private _idx = _y findIf')
    text = text.replace('forEach _map;', 'forEach (keys _map);')
    return adapt(map_defaults(text))


def function(name, baseline=False):
    return f'ACME_fnc_{name}={{' + adapted(raw(name, baseline)) + '};\n'


def setup(baseline=False):
    text = r'''
    private _stringUid={params ["_array","_index"];if (count _array<=_index) exitWith {""};private _v=_array select _index;if (isNil "_v" || {!(_v isEqualType "")}) exitWith {""};_v};
    private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    private _patientLocal=true; private _validAccess=true;private _accessType=1;private _hasY=false;
    private _configuredType="Saline";private _configuredVolume=100;
    private _validClasses=["CalciumChloride_IV","Lidocaine_IV","Epinephrine_IV","MagnesiumSulfate_IV"];
    private _bagWrites=[];private _medWrites=[];private _activeWrites=[];private _notices=[];private _logs=[];
    private _clampQueue=[];private _reopens=[];private _refunds=[];private _updates=0;private _factoryCalls=0;
    ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
    ACME_infusion_allowedBagTypes=["Saline"];
    ACME_infusion_premixedByType=createHashMap;
    ACME_infusion_defaultDurationSeconds=createHashMap;
    ACME_infusion_activePatients=[];
    ACME_infusion_defaultDropSet=20;
    ACME_fnc_isYLineAccess={_hasY};
    ACME_fnc_transfusionAccessValid={_validAccess};
    ACM_circulation_fnc_getAccessType={_accessType};
    ACM_circulation_fnc_isBloodTypeCompatible={true};
    ACM_circulation_fnc_updateActiveFluidBags={_updates=_updates+1;};
    ACM_circulation_fnc_setRuntimeState={params ["_p","_changes"];{
        _x params ["_key","_value"];
        private _name=switch (_key) do {case "ivBagsActive":{"ACM_circulation_IV_Bags_Active"};case "fluidBagsFlowIV":{"ACM_circulation_FluidBagsFlow_IV"};default {"ACM_circulation_FluidBagsFlow_IO"};};
        _p setVariable [_name,_value];_activeWrites pushBack [_key,_value];
    } forEach _changes;};
    ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];true};
    ACME_fnc_ivBagsCommit={params ["_p","_bags",["_public",true]];
        _p setVariable ["ACM_circulation_IV_Bags",_bags];
        if (_public) then {_bagWrites pushBack [str _bags,str (_p getVariable ["ACME_infusion_BagMedications",[]])];};true};
    ACME_fnc_infusionMedicationStateCommit={params ["_p","_entries",["_public",true]];
        _p setVariable ["ACME_infusion_BagMedications",_entries];
        _p setVariable ["ACME_infusion_HasBagMedications",!(_entries isEqualTo [])];
        if (_public) then {_medWrites pushBack (+_entries);};true};
    ACME_fnc_clampPositionToDrops={(_this select 0)*100};
    ACME_fnc_clinicalNotice={_notices pushBack _this;};
    ACME_fnc_reopenTransfusion={_reopens pushBack _this;};
    ACME_fnc_queueInfusionClamp={_clampQueue pushBack _this;};
    ace_medical_treatment_fnc_addToTriageCard={};
    ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
    ace_common_fnc_addToInventory={_refunds pushBack _this;};
    _patient setVariable ["ACME_clinicalEpoch",1];
    _patient setVariable ["ACM_circulation_IV_Bags",createHashMap];
    _patient setVariable ["ACME_infusion_BagMedications",[]];
    _patient setVariable ["ACM_circulation_FluidBagsFlow_IV",[[1,1,1],[1,1,1],[0,1,1],[1,1,1],[1,1,1],[1,1,1]]];
    _patient setVariable ["ACM_circulation_FluidBagsFlow_IO",[1,0,1,1,1,1]];
    '''
    for name in ('preparedComponents', 'clinicalEpoch', 'preparedAttachLocal', 'infusionRegisterLocal',
                 'infusionRegisterCore', 'canMedicateBagContext', 'isYLineBagContext', 'findTrackedBag',
                 'bagIdentity', 'infusionFlow', 'resumeSiteFlow', 'yBagReplaceEmpty', 'preparedAttachAck'):
        text += function(name, baseline)
    if not baseline:
        text += function('preparedCarrierResolve')
        text += function('preparedAttachBlockReason')
        text += function('preparedAttachMessage')
    path = 'addons/core/overrides/fnc_ivBagLocal.sqf'
    native = subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT,text=True) if baseline else (ROOT/path).read_text()
    native = native.replace('ALL_BODY_PARTS','ACME_infusion_bodyParts').replace('FBTK_ARRAY_DATA','[]')
    native = native.replace('QUOTE(ACE_ADDON(medical_treatment))','"ace_medical_treatment"')
    native = native.replace('configFile >> "ace_medical_treatment" >> "IV"','"IV"')
    native = native.replace('_defaultConfig >> _classname','_classname')
    native = native.replace('GET_NUMBER(_ivConfig >> "volume",getNumber (_defaultConfig >> "volume"))','_configuredVolume')
    native = native.replace('GET_STRING(_ivConfig >> "type",getText (_defaultConfig >> "type"))','_configuredType')
    native = native.replace('GET_NUMBER(_ivConfig >> "bloodtype",-1)','-1').replace('GET_BLOODTYPE(_patient)','0')
    text += 'ACM_circulation_fnc_setIVBagsState=ACME_fnc_ivBagsCommit;\n'
    text += '_nativeCarrier={' + adapted(native) + '};\n'
    text += r'''
    private _returnMode="normal";
    ace_medical_treatment_fnc_ivBagLocal={
        _factoryCalls=_factoryCalls+1;
        if (_returnMode=="no-create") exitWith {""};
        private _ret=_this call _nativeCarrier;
        private _bag=((_patient getVariable "ACM_circulation_IV_Bags") get (_this select 1)) select 0;
        switch (_returnMode) do {
            case "empty": {""};
            case "bool": {true};
            case "nil": {nil};
            case "wrong": {"unrelated-uid"};
            case "legacy": {_bag resize 8;nil};
            case "wrong-access": {_bag set [2,99];_ret};
            case "wrong-site": {_bag set [3,2];_ret};
            case "wrong-type": {_bag set [0,"Blood"];_ret};
            case "wrong-volume": {_bag set [1,1];_ret};
            case "double": {_this call _nativeCarrier;_ret};
            default {_ret};
        }
    };
    private _set=["set1","saline100","SalineIV_100","","","","CaCl",false,"saline",100];
    private _prepared=["set1","saline100","SalineIV_100","CalciumChloride",1000,600,20,0,0,10,110,0,_medic,objNull,[["CalciumChloride",1000,1]],"set1",100];
    private _store={_medic setVariable ["ACME_preparedIVSets",[_set]];_medic setVariable ["ACME_infusion_PreparedBags",[_prepared]];};
    call _store;
    private _request=[_medic,_patient,_medic,"saline100","SalineIV_100",objNull,"leftarm",true,0,110,_prepared,0,"1g CaCl"];
    private _stock={(_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_request select 6,[]]};
    private _entries={_patient getVariable ["ACME_infusion_BagMedications",[]]};
    private _ack={(_events select ((count _events)-1)) select 1};
    private _send={[_request,"req1",1] call ACME_fnc_preparedAttachLocal;};
    private _pending={missionNamespace setVariable ["ACME_preparedPending",createHashMapFromArray [["req1",[_request,10,false,1]]]];};
    '''
    # Also adapt fixture HashMap defaults (without changing decision logic).
    return map_defaults(text)


def test_b229_reproduces_report_when_native_callback_return_loses_identity():
    execute(setup(True)+r'''
      _returnMode="empty";call _pending;call _send;
      [!(call _ack select 1),"baseline did not reject"] call _check;
      [count (call _stock)==1 && {(call _stock select 0 select 1)==100},"baseline no longer leaves 100mL saline"] call _check;
      [call _entries isEqualTo [],"baseline unexpectedly retained calcium"] call _check;
      (call _ack) call ACME_fnc_preparedAttachAck;
      [count (_medic getVariable "ACME_infusion_PreparedBags")==1,"baseline consumed rejected set"] call _check;
    ''')


@pytest.mark.parametrize('return_mode',['normal','empty','bool','nil','wrong','legacy'])
@pytest.mark.parametrize('route', ['iv','io'])
def test_exact_carrier_attaches_complete_110ml_calcium_mixture_despite_callback_return(return_mode,route):
    move='' if route=='iv' else '_request set [6,"body"];_request set [7,false];_request set [8,-1];'
    execute(setup()+move+f'_returnMode="{return_mode}";'+r'''
      call _pending;call _send;
      [call _ack select 1,"valid mixture rejected"] call _check;
      private _bags=call _stock;private _meds=call _entries;
      [count _bags==1 && {(_bags select 0 select 1)==110} && {(_bags select 0 select 6)==110},"carrier volume wrong"] call _check;
      [count _meds==1 && {(_meds select 0 select 14)==1000} && {(_meds select 0 select 10)==110},"calcium mass wrong"] call _check;
      [(_meds select 0 select 23)==(_bags select 0 select 8),"medication lost physical carrier"] call _check;
      [abs ((_meds select 0 select 26)-1000/110)<.00001,"concentration wrong"] call _check;
      [(_meds select 0 select 22)==0,"attachment opened roller clamp"] call _check;
      [count _bagWrites==1 && {count _medWrites==1},"intermediate plain/partial state was published"] call _check;
      [(_bagWrites select 0 select 1)!="[]","carrier published without medications"] call _check;
      [count (_medic getVariable "ACME_infusion_PreparedBags")==1,"set removed before ACK"] call _check;
      (call _ack) call ACME_fnc_preparedAttachAck;
      [(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo [] && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []},"accepted set not settled"] call _check;
      [count _clampQueue==1 && {count _logs==1},"no one-shot clamp/log handoff"] call _check;
    ''')


@pytest.mark.parametrize('failure',['no-create','wrong-site','wrong-access','wrong-type','wrong-volume','double'])
def test_ambiguous_or_invalid_creation_leaves_no_carrier_and_retains_prepared_set(failure):
    execute(setup()+f'_returnMode="{failure}";'+r'''
      call _pending;call _send;
      [!(call _ack select 1),"invalid creation accepted"] call _check;
      [call _stock isEqualTo [] && {call _entries isEqualTo []},"orphan or partial dose remained"] call _check;
      [!(_patient getVariable ["ACM_circulation_IV_Bags_Active",false]),"failed attempt activated fluids"] call _check;
      [ACME_infusion_activePatients isEqualTo [],"failed attempt entered drug worker"] call _check;
      (call _ack) call ACME_fnc_preparedAttachAck;
      [count (_medic getVariable "ACME_infusion_PreparedBags")==1 && {count (_medic getVariable "ACME_preparedIVSets")==1},"failed attachment consumed prepared stock"] call _check;
      [count _clampQueue==0 && {count _refunds==0} && {count _notices==1},"rejection incorrectly opened clamp/refunded twice"] call _check;
      [(_notices select 0 select 1) isEqualTo "Could not identify the new carrier bag.","diagnostic missing"] call _check;
    ''')


@pytest.mark.parametrize('which',[0,1])
def test_registration_failure_rolls_back_all_components_without_touching_other_lines(which):
    execute(setup()+r'''
      private _other=["Saline",70,1,1,true,-1,100,-1,"other"];
      private _oldMed=["old","leftarm",0,"Saline",1,true,-1,100,-1,100,70,"Lidocaine","Lidocaine_IV",50,35,0,10,0,10,600,20,0,0,"other",0,0,.5,1];
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_other]]]];
      _patient setVariable ["ACME_infusion_BagMedications",[_oldMed]];
      _patient setVariable ["ACM_circulation_IV_Bags_Active",true];
      _patient setVariable ["ACME_clampRate_2_true_1",.01];
      _prepared set [14,[["CalciumChloride",1000,1],["Lidocaine",100,1]]];call _store;
      private _register=ACME_fnc_infusionRegisterLocal;private _calls=0;
    '''+f'private _fail={which};'+r'''
      ACME_fnc_infusionRegisterLocal={private _n=_calls;_calls=_calls+1;if (_n==_fail) exitWith {""};_this call _register};
      call _pending;call _send;
      [!(call _ack select 1) && {(call _ack select 3)=="medication-registration"},"partial mixture accepted"] call _check;
      [call _stock isEqualTo [_other],"other access changed"] call _check;
      [call _entries isEqualTo [_oldMed],"old medication changed/partial medication retained"] call _check;
      [(_patient getVariable "ACME_clampRate_2_true_1")==.01,"other clamp changed"] call _check;
      [(_patient getVariable "ACM_circulation_IV_Bags_Active"),"other line stopped"] call _check;
      [count _medWrites==1 && {(_medWrites select 0) isEqualTo [_oldMed]},"partial mixture was published"] call _check;
      (call _ack) call ACME_fnc_preparedAttachAck;
      [count (_medic getVariable "ACME_infusion_PreparedBags")==1 && {count _refunds==0},"prepared stock lost or duplicated"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['epoch','provider-down','range','access','no-site','yline','missing-set','changed-dose','occupied','action','blood','empty','overlarge-premix'])
def test_preflight_rejects_before_creating_any_fluid(invalid):
    edits={
      'epoch':'_patient setVariable ["ACME_clinicalEpoch",2];',
      'provider-down':'_medic setVariable ["ACE_isUnconscious",true];',
      'range':'_distance=9;',
      'access':'_validAccess=false;',
      'no-site':'_accessType=0;',
      'yline':'_hasY=true;',
      'missing-set':'_medic setVariable ["ACME_preparedIVSets",[]];',
      'changed-dose':'private _wrong=+_prepared;_wrong set [4,100];_medic setVariable ["ACME_infusion_PreparedBags",[_wrong]];',
      'occupied':'_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",50,1,0,true,-1,100,-1,"old"]]]]];',
      'action':'_request set [4,"InvalidAction"];',
      'blood':'_configuredType="Blood";',
      'empty':'_prepared set [10,0];call _store;',
      'overlarge-premix':'_configuredVolume=0;',
    }[invalid]
    execute(setup()+edits+r'''
      private _before=str (_patient getVariable "ACM_circulation_IV_Bags");call _send;
      [!(call _ack select 1) && {_factoryCalls==0},"invalid request created a carrier"] call _check;
      [str (_patient getVariable "ACM_circulation_IV_Bags")==_before && {call _entries isEqualTo []},"rejection mutated bag state"] call _check;
    ''')


def test_multi_component_success_commits_once_and_replays_idempotently():
    execute(setup()+r'''
      _prepared set [10,115];_prepared set [14,[["CalciumChloride",1000,1],["Lidocaine",100,1]]];call _store;
      call _pending;call _send;private _first=call _ack;
      [call _ack select 1 && {count (call _entries)==2},"mixture did not attach"] call _check;
      [count _medWrites==1 && {count (_medWrites select 0)==2},"published partial mixture"] call _check;
      call _send;[call _ack isEqualTo _first && {_factoryCalls==1},"replay duplicated carrier"] call _check;
      (call _ack) call ACME_fnc_preparedAttachAck;(call _ack) call ACME_fnc_preparedAttachAck;
      [count _clampQueue==1 && {count _logs==1},"duplicate ACK repeated UI/custody"] call _check;
    ''')


def test_different_request_id_cannot_duplicate_same_set_before_ack():
    execute(setup()+r'''
      call _send;[_request,"req2",1] call ACME_fnc_preparedAttachLocal;
      [!(call _ack select 1) && {_factoryCalls==1} && {count (call _stock)==1},"in-flight set duplicated"] call _check;
    ''')


def test_request_id_cannot_replay_success_for_changed_site():
    execute(setup()+r'''
      call _send;_request set [8,1];call _send;
      [!(call _ack select 1) && {(call _ack select 3)=="request-mismatch"} && {_factoryCalls==1},"changed replay accepted"] call _check;
    ''')


def test_locality_handoff_reroutes_without_creating_bag():
    execute(setup()+r'''
      _patientLocal=false;call _send;
      [_factoryCalls==0 && {call _stock isEqualTo []},"nonowner mutated carrier"] call _check;
      [(_events select 0 select 1)=="preparedAttach","no owner reroute"] call _check;
    ''')


def test_native_nonprepared_bag_keeps_original_public_and_active_behavior():
    execute(setup()+r'''
      ACME_fnc_syncPremixedBags={};
      [_patient,"leftarm","SalineIV_100",1,true,0,false,false] call ace_medical_treatment_fnc_ivBagLocal;
      [count _bagWrites==1 && {_patient getVariable ["ACM_circulation_IV_Bags_Active",false]},"ordinary saline path was deferred"] call _check;
      [count (call _stock)==1 && {call _entries isEqualTo []},"ordinary saline became medication"] call _check;
    ''')


def test_staged_premix_retains_partial_volume_and_scaled_dose():
    execute(setup()+r'''
      _configuredType="Magnesium";_configuredVolume=100;
      ACME_infusion_premixedByType=createHashMapFromArray [["magnesium",["MagnesiumSulfate",2000]]];
      _set set [2,"MagnesiumBag"];_set set [8,"premix"];_set set [9,40];
      _prepared=["set1","premix","MagnesiumBag","MagnesiumSulfate",800,600,20,0,0,10,100,0,_medic,objNull];
      _medic setVariable ["ACME_preparedIVSets",[_set]];
      _request set [4,"MagnesiumBag"];_request set [10,_prepared];_request pushBack _set;
      call _send;
      [call _ack select 1 && {(call _stock select 0 select 1)==40},"partial premix carrier failed"] call _check;
      [count (call _entries)==1 && {(call _entries select 0 select 14)==800},"premix dose changed/doubled"] call _check;
    ''')


def test_unscheduled_staging_and_activation_order_source_contract():
    local=raw('preparedAttachLocal'); native=(ROOT/'addons/core/overrides/fnc_ivBagLocal.sqf').read_text()
    assert 'if (canSuspend) exitWith {isNil {' in local
    assert local.index('ACME_fnc_preparedCarrierResolve') < local.index('ACME_fnc_infusionRegisterLocal')
    assert native.index('if (_deferPremixed) exitWith') < native.index('QEGVAR(circulation,IV_Bags_Active)')
    assert '[], 0, true] call ACME_fnc_infusionRegisterLocal' in local
    assert '_beforeBags' in local and '_beforeMeds' in local and 'carrier-identity' in local
    assert 'class preparedCarrierResolve {};' in (ROOT/'addons/acm_extended/config.cpp').read_text()


@pytest.mark.parametrize('returned', ['nil', 'false', '"fake-success"'])
def test_unregistered_nonempty_or_invalid_reply_is_not_a_success(returned):
    execute(setup()+f'ACME_fnc_infusionRegisterLocal={{{returned}}};'+r'''
      call _send;
      [!(call _ack select 1) && {call _stock isEqualTo []} && {call _entries isEqualTo []},"unregistered reply left a carrier"] call _check;
    ''')


def test_rejected_request_replay_is_cached_but_new_attempt_can_succeed():
    execute(setup()+r'''
      _returnMode="double";call _send;private _failed=call _ack;
      _returnMode="normal";call _send;
      [call _ack isEqualTo _failed && {_factoryCalls==1} && {call _stock isEqualTo []},"replayed rejection mutated state"] call _check;
      [_request,"req2",1] call ACME_fnc_preparedAttachLocal;
      [call _ack select 1 && {_factoryCalls==2} && {count (call _stock)==1},"new retry did not recover"] call _check;
    ''')
