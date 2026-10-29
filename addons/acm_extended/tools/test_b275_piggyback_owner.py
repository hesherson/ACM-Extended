"""Execute the B275 piggyback owner transaction against adverse request inputs.

Object/config/locality/publication/transport commands are explicit boundaries.
The checked-out native carrier factory, exact before/after carrier resolver,
medication registration, eligibility and owner transaction execute in SQF-VM.
These tests do not certify Arma UI or real network delivery.
"""
import pytest

from test_b230_prepared_infusion_transaction import adapted, raw, setup
from test_menu_death_lifecycle import execute


def owner_function(name):
    source = adapted(raw(name)).replace("serverTime", "_serverTime")
    # Config command whitespace differs from the older prepared-attach source.
    source = source.replace("isClass(_class)", "(_class in _validClasses)")
    return f"ACME_fnc_{name}={{" + source + "};\n"


def owner_setup():
    return setup() + r'''
      private _serverTime=100;
      private _flowRate=2;
      ace_common_fnc_isAwake={true};
      ACM_circulation_fnc_getIVFlowRate={_flowRate};
      private _primary=["Saline",420,1,0,true,-1,500,-1,"primary"];
      private _neighbor=["Plasma",300,1,1,true,-1,500,-1,"neighbor"];
      private _oldMed=["old","leftarm",1,"Plasma",1,true,-1,500,-1,500,300,"Lidocaine","Lidocaine_IV",50,30,0,10,0,10,600,20,0,0,"neighbor",0,0,.1,1];
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_primary,_neighbor]]]];
      _patient setVariable ["ACM_circulation_IV_Bags_Active",true];
      _patient setVariable ["ACME_infusion_BagMedications",[_oldMed]];
      _patient setVariable ["ACM_circulation_FluidBagsFlow_IV",[[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]];
      _patient setVariable ["ACME_PiggybackLines",createHashMap];
      _patient setVariable ["ACME_piggybackResults",createHashMap];
      _medic setVariable ["ACME_preparedIVSets",[]];
      _medic setVariable ["ACME_infusion_PreparedBags",[]];
      private _ownerArgs=[_medic,_patient,"pib1","set1","leftarm",true,0,"primary",1,_set,_prepared,100];
      private _reserve={_medic setVariable ["ACME_piggybackEscrow",createHashMapFromArray [["set1",["pib1",_patient,1,_set,_prepared,100,+_ownerArgs]]]];};
      call _reserve;
      _stock={(_patient getVariable "ACM_circulation_IV_Bags") get "leftarm"};
      _send={_ownerArgs call ACME_fnc_piggybackAttachLocal;};
      // Keep the actual factory. Mutate only the carrier it has just appended;
      // the pre-existing primary and neighboring line are never fixture targets.
      ace_medical_treatment_fnc_ivBagLocal={
        _factoryCalls=_factoryCalls+1;
        if (_returnMode=="false-success") exitWith {true};
        private _ret=_this call _nativeCarrier;
        private _bags=(_patient getVariable "ACM_circulation_IV_Bags") get (_this select 1);
        private _bag=_bags select ((count _bags)-1);
        switch (_returnMode) do {
          case "empty": {""};
          case "bool": {true};
          case "nil": {nil};
          case "wrong": {"unrelated-uid"};
          case "wrong-site": {_bag set [3,2];_ret};
          case "wrong-access": {_bag set [2,99];_ret};
          case "wrong-type": {_bag set [0,"Blood"];_ret};
          case "wrong-volume": {_bag set [1,1];_ret};
          case "double": {_this call _nativeCarrier;_ret};
          default {_ret};
        }
      };
      private _assertUnchanged={
        [call _stock isEqualTo [_primary,_neighbor],"primary or neighboring physical bag changed"] call _check;
        [call _entries isEqualTo [_oldMed],"old medications changed or partial new medication remained"] call _check;
        [count (_patient getVariable "ACME_PiggybackLines")==0,"failed attach left topology"] call _check;
        [_patient getVariable "ACM_circulation_IV_Bags_Active","failed attach stopped existing fluids"] call _check;
        [count (_medic getVariable "ACME_piggybackEscrow")==1,"owner consumed or refunded escrow before provider ACK"] call _check;
        [count _refunds==0,"owner invented an inventory refund"] call _check;
      };
    ''' + "".join(owner_function(name) for name in (
        "piggybackLine", "piggybackRole", "piggybackFlow", "piggybackEligible",
        "piggybackLinesCommit", "piggybackAttachLocal",
    ))


