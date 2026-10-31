"""Execute physical valve receipts and clinical serialization from production SQF.

Object handles, finite-number support and CBA transport cross explicit engine
boundaries. Owner validation, replay order, mixed-bag mutation, publication and
snapshot validation execute actual checked-out functions. Native wire transport
and Arma rendering are not certified by these cases.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from test_historical_medication_rows import iteration_scopes
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import adapt, execute, read


@pytest.fixture(autouse=True)
def warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def compiled(name):
    text = read(name).replace("local _patient", "_ownerLocal")
    text = text.replace("owner _patient", "_patientOwner")
    text = re.sub(r"\bfinite (_\w+)", r"(\1 call _finite)", text)
    text = re.sub(r"\b(_(?:medic|patient)) isEqualType objNull",
                  r"(\1 isEqualTo objNull || {\1 isEqualType profileNamespace})", text)
    return f"ACME_fnc_{name}={{" + adapt(map_defaults(iteration_scopes(text))) + "};\n"


def row_setup():
    return r'''
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _ownerLocal=true;private _patientOwner=2;
        private _packets=[];private _replies=[];private _commits=0;
        ACME_fnc_clinicalEpoch={7};
        CBA_fnc_targetEvent={_replies pushBack _this;};
        ACME_fnc_setVarNet={params ["_p","_name","_value"];
            _packets pushBack [_name,str _value];_p setVariable [_name,_value];};
        missionNamespace setVariable ["ACME_infusion_dropSets",[10,15,20,60]];
        missionNamespace setVariable ["ACME_infusion_stateNetInterval",1];
        missionNamespace setVariable ["ACME_infusion_clampCurve",2];
        missionNamespace setVariable ["ACME_infusion_maxDropsPerMinute",120];
        private _dose={params ["_id",["_bag","bag-a"],["_med","Epinephrine"]];
            [_id,"leftarm",0,"Saline",0,true,-1,100,-1,100,100,_med,
                _med+"_IV",10,10,0,10,0,10,600,20,30,0.5,_bag,0,0,0.1,1]};
        private _entries=[["dose-a"] call _dose,["dose-b","bag-a","Ketamine"] call _dose,
            ["dose-other","bag-b","Calcium"] call _dose];
        private _physical=[["Saline",100,1,0,true,-1,100,-1,"bag-a"],
            ["Saline",100,1,1,true,-1,100,-1,"bag-b"]];
        private _publish={
            _patient setVariable ["ACME_infusion_BagMedications",_entries];
            _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",_physical]]];};
        call _publish;
        private _saved={str (_patient getVariable "ACME_infusion_BagMedications")};
        private _current={(_patient getVariable "ACME_infusion_BagMedications") select 0};
        private _position={(call _current) select 22};
        private _receipts={(call _current) param [28,[]]};
        private _lastAccepted={((_replies select ((count _replies)-1)) select 1) select 3};
    ''' + ''.join(compiled(name) for name in (
        'clampPositionToDrops', 'infusionMedicationStateCommit', 'infusionClampLocal')) + r'''
        private _commit=ACME_fnc_infusionMedicationStateCommit;
        ACME_fnc_infusionMedicationStateCommit={_commits=_commits+1;_this call _commit};
        private _send={params ["_stamp",["_position",0.25],["_dropSet",60],
            ["_ids",["dose-a"]],["_bag","bag-a"],["_actor",ACE_player]];
            [_patient,_ids,7,_position,_dropSet,[_actor,_stamp,_bag]] call ACME_fnc_infusionClampLocal;};
    '''


def test_new_command_changes_every_additive_on_only_its_physical_bag():
    execute(row_setup() + r'''
        private _other=str (_entries select 2);
        [[7,1,1],0.25,60,["dose-a","dose-b"]] call _send;
        [call _lastAccepted && {_commits==1},"new command was not positively acknowledged"] call _check;
        private _live=_patient getVariable "ACME_infusion_BagMedications";
        [{(_x select 22)==0.25 && {(_x select 20)==60} && {(_x select 28) isEqualTo [[7,1,1]]}} count (_live select [0,2])==2,
            "mixed additives did not share valve and receipt"] call _check;
        [str (_live select 2)==_other,"different bag changed"] call _check;
        [str (_entries select 0 select 22)=="0.5","source row alias changed before commit"] call _check;
        [(_replies select 0) isEqualTo ["ACME_clampResult",[_patient,ACE_player,[7,1,1],true],ACE_player],
            "result lost exact recipient or stamp"] call _check;
    ''')


@pytest.mark.parametrize('stamp', ('[7,1,1]', '[7,1,4]', '[7,2,1]'))
def test_older_session_or_sequence_cannot_replace_the_latest_value(stamp):
    execute(row_setup() + r'''
        [[7,2,3],0.7] call _send;private _before=call _saved;
        private _beforeCommits=_commits;
    ''' + f'[{stamp},0.1] call _send;' + r'''
        [!(call _lastAccepted) && {call _saved==_before} && {_commits==_beforeCommits},
            "older owner command changed source state or was accepted"] call _check;
    ''')


def test_duplicate_stamp_acknowledges_without_reapplying_altered_payload():
    execute(row_setup() + r'''
        [[7,1,1],0.7,60] call _send;private _before=call _saved;
        private _beforeCommits=_commits;private _beforePackets=count _packets;
        [[7,1,1],0.1,10] call _send;
        [call _lastAccepted && {call _saved==_before} && {_commits==_beforeCommits}
            && {count _packets==_beforePackets},"duplicate reapplied a changed payload or republished"] call _check;
    ''')


def test_another_medic_does_not_erase_the_first_medic_replay_fence():
    execute(row_setup() + r'''
        [[7,3,8],0.7] call _send;
        [[9,1,1],0.4] call _send;
        private _before=call _saved;
        [[7,3,7],0.9] call _send;
        [!(call _lastAccepted) && {call _saved==_before},"interleaved medic erased first-client fence"] call _check;
        [(call _receipts) isEqualTo [[7,3,8],[9,1,1]],"per-client history was not retained"] call _check;
        [[7,4,1],0.2] call _send;
        [call _lastAccepted && {call _position==0.2} && {(call _receipts) isEqualTo [[7,4,1],[9,1,1]]},
            "newer session did not reset only its own sequence"] call _check;
    ''')


@pytest.mark.parametrize('stamp,accepted', [('[7,2,2]', False), ('[7,2,4]', True)])
def test_divergent_component_ledgers_merge_maxima_before_admission(stamp, accepted):
    execute(row_setup() + r'''
        (_entries select 0) set [28,[[7,1,9]]];
        (_entries select 1) set [28,[[7,2,3],[9,1,5]]];
        call _publish;private _before=call _saved;
    ''' + f'[{stamp},0.2] call _send;' + f'''
        [(call _lastAccepted) isEqualTo {str(accepted).lower()},"merged receipt admission was wrong"] call _check;
    ''' + (r'''
        private _live=_patient getVariable "ACME_infusion_BagMedications";
        [(_live select 0 select 28) isEqualTo [[7,2,4],[9,1,5]]
            && {(_live select 1 select 28) isEqualTo (_live select 0 select 28)},
            "new command did not normalize merged component receipts"] call _check;
    ''' if accepted else r'''
        [call _saved==_before && {_commits==0},"rejection normalized or mutated source rows"] call _check;
    '''))


def test_copied_rows_on_a_new_owner_keep_all_replay_receipts():
    execute(row_setup() + r'''
        [[7,2,5],0.7] call _send;
        private _carried=(_patient getVariable "ACME_infusion_BagMedications") apply {
            private _row=+_x;if (count _row>28) then {_row set [28,(_row select 28) apply {+_x}];};_row};
        _patient=missionNamespace;_patientOwner=9;
        _patient setVariable ["ACME_infusion_BagMedications",_carried];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",_physical]]];
        private _before=call _saved;
        [[7,2,4],0.1] call _send;
        [!(call _lastAccepted) && {call _saved==_before},"new owner lost carried replay fence"] call _check;
        [[7,2,6],0.3] call _send;
        [call _lastAccepted && {call _position==0.3},"new owner rejected next ordered command"] call _check;
    ''')


@pytest.mark.parametrize('count', (26, 27, 28))
def test_legacy_rows_gain_receipts_without_sparse_holes_or_losing_existing_fields(count):
    execute(row_setup() + f'''
        (_entries select 0) resize {count};(_entries select 1) resize {count};
        if ({count}>26) then {{(_entries select 0) set [26,0.075];}};
        if ({count}>27) then {{(_entries select 0) set [27,5];}};
        call _publish;
        [[7,1,1]] call _send;
        private _row=call _current;
        [count _row==29 && {{(_row findIf {{isNil "_x"}})<0}},"legacy extension introduced nil holes"] call _check;
        [abs ((_row select 26)-{0.1 if count == 26 else 0.075})<0.000001 && {{(_row select 27)=={5 if count == 28 else 1}}},
            "legacy concentration or dose revision was overwritten"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_physical deleteAt 0;call _publish;',
    '_physical pushBack (+(_physical select 0));call _publish;',
    '(_physical select 0) set [8,"replacement"];call _publish;',
    '(_entries select 0) set [0,"replacement-dose"];call _publish;',
    '(_entries select 0) set [23,"orphan"];call _publish;',
    '_patient setVariable ["ACME_persistenceFrozen",true];',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
    '_alive=false;',
    'ACME_fnc_clinicalEpoch={8};',
])
def test_invalid_context_is_negatively_acknowledged_without_mutating_source(change):
    execute(row_setup() + change + r'''
        private _before=call _saved;
        [[7,1,1]] call _send;
        [!(call _lastAccepted) && {call _saved==_before} && {_commits==0},
            "invalid context changed source or lacked negative result"] call _check;
    ''')


@pytest.mark.parametrize('ids,bag', [
    ('["dose-a","missing"]', 'bag-a'), ('["dose-a","dose-other"]', 'bag-a'),
    ('[]', 'bag-a'), ('["dose-a"]', 'bag-b'),
])
def test_every_requested_medication_id_must_resolve_to_the_captured_bag(ids, bag):
    execute(row_setup() + r'private _before=call _saved;' +
            f'[[7,1,1],0.2,20,{ids},"{bag}"] call _send;' + r'''
        [!(call _lastAccepted) && {call _saved==_before} && {_commits==0},
            "partial or cross-bag identity list was accepted"] call _check;
    ''')


@pytest.mark.parametrize('stamp', [
    '[]', '[7,1]', '[7,1,1,1]', '[7,0,1]', '[7,1,0]', '[-1,1,1]',
    '[7,1.5,1]', '[7,1,1.5]', '["7",1,1]', '[7,1,"bad"]',
])
def test_malformed_numeric_stamps_never_mutate_the_patient(stamp):
    execute(row_setup() + r'private _before=call _saved;' + f'[{stamp}] call _send;' + r'''
        [call _saved==_before && {_commits==0},"malformed stamp changed source"] call _check;
    ''')


@pytest.mark.parametrize('ledger', ['"bad"', '[[7,1,1],[7,2,1]]', '[[7,0,1]]', '[[7,1,0]]'])
def test_malformed_persisted_ledger_is_not_silently_replaced(ledger):
    execute(row_setup() + f'(_entries select 1) set [28,{ledger}];call _publish;' + r'''
        private _before=call _saved;
        [[7,1,2]] call _send;
        [!(call _lastAccepted) && {call _saved==_before} && {_commits==0},
            "malformed saved ledger was erased by new command"] call _check;
    ''')


def test_legacy_five_argument_caller_retains_carrier_and_dead_patient_compatibility():
    execute(row_setup() + r'''
        _patientAlive=false;
        [_patient,["dose-a"],7,0.25,60] call ACME_fnc_infusionClampLocal;
        [call _position==0.25 && {_commits==1} && {_replies isEqualTo []},
            "legacy caller or retained dead-patient equipment changed contract"] call _check;
        [(call _current) param [28,[]] isEqualTo [],"legacy caller fabricated a receipt"] call _check;
    ''')


@pytest.mark.parametrize('missing', ('medic', 'patient'))
def test_missing_request_participant_never_mutates_the_medication_store(missing):
    execute(row_setup() + r'private _before=call _saved;' +
            ('[[7,1,1],0.2,20,["dose-a"],"bag-a",objNull] call _send;' if missing == 'medic' else
             '[objNull,["dose-a"],7,0.2,20,[ACE_player,[7,1,1],"bag-a"]] call ACME_fnc_infusionClampLocal;') + r'''
        [call _saved==_before && {_commits==0},"missing participant changed source store"] call _check;
    ''')


def test_new_same_position_receipt_publishes_immediately_and_signature_has_no_alias():
    execute(row_setup() + r'''
        [[7,1,1],0.5,20] call _send;
        private _before=count (_packets select {(_x select 0)=="ACME_infusion_BagMedications"});
        _nowTime=10.1;
        [[7,1,2],0.5,20] call _send;
        [count (_packets select {(_x select 0)=="ACME_infusion_BagMedications"})==_before+1,
            "same-position new receipt was delayed by cadence"] call _check;
        // The owner row array is mutable; the prior signature must retain its
        // old value even if an embedded receipt is modified in place.
        private _live=_patient getVariable "ACME_infusion_BagMedications";
        (_live select 0 select 28 select 0) set [2,3];
        [_patient,_live] call ACME_fnc_infusionMedicationStateCommit;
        [count (_packets select {(_x select 0)=="ACME_infusion_BagMedications"})==_before+2,
            "mutable receipt aliased its prior structural signature"] call _check;
    ''')


@pytest.mark.parametrize('existing', (False, True))
def test_later_additive_inherits_the_merged_receipt_ledger(existing):
    execute(row_setup() + compiled('infusionRegisterCore') + r'''
        (_entries select 0) set [28,[[7,1,9]]];
        (_entries select 1) set [28,[[7,2,3],[9,1,5]]];call _publish;
        ACME_fnc_canMedicateBagContext={true};
        ACME_fnc_findTrackedBag={["leftarm",0,_physical select 0]};
        ACME_fnc_bagIdentity={"bag-a"};
        missionNamespace setVariable ["ACME_infusion_deliveryClassOverride",createHashMap];
        private _context=[_patient,"leftarm",0,"Saline",1,0,true,-1,100,-1,100];
    ''' + f'private _medication="{"Epinephrine" if existing else "MagnesiumSulphate"}";' + r'''
        private _result=[_context,_medication,5,600,20,30,0.5,"new-dose","bag-a",7,0,true] call ACME_fnc_infusionRegisterCore;
        private _rows=(_patient getVariable "ACME_infusion_BagMedications") select {(_x select 23)=="bag-a"};
        [(_rows findIf {(_x select 28) isNotEqualTo [[7,2,3],[9,1,5]]})<0,
            "dose addition discarded mixed-bag receipt history"] call _check;
    ''' + f'''
        [_result=="{'dose-a' if existing else 'new-dose'}" && {{count _rows=={2 if existing else 3}}},
            "registration skipped its dose addition"] call _check;
        private _added=_rows select (_rows findIf {{(_x select 0)==_result}});
        [(_added select 28) isEqualTo [[7,2,3],[9,1,5]],"added dose did not inherit receipts"] call _check;
    ''')


@pytest.mark.parametrize('ledger,valid', [
    ('[]', True), ('[[7,1,1]]', True), ('[[7,2,3],[9,1,5]]', True),
    ('"bad"', False), ('[[7,1]]', False), ('[[7,1,1,2]]', False),
    ('[[7,0,1]]', False), ('[[7,1,0]]', False), ('[[-1,1,1]]', False),
    ('[[7,1.5,1]]', False), ('[[7,1,1.5]]', False), ('[["7",1,1]]', False),
    ('[[7,1,1],[7,2,1]]', False),
])
def test_clinical_snapshot_validator_preserves_only_valid_receipt_ledgers(ledger, valid):
    from test_b271_ptx_stability import execute as clinical_execute, restore_setup

    clinical_execute(restore_setup() + r'''
        private _row=["dose-a","leftarm",0,"Saline",0,true,-1,100,-1,100,100,
            "Epinephrine","Epinephrine_IV",10,10,0,10,0,10,600,20,30,0.5,"bag-a",0,0,0.1,1];
    ''' + f'_row set [28,{ledger}];' + r'''
        private _encoded=[[_row],true] call ACME_fnc_clinicalCodec;
        private _payload=[3,[["ACME_infusion_BagMedications",_encoded]]];
        private _result=[_payload] call ACME_fnc_clinicalValidate;
    ''' + f'''[(_result select 0) isEqualTo {str(valid).lower()},"clinical receipt validation mismatch"] call _check;''' +
        (r'''
            private _decoded=[_encoded,false] call ACME_fnc_clinicalCodec;
            [(_decoded select 0 select 28) isEqualTo (_row select 28),"codec discarded numeric receipt history"] call _check;
        ''' if valid else ''))
