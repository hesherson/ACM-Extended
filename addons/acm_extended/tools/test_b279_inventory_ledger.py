"""Execute opaque native-inventory ledger issue/transfer/escrow/settlement under SQF-VM.

Production commit, broker, reply, projection and claim rules execute. Engine-native
magazine cargo, capacity, transport and object locality are explicit fixtures;
this is not a dedicated-server/network or in-engine Gear test.
"""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import F, adapt, execute
from test_historical_vial_execution import map_defaults

FUNCTIONS = ['inventoryLedgerClass','inventoryLedgerMarkIncoming','inventoryLedgerAdopt','inventoryLedgerRows','inventoryLedgerPossessed','inventoryLedgerCommit',
             'inventoryLedgerReserve','inventoryLedgerClaim','inventoryLedgerSettle',
             'inventoryLedgerBroker','inventoryLedgerReply','inventoryLedgerCertificate',
             'inventoryLedgerReconcile','preparedInventoryCommit']


def adapted(text):
    text = text.replace('canSuspend','false').replace('local _owner','true')
    text = text.replace('isServer','true')
    text = text.replace('_owner canAdd [_class,1,true]', '(_owner getVariable ["capacity",true])')
    text = text.replace('_owner addMagazine [_class,_token]', '[_owner,_class,_token] call _addNative')
    text = text.replace('createVehicle ["GroundWeaponHolder",getPosATL _owner,[],0,"CAN_COLLIDE"]','_holder')
    text = text.replace('_destination addMagazineAmmoCargo [_class,1,_token]', '[_destination,_class,_token] call _addNative')
    text = re.sub(r'values (\([^;\n]+? getVariable \[[^\n]+?\]\))', r'(\1 call _values)', text)
    text = re.sub(r'values (_\w+)', r'(\1 call _values)', text)
    # HashMap key/value iteration is a VM boundary (Arma supplies _y).
    text = text.replace('forEach _cache;', 'forEach (keys _cache);')
    text = text.replace('private _key = _x;\n    private _token', 'private _key = _x; private _y = _cache get _x;\n    private _token')
    return adapt(map_defaults(text))


def setup():
    pre = r'''
    private _receiver=profileNamespace; private _holder=missionNamespace;
    private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    private _values={private _m=_this; (keys _m) apply {_m get _x}};
    private _queue=[]; private _replies=[];
    missionNamespace setVariable ["ACME_inventoryLedgerIndex",createHashMap];
    missionNamespace setVariable ["ACME_inventoryTokenSequence",0];
    { _x setVariable ["native",[]]; _x setVariable ["ACME_preparedIVSets",[]]; _x setVariable ["ACME_infusion_PreparedBags",[]]; _x setVariable ["ACME_inventoryPending",createHashMap];
      _x setVariable ["ACME_inventoryEscrow",createHashMap];
      _x setVariable ["ACME_inventoryPayloadCache",createHashMap];
      _x setVariable ["ACME_inventoryRequests",createHashMap];
      _x setVariable ["ACME_equipmentKitEpoch",0];
    } forEach [_medic,_receiver];
    _holder setVariable ["native",[]];
    CBA_fnc_serverEvent={_queue pushBack (_this select 1)};
    CBA_fnc_targetEvent={_replies pushBack (_this select 1)};
    CBA_fnc_waitAndExecute={_waits pushBack _this};
    ACME_fnc_inventoryLedgerNative={params ["_o",["_k",""]]; (_o getVariable ["native",[]]) select {_k=="" || {(_x select 1)==_k}}};
    private _addNative={params ["_o","_class","_token"]; private _n=+(_o getVariable ["native",[]]); _n pushBack [_token,["prepared","syringe"] select (_class=="ACME_PreparedSyringe")]; _o setVariable ["native",_n];};
    ace_common_fnc_removeSpecificMagazine={params ["_o","_class","_token"]; private _n=+(_o getVariable ["native",[]]); private _i=_n findIf {(_x select 0)==_token}; if (_i<0) exitWith {false}; _n deleteAt _i; _o setVariable ["native",_n];true};
    ACME_fnc_skInventoryReconcile={};
    private _broker={while {count _queue>0} do {(_queue deleteAt 0) call ACME_fnc_inventoryLedgerBroker}};
    private _reply={while {count _replies>0} do {(_replies deleteAt 0) call ACME_fnc_inventoryLedgerReply}};
    private _flush={while {count _queue>0 || {count _replies>0}} do {call _broker;call _reply}};
    private _set=["set1","Blood500","BloodIV_500","Saline500","SalineIV_500","patientA","Y set exact",true,"yset",221.7,109.25];
    private _med=["set1","Saline500","SalineIV_500","Lidocaine",100,600,20,0,0,10,119.25,0,_medic,objNull,[["Lidocaine",100,1],["Calcium",850,2]],"set1",109.25];
    private _payload=["set1",_set,_med];
    private _issue={[_medic,"prepared",[_payload]] call ACME_fnc_inventoryLedgerCommit;call _flush};
    private _token={((missionNamespace getVariable "ACME_inventoryLedgerIndex") get "prepared:set1")};
    private _record={missionNamespace getVariable [format ["ACME_inventoryToken_%1",call _token],[]]};
    '''
    return pre + '\n'.join(f'ACME_fnc_{n}={{'+adapted((F/f'fn_{n}.sqf').read_text())+'};' for n in FUNCTIONS)


