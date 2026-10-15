"""Execute exact syringe identity, transfer projection and receipt settlement.

Native cargo, locality and networking are captured engine boundaries. The actual
SQF codecs, normalization, claim callback, refunds and terminal writer execute.
"""
import re

from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_historical_medication_rows import iteration_scopes
from test_historical_vial_execution import map_defaults
from test_historical_syringe_identity import setup as identity_setup


def code(name):
    text = read(name)
    text = text.replace('local _owner', 'true')
    text = text.replace('finite _drug', 'true').replace('finite _saline', 'true')
    # VM numeric typed-param fallback differs from Arma on the new four-field
    # native import row. Retain Arma's real default at this engine boundary.
    text = text.replace('_row param [4, 0, [0]]','_row param [4, 0]')
    text = text.replace('uniformContainer _owner', '_medic')
    text = text.replace('vestContainer _owner', 'objNull').replace('backpackContainer _owner', 'objNull')
    text = text.replace('magazinesAmmoCargo _x', '_nativeRows')
    text = text.replace('getNumber (_cfg >> "ACM_isSyringe")','1')
    text = text.replace('_container addMagazineAmmoCargo [_class,-1,_ammo];', '_removedMags pushBack [_class,_ammo]; private _at=_nativeRows find [_class,_ammo]; if (_at>=0) then {_nativeRows deleteAt _at;};')
    text = text.replace('_owner setVariable ["ACME_narcStore", _store, _public];', '_publications pushBack _public; _owner setVariable ["ACME_narcStore",_store];')
    text = text.replace('_owner setVariable ["ACME_narcStore",_ordered,_reserved isEqualTo []];', '_publications pushBack (_reserved isEqualTo []); _owner setVariable ["ACME_narcStore",_ordered];')
    text = text.replace('_medic addMagazine [_class,_ammo];', '_returnedMags pushBack [_class,_ammo];')
    text = text.replace('_medic == ACE_player', '_medic isEqualTo ACE_player')
    text = text.replace('findDisplay 84000','objNull')
    text = text.replace('_job getOrDefault ["med","Medication"]','([_job,["med","Medication"]] call _mapDefault)')
    return adapt(iteration_scopes(map_defaults(text)))


def function(name):
    return 'ACME_fnc_' + name + '={' + code(name) + '};'


def setup():
    return '''
        ACE_player=_medic;
        private _nativeRows=[]; private _removedMags=[]; private _returnedMags=[];
        private _ledgerCalls=[]; private _publications=[]; private _settlements=[]; private _deliveries=[]; private _journalCalls=[];
        private _mapDefault={params ["_map","_args"]; _args params ["_key","_default"]; if (_key in _map) then {_map get _key} else {_default}};
        private _row=["Ketamine",10,2,"exact label",1,[["Ketamine",2]],"dilutionB13","blue_opioid","line A","line B","line C","id-owned","flush","inventoryB279"];
        ACME_fnc_inventoryLedgerCommit={_ledgerCalls pushBack _this;true};
        ACME_fnc_inventoryLedgerSettle={_settlements pushBack _this;true};
        ACME_fnc_treatmentSupplyRefund={};
        ace_common_fnc_addToInventory={_returnedMags pushBack _this;};
        ACME_fnc_skStoreEnsureIds={(_this select 0) getVariable ["ACME_narcStore",[]]};
        ACME_fnc_medicationRequest={_deliveries pushBack _this;true};
        ACME_fnc_medicationLineIdentity={[0,1,1]};
        ACME_fnc_medicationLineBloodBusy={false};
        ACME_fnc_clinicalEpoch={0};
        // Explicit broker boundary: the real ordinary continuation can debit
        // only after BEGIN is acknowledged; B285 exercises the durable broker.
        ACME_fnc_syringeDeliveryRequest={
            _journalCalls pushBack _this;
            if ((_this select 0)=="begin") then {[true,_this select 5] call (_this select 4);};
            if ((_this select 0)=="batch") then {_deliveries pushBack ((_this select 3) select 2);};
            true
        };
    ''' + ''.join(function(n) for n in ('skInventoryCommit','narcStoreCommit','skInventoryReconcile','skInventorySettle','skInventoryInjectClaim','medicationRefund'))


