"""Execute B275 downstream warmer custody and confirmation using production SQF.

Engine objects, locality, rendering and CBA delivery are explicit adapters. Supply
reservation/refund and warmer request, owner decision, ACK, move and return code
execute unchanged apart from unsupported VM command boundaries. This is not a
native Arma networking or visual acceptance test.
"""
import re
import pytest
from test_menu_death_lifecycle import read, adapt, execute
from test_b156_procedure_supplies import supply_setup, primitives


def function(name):
    source = read(name).replace("serverTime", "_serverTime").replace("canSuspend", "false")
    source = source.replace("local _medic", "_medicLocal").replace("local _patient", "_patientLocal")
    source = source.replace("isNull findDisplay 86000", "(!_menuOpen)")
    source = source.replace("isNull (_receipt param [0, objNull])", "((_receipt param [0, objNull]) isEqualTo objNull)")
    source = re.sub(r"objNull,\s*\[objNull\]", "objNull, [profileNamespace]", source)
    source = re.sub(r"\bfinite (_\w+)", r"(\1 call _finite)", source)
    source = re.sub(r"\bvalues (_\w+)", r"((keys \1) apply {\1 get _x})", source)
    # This VM fails typed param defaults on missing elements; preserve Arma defaults.
    source = re.sub(r'(\b_\w+) param \[(\d+), "", \[""\]\]', r'(if (count \1 <= \2) then {""} else {\1 param [\2,"",[""]]})', source)
    return f"ACME_fnc_{name}={{" + primitives(adapt(source)) + "};\n"


def setup():
    supplies = supply_setup().replace("_medic removeItem _x", "[_medic,_x] call _removeStock")
    return supplies + r'''
      private _removeStock={params ["_u","_item"];private _stock=+(_u getVariable ["fixtureStock",[]]);private _i=_stock find _item;if (_i>=0) then {_stock deleteAt _i;_u setVariable ["fixtureStock",_stock];};};
      private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
      private _serverTime=100;private _liveEpoch=1;private _patientLocal=true;private _medicLocal=true;
      private _accessValid=true;private _menuOpen=true;private _sent=[];
      ACME_fnc_clinicalEpoch={_liveEpoch};
      ACME_fnc_patientInteractionDistance={_distance};
      ACME_fnc_transfusionAccessValid={_accessValid};
      ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
      ACME_fnc_ownerDispatch={_sent pushBack _this;};
      ACME_fnc_updateTransfusionControls={};ACME_fnc_clinicalNotice={};
      ace_common_fnc_isAwake={true};
      _medic setVariable ["fixtureStock",["ACME_BloodWarmer"]];
      _patient setVariable ["fixtureStock",["ACME_BloodWarmer"]];
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[
        ["Blood",400,1,0,true,-1,500,-1,"blood"],
        ["ACME_SalineY",500,1,0,true,-1,500,-1,"reserve"],
        ["Saline",200,1,1,true,-1,500,-1,"other"]]]]];
      missionNamespace setVariable ["ACE_player",_medic];
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
      private _stock={[_medic,"ACME_BloodWarmer"] call ace_common_fnc_getCountOfItem};
      private _lastRequest={(_sent select ((count _sent)-1)) select 2};
      private _send={call _lastRequest call ACME_fnc_lineWarmerCommit;};
      private _ack={private _all=_events select {(_x select 0)=="ACME_lineWarmerAck"};(_all select ((count _all)-1)) select 1};
      private _returnEvents={_events select {(_x select 0)=="ACME_lineWarmerReturn"}};
    ''' + "".join(function(name) for name in (
        "lineWarmer", "lineWarmerRate", "lineWarmerActionState", "lineWarmerRequest",
        "lineWarmerRecover", "lineWarmerCommit", "lineWarmerAck", "lineWarmerDetach",
        "lineWarmerReturn", "lineWarmerReturnsTick", "lineWarmerMove", "lineWarmerRestore"))