def test_native_transfer_moves_exact_y_and_linked_medication_rows_without_remint():
    execute(setup()+r'''
    call _issue;
    [count (_medic getVariable "native")==1,"issue missing carrier"] call _check;
    [count (_medic getVariable "ACME_preparedIVSets")==1,"issue projection missing"] call _check;
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    [_medic] call ACME_fnc_inventoryLedgerReconcile;[_receiver] call ACME_fnc_inventoryLedgerReconcile;
    [!([_receiver,"prepared","set1"] call ACME_fnc_inventoryLedgerPossessed),"unadopted receiver became editable"] call _check;call _flush;
    [(_medic getVariable "ACME_preparedIVSets") isEqualTo [] && {(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo []},"donor retained contents"] call _check;
    [(_receiver getVariable "ACME_preparedIVSets") isEqualTo [_set],"transfer changed Y state"] call _check;
    private _expected=+_med;_expected set [12,_receiver];
    [(_receiver getVariable "ACME_infusion_PreparedBags") isEqualTo [_expected],"transfer changed exact drugs/volume"] call _check;
    [_medic,"prepared",[_payload]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    [count (_medic getVariable "native")==0 && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"stale donor reminted carrier"] call _check;
    ''')


@pytest.mark.parametrize('consume',[False,True])
def test_claim_removes_transferable_carrier_then_return_or_consume_settles_exactly_once(consume):
    execute(setup()+r'''
    call _issue;private _request="claim1";
    private _receipt=[_medic,"prepared","set1",_request] call ACME_fnc_inventoryLedgerReserve;
    [count _receipt==2 && {(_medic getVariable "native") isEqualTo []},"reserve did not remove exact carrier"] call _check;
    private _accepted=false;
    [_medic,_request,{params ["_ok"];_accepted=_ok},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
    [_accepted && {(call _record select 5)=="reserved"},"server claim not certified"] call _check;
    [count ([_medic,"prepared","set1",_request] call ACME_fnc_inventoryLedgerCertificate)==3,"certificate missing"] call _check;
    [_receiver] call ACME_fnc_inventoryLedgerReconcile;
    [(_receiver getVariable "ACME_preparedIVSets") isEqualTo [],"reserved token transferred"] call _check;
    '''+f'[_medic,_request,{str(consume).lower()}] call ACME_fnc_inventoryLedgerSettle;call _flush;'+r'''
    private _first=_medic getVariable "native";
    [_medic,_request,false] call ACME_fnc_inventoryLedgerSettle;call _flush;
    [(_medic getVariable "native") isEqualTo _first,"duplicate settlement minted carrier"] call _check;
    '''+(r'''[count _first==0 && {(call _record select 5)=="spent"},"consumed token survived"] call _check;''' if consume else r'''[count _first==1 && {(call _record select 5)=="held"} && {(_medic getVariable "ACME_preparedIVSets") isEqualTo [_set]},"returned token contents lost"] call _check;'''))


def test_allocation_event_before_public_pending_is_retried_without_block_or_duplicate_identity():
    execute(setup()+r'''
    ["register",_medic,"prepared","set1",_payload,""] call ACME_fnc_inventoryLedgerBroker;
    [count _replies==0 && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==0},"early event rejected or allocated without funding"] call _check;
    call _issue;
    [count (_medic getVariable "native")==1 && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"funded retry failed"] call _check;
    ["register",_medic,"prepared","set1",_payload,""] call ACME_fnc_inventoryLedgerBroker;call _reply;
    [count (_medic getVariable "native")==1,"duplicate allocation ACK minted second token"] call _check;
    ''')


