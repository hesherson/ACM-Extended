"""Run production identity allocation, import and save code with native boundaries mocked.

Profile flush, native cargo and network transport are explicit fixtures. These
cases prove ordering/conservation in SQF, not disk durability or an Arma restart.
"""
import re

import pytest

from test_b279_inventory_ledger import setup as ledger_setup, adapted
from test_menu_death_lifecycle import F, execute


def source(name):
    code = (F / f"fn_{name}.sqf").read_text()
    code = re.sub(r'finite (_\w+)', 'true', code)
    code = re.sub(r'finite \(_meta select 2\)', 'true', code)
    code = code.replace('local _holder', 'true')
    code = code.replace('if (_holder isKindOf "CAManBase") then {[uniformContainer _holder,vestContainer _holder,backpackContainer _holder]} else {[_holder]}', '[_holder]')
    code = code.replace('magazinesAmmoCargo _x', '([_x] call _nativePairs)')
    code = code.replace('isClass (configFile >> "CfgMagazines" >> _class)', 'true')
    code = code.replace('getText (configFile >> "CfgMagazines" >> (_x select 0) >> "ACME_inventoryKind")', '(["prepared","syringe"] select (((_x select 0) find "ACME_PreparedSyringe")==0))')
    code = code.replace('getText (configFile >> "CfgMagazines" >> _class >> "ACME_inventoryKind")', '(["prepared","syringe"] select ((_class find "ACME_PreparedSyringe")==0))')
    code = code.replace('objectFromNetId (_set select 5)', 'objNull').replace('netId _patient', '"rebound-patient"')
    return f'ACME_fnc_{name}={{' + adapted(code) + '};'


def setup():
    return ledger_setup() + r'''
    CBA_missionTime=12;
    private _nativePairs={params ["_o"];(_o getVariable ["native",[]]) apply {
        private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_x select 0],[]];
        [_record param [8,"ACME_PreparedIVSet"],_x select 0]
    }};
    ACME_fnc_clinicalObjectRef={params ["_mode","_ref"];if (_mode=="decode") then {objNull} else {["patient","session","stable-patient"]}};
    private _removeAllowed=true;private _lyingRemove=false;private _commitAllowed=true;
    private _realRemove=ace_common_fnc_removeSpecificMagazine;
    ace_common_fnc_removeSpecificMagazine={
        if (!_removeAllowed) exitWith {false};if (_lyingRemove) exitWith {true};_this call _realRemove
    };
    ''' + '\n'.join(source(n) for n in ['inventorySnapshotValid', 'inventorySnapshot', 'inventoryRestore'])


def test_prepared_snapshot_normalizes_runtime_fields_and_retains_exact_contents():
    execute(setup() + r'''
    call _issue;private _before=str (call _record);
    private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    [count _snapshot==2 && {count (_snapshot select 1)==1},"prepared snapshot missing"] call _check;
    private _saved=((_snapshot select 1) select 0) select 3;
    [(_saved select 1 select 5)=="" && {(_saved select 2 select 9)==0}
        && {(_saved select 2 select 12)==""} && {(_saved select 2 select 13)==""},"session fields leaked into snapshot"] call _check;
    [(_saved select 1 select 9)==221.7 && {(_saved select 2 select 10)==119.25}
        && {(_saved select 2 select 14) isEqualTo [["Lidocaine",100,1],["Calcium",850,2]]},"exact volume or mixture changed"] call _check;
    [str (call _record)==_before,"snapshot edited live payload"] call _check;
    ''')


@pytest.mark.parametrize('field', [
    'ACME_inventoryPending', 'ACME_inventoryEscrow', 'ACME_inventoryMutations',
    'ACME_inventoryRequests', 'ACME_inventoryAdoptions', 'ACME_inventoryPlacement', 'ACME_inventoryIncoming',
])
def test_snapshot_rejects_unsettled_equipment(field):
    execute(setup() + 'call _issue;' + f'_medic setVariable ["{field}",createHashMapFromArray [["busy",[]]]];' + r'''
    [([_medic] call ACME_fnc_inventorySnapshot) isEqualTo [],"busy checkpoint silently omitted custody"] call _check;
    ''')