def test_private_plunger_writes_never_materialize_or_publish_tokens():
    execute(setup()+'''
        for "_i" from 1 to 20 do {
            private _live=+_row; _live set [2,2-(_i/100)];
            [_medic,[_live],false] call ACME_fnc_narcStoreCommit;
        };
        [count _ledgerCalls==0 && {({ _x } count _publications)==0},"private writes registered inventory or published dose state"] call _check;
        [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.8,"private volume lost"] call _check;
    ''')


def test_native_magazine_conversion_uses_exact_hundredths_once_and_preserves_tag_identity():
    execute(setup()+'''
        private _native=["Fentanyl",3,1.23,"native","","","","blue_opioid","written","dose","time","id-native"];
        _native set [4,0]; _native set [5,[]];
        _nativeRows=[["ACM_Syringe_3_Fentanyl",123],["ACM_Syringe_3_Fentanyl",124]];
        [_medic,[_native,_row]] call ACME_fnc_narcStoreCommit;
        private _after=_medic getVariable "ACME_narcStore";
        [_removedMags isEqualTo [["ACM_Syringe_3_Fentanyl",123]],"conversion debited wrong amount or duplicate native magazine"] call _check;
        [_nativeRows isEqualTo [["ACM_Syringe_3_Fentanyl",124]],"conversion consumed another partial syringe"] call _check;
        [((_after select 0) select [0,12]) isEqualTo _native,"conversion altered exact drug/tag/stable identity"] call _check;
        [count ((_ledgerCalls select 0) select 2)==2,"native and medicated flush not both materialized"] call _check;
        [_medic,_after] call ACME_fnc_narcStoreCommit;
        [count _removedMags==1,"repeat publication debited same source twice"] call _check;
    ''')


def test_native_transfer_recipient_gets_exact_partial_payload_and_donor_loses_it():
    execute(setup()+'''
        private _partial=+_row; _partial set [2,0.75]; _partial set [4,0.375]; _partial set [5,[["Ketamine",0.75]]];
        _medic setVariable ["ACME_narcStore",[_row]];
        [_medic,[],[],[]] call ACME_fnc_skInventoryReconcile;
        [(_medic getVariable "ACME_narcStore") isEqualTo [],"donor retained transferred syringe"] call _check;
        _patient setVariable ["ACME_narcStore",[]];
        [_patient,[["id-owned",_partial]],[],[]] call ACME_fnc_skInventoryReconcile;
        [(_patient getVariable "ACME_narcStore") isEqualTo [_partial],"recipient lost mixture volume, medication, label, tag or identity"] call _check;
        private _before=count _publications;
        [_patient,[["id-owned",_partial]],[],[]] call ACME_fnc_skInventoryReconcile;
        [count _publications==_before,"unchanged inventory poll published repeatedly"] call _check;
    ''')


def test_reserved_live_row_is_preserved_without_full_volume_poll_publication():
    execute(setup()+'''
        private _live=+_row; _live set [2,0.4]; _live set [4,0.2];
        _medic setVariable ["ACME_narcStore",[_live]];
        [_medic,[],[["id-owned",_row]],[]] call ACME_fnc_skInventoryReconcile;
        [(_medic getVariable "ACME_narcStore") isEqualTo [_live],"inventory poll restored stale full plunger"] call _check;
        [count _publications==0,"reserved live state was periodically broadcast"] call _check;
    ''')


def test_rejected_partial_receipt_restores_same_syringe_without_duplicate_identity():
    execute(setup()+'''
        private _remaining=+_row; _remaining set [2,1.25]; _remaining set [4,0.625]; _remaining set [5,[["Ketamine",1.25]]];
        private _aliquot=+_row; _aliquot set [2,0.75]; _aliquot set [4,0.375]; _aliquot set [5,[["Ketamine",0.75]]];
        _medic setVariable ["ACME_narcStore",[_remaining]];
        [_medic,[[],[_aliquot],[]],false] call ACME_fnc_medicationRefund;
        private _rows=_medic getVariable "ACME_narcStore";
        [count _rows==1 && {((_rows select 0) select 11)=="id-owned"},"refund cloned the physical syringe identity"] call _check;
        [((_rows select 0) select 2)==2 && {((_rows select 0) select 4)==1} && {((_rows select 0) select 5) isEqualTo [["Ketamine",2]]},"refund lost medication or saline volume"] call _check;
        [_medic,"request","id-owned"] call ACME_fnc_skInventorySettle;
        private _settled=_settlements select 0;
        [!(_settled select 2) && {((_settled select 3) select 1) isEqualTo (_rows select 0)},"receipt returned a stale payload or wrong token"] call _check;
    ''')