@pytest.mark.parametrize("infusion", [False, True])
@pytest.mark.parametrize("return_mode", ["normal", "empty", "bool", "nil", "wrong"])
def test_exact_secondary_attaches_once_from_physical_carrier_proof(infusion, return_mode):
    edit = "" if infusion else '_ownerArgs set [10,[]];_prepared=[];call _reserve;'
    execute(owner_setup() + edit + f'_returnMode="{return_mode}";' + r'''
      call _send;
      [call _ack select 3,"valid secondary rejected"] call _check;
      private _bags=call _stock;
      [count _bags==3,"secondary not created exactly once"] call _check;
      [_bags select 0 isEqualTo _primary && {_bags select 1 isEqualTo _neighbor},"existing physical bags changed"] call _check;
      private _secondary=_bags select 2;
      private _line=[_patient,"leftarm",true,0] call ACME_fnc_piggybackLine;
      [_line isEqualTo ["primary",_secondary select 8,1],"topology lost exact physical UID endpoints"] call _check;
      private _first=call _ack;
      call _send;
      [call _ack isEqualTo _first && {_factoryCalls==1},"exact replay created another secondary"] call _check;
      [count _bagWrites==1 && {count _medWrites==1} && {count _logs==1},"attach/replay published partial state or logged twice"] call _check;
      [count (_medic getVariable "ACME_piggybackEscrow")==1 && {count _refunds==0},"owner settled provider custody directly"] call _check;
    ''' + (r'''
      [(_secondary select 1)==110 && {(_secondary select 6)==110},"infusion exact mixed volume lost"] call _check;
      private _meds=call _entries;
      [count _meds==2 && {_meds select 0 isEqualTo _oldMed},"infusion registration changed neighboring medication"] call _check;
      [(_meds select 1 select 23)==(_secondary select 8) && {(_meds select 1 select 14)==1000},"dose is not bound to actual carrier UID"] call _check;
      [abs ((_meds select 1 select 26)-1000/110)<.00001,"mixture concentration wrong"] call _check;
      [(_meds select 1 select 22)==0,"attachment opened secondary roller clamp"] call _check;
      [ACME_infusion_activePatients isEqualTo [_patient],"successful infusion not enrolled"] call _check;
    ''' if infusion else r'''
      [(_secondary select 1)==100 && {(_secondary select 6)==100},"plain secondary volume wrong"] call _check;
      [call _entries isEqualTo [_oldMed],"plain secondary created medication"] call _check;
      [ACME_infusion_activePatients isEqualTo [],"plain secondary enrolled in medication worker"] call _check;
    '''))


def test_same_request_id_with_changed_fingerprint_cannot_attach_or_ack_another_action():
    execute(owner_setup() + r'''
      call _send;
      private _eventsBefore=count _events;
      private _bagsBefore=str (call _stock);
      _ownerArgs set [6,1];call _send;
      [count _events==_eventsBefore && {_factoryCalls==1},"altered replay reused receipt or created another bag"] call _check;
      [str (call _stock)==_bagsBefore && {count _logs==1},"altered replay changed accepted physical state"] call _check;
    ''')


def test_event_before_escrow_publication_is_retryable_without_terminal_rejection():
    execute(owner_setup() + r'''
      _medic setVariable ["ACME_piggybackEscrow",createHashMap];call _send;
      [count _events==0 && {_factoryCalls==0} && {count (_patient getVariable "ACME_piggybackResults")==0},"missing escrow was terminal or created a carrier"] call _check;
      [call _stock isEqualTo [_primary,_neighbor],"missing escrow changed bags"] call _check;
      call _reserve;call _send;
      [call _ack select 3 && {_factoryCalls==1},"late escrow did not permit exact retry"] call _check;
      [count (call _stock)==3,"late retry did not create exactly one carrier"] call _check;
    ''')


def test_terminal_receipt_survives_age_and_changed_patient_epoch_while_source_escrow_exists():
    execute(owner_setup() + r'''
      call _send;private _accepted=call _ack;
      _serverTime=400;
      // An unrelated mismatched request forces the real receipt-pruning loop.
      private _unrelated=+_ownerArgs;_unrelated set [2,"other-request"];
      _unrelated call ACME_fnc_piggybackAttachLocal;
      ["pib1" in (_patient getVariable "ACME_piggybackResults"),"outstanding receipt expired before provider settled escrow"] call _check;
      _patient setVariable ["ACME_clinicalEpoch",2];
      call _send;
      [call _ack isEqualTo _accepted && {_factoryCalls==1},"historical exact replay was rejected or recreated after state epoch changed"] call _check;
      [count (_medic getVariable "ACME_piggybackEscrow")==1,"receipt replay settled source escrow on patient owner"] call _check;
    ''')