def test_empty_snapshot_is_valid_and_unknown_carrier_is_not():
    execute(setup() + r'''
    [([_medic] call ACME_fnc_inventorySnapshot) isEqualTo [1,[]],"empty checkpoint rejected"] call _check;
    _medic setVariable ["native",[[123,"prepared"]]];
    [([_medic] call ACME_fnc_inventorySnapshot) isEqualTo [],"unidentified raw carrier silently saved"] call _check;
    ''')


def test_snapshot_rejects_duplicate_tuple_and_unacknowledged_edit():
    execute(setup() + r'''
    call _issue;private _n=+(_medic getVariable "native");_n pushBack (+(_n select 0));_medic setVariable ["native",_n];
    [([_medic] call ACME_fnc_inventorySnapshot) isEqualTo [],"duplicate carrier saved as two doses"] call _check;
    _medic setVariable ["native",[[call _token,"prepared"]]];
    _medic setVariable ["ACME_inventoryPayloadCache",createHashMapFromArray [["prepared:set1",[_payload,99]]]];
    [([_medic] call ACME_fnc_inventorySnapshot) isEqualTo [],"unacknowledged newer payload saved"] call _check;
    ''')


@pytest.mark.parametrize('kind', ['prepared', 'syringe'])
def test_restore_remaps_identity_exactly_once_and_preserves_all_dose_data(kind):
    prep = 'call _issue;' if kind == 'prepared' else r'''
    private _row=["Lidocaine",10,3.25,"Custom",2.125,[["Lidocaine",3.25]],"dilutionB13","red","line1","line2","line3","sy1","flush","inventoryB279"];
    [_medic,"syringe",[["sy1",_row]]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    '''
    execute(setup() + prep + r'''
    private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    private _old=+(_medic getVariable "native");
    [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"valid import rejected"] call _check;
    [(_medic getVariable "native") isEqualTo [],"saved source tuple survived exchange"] call _check;
    call _flush;
    private _new=_medic getVariable "native";
    [count _new==1 && {_new isNotEqualTo _old},"identity not remapped"] call _check;
    private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_new select 0 select 0],[]];
    [(_record select 1)!="set1" && {(_record select 1)!="sy1"},"saved SID reused"] call _check;
    [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"completed import replay rejected"] call _check;call _flush;
    [(_medic getVariable "native") isEqualTo _new,"completed replay minted another identity"] call _check;
    ''' + (r'''
    private _medNew=(_record select 2) select 2;
    [(_medNew select 10)==119.25 && {(_medNew select 14) isEqualTo (_med select 14)}
        && {(_medNew select 9)==12} && {(_medNew select 12) isEqualTo _medic},"prepared mixture/provider/clock changed incorrectly"] call _check;
    [((_record select 2) select 1 select 5) find "ACME_unresolved:"==0,"unresolved patient tie reused raw netId"] call _check;
    ''' if kind == 'prepared' else r'''
    private _newRow=(_record select 2) select 1;
    _newRow set [11,"sy1"];
    [_newRow isEqualTo _row,"exact syringe volumes/components/tags lost"] call _check;
    '''))


def test_explicit_patient_rebinding_keeps_tied_set_patient_restriction():
    execute(setup() + r'''
    call _issue;private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    [([_medic,_snapshot,createHashMapFromArray [["patientA",_receiver]]] call ACME_fnc_inventoryRestore),"explicit binding rejected"] call _check;call _flush;
    private _sets=_medic getVariable "ACME_preparedIVSets";
    [(_sets select 0 select 5)=="rebound-patient","bound patient identity lost"] call _check;
    ''')