def test_last_spare_confirmation_no_and_stale_yes_never_debit():
    execute(setup() + r'''
      ["add","blood"] call ACME_fnc_lineWarmerRequest;
      [call _stock==1 && {count _sent==0},"last spare consumed before confirmation"] call _check;
      private _state=[_patient,"leftarm",true,0,"blood",_medic,true] call ACME_fnc_lineWarmerActionState;
      [_state select 4,"last spare confirmation not bound to physical bag"] call _check;
      ["no","blood"] call ACME_fnc_lineWarmerRequest;
      [call _stock==1 && {(uiNamespace getVariable "ACME_lineWarmerConfirm") isEqualTo []},"declining lost inventory"] call _check;
      ["add","blood"] call ACME_fnc_lineWarmerRequest;
      ["yes","reserve"] call ACME_fnc_lineWarmerRequest;
      [call _stock==1 && {count _sent==0},"cross-bag Yes consumed the warmer"] call _check;
      ["add","blood"] call ACME_fnc_lineWarmerRequest;
      _liveEpoch=2;
      ["yes","blood"] call ACME_fnc_lineWarmerRequest;
      [call _stock==1 && {count _sent==0},"cross-epoch Yes consumed the warmer"] call _check;
    ''')


def test_add_from_reserve_owns_one_shared_device_and_remove_returns_once():
    execute(setup() + r'''
      ["add","reserve"] call ACME_fnc_lineWarmerRequest;
      ["yes","reserve"] call ACME_fnc_lineWarmerRequest;
      [call _stock==0,"confirmed add did not reserve one personal warmer"] call _check;
      [([_patient,"ACME_BloodWarmer"] call ace_common_fnc_getCountOfItem)==1,"add stole patient's warmer"] call _check;
      call _send;call _send;
      [count (_patient getVariable "ACME_lineWarmers")==1 && {count (_patient getVariable "ACME_lineWarmerCustody")==1},"add replay duplicated equipment"] call _check;
      [[_patient,"leftarm",true,0] call ACME_fnc_lineWarmer,"reserve member did not fit downstream"] call _check;
      [!([_patient,"leftarm",true,1] call ACME_fnc_lineWarmer),"warmer leaked to unrelated line"] call _check;
      (call _ack) call ACME_fnc_lineWarmerAck;(call _ack) call ACME_fnc_lineWarmerAck;
      [call _stock==0,"accepted receipt returned a duplicate warmer"] call _check;
      ["remove","blood"] call ACME_fnc_lineWarmerRequest;call _send;call _send;
      private _returns=call _returnEvents;
      [count _returns==1,"remove replay emitted a second custody return"] call _check;
      (_returns select 0 select 1) call ACME_fnc_lineWarmerReturn;
      (_returns select 0 select 1) call ACME_fnc_lineWarmerReturn;
      (call _ack) call ACME_fnc_lineWarmerAck;
      [call _stock==1 && {count (_patient getVariable "ACME_lineWarmers")==0},"remove did not return exactly one warmer"] call _check;
    ''')


@pytest.mark.parametrize("reason", ["epoch", "bag-moved", "dead", "expired"])
def test_definitive_owner_rejection_refunds_original_receipt_once_after_handoff(reason):
    edit = {
        "epoch": "_liveEpoch=2;",
        "bag-moved": 'private _map=_patient getVariable "ACM_circulation_IV_Bags";(_map get "leftarm" select 0) set [3,2];',
        "dead": "_patientAlive=false;",
        "expired": "_serverTime=120;",
    }[reason]
    execute(setup() + r'''
      ["add","blood"] call ACME_fnc_lineWarmerRequest;["yes","blood"] call ACME_fnc_lineWarmerRequest;
      [call _stock==0,"reservation missing"] call _check;
    ''' + edit + r'''
      call _send;[!(call _ack select 3),"invalid owner state accepted fitting"] call _check;
      // A new provider owner has escrow but no old machine's generic receipt cache.
      missionNamespace setVariable ["ACME_supplyReceipts",createHashMap];
      (call _ack) call ACME_fnc_lineWarmerAck;(call _ack) call ACME_fnc_lineWarmerAck;
      [call _stock==1 && {count (_patient getVariable ["ACME_lineWarmers",createHashMap])==0},"handoff rejection lost or duplicated reserved item"] call _check;
    ''')