def test_latest_pending_mixture_wins_when_index_arrives_before_token_ack():
    execute(setup()+r'''
    [_medic,"prepared",[_payload]] call ACME_fnc_inventoryLedgerCommit;call _broker;
    private _oldReply=_replies deleteAt 0;
    _payload set [2,+_med];(_payload select 2) set [10,129.25];(_payload select 2) set [14,[["Lidocaine",200,2]]];
    [_medic,"prepared",[_payload]] call ACME_fnc_inventoryLedgerCommit;call _broker;
    _oldReply call ACME_fnc_inventoryLedgerReply;call _reply;
    [count (_medic getVariable "native")==1,"pending mixture minted duplicate"] call _check;
    [(((call _record) select 2) select 2) isEqualTo (_payload select 2),"older queued registration replaced latest drug state"] call _check;
    [((_medic getVariable "ACME_infusion_PreparedBags") select 0 select 10)==129.25,"projection lost latest mixture volume"] call _check;
    ''')


def test_delayed_return_certificate_retains_escrow_until_held_state_arrives():
    execute(setup()+r'''
    call _issue;[_medic,"prepared","set1","req"] call ACME_fnc_inventoryLedgerReserve;
    [_medic,"req",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
    private _reserved=+(call _record);
    [_medic,"req",false] call ACME_fnc_inventoryLedgerSettle;call _broker;
    private _terminal=+(call _record);private _ack=_replies deleteAt 0;
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_reserved];_ack call ACME_fnc_inventoryLedgerReply;
    [count (_medic getVariable "ACME_inventoryEscrow")==1 && {count (_medic getVariable "native")==0},"reply outran certificate and lost custody"] call _check;
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_terminal];_ack call ACME_fnc_inventoryLedgerReply;
    [count (_medic getVariable "ACME_inventoryEscrow")==0 && {count (_medic getVariable "native")==1},"delayed certificate did not refund exact token"] call _check;
    ''')


def test_kit_replacement_cannot_restore_old_pending_or_reserved_item():
    execute(setup()+r'''
    call _issue;[_medic,"prepared","set1","req"] call ACME_fnc_inventoryLedgerReserve;
    [_medic,"req",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
    _medic setVariable ["ACME_equipmentKitEpoch",1];[_medic] call ACME_fnc_inventoryLedgerReconcile;
    [(_medic getVariable "ACME_preparedIVSets") isEqualTo [],"old escrow projected into fresh kit"] call _check;
    [_medic,"req",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
    [count (_medic getVariable "native")==0 && {(call _record select 5)=="spent"},"late return replenished fresh kit"] call _check;
    ''')