@pytest.mark.parametrize('fault', ['missing_second', 'remove_false', 'lying_remove'])
def test_restore_never_issues_without_exact_complete_source_funding(fault):
    action = {
        'missing_second': 'private _second=+((_snapshot select 1) select 0);_second set [1,444];private _p=+(_second select 3);_p set [0,"other"];private _s=+(_p select 1);_s set [0,"other"];_p set [1,_s];_p set [2,[]];_second set [3,_p];(_snapshot select 1) pushBack _second;',
        'remove_false': '_removeAllowed=false;',
        'lying_remove': '_lyingRemove=true;',
    }[fault]
    execute(setup() + 'call _issue;private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;private _before=+(_medic getVariable "native");' + action + r'''
    [!([_medic,_snapshot] call ACME_fnc_inventoryRestore),"unfunded import succeeded"] call _check;call _flush;
    [(_medic getVariable "native") isEqualTo _before && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"unproven removal created/lost carrier"] call _check;
    ''')


def test_funded_retry_keeps_payload_and_cannot_cross_kit_retirement():
    execute(setup() + r'''
    call _issue;private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    private _commit=ACME_fnc_inventoryLedgerCommit;ACME_fnc_inventoryLedgerCommit={false};
    [!([_medic,_snapshot] call ACME_fnc_inventoryRestore),"failed enqueue reported complete"] call _check;
    private _evidence=str (_medic getVariable "ACME_inventoryRestoreJournal");
    _medic setVariable ["ACME_equipmentKitEpoch",1];ACME_fnc_inventoryLedgerCommit=_commit;
    [!([_medic,_snapshot] call ACME_fnc_inventoryRestore),"retired funding reminted"] call _check;
    [_evidence==str (_medic getVariable "ACME_inventoryRestoreJournal") && {count _queue==0},"retired evidence lost or enqueued"] call _check;
    ''')


@pytest.mark.parametrize('bad', [
    '[]', '[2,[]]', '[1,"bad"]', '[1,[nil]]',
    '[1,[["prepared",1,"ACME_PreparedIVSet",["s",["s","bag","action","","","","label",true,"blood"],[]],[]],["prepared",1,"ACME_PreparedIVSet",["s2",["s2","bag","action","","","","label",true,"blood"],[]],[]]]]',
    '[1,[["prepared",1,"ACME_PreparedIVSet",["s",["s","bag","action","","","","label",true,"blood"],["s"]],[]]]]',
    '[1,[["syringe",1,"ACME_PreparedSyringe",["s",["Lidocaine",1,2,"",0,[],"","","","","","s","","inventoryB279"]],[]]]]',
])
def test_malformed_metadata_is_rejected_before_any_native_mutation(bad):
    execute(setup() + 'call _issue;private _before=str (_medic getVariable "native");' + f'private _bad={bad};' + r'''
    [!([_bad] call ACME_fnc_inventorySnapshotValid),"malformed snapshot validated"] call _check;
    [!([_medic,_bad] call ACME_fnc_inventoryRestore),"malformed snapshot restored"] call _check;
    [str (_medic getVariable "native")==_before && {count _queue==0},"malformed snapshot mutated inventory"] call _check;
    ''')


def test_profile_blocks_are_reserved_before_issuance_and_skipped_after_restart():
    execute(setup() + r'''
    private _one=call ACME_fnc_inventoryLedgerNextToken;
    [_one==1 && {_profileWrites==1} && {(profileNamespace getVariable "ACME_inventoryTokenHighWater_v1")==256},"first block was not flushed"] call _check;
    private _two=call ACME_fnc_inventoryLedgerNextToken;
    [_two==2 && {_profileWrites==1},"allocation flushed per item or repeated ID"] call _check;
    missionNamespace setVariable ["ACME_inventoryTokenReservedThrough",nil];
    missionNamespace setVariable ["ACME_inventoryTokenSequence",0];
    private _after=call ACME_fnc_inventoryLedgerNextToken;
    [_after==257 && {_profileWrites==2} && {(profileNamespace getVariable "ACME_inventoryTokenHighWater_v1")==512},"restart recycled abandoned block"] call _check;
    ''')