def test_move_preserves_custody_and_long_delayed_return_reconciles_once():
    execute(setup() + r'''
      ["add","blood"] call ACME_fnc_lineWarmerRequest;["yes","blood"] call ACME_fnc_lineWarmerRequest;
      call _send;(call _ack) call ACME_fnc_lineWarmerAck;
      [_patient,"leftarm",true,0,"rightarm",true,2] call ACME_fnc_lineWarmerMove;
      [!([_patient,"leftarm",true,0] call ACME_fnc_lineWarmer) && {[_patient,"rightarm",true,2] call ACME_fnc_lineWarmer},"move lost downstream equipment"] call _check;
      [_patient,"rightarm",true,2] call ACME_fnc_lineWarmerDetach;
      [_patient,"rightarm",true,2] call ACME_fnc_lineWarmerDetach;
      [count (call _returnEvents)==1 && {call _stock==0},"detach duplicated or prematurely granted custody"] call _check;
      _serverTime=200;[_patient] call ACME_fnc_lineWarmerReturnsTick;
      private _returns=call _returnEvents;
      (_returns select ((count _returns)-1) select 1) call ACME_fnc_lineWarmerReturn;
      (_returns select ((count _returns)-1) select 1) call ACME_fnc_lineWarmerReturn;
      [call _stock==1,"delayed owner return did not recover once"] call _check;
      _serverTime=300;[_patient] call ACME_fnc_lineWarmerReturnsTick;
      [count (_patient getVariable "ACME_lineWarmerReturns")==0 && {call _stock==1},"settled custody return remained retryable"] call _check;
    ''')


def test_legacy_global_flag_and_unreserved_fit_cannot_create_or_return_device():
    execute(setup() + r'''
      _patient setVariable ["ACME_warmedBlood",true];
      [!([_patient,"leftarm",true,0,true,_medic] call ACME_fnc_lineWarmer),"possession or global flag manufactured downstream equipment"] call _check;
      _patient setVariable ["ACME_lineWarmers",createHashMapFromArray [["leftarm#true#0",true]]];
      [_patient,"leftarm",true,0,_medic] call ACME_fnc_lineWarmerDetach;
      [count (call _returnEvents)==0 && {call _stock==1},"legacy free flag manufactured returned item"] call _check;
    ''')


def test_ack_before_provider_escrow_replication_waits_and_settles_once():
    execute(setup() + r'''
      ["add","blood"] call ACME_fnc_lineWarmerRequest;["yes","blood"] call ACME_fnc_lineWarmerRequest;
      call _send;private _payload=call _ack;
      private _durable=_medic getVariable "ACME_lineWarmerEscrow";
      _medic setVariable ["ACME_lineWarmerEscrow",createHashMap];
      missionNamespace setVariable ["ACME_supplyReceipts",createHashMap];
      _payload call ACME_fnc_lineWarmerAck;
      [call _stock==0 && {count _waits==1},"early ACK guessed absent provider escrow"] call _check;
      _medic setVariable ["ACME_lineWarmerEscrow",_durable];
      private _waiting=_waits select 0;(_waiting select 1) call (_waiting select 0);
      _payload call ACME_fnc_lineWarmerAck;
      [(_medic getVariable "ACME_lineWarmerEscrow" get (_payload select 2) select 1) && {call _stock==0},"replicated ACK failed or returned spent warmer"] call _check;
      [count (missionNamespace getVariable "ACME_supplyReceipts")==0,"adopted supply receipt remained refundable"] call _check;
    ''')


def restore_setup():
    # Execute the production warmer part of reset(begin); unrelated medical
    # teardown helpers are covered by their own full lifecycle fixtures.
    source = read("clinicalReset")
    start = source.index('    private _warmerRestore =')
    end = source.index('    [_patient, "reset"]', start)
    warmer_reset = primitives(adapt(source[start:end]))
    return setup() + 'private _resetWarmers={' + warmer_reset + '};' + r'''
      ["add","blood"] call ACME_fnc_lineWarmerRequest;["yes","blood"] call ACME_fnc_lineWarmerRequest;
      call _send;(call _ack) call ACME_fnc_lineWarmerAck;
      private _savedWarmers=createHashMapFromArray [["leftarm#true#0",true]];
      private _row=+((_patient getVariable "ACME_lineWarmerCustody") get "leftarm#true#0");
      private _savedCustody=createHashMapFromArray [["leftarm#true#0",_row]];
    '''