def test_claim_rejection_delivers_nothing_and_returns_exact_reserved_payload():
    execute(setup()+'''
        _medic setVariable ["ACME_narcStore",[_row]];
        [false,[_medic,_patient,"leftarm",[["Ketamine_IV",100,true,"dose"]],0,_row,[],_row,"request"]] call ACME_fnc_skInventoryInjectClaim;
        [count _deliveries==0 && {(_medic getVariable "ACME_narcStore") isEqualTo [_row]},"rejected custody claim administered or debited medication"] call _check;
        [(_settlements select 0) isEqualTo [_medic,"request",false,["id-owned",_row]],"claim rejection lost the reserved identity"] call _check;
    ''')


def test_claim_success_dispatches_capture_and_hides_only_full_reserved_syringe():
    execute(setup()+'''
        _medic setVariable ["ACME_narcStore",[_row]];
        [true,[_medic,_patient,"leftarm",[["Ketamine_IV",100,true,"dose"]],0,_row,[],_row,"request"]] call ACME_fnc_skInventoryInjectClaim;
        [count _deliveries==1 && {(_medic getVariable "ACME_narcStore") isEqualTo []},"certified syringe did not debit exactly once"] call _check;
        [((_deliveries select 0) select 9) isEqualTo ["syringeB279","request","id-owned"],"patient request lost exact custody receipt"] call _check;
        [_medic,[],[["id-owned",_row]],[]] call ACME_fnc_skInventoryReconcile;
        [(_medic getVariable "ACME_narcStore") isEqualTo [],"pending patient ACK recreated full syringe"] call _check;
        [_medic,"request","id-owned"] call ACME_fnc_skInventorySettle;
        [(_settlements select 0 select 2),"fully delivered syringe carrier remained usable"] call _check;
    ''')


def test_partial_claim_pending_receipt_keeps_exact_local_remainder_until_return():
    execute(setup()+'''
        private _remaining=+_row; _remaining set [2,1.25]; _remaining set [4,0.625]; _remaining set [5,[["Ketamine",1.25]]];
        private _aliquot=+_row; _aliquot set [2,0.75]; _aliquot set [4,0.375]; _aliquot set [5,[["Ketamine",0.75]]];
        _medic setVariable ["ACME_narcStore",[_row]];
        [true,[_medic,_patient,"leftarm",[["Ketamine_IV",37.5,true,"dose"]],0,_row,_remaining,_aliquot,"request"]] call ACME_fnc_skInventoryInjectClaim;
        [_medic,[],[["id-owned",_row]],[]] call ACME_fnc_skInventoryReconcile;
        [(_medic getVariable "ACME_narcStore") isEqualTo [_remaining],"pending receipt removed or refilled the remaining syringe"] call _check;
        [_medic,"request","id-owned"] call ACME_fnc_skInventorySettle;
        [(_settlements select 0) isEqualTo [_medic,"request",false,["id-owned",_remaining]],"accepted aliquot consumed remaining solution"] call _check;
    ''')


def test_incremental_push_waits_for_all_receipts_then_returns_token_without_native_duplicate():
    execute(setup()+function('hardcorePushFinalize')+'''
        ACME_fnc_hardcorePushOverlay={};
        private _partial=+_row; _partial set [2,0.75]; _partial set [4,0.375]; _partial set [5,[["Ketamine",0.75]]];
        _medic setVariable ["ACME_narcStore",[_partial]];
        private _job=createHashMapFromArray [["medic",_medic],["stableId","id-owned"],["pendingAcks",1],
            ["unsentDelta",[0,0,[]]],["virtual",false],["inventoryBacked",true],["inventoryRequest","reserved-push"],
            ["magClass","ACM_Syringe_10_Ketamine"],["magContainer",objNull]];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        missionNamespace setVariable ["ACME_HCMedPushPFH",-1];
        [!(call ACME_fnc_hardcorePushFinalize),"carrier was released before patient receipt"] call _check;
        [count _settlements==0 && {count _ledgerCalls==0},"pending ACK returned a usable syringe"] call _check;
        _job set ["pendingAcks",0]; missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        [call ACME_fnc_hardcorePushFinalize,"settled push failed to finalize"] call _check;
        [count _returnedMags==0,"token push returned a second native medication magazine"] call _check;
        [(_settlements select 0) isEqualTo [_medic,"reserved-push",false,["id-owned",_partial]],"finalizer returned wrong remaining dose or identity"] call _check;
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0,"settled worker still owns returned token"] call _check;
    ''')