def test_capacity_failure_spills_same_token_and_exhaustion_retains_funded_payload():
    # Diagnostic output is an engine boundary; execute the actual allocation,
    # failed reply and blocked-payload updates while recording emitter count.
    fixture='private _inventoryDiagnostics=[];' + setup().replace('diag_log ','_inventoryDiagnostics pushBack ')
    execute(fixture+r'''
    _medic setVariable ["capacity",false];call _issue;
    [count (_medic getVariable "native")==0 && {(_holder getVariable "native") isEqualTo [[1,"prepared"]]},"full kit lost or defaulted spilled token"] call _check;
    [count _inventoryDiagnostics==0,"ordinary capacity spill emitted inventory diagnostics"] call _check;
    missionNamespace setVariable ["ACME_inventoryTokenSequence",65534];
    private _otherSet=+_set;_otherSet set [0,"set2"];
    private _other=["set2",_otherSet,[]];
    [_medic,"prepared",[_other]] call ACME_fnc_inventoryLedgerCommit;call _broker;
    [count _replies==1 && {!((_replies select 0) select 6)},"exhausted registration must emit exactly one failed terminal ACK"] call _check;
    private _failed=_replies select 0;call _reply;
    private _pending=(_medic getVariable "ACME_inventoryPending") get "prepared:set2";
    [count (_medic getVariable "ACME_inventoryPending")==1 && {(_pending select 2) isEqualTo _other} && {(_pending select 6)=="blocked"},"exhaustion lost funded row or failed to block retries"] call _check;
    [count _inventoryDiagnostics==1,"exhaustion diagnostic was omitted or duplicated by client reply"] call _check;
    for "_i" from 1 to 3 do {
        ["register",_medic,"prepared","set2",_other,""] call ACME_fnc_inventoryLedgerBroker;
        [count _replies==1 && {!((_replies select 0) select 6)},"replayed registration emitted duplicate or successful ACK"] call _check;
        call _reply;_failed call ACME_fnc_inventoryLedgerReply;
    };
    [count _inventoryDiagnostics==1,"exhaustion retry or duplicate ACK emitted repeated diagnostics"] call _check;
    [_medic,"prepared",[_other]] call ACME_fnc_inventoryLedgerCommit;
    private _unchanged=(_medic getVariable "ACME_inventoryPending") get "prepared:set2";
    [count _queue==0 && {(_unchanged select 6)=="blocked"} && {(_unchanged select 2) isEqualTo _other},"unchanged same-kit commit rearmed failed allocation"] call _check;
    private _latest=+_other;private _latestMed=+_med;
    _latestMed set [0,"set2"];_latestMed set [15,"set2"];_latestMed set [10,139.25];
    _latest set [2,_latestMed];
    [_medic,"prepared",[_latest]] call ACME_fnc_inventoryLedgerCommit;
    // An actual payload change may repair a generic registration rejection;
    // permit one new attempt while retaining every newly funded component.
    [count _queue==1,"changed pending payload did not get one repair attempt"] call _check;
    call _broker;
    [count _replies==1 && {!((_replies select 0) select 6)},"changed exhausted payload emitted duplicate or successful ACK"] call _check;
    call _reply;
    [_medic,"prepared",[_latest]] call ACME_fnc_inventoryLedgerCommit;
    private _blocked=(_medic getVariable "ACME_inventoryPending") get "prepared:set2";
    [count _queue==0 && {(_blocked select 6)=="blocked"} && {(_blocked select 2) isEqualTo _latest} && {count _inventoryDiagnostics==1},"unchanged repaired payload rearmed failure, repeated diagnostics or lost contents"] call _check;
    [count ([_medic,"prepared","set2","unissued"] call ACME_fnc_inventoryLedgerReserve)==0,"unissued funded row acquired physical custody"] call _check;
    private _thirdSet=+_set;_thirdSet set [0,"set3"];
    private _third=["set3",_thirdSet,[]];
    [_receiver,"prepared",[_third]] call ACME_fnc_inventoryLedgerCommit;call _broker;
    [count _replies==1 && {!((_replies select 0) select 6)},"another exhausted owner did not get one failed ACK"] call _check;
    call _reply;
    [count (_receiver getVariable "ACME_inventoryPending")==1 && {count _inventoryDiagnostics==1},"exhaustion discarded another funded row or logged per owner"] call _check;
    _receiver setVariable ["ACME_equipmentKitEpoch",1];
    [_receiver,"prepared",[_third]] call ACME_fnc_inventoryLedgerCommit;
    [count _queue==1,"fresh-kit funded publication retained a previous generation block"] call _check;
    call _broker;[count _replies==1,"fresh-kit rejection sent duplicate ACK"] call _check;call _reply;
    private _fresh=(_receiver getVariable "ACME_inventoryPending") get "prepared:set3";
    [(_fresh select 3)==1 && {(_fresh select 6)=="blocked"} && {(_fresh select 2) isEqualTo _third} && {count _inventoryDiagnostics==1},"fresh-kit rejection lost funded generation or repeated diagnostics"] call _check;
    private _index=missionNamespace getVariable "ACME_inventoryLedgerIndex";
    [(missionNamespace getVariable "ACME_inventoryTokenSequence")==65534 && {!('prepared:set2' in _index)} && {!('prepared:set3' in _index)},"failed allocation wrote an invalid token or reused identity"] call _check;
    [isNil {missionNamespace getVariable "ACME_inventoryToken_0"} && {isNil {missionNamespace getVariable "ACME_inventoryToken_65535"}},"failed allocation created an invalid zero/default-ammo record"] call _check;
    [(_medic getVariable "native") isEqualTo [] && {(_receiver getVariable "native") isEqualTo []} && {(_holder getVariable "native") isEqualTo [[1,"prepared"]]},"failed allocation materialized or spilled invalid carrier"] call _check;
    ''')


def test_runtime_uses_native_exact_ammo_and_tracked_owners_only():
    native=(F/'fn_inventoryLedgerNative.sqf').read_text();reserve=(F/'fn_inventoryLedgerReserve.sqf').read_text();init=(F/'fn_inventoryLedgerInit.sqf').read_text()
    assert 'magazinesAmmoCargo' in native
    assert 'ace_common_fnc_removeSpecificMagazine' in reserve
    assert 'allUnits' not in init
    assert 'ACME_inventoryTracked' in init
    assert 'ACME_inventoryTokenSequence' in (F/'fn_inventoryLedgerBroker.sqf').read_text()