@pytest.mark.parametrize('value', ['65534', '-1', '1.5', '"bad"'])
def test_exhausted_or_invalid_profile_fails_closed(value):
    execute(setup() + f'profileNamespace setVariable ["ACME_inventoryTokenHighWater_v1",{value}];' + r'''
    private _token=call ACME_fnc_inventoryLedgerNextToken;
    [_token==0 && {_profileWrites==0},"invalid/exhausted profile allocated or rewrote evidence"] call _check;
    ''')


def test_matching_raw_old_token_cannot_adopt_current_preparation_while_prior_custody_remains():
    execute(setup() + r'''
    call _issue;private _before=str (call _record);
    _receiver setVariable ["native",+(_medic getVariable "native")];
    [!([_receiver,"prepared",call _token,true] call ACME_fnc_inventoryLedgerAdopt),"raw duplicate adopted a current item"] call _check;
    [([_receiver,"prepared","set1","raw-adopt",true] call ACME_fnc_inventoryLedgerReserve) isEqualTo [],"direct duplicate reserve removed source"] call _check;
    [str (call _record)==_before && {count _queue==0} && {count (_receiver getVariable "native")==1},"duplicate changed canonical contents or custody"] call _check;
    ''')


@pytest.mark.parametrize('mode', ['update', 'claim', 'return', 'consume'])
def test_server_rejects_all_mutations_from_duplicate_claimant(mode):
    execute(setup() + r'''
    call _issue;private _before=str (call _record);
    _receiver setVariable ["native",+(_medic getVariable "native")];
    _receiver setVariable ["ACME_inventoryEscrow",createHashMapFromArray [["duplicate",[call _token,_payload,"prepared","duplicate",0,true]]]];
    ''' + f'["{mode}",_receiver,"prepared","set1",_payload,"duplicate"] call ACME_fnc_inventoryLedgerBroker;' + r'''
    [str (call _record)==_before,"duplicate claimant changed live payload/custody"] call _check;
    [count _replies==1 && {!((_replies select 0) select 6)},"duplicate mutation not rejected once"] call _check;
    ''')


def test_fresh_blood_prepared_snapshot_captures_donor_data_and_rebases_collection_age():
    execute(setup() + r'''
    CBA_missionTime=7200;
    _set set [1,"ACM_FreshBloodBag_500_17"];_set set [2,"FreshBloodBag_500_17"];
    _payload set [1,_set];_payload set [2,[]];
    missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[17,[objNull,500,6,true,3600]]]];
    call _issue;private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    [((_snapshot select 1) select 0 select 3 select 1 select 11) isEqualTo ["freshAgeV1",true,3600,6],"fresh donor age/type not captured"] call _check;
    CBA_missionTime=12;
    missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[17,[objNull,500,0,false,12]]]];
    [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"fresh prepared import failed"] call _check;call _flush;
    private _restored=(_medic getVariable "ACME_preparedIVSets") select 0;
    [(_restored select 11) isEqualTo ["freshV1",true,-3588,6],"fresh import reused donor ID or absolute old clock"] call _check;
    private _again=[_medic] call ACME_fnc_inventorySnapshot;
    [((_again select 1) select 0 select 3 select 1 select 11) isEqualTo ["freshAgeV1",true,3600,6],"re-save replaced inline donor metadata with reused registry ID"] call _check;
    ''')


def test_missing_fresh_blood_metadata_is_fenced_across_import_and_resave():
    execute(setup() + r'''
    _set set [1,"ACM_FreshBloodBag_500_17"];_set set [2,"FreshBloodBag_500_17"];
    _payload set [1,_set];_payload set [2,[]];
    call _issue;private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    [((_snapshot select 1) select 0 select 3 select 1 select 11) isEqualTo ["freshMissingV1"],"unknown donor silently accepted"] call _check;
    missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[17,[objNull,500,0,true,12]]]];
    [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"missing donor carrier could not be retained"] call _check;call _flush;
    private _again=[_medic] call ACME_fnc_inventorySnapshot;
    [((_again select 1) select 0 select 3 select 1 select 11) isEqualTo ["freshMissingV1"],"re-save acquired unrelated reused donor registry data"] call _check;
    ''')