def test_new_request_id_cannot_reuse_a_prepared_set_already_accepted_by_the_owner():
    execute(owner_setup() + r'''
      call _send;
      // Even if the accepted secondary was subsequently removed, changing the
      // request ID cannot make the already accepted source set consumable again.
      private _map=_patient getVariable "ACM_circulation_IV_Bags";
      _map set ["leftarm",[_primary,_neighbor]];
      _patient setVariable ["ACME_PiggybackLines",createHashMap];
      _patient setVariable ["ACME_infusion_BagMedications",[_oldMed]];
      _ownerArgs set [2,"pib2"];
      _medic setVariable ["ACME_piggybackEscrow",createHashMapFromArray [["set1",["pib2",_patient,1,_set,_prepared,100,+_ownerArgs]]]];
      call _send;
      [!(call _ack select 3) && {_factoryCalls==1},"new request ID consumed previously accepted prepared source twice"] call _check;
      call _assertUnchanged;
    ''')


@pytest.mark.parametrize("cause", ["epoch", "dead", "provider-dead", "range", "replaced-primary", "stopped", "escrow-record", "blood", "propofol"])
def test_owner_latest_state_preflight_rejects_before_native_creation(cause):
    change = {
        "epoch": '_patient setVariable ["ACME_clinicalEpoch",2];',
        "dead": '_patientAlive=false;',
        "provider-dead": '_alive=false;',
        "range": '_distance=8;',
        "replaced-primary": '_primary set [8,"replacement"];',
        "stopped": '_flowRate=0;',
        "escrow-record": 'private _changed=+_set;_changed set [9,50];private _held=(_medic getVariable "ACME_piggybackEscrow") get "set1";_held set [3,_changed];',
        "blood": '_configuredType="Blood";',
        "propofol": '_prepared set [14,[["Propofol",1000,1]]];call _reserve;',
    }[cause]
    if cause in ("dead", "stopped"):
        # Retain these historical case IDs while testing the B289 mechanical
        # connection contract: life/flow do not determine port compatibility.
        execute(owner_setup() + change + r'''
          private _flowBefore=str (_patient getVariable "ACM_circulation_FluidBagsFlow_IV");
          call _send;
          [call _ack select 3 && {_factoryCalls==1},"retained apparatus refused a mechanical connection"] call _check;
          private _bags=call _stock;
          [count _bags==3 && {_bags select 0 isEqualTo _primary} && {_bags select 1 isEqualTo _neighbor},
            "connection replaced the primary or neighboring bag"] call _check;
          [str (_patient getVariable "ACM_circulation_FluidBagsFlow_IV")==_flowBefore,
            "mechanical attachment changed the existing flow switches"] call _check;
          private _certificate=(_patient getVariable "ACME_piggybackResults") get "pib1";
          [_certificate select 0,"owner did not certify the mechanical attachment"] call _check;
          call _send;
          [_factoryCalls==1 && {count (call _stock)==3},"replay created another secondary"] call _check;
        ''')
        return
    execute(owner_setup() + change + r'''
      call _send;
      [!(call _ack select 3) && {_factoryCalls==0},"stale or incompatible request reached carrier factory"] call _check;
      call _assertUnchanged;
      private _certificate=(_patient getVariable "ACME_piggybackResults") get "pib1";
      [!(_certificate select 0),"owner failed to publish terminal rejection proof"] call _check;
    ''')


@pytest.mark.parametrize("failure", ["false-success", "wrong-site", "wrong-access", "wrong-type", "wrong-volume", "double"])
def test_invalid_native_creation_rolls_back_without_losing_any_physical_bag(failure):
    execute(owner_setup() + f'_returnMode="{failure}";' + r'''
      call _send;
      [!(call _ack select 3),"false or ambiguous carrier accepted"] call _check;
      [_factoryCalls==1,"creation retried outside explicit transaction"] call _check;
      call _assertUnchanged;
      [ACME_infusion_activePatients isEqualTo [],"rolled-back carrier enrolled in medication worker"] call _check;
      [count _logs==0,"failed carrier logged success"] call _check;
    ''')


@pytest.mark.parametrize("which", [0, 1])
@pytest.mark.parametrize("false_registration", [False, True])
def test_partial_or_unrecorded_medication_registration_restores_exact_prior_state(which, false_registration):
    execute(owner_setup() + r'''
      _prepared set [10,115];
      _prepared set [14,[["CalciumChloride",1000,1],["Lidocaine",100,1]]];call _reserve;
      private _register=ACME_fnc_infusionRegisterLocal;private _calls=0;
    ''' + f'private _fail={which};private _falseRegistration={str(false_registration).lower()};' + r'''
      ACME_fnc_infusionRegisterLocal={
        private _n=_calls;_calls=_calls+1;
        if (_n==_fail) exitWith {if (_falseRegistration) then {"unrecorded-id"} else {""}};
        _this call _register
      };
      call _send;
      [!(call _ack select 3),"partial or unrecorded medication accepted"] call _check;
      call _assertUnchanged;
      [count _medWrites==1 && {_medWrites select 0 isEqualTo [_oldMed]},"partial mixture published before rollback"] call _check;
      [ACME_infusion_activePatients isEqualTo [] && {count _logs==0},"failed partial mixture became active or logged success"] call _check;
    ''')