def test_two_pending_metadata_changes_preserve_latest_between_intermediate_server_revisions():
    execute(setup()+r'''
    call _issue;
    private _one=+_payload;_one set [2,+_med];(_one select 2) set [10,129.25];
    private _two=+_payload;_two set [2,+_med];(_two select 2) set [10,139.25];
    [_medic,"prepared",[_one]] call ACME_fnc_inventoryLedgerCommit;
    [_medic,"prepared",[_two]] call ACME_fnc_inventoryLedgerCommit;
    call _broker;
    [_medic] call ACME_fnc_inventoryLedgerReconcile;
    [((_medic getVariable "ACME_infusion_PreparedBags") select 0 select 10)==139.25,"intermediate metadata erased latest preparation"] call _check;
    [([_medic,"prepared","set1","req"] call ACME_fnc_inventoryLedgerReserve) isEqualTo [],"unconfirmed intermediate mixture reserved"] call _check;
    call _flush;
    [count ([_medic,"prepared","set1","req"] call ACME_fnc_inventoryLedgerReserve)==2,"settled latest mixture could not reserve"] call _check;
    ''')


def test_stale_donor_escrow_cannot_edit_after_return_and_recipient_transfer():
    execute(setup()+r'''
    call _issue;[_medic,"prepared","set1","req"] call ACME_fnc_inventoryLedgerReserve;
    [_medic,"req",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
    private _oldEscrow=_medic getVariable "ACME_inventoryEscrow"; private _stale=createHashMapFromArray ((keys _oldEscrow) apply {[_x,+(_oldEscrow get _x)]});
    [_medic,"req",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    [_receiver] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    private _updated=+_payload;_updated set [2,+_med];(_updated select 2) set [10,149.25];
    [_receiver,"prepared",[_updated]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    _medic setVariable ["ACME_inventoryEscrow",_stale];
    ["update",_medic,"prepared","set1",_payload,""] call ACME_fnc_inventoryLedgerBroker;
    [(((call _record) select 2) select 2 select 10)==149.25,"stale donor escrow changed recipient contents"] call _check;
    ''')


def test_stale_transfer_claim_rejection_returns_canonical_contents_without_old_override():
    execute(setup()+r'''
    call _issue;private _old=+(call _record);
    private _updated=+_payload;_updated set [2,+_med];(_updated select 2) set [10,149.25];
    [_medic,"prepared",[_updated]] call ACME_fnc_inventoryLedgerCommit;call _flush;private _new=+(call _record);
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_old];
    [_receiver] call ACME_fnc_inventoryLedgerReconcile;
    [!([_receiver,"prepared","set1"] call ACME_fnc_inventoryLedgerPossessed),"stale recipient could edit/debit before adoption"] call _check;
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_new];call _flush;
    [count (_receiver getVariable "native")==1 && {(((call _record) select 2) select 2 select 10)==149.25},"stale return overwrote latest canonical contents"] call _check;
    [((_receiver getVariable "ACME_infusion_PreparedBags") select 0 select 10)==149.25,"refund projected stale content"] call _check;
    ''')


def test_losing_custody_prunes_cache_so_returned_token_uses_recipient_edits():
    execute(setup()+r'''
    call _issue;
    private _updated=+_payload;_updated set [2,+_med];(_updated select 2) set [10,149.25];
    [_medic,"prepared",[_updated]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];[_medic] call ACME_fnc_inventoryLedgerReconcile;
    [count (_medic getVariable "ACME_inventoryPayloadCache")==0,"donor retained mutation cache"] call _check;
    [_receiver] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    private _latest=+_payload;_latest set [2,+_med];(_latest select 2) set [10,169.25];[_receiver,"prepared",[_latest]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    _medic setVariable ["native",_receiver getVariable "native"];_receiver setVariable ["native",[]];[_medic] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    [((_medic getVariable "ACME_infusion_PreparedBags") select 0 select 10)==169.25,"reacquired token resurrected donor cache"] call _check;
    ''')