@pytest.mark.parametrize('marker', ['["unknown"]', '["freshAgeV1",true,300,0]', '["freshV1",true,"bad",0]'])
def test_nonempty_invalid_prepared_fresh_marker_never_rebinds_reused_registry_id(marker):
    execute(setup() + r'''
    _set set [1,"ACM_FreshBloodBag_500_17"];_set set [2,"FreshBloodBag_500_17"];
    ''' + f'_set set [11,{marker}];' + r'''
    _payload set [1,_set];_payload set [2,[]];
    missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[17,[objNull,500,0,true,12]]]];
    call _issue;private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    [((_snapshot select 1) select 0 select 3 select 1 select 11) isEqualTo ["freshMissingV1"],"invalid inline donor marker fell back to reused registry ID"] call _check;
    ''')


def test_fresh_profile_import_skips_source_token_even_if_separate_fence_publication_is_delayed():
    execute(setup() + r'''
    call _issue;private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
    // Simulate migrating this native+metadata save to a clean server profile.
    missionNamespace setVariable ["ACME_inventoryLedgerIndex",createHashMap];
    missionNamespace setVariable ["ACME_inventoryToken_1",[]];
    missionNamespace setVariable ["ACME_inventoryTokenSequence",0];
    missionNamespace setVariable ["ACME_inventoryTokenReservedThrough",nil];
    profileNamespace setVariable ["ACME_inventoryTokenHighWater_v1",0];
    [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"fresh-profile import failed"] call _check;
    // The pending allocation contains its immutable exclusions, independently
    // of the separately replicated owner fence variable.
    _medic setVariable ["ACME_inventoryImportAvoid",[]];call _flush;
    private _after=+(_medic getVariable "native");
    [(_after select 0 select 0)==2,"fresh-profile import reused saved source token"] call _check;
    [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"fresh-profile replay rejected"] call _check;call _flush;
    [(_medic getVariable "native") isEqualTo _after,"fresh-profile import replay minted another carrier"] call _check;
    ''')


def test_frozen_server_defers_funded_registration_then_retries_without_losing_payload():
    execute(setup() + r'''
    _medic setVariable ["ACME_persistenceFrozen",true];
    [_medic,"prepared",[_payload]] call ACME_fnc_inventoryLedgerCommit;call _broker;
    [count _replies==0 && {count (_medic getVariable "native")==0}
        && {count (_medic getVariable "ACME_inventoryPending")==1},"freeze terminally rejected funded registration"] call _check;
    _medic setVariable ["ACME_persistenceFrozen",false];
    [_medic,"prepared",[_payload]] call ACME_fnc_inventoryLedgerCommit;call _flush;
    [count (_medic getVariable "native")==1 && {(call _record select 2) isEqualTo _payload},"unfreeze lost funded preparation"] call _check;
    ''')


def test_freeze_blocks_new_reservation_but_preserves_existing_claim_and_settlement():
    execute(setup() + r'''
    call _issue;_medic setVariable ["ACME_persistenceFrozen",true];
    [([_medic,"prepared","set1","new"] call ACME_fnc_inventoryLedgerReserve) isEqualTo [],"frozen reserve removed source"] call _check;
    _medic setVariable ["ACME_persistenceFrozen",false];
    [_medic,"prepared","set1","existing"] call ACME_fnc_inventoryLedgerReserve;
    [_medic,"existing",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
    _medic setVariable ["ACME_persistenceFrozen",true];
    ["claim",_medic,"prepared","set1",_payload,"existing"] call ACME_fnc_inventoryLedgerBroker;
    [count _replies==1 && {(_replies select 0) select 6},"existing claim duplicate could not drain"] call _check;call _reply;
    [_medic,"existing",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
    [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_inventoryEscrow")==0},"freeze blocked existing settlement"] call _check;
    ''')