def test_legacy_push_import_protects_exact_fresh_native_tuple_through_delayed_registration():
    execute(setup()+function('skInventoryImportNative')+'''
        private _older=+_row; _older set [2,1.5]; _older set [4,0]; _older set [5,[]]; _older set [6,""];
        _medic setVariable ["ACME_narcStore",[_older]];
        _nativeRows=[["ACM_Syringe_10_Ketamine",124],["ACM_Syringe_10_Ketamine",200]];
        _medic setVariable ["ACME_nativeSyringePending",[["ACM_Syringe_10_Ketamine",124,"fresh-push",40]]];
        _nowTime=10;
        private _imported=[_medic,[_older]] call ACME_fnc_skInventoryImportNative;
        [count _imported==2 && {(_imported select 1 select 2)==2},"legacy importer upgraded fresh syringe during push timer"] call _check;
        [_medic,_imported] call ACME_fnc_narcStoreCommit;
        [_nativeRows isEqualTo [["ACM_Syringe_10_Ketamine",124]],"pending token allocation consumed protected fresh draw"] call _check;
        [count _removedMags==1 && {(_removedMags select 0 select 1)==200},"background import removed wrong raw volume"] call _check;
        // No allocation ACK is delivered; the exact raw push syringe still exists.
        [_medic,_medic getVariable "ACME_narcStore"] call ACME_fnc_skInventoryImportNative;
        [_nativeRows isEqualTo [["ACM_Syringe_10_Ketamine",124]],"delayed ACK protection expired while timer owns syringe"] call _check;
    ''')


def test_legacy_fresh_push_uses_captured_raw_dose_before_older_same_drug_token():
    text=(ROOT/'addons/circulation/functions/fnc_Syringe_Inject.sqf').read_text()
    text=text.replace('uniformContainer _medic','_medic').replace('vestContainer _medic','objNull').replace('backpackContainer _medic','objNull')
    text=text.replace('magazinesAmmoCargo _x','_nativeRows')
    text=text.replace('getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _classname >> "concentration")','50')
    text=text.replace('localize (format ["STR_ACM_Circulation_Medication_%1", _classname])','_classname')
    text=text.replace('localize (format ["STR_ACM_Circulation_Medication_%1",_classname])','_classname')
    text=text.replace('_x addMagazineAmmoCargo [_itemClassname, -1, _count];','_removedMags pushBack [_itemClassname,_count]; _nativeRows deleteAt (_nativeRows find [_itemClassname,_count]);')
    text=text.replace('GET_BODYPART_INDEX(_bodyPart)','0')
    text=adapt(iteration_scopes(text),'circulation')
    execute(setup()+'private _nativeInject={'+text+'};'+'''
        ACME_fnc_medicationRouteAllowed={true}; ACM_circulation_fnc_hasIV={true}; ACM_circulation_fnc_hasIO={true};
        private _older=+_row; _older set [2,1.5]; _older set [4,0]; _older set [5,[]]; _older set [6,""];
        _medic setVariable ["ACME_narcStore",[_older]];
        _nativeRows=[["ACM_Syringe_10_Ketamine",124],["ACM_Syringe_10_Ketamine",200]];
        [_medic,_patient,"leftarm","Ketamine",10,true,false,["ACM_Syringe_10_Ketamine",124,"fresh-push"]] call _nativeInject;
        [count _deliveries==1 && {((_deliveries select 0 select 3) select 0 select 1)==62},"legacy push delivered older token or largest unrelated raw volume"] call _check;
        [_removedMags isEqualTo [["ACM_Syringe_10_Ketamine",124]],"fresh push debited wrong native syringe"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo [_older],"native direct push deleted an older token row"] call _check;
    ''')


def test_death_keeps_tangible_syringes_for_corpse_transfer():
    source = read('registerSyringeLifecycleRuntime')
    killed = source.split('player addEventHandler ["Killed",',1)[1].split('player addEventHandler ["Respawn",',1)[0]
    assert 'narcStoreCommit' not in killed
    assert 'ACME_SK_SelectedSyringeId' in killed