def test_edit_after_return_sent_reserves_same_identity_until_latest_payload_settles():
    execute(setup()+r'''
    call _issue;
    private _one=+_payload;_one set [2,+_med];(_one select 2) set [10,129.25];
    private _two=+_payload;_two set [2,+_med];(_two select 2) set [10,139.25];
    [_medic,"prepared",[_one]] call ACME_fnc_inventoryLedgerCommit;
    call _broker;call _reply; // certified Claim queues Return(payload1).
    [_medic,"prepared",[_two]] call ACME_fnc_inventoryLedgerCommit;
    call _broker;call _reply; // terminal reply starts a second edit with the SAME token.
    [count (_medic getVariable "native")==0 && {count (_medic getVariable "ACME_inventoryEscrow")==1},"late edit briefly made stale carrier transferable"] call _check;
    call _flush;
    [count (_medic getVariable "native")==1 && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"follow-up edit reminted identity"] call _check;
    [(((call _record) select 2) select 2 select 10)==139.25 && {((_medic getVariable "ACME_infusion_PreparedBags") select 0 select 10)==139.25},"later funded edit lost during terminal ACK"] call _check;
    ''')


def test_funded_metadata_edit_cannot_transfer_carrier_before_server_confirmation():
    execute(setup()+r'''
    call _issue;
    private _new=+_payload;_new set [2,+_med];(_new select 2) set [10,149.25];
    [_medic,"prepared",[_new]] call ACME_fnc_inventoryLedgerCommit;
    [count (_medic getVariable "native")==0,"funded edit left old transferable carrier"] call _check;
    _receiver setVariable ["native",_medic getVariable "native"];[_receiver] call ACME_fnc_inventoryLedgerReconcile;
    [(_receiver getVariable "ACME_preparedIVSets") isEqualTo [],"recipient acquired unconfirmed old contents"] call _check;
    call _flush;
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];[_receiver] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    [((_receiver getVariable "ACME_infusion_PreparedBags") select 0 select 10)==149.25,"confirmed transfer lost added solution"] call _check;
    ''')


def test_late_edit_with_new_full_kit_spills_only_final_payload_after_same_token_rearm():
    execute(setup()+r'''
    call _issue;
    private _one=+_payload;_one set [2,+_med];(_one select 2) set [10,129.25];
    private _two=+_payload;_two set [2,+_med];(_two select 2) set [10,139.25];
    [_medic,"prepared",[_one]] call ACME_fnc_inventoryLedgerCommit;call _broker;call _reply;
    [_medic,"prepared",[_two]] call ACME_fnc_inventoryLedgerCommit;
    _medic setVariable ["capacity",false];call _broker;call _reply;
    [count (_medic getVariable "native")==0 && {count (_holder getVariable "native")==0},"intermediate payload spilled before latest edit settled"] call _check;
    call _flush;
    [(_holder getVariable "native") isEqualTo [[1,"prepared"]] && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"final coalesced item lost or identity duplicated"] call _check;
    [(((call _record) select 2) select 2 select 10)==139.25,"full-kit spill lost later funded payload"] call _check;
    ''')


def test_mutation_claim_callback_can_recover_after_provider_locality_changes():
    execute(setup()+r'''
    call _issue;
    private _new=+_payload;_new set [2,+_med];(_new select 2) set [10,149.25];
    [_medic,"prepared",[_new]] call ACME_fnc_inventoryLedgerCommit;
    missionNamespace setVariable ["ACME_inventoryCallbacks",createHashMap]; // new owner has durable public rows, no old machine closures.
    call _flush;
    [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_inventoryEscrow")==0},"lost callback stranded durable edit custody"] call _check;
    [(((call _record) select 2) select 2 select 10)==149.25,"owner handoff discarded desired edit"] call _check;
    ''')


def test_locality_event_enrolls_participant_and_poll_prunes_old_nonlocal_owner():
    init=(F/'fn_inventoryLedgerInit.sqf').read_text()
    init=init.replace('local _x', '(_x getVariable ["testLocal",true])').replace('local _unit','(_unit getVariable ["testLocal",true])')
    init=adapted(init).replace('forEach _pending;', 'forEach (keys _pending);').replace('private _p = _y;', 'private _p = _pending get _x;')
    init=init.replace('forEach _requests;', 'forEach (keys _requests);').replace('private _r = _y;', 'private _r = _requests get _x;')
    execute(setup()+r'''
    private _classes=[];private _poll={};private _recover=[];
    CBA_fnc_addClassEventHandler={_classes pushBack _this};
    CBA_fnc_addPlayerEventHandler={};
    CBA_fnc_addPerFrameHandler={_poll=_this select 0};
    ACME_fnc_preparedInventoryRecover={_recover pushBack (_this select 0)};
    _medic setVariable ["testLocal",false];_receiver setVariable ["testLocal",true];
    missionNamespace setVariable ["ACME_inventoryTracked",[_medic]];
    _receiver setVariable ["ACME_inventoryPending",createHashMapFromArray [["prepared:set1",["prepared","set1",_payload,0,0,0,"pending"]]]];
    '''+init+r'''
    private _localIndex=_classes findIf {(_x select 1)=="Local"};
    [[_localIndex>=0,"Local handler missing"] call _check];
    [_receiver,true] call ((_classes select _localIndex) select 2);
    [_receiver in (missionNamespace getVariable "ACME_inventoryTracked") && {_receiver in _recover},"new owner did not enroll/recover"] call _check;
    call _poll;
    [(missionNamespace getVariable "ACME_inventoryTracked") isEqualTo [_receiver],"old nonlocal owner stayed in polling registry"] call _check;
    ''')