def test_restore_retains_same_device_through_reset_and_any_detach_hook():
    execute(restore_setup() + r'''
      [_patient,_savedWarmers,_savedCustody,2,"prepare"] call ACME_fnc_lineWarmerRestore;
      _patient setVariable ["ACME_clinicalRestoring",true];call _resetWarmers;
      // Native IV/topology teardown must not return a retained physical device.
      [_patient,"leftarm",true,0,_medic] call ACME_fnc_lineWarmerDetach;
      [count (call _returnEvents)==0 && {call _stock==0},"reset returned retained device before restore"] call _check;
      _patient setVariable ["ACME_lineWarmers",createHashMap];_patient setVariable ["ACME_lineWarmerCustody",createHashMap];
      [_patient,_savedWarmers,_savedCustody,2,"apply"] call ACME_fnc_lineWarmerRestore;
      [count (_patient getVariable "ACME_lineWarmers")==1 && {count (_patient getVariable "ACME_lineWarmerCustody")==1} && {call _stock==0},"snapshot duplicated or lost retained device"] call _check;
      [((_patient getVariable "ACME_lineWarmerCustody") get "leftarm#true#0" select 2)==2,"restored device kept stale clinical epoch"] call _check;
      [isNil {_patient getVariable "ACME_lineWarmerRestorePlan"},"restore leaked old custody plan"] call _check;
    ''')


def test_restore_omits_live_device_returns_once_and_stale_snapshot_cannot_revive_it():
    execute(restore_setup() + r'''
      [_patient,createHashMap,createHashMap,2,"prepare"] call ACME_fnc_lineWarmerRestore;
      _patient setVariable ["ACME_clinicalRestoring",true];call _resetWarmers;
      [count (call _returnEvents)==1,"omitted live device was discarded or returned twice"] call _check;
      private _return=call _returnEvents select 0 select 1;_return call ACME_fnc_lineWarmerReturn;
      _patient setVariable ["ACME_lineWarmers",createHashMap];_patient setVariable ["ACME_lineWarmerCustody",createHashMap];
      [_patient,createHashMap,createHashMap,2,"apply"] call ACME_fnc_lineWarmerRestore;
      [call _stock==1 && {count (_patient getVariable "ACME_lineWarmers")==0},"omitted device remained inline after return"] call _check;
      [_patient,_savedWarmers,_savedCustody,3,"prepare"] call ACME_fnc_lineWarmerRestore;
      [_patient,_savedWarmers,_savedCustody,3,"apply"] call ACME_fnc_lineWarmerRestore;
      [call _stock==1 && {count (_patient getVariable "ACME_lineWarmers")==0} && {count (call _returnEvents)==1},"old snapshot revived already returned physical device"] call _check;
    ''')


def test_restore_drops_already_returned_or_duplicate_incoming_identities():
    execute(restore_setup() + r'''
      // Permanent provider evidence also blocks a device returned on another
      // patient's line, without relying on a still-pending return certificate.
      _medic setVariable ["ACME_lineWarmerReturned",createHashMapFromArray [[_row select 0,100]]];
      [_patient,_savedWarmers,_savedCustody,2,"prepare"] call ACME_fnc_lineWarmerRestore;
      [_patient,_savedWarmers,_savedCustody,2,"apply"] call ACME_fnc_lineWarmerRestore;
      [count (_patient getVariable "ACME_lineWarmers")==0,"provider-retired incoming identity restored inline"] call _check;
      private _new=["snapshot-other-device",_medic,1];
      private _warmers=createHashMapFromArray [["leftarm#true#0",true],["rightarm#true#0",true]];
      private _custody=createHashMapFromArray [["leftarm#true#0",_new],["rightarm#true#0",_new]];
      [_patient,_warmers,_custody,3,"prepare"] call ACME_fnc_lineWarmerRestore;
      [_patient,_warmers,_custody,3,"apply"] call ACME_fnc_lineWarmerRestore;
      [count (_patient getVariable "ACME_lineWarmers")==0,"duplicate snapshot identity became two downstream devices"] call _check;
    ''')