def tag_transfer_setup():
    return identity_setup()+function('skInventoryEditable')+'''
        private _mapDefault={params ["_map","_args"]; _args params ["_key","_default"]; if (_key in _map) then {_map get _key} else {_default}};
        private _ownedIds=["id-a","id-b"];
        ACME_fnc_inventoryLedgerPossessed={(_this select 2) in _ownedIds};
        while {count _a<14} do {_a pushBack "";}; _a set [13,"inventoryB279"];
        while {count _b<14} do {_b pushBack "";}; _b set [13,"inventoryB279"];
        _b set [8,"B original label"]; _a set [8,"A original label"];
        _rows=[_a,_b,_c]; _medic setVariable ["ACME_narcStore",_rows];
        ["id-b",_rows] call ACME_fnc_skSelectStored;
        _drawDisplay setVariable ["ACME_SK_TagEditSyringeId","id-b"];
        _drawDisplay setVariable ["ACME_SK_TagEditSignature",_b select [7,4]];
        uiNamespace setVariable ["ACME_SK_TagEditMode",true];
        _textValues set ["84460","stale unsaved text"]; _textValues set ["84461","stale line2"]; _textValues set ["84462","stale line3"];
        _chosenColor="red_paralytic";
    '''


def test_moved_syringe_tag_event_cannot_change_donor_or_recipient_labels():
    execute(tag_transfer_setup()+'''
        _ownedIds=["id-a"];
        _patient setVariable ["ACME_narcStore",[_b]];
        private _before=_medic getVariable "ACME_narcStore";
        call ACME_fnc_skTagCommit;
        [100,0] call ACME_fnc_skTagColor;
        [(_medic getVariable "ACME_narcStore") isEqualTo _before,"stale donor tag event changed syringe metadata"] call _check;
        [(_patient getVariable "ACME_narcStore") isEqualTo [_b],"donor changed transferred recipient label"] call _check;
        [(_drawDisplay getVariable "ACME_SK_TagEditSyringeId")=="","rejected editor stayed bound to moved token"] call _check;
        [count _textWrites==0 && {_renders==0},"rejected ownership edit changed UI or store"] call _check;
    ''')


def test_tag_editor_binding_rejects_carousel_fallback_to_other_owned_syringe():
    execute(tag_transfer_setup()+'''
        _patient setVariable ["ACME_narcStore",[_b]];
        [_medic,[_a,_c]] call ACME_fnc_narcStoreCommit;
        // Renderer fallback now points at A, while this editor was opened on B.
        private _current=_medic getVariable "ACME_narcStore";
        uiNamespace setVariable ["ACME_SK_CarouselIdx",0];
        private _fallback=[_current] call ACME_fnc_skSelectedIndex;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a","fixture did not reproduce carousel fallback"] call _check;
        call ACME_fnc_skTagCommit; [100,0] call ACME_fnc_skTagColor;
        [(_medic getVariable "ACME_narcStore") isEqualTo [_a,_c],"fallback wrote stale B text/color onto A"] call _check;
        [(_patient getVariable "ACME_narcStore") isEqualTo [_b],"fallback changed moved syringe label"] call _check;
    ''')


def test_canonical_changed_tag_signature_rejects_old_text_on_same_returned_identity():
    execute(tag_transfer_setup()+'''
        private _canonical=+_b; _canonical set [8,"recipient corrected label"];
        _medic setVariable ["ACME_narcStore",[_a,_canonical,_c]];
        call ACME_fnc_skTagCommit; [100,0] call ACME_fnc_skTagColor;
        [(_medic getVariable "ACME_narcStore") isEqualTo [_a,_canonical,_c],"old editor overwrote canonical returned syringe tag"] call _check;
    ''')


def test_source_funded_current_kit_pending_syringe_remains_taggable():
    execute(tag_transfer_setup()+'''
        _ownedIds=[];
        private _pending=createHashMapFromArray [["syringe:id-b",["syringe","id-b",["id-b",_b],0]]];
        _medic setVariable ["ACME_inventoryPending",_pending];
        call ACME_fnc_skTagCommit; [100,0] call ACME_fnc_skTagColor;
        private _saved=(_medic getVariable "ACME_narcStore") select 1;
        [(_saved select 8)=="stale unsaved text" && {(_saved select 7)=="red_paralytic"},"initial allocation ACK blocked own funded tag workflow"] call _check;
        [(_saved select [0,7]) isEqualTo (_b select [0,7]) && {(_saved select 11)=="id-b"},"pending tag changed contents or identity"] call _check;
    ''')