def test_stale_transfer_adoption_blocks_old_mixture_edits_then_new_medicine_uses_canonical_base():
    execute(setup()+r'''
    call _issue;private _old=+(call _record);
    private _donor=+_payload;_donor set [2,+_med];(_donor select 2) set [14,[["Lidocaine",200,2],["Calcium",850,2]]];
    [_medic,"prepared",[_donor]] call ACME_fnc_inventoryLedgerCommit;call _flush;private _canonical=+(call _record);
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_old];
    [!([_receiver,"prepared","set1"] call ACME_fnc_inventoryLedgerPossessed),"stale receiver was allowed to debit new medicine"] call _check;
    private _stale=+_payload;_stale set [2,+_med];(_stale select 2) set [14,[["Lidocaine",100,1],["Calcium",900,3]]];
    [_receiver,"prepared",[_stale]] call ACME_fnc_inventoryLedgerCommit; // even a direct stale writer performs adoption only.
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_canonical];call _flush;
    [(((call _record) select 2) select 2 select 14) isEqualTo [["Lidocaine",200,2],["Calcium",850,2]],"adoption mutated medicine before source debit"] call _check;
    private _latest=+(([_receiver,"prepared"] call ACME_fnc_inventoryLedgerRows) select 0);
    _latest set [2,+(_latest select 2)];(_latest select 2) set [14,[["Lidocaine",200,2],["Calcium",900,3]]];
    [_receiver,"prepared",[_latest]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    [(((call _record) select 2) select 2 select 14) isEqualTo [["Lidocaine",200,2],["Calcium",900,3]],"post-adoption addition erased donor drug"] call _check;
    ''')


@pytest.mark.parametrize('kind',['prepared','syringe'])
def test_every_kind_requires_certified_receiver_custody_before_treatment_or_edit(kind):
    payload='["set1",_set,_med]' if kind=='prepared' else '["set1",["Lidocaine",10,5,"exact tag",2,20,"compound",[],[],[],[],"set1","","inventoryB279"]]'
    execute(setup()+f'private _kind="{kind}";private _item={payload};'+r'''
    [_medic,_kind,[_item]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    private _number=(missionNamespace getVariable "ACME_inventoryLedgerIndex") get (_kind+":set1");
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    [([_receiver,_kind] call ACME_fnc_inventoryLedgerRows) isEqualTo [],"foreign-owner record projected as receiver equipment"] call _check;
    [([_receiver,_kind,"set1","treatment"] call ACME_fnc_inventoryLedgerReserve) isEqualTo [],"unadopted treatment removed foreign token"] call _check;
    [_receiver] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    [[_receiver,_kind,"set1"] call ACME_fnc_inventoryLedgerPossessed,"adopted receiver could not use its equipment"] call _check;
    [(_receiver getVariable "native") isEqualTo [[_number,_kind]],"adoption duplicated or changed physical identity"] call _check;
    [(([_receiver,_kind] call ACME_fnc_inventoryLedgerRows) select 0 select 1) isEqualTo (_item select 1),"adoption changed exact equipment contents"] call _check;
    ''')


def test_foreign_first_record_does_not_skip_later_funded_owned_record_in_bulk_commit():
    execute(setup()+r'''
    call _issue;
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    private _newSet=+_set;_newSet set [0,"second"];
    [_receiver,"prepared",[_payload,["second",_newSet,[]]]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    [count (_receiver getVariable "native")==2 && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==2},"foreign first row dropped funded later preparation"] call _check;
    [count (_receiver getVariable "ACME_preparedIVSets")==2,"bulk commit lost adopted or new set projection"] call _check;
    ''')