def test_previous_kit_pending_and_foreign_tag_escrow_are_read_only():
    execute(tag_transfer_setup()+'''
        _ownedIds=[];
        _medic setVariable ["ACME_equipmentKitEpoch",2];
        _medic setVariable ["ACME_inventoryPending",createHashMapFromArray [["syringe:id-b",["syringe","id-b",["id-b",_b],1]]]];
        [!([_medic,_b] call ACME_fnc_skInventoryEditable),"previous kit pending tag remained writable"] call _check;
        _medic setVariable ["ACME_inventoryMutations",createHashMapFromArray [["tag-request",["id-b",_b]]]];
        _medic setVariable ["ACME_inventoryEscrow",createHashMapFromArray [["tag-request",[99,["id-b",_b],"syringe","tag-request",2,true]]]];
        missionNamespace setVariable ["ACME_inventoryToken_99",["syringe","id-b",["id-b",_b],_patient,"tag-request","reserved",1]];
        [!([_medic,_b] call ACME_fnc_skInventoryEditable),"foreign canonical owner accepted stale tag escrow"] call _check;
        missionNamespace setVariable ["ACME_inventoryToken_99",["syringe","id-b",["id-b",_b],_medic,"tag-request","reserved",1]];
        [[_medic,_b] call ACME_fnc_skInventoryEditable,"owned in-flight tag request interrupted continuous typing"] call _check;
    ''')