@pytest.mark.parametrize('replay',['return','claim','consume'])
def test_old_terminal_request_cannot_reacquire_custody_after_native_transfer_and_adoption(replay):
    execute(setup()+r'''
    call _issue;[_medic,"prepared","set1","oldreq"] call ACME_fnc_inventoryLedgerReserve;
    [_medic,"oldreq",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
    private _oldEscrow=_medic getVariable "ACME_inventoryEscrow";private _stale=createHashMapFromArray((keys _oldEscrow) apply {[_x,+(_oldEscrow get _x)]});
    [_medic,"oldreq",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];[_receiver] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    _medic setVariable ["ACME_inventoryEscrow",_stale];
    '''+f'["{replay}",_medic,"prepared","set1",_payload,"oldreq"] call ACME_fnc_inventoryLedgerBroker;'+r'''
    [((call _record) select 3) isEqualTo _receiver && {((call _record) select 5)=="held"},"old terminal replay changed current adopted custodian"] call _check;
    [count (_medic getVariable "native")==0 && {count (_receiver getVariable "native")==1},"old request duplicated native equipment"] call _check;
    ''')


def test_historical_return_reply_waits_for_required_server_revision_before_native_refund():
    execute(setup()+r'''
    call _issue;[_medic,"prepared","set1","req"] call ACME_fnc_inventoryLedgerReserve;
    [_medic,"req",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
    [_medic,"req",false] call ACME_fnc_inventoryLedgerSettle;call _broker;
    private _current=+(call _record);private _ack=_replies deleteAt 0;
    private _stale=+_current;_stale set [6,(_current select 6)-1];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_stale];_ack call ACME_fnc_inventoryLedgerReply;
    [count (_medic getVariable "native")==0 && {count (_medic getVariable "ACME_inventoryEscrow")==1},"stale terminal revision materialized carrier"] call _check;
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_current];_ack call ACME_fnc_inventoryLedgerReply;
    [count (_medic getVariable "native")==1,"current terminal certificate failed exact refund"] call _check;
    ''')


def test_external_take_with_stale_self_owner_requires_new_adoption_before_roundtrip_edit():
    execute(setup()+r'''
    call _issue;private _oldSelf=+(call _record);
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    [_receiver,"prepared"] call ACME_fnc_inventoryLedgerMarkIncoming;[_receiver] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    private _new=+_payload;_new set [2,+_med];(_new select 2) set [14,[["Lidocaine",200,2],["Calcium",850,2]]];
    [_receiver,"prepared",[_new]] call ACME_fnc_inventoryLedgerCommit;call _flush;private _canonical=+(call _record);
    _medic setVariable ["native",_receiver getVariable "native"];_receiver setVariable ["native",[]];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_oldSelf]; // old mirror incorrectly still names self and 100 mg.
    [_medic,"prepared"] call ACME_fnc_inventoryLedgerMarkIncoming;
    [!([_medic,"prepared","set1"] call ACME_fnc_inventoryLedgerPossessed),"stale self-owner bypassed synchronous Take readiness"] call _check;
    [([_medic,"prepared","set1","drug"] call ACME_fnc_inventoryLedgerReserve) isEqualTo [],"old self snapshot allowed clinical debit"] call _check;
    [_medic] call ACME_fnc_inventoryLedgerReconcile;
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",call _token],_canonical];call _flush;
    [(([_medic,"prepared"] call ACME_fnc_inventoryLedgerRows) select 0 select 2 select 14) isEqualTo [["Lidocaine",200,2],["Calcium",850,2]],"roundtrip adoption lost receiver medicine"] call _check;
    private _latest=+(([_medic,"prepared"] call ACME_fnc_inventoryLedgerRows) select 0);_latest set [2,+(_latest select 2)];(_latest select 2) set [14,[["Lidocaine",200,2],["Calcium",900,3]]];
    [_medic,"prepared",[_latest]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    [(((call _record) select 2) select 2 select 14) isEqualTo [["Lidocaine",200,2],["Calcium",900,3]],"post-roundtrip addition used stale dose base"] call _check;
    ''')


def test_take_readiness_handles_native_cargo_arriving_after_event_marker():
    execute(setup()+r'''
    call _issue;private _incoming=_medic getVariable "native";
    _medic setVariable ["native",[]]; // native EH boundary has not inserted the new tuple yet.
    [_medic,"prepared"] call ACME_fnc_inventoryLedgerMarkIncoming;
    _medic setVariable ["native",_incoming];
    [([_medic,"prepared"] call ACME_fnc_inventoryLedgerRows) isEqualTo [],"kind readiness allowed late native tuple before adoption"] call _check;
    [_medic] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    [[_medic,"prepared","set1"] call ACME_fnc_inventoryLedgerPossessed,"late native tuple never completed forced adoption"] call _check;
    ''')