def test_tangible_epinephrine_consumer_claim_receipt_preserves_identity_and_remaining_solution():
    """Real epi consumer/claims/patient receipts; cargo, transport and physiology are engine boundaries."""
    from test_b279_inventory_ledger import setup as ledger_setup
    consumers = '\n'.join(function(name) for name in (
        'skInventoryCommit','narcStoreCommit','skInventoryImportNative','skStoreEnsureIds',
        'skInventoryReconcile','skInventoryReserve','skInventorySettle','skInventoryInjectClaim',
        'epinephrinePushStored','medicationRequest','medicationEscrowCommit','medicationAck',
        'medicationRefund','medicationLineLocal'))
    # The fixture represents engine objects by namespaces and supplies finite
    # numeric inputs. Opaque carriers are distinct from stock ACM syringe cargo.
    consumers = consumers.replace('["_owner", ACE_player, [objNull]]','["_owner", ACE_player]')
    consumers = re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', consumers)
    consumers = consumers.replace('finite (_x select 1)','((_x select 1) call _finite)')
    consumers = consumers.replace('netId _medic','"medic"')
    from test_b285_syringe_migration import adapted as journal_adapter
    journal_names = ('syringeDeliveryCopy','syringeDeliveryDelta','syringeDeliveryDoseValid',
                     'syringeDeliveryClaim','syringeDeliveryBroker','syringeDeliveryRequest',
                     'syringeDeliveryReply','syringeDeliveryRecover')
    journal = ''.join('ACME_fnc_'+name+'={'+journal_adapter(read(name))+'};' for name in journal_names)
    consumers = consumers.replace('owner _patient','7').replace('canSuspend','false')
    execute(ledger_setup()+consumers+journal+r'''
        private _machineSpace=missionNamespace;
        private _machineOwner=7; private _providerOwner=7; private _patientOwner=7;
        missionNamespace setVariable ["ACME_syringeDeliveryMachines",createHashMapFromArray [["7","machine7"]]];
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","machine7"];
        private _providerLocal=true; private _patientLocal=true;
        private _onServer=true; private _hasInterface=true; private _serverTime=10;
        private _configNumber={0.1};
        _broker={while {count _queue>0} do {
            private _event=_queue deleteAt 0;
            if ((_event select 0)=="ACME_inventoryBroker") then {(_event select 1) call ACME_fnc_inventoryLedgerBroker;}
            else {(_event select 1) call ACME_fnc_syringeDeliveryBroker;};
        }};
        _reply={while {count _replies>0} do {
            private _event=_replies deleteAt 0;
            if ((_event select 0)=="ACME_inventoryReply") then {(_event select 1) call ACME_fnc_inventoryLedgerReply;}
            else {(_event select 1) call ACME_fnc_syringeDeliveryReply;};
        }};
        CBA_fnc_serverEvent={_queue pushBack _this;};
        private _nativeRows=[]; // no stock ACM dose magazines; token possession uses real ledger/native() below.
        private _removedMags=[]; private _returnedMags=[]; private _publications=[];
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _lineIdentity=[1,2,100]; private _patientRequests=[]; private _patientAcks=[];
        private _dispatchStores=[]; private _dispatchProofs=[]; private _drugDeliveries=[];
        ACM_circulation_fnc_hasIV={count _this < 4 || {(_this select 3)==1}};
        ACM_circulation_fnc_hasIO={false};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",1]};
        ACME_fnc_medicationRouteAllowed={params ["_class","_iv"];_class=="Epinephrine_IV" && {_iv}};
        ACME_fnc_medicationLineIdentity={_lineIdentity};
        ACME_fnc_medicationLineBloodBusy={false};
        ACME_fnc_medicationLineFraction={1};
        ACME_fnc_medicationLeak={};
        ACME_fnc_ownerRegister={};
        ace_medical_treatment_fnc_addToTriageCard={};
        ace_medical_treatment_fnc_medicationLocal={_drugDeliveries pushBack _this;};
        ACME_fnc_ownerDispatch={
            params ["_target","_operation","_args"];
            [_operation=="medicationLine","unexpected patient transport operation"] call _check;
            _patientRequests pushBack _args;
            _dispatchStores pushBack (+(_medic getVariable ["ACME_narcStore",[]]));
            private _meta=(_args select 9) select 4;
            _dispatchProofs pushBack ([_medic,"syringe",_meta select 2,_meta select 1] call ACME_fnc_inventoryLedgerCertificate);
        };
        CBA_fnc_targetEvent={
            params ["_event","_args"];
            if (_event in ["ACME_inventoryReply","ACME_syringeDeliveryReply"]) then {_replies pushBack [_event,_args];} else {
                [_event=="ACME_medicationAck","unexpected provider transport event"] call _check;
                _patientAcks pushBack _args;
            };
        };
        private _settlePatient={call _flush;};
        private _initial=["EpinephrineCardiac",10,1,"Push-dose epinephrine 10 mcg/mL",9,[],"epiMixB12",
            "violet_vasopressor","correct epi label","10 mcg/mL","owner tag","epi-physical","flush","inventoryB279"];
        [_medic,[_initial]] call ACME_fnc_narcStoreCommit;call _flush;
        private _epiToken=(missionNamespace getVariable "ACME_inventoryLedgerIndex") get "syringe:epi-physical";
        private _epiRecord={missionNamespace getVariable [format ["ACME_inventoryToken_%1",_epiToken],[]]};
        [(_medic getVariable "native") isEqualTo [[_epiToken,"syringe"]]
            && {(call _epiRecord select 3) isEqualTo _medic} && {(call _epiRecord select 5)=="held"},"owned canonical epi carrier not established"] call _check;
        // The actual epi wrapper selects its inventoryB279 branch. Reserve
        // removes the exact token and no patient work precedes the server claim.
        [[_medic,_patient,"leftarm",0,2,1,20] call ACME_fnc_epinephrinePushStored,"owned 2 mL physical epi push rejected"] call _check;
        [(_medic getVariable "native") isEqualTo [] && {count _patientRequests==0}
            && {(_medic getVariable "ACME_narcStore") isEqualTo [_initial]},"epi debit/dispatched before certified claim or left carrier transferable"] call _check;
        call _flush;
        [count _patientRequests==1 && {count (_dispatchProofs select 0)==2}
            && {(call _epiRecord select 5)=="reserved"} && {(_medic getVariable "native") isEqualTo []},"physical epi consumer bypassed canonical custody proof"] call _check;
        private _first=_patientRequests select 0;
        [abs ((_first select 6 select 0 select 1)-0.02)<0.000001
            && {(_first select 6 select 0 select 4)==20} && {(_first select 7)==1},"physical 2 mL epi push changed dose, duration or access"] call _check;
        private _left=_medic getVariable "ACME_narcStore";
        [(_dispatchStores select 0) isEqualTo _left,"physical epi medication request preceded its exact syringe debit"] call _check;
        [count _left==1 && {abs ((_left select 0 select 2)-0.8)<0.000001}
            && {abs ((_left select 0 select 4)-7.2)<0.000001}
            && {(_left select 0 select [7,7]) isEqualTo (_initial select [7,7])},"physical partial debit lost exact solution or label identity"] call _check;
        _first call ACME_fnc_medicationLineLocal;_first call ACME_fnc_medicationLineLocal;
        [count _drugDeliveries==1 && {abs ((_drugDeliveries select 0 select 3)-0.02)<0.000001}
            && {(_medic getVariable "native") isEqualTo []},"duplicate patient receipt delivered twice or returned token before provider ACK"] call _check;
        call _settlePatient;
        private _accepted=+(_medic getVariable "ACME_narcStore");
        [(_medic getVariable "native") isEqualTo [[_epiToken,"syringe"]]
            && {(call _epiRecord select 2) isEqualTo ["epi-physical",_accepted select 0]}
            && {(call _epiRecord select 5)=="held"},"accepted partial receipt changed token or failed to return exact remaining solution"] call _check;
        // A later real patient-owner rejection returns the exact aliquot into
        // that same SID. Repeated rejection ACKs cannot add volume/carriers.
        [[_medic,_patient,"leftarm",0,1,1,3] call ACME_fnc_epinephrinePushStored,"second physical epi push rejected before patient receipt"] call _check;
        [count _patientRequests==1 && {(_medic getVariable "native") isEqualTo []},"second push dispatched before server claim"] call _check;
        call _flush;
        private _second=_patientRequests select 1;
        [abs ((_second select 6 select 0 select 1)-0.01)<0.000001,"physical 1 mL epi request dose changed"] call _check;
        _lineIdentity=[1,3,101]; // actual catheter-generation validation rejects this submitted request.
        _second call ACME_fnc_medicationLineLocal;_second call ACME_fnc_medicationLineLocal;
        [count _drugDeliveries==1 && {(_medic getVariable "native") isEqualTo []},"rejected request delivered drug or returned carrier before ACK"] call _check;
        call _settlePatient;
        private _restored=_medic getVariable "ACME_narcStore";
        [count _restored==1 && {abs ((_restored select 0 select 2)-0.8)<0.000001}
            && {abs ((_restored select 0 select 4)-7.2)<0.000001}
            && {(_restored select 0 select [7,7]) isEqualTo (_initial select [7,7])}
            && {(_medic getVariable "native") isEqualTo [[_epiToken,"syringe"]]},"rejected receipt lost solution/tag/SID or cloned physical epi carrier"] call _check;
        [(call _epiRecord select 2) isEqualTo ["epi-physical",_restored select 0]
            && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"receipt restoration reminted an identity or left canonical contents stale"] call _check;
        [_medic,_second select 3,false,"late duplicate"] call ACME_fnc_medicationAck;call _flush;
        [(_medic getVariable "ACME_narcStore") isEqualTo _restored
            && {(_medic getVariable "native") isEqualTo [[_epiToken,"syringe"]]}
            && {(call _epiRecord select 2) isEqualTo ["epi-physical",_restored select 0]},"late duplicate rejection ACK repaid returned physical syringe"] call _check;
        // Native transfer removes original possession. A stale row at either
        // provider remains unusable until the foreign carrier is adopted.
        private _foreign=parsingNamespace;
        _foreign setVariable ["native",_medic getVariable "native"];
        _foreign setVariable ["ACME_narcStore",+_restored];
        _medic setVariable ["native",[]];
        _lineIdentity=[1,2,100];
        [!([_medic,_patient,"leftarm",0,1,1,3] call ACME_fnc_epinephrinePushStored),"stale original provider pushed a moved token"] call _check;
        [!([_foreign,_patient,"leftarm",0,1,1,3] call ACME_fnc_epinephrinePushStored),"unadopted holder pushed foreign canonical epi contents"] call _check;
        [count _patientRequests==2 && {count _queue==0} && {count _drugDeliveries==1}
            && {(_medic getVariable "ACME_narcStore") isEqualTo _restored}
            && {(_foreign getVariable "native") isEqualTo [[_epiToken,"syringe"]]},"failed possession/canonical proof mutated stock or administered medication"] call _check;
    ''')
