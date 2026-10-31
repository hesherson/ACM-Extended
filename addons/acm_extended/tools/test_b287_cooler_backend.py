"""Execute identified cooler issue, custody and edit helpers with real ledger code.

Native inventory, capacity and networking are explicit fixture boundaries; this
suite does not certify native Arma replication or external mission persistence.
"""
import re

from test_b279_inventory_ledger import setup as ledger_setup, adapted
from test_menu_death_lifecycle import F, execute
from test_historical_medication_rows import iteration_scopes


def function(name):
    text=(F/f"fn_{name}.sqf").read_text()
    text=text.replace("serverTime","CBA_missionTime")
    if name == "coolerRecover":
        for statement in ['_owner setVariable ["ACME_coolerBoxRequests",_requests,true]','_owner setVariable ["ACME_coolerIntents",_intents,true]']:
            text=text.replace(statement,'_publications=_publications+1; '+statement)
    text=text.replace('_owner isKindOf "CAManBase"','true')
    text=text.replace("_holder setVariable [_name, _value, _public]","_holder setVariable [_name, _value]")
    text=text.replace('netId _owner','"provider"')
    text=text.replace('uniformItems _owner','(_owner getVariable ["inputItems",[]])')
    text=text.replace('vestItems _owner','[]').replace('backpackItems _owner','[]')
    text=text.replace('_owner removeItem _base','[_owner,_base] call _removeInput')
    text=text.replace('_owner addItem _base','[_owner,_base] call _addInput')
    text=text.replace('getNumber (configFile >> "CfgWeapons" >> _base >> "ACME_coolerCapacityMl")','1000')
    # Mission time and server time are independent fixture clocks for migration.
    text=re.sub(r'(?<!\w)time(?!\w)','_missionTime',text)
    for map_name in ('_requests','_intents'):
        text=text.replace(f'forEach {map_name};',f'forEach (keys {map_name});')
    text=text.replace('private _args=+_y;','private _args=+(_requests get _x);')
    text=text.replace('private _intent=_y;','private _intent=_intents get _x;')
    return f'ACME_fnc_{name}={{'+adapted(iteration_scopes(text))+'};'


def setup():
    text=ledger_setup()
    text=text.replace('["prepared","syringe"] select ((_class find "ACME_PreparedSyringe")==0)',
        'if ((_class find "ACME_CoolerCarrier_")==0) then {"cooler"} else {["prepared","syringe"] select ((_class find "ACME_PreparedSyringe")==0)}')
    text=text.replace('isClass (configFile >> "CfgMagazines" >> _class)','true')
    text=text.replace('_owner isKindOf "CAManBase"','true')
    text=text.replace('_owner addMagazineAmmoCargo [_class,1,_token]','[_owner,_class,_token] call _addNative')
    text += r'''
    private _publications=0;
    private _missionTime=1;
    CBA_missionTime=100;
    private _removeInput={params ["_owner","_base"]; private _items=+(_owner getVariable ["inputItems",[]]);
        private _index=_items find _base; if (_index>=0) then {_items deleteAt _index;}; _owner setVariable ["inputItems",_items];};
    private _addInput={params ["_owner","_base"];private _items=+(_owner getVariable ["inputItems",[]]);_items pushBack _base;_owner setVariable ["inputItems",_items];};
    ACME_fnc_coolerAdvance={params ["_state",["_now",CBA_missionTime]]; [_state select 0,_state select 1,(_state select 2) apply {+_x},_now]};
    private _base="ACME_BloodCooler_CSWB2U";
    private _state=[_base,20,[["ACM_BloodBag_ON_500",123]],100];
    '''
    text += '\n'.join(function(n) for n in ['coolerStateCommit','coolerRows','coolerIssue','coolerMutate','coolerRecover'])
    return text


def test_same_class_coolers_receive_independent_tokens_and_exact_payloads():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base,_base]];
    private _one=[_medic,_base,_state] call ACME_fnc_coolerIssue;
    private _second=[_base,50,[["ACM_BloodBag_A_500",456]],100];
    private _two=[_medic,_base,_second] call ACME_fnc_coolerIssue;
    call _flush;
    [_one != "" && {_two != ""} && {_one != _two},"same-class issue reused SID"] call _check;
    [count (_medic getVariable "native")==2 && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==2},"same-class issue did not allocate two carriers"] call _check;
    private _rows=[_medic] call ACME_fnc_coolerRows;
    [count _rows==2 && {((_rows select 0) select 1) isEqualTo _state} && {((_rows select 1) select 1) isEqualTo _second},"independent payloads mixed"] call _check;
    [(_medic getVariable "inputItems") isEqualTo [],"funding inputs not consumed exactly once"] call _check;
    ''')


def test_missing_funding_input_cannot_issue_or_create_pending_payload():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;
    [_sid == "" && {count _queue==0} && {count (_medic getVariable "ACME_inventoryPending")==0},"unfunded cooler issued"] call _check;
    ''')


def test_legacy_class_state_is_adopted_once_and_clock_rebased():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base,_base]];
    _medic setVariable ["ACME_coolerCoolant",createHashMapFromArray [[_base,-99]]];
    _medic setVariable ["ACME_coolerStore",createHashMapFromArray [[_base,[["ACM_BloodBag_ON_500",777]]]]];
    private _one=[_medic,_base] call ACME_fnc_coolerIssue;
    private _two=[_medic,_base] call ACME_fnc_coolerIssue;
    call _flush;
    private _rows=[_medic] call ACME_fnc_coolerRows;
    [((_rows select 0) select 1 select 1)==0 && {((_rows select 0) select 1 select 2) isEqualTo [["ACM_BloodBag_ON_500",777]]},"migration reset legacy age or start"] call _check;
    [((_rows select 1) select 1 select 1)==100 && {count ((_rows select 1) select 1 select 2)==2},"second independent cooler inherited legacy state"] call _check;
    [!(_base in (_medic getVariable "ACME_coolerStore")) && {!(_base in (_medic getVariable "ACME_coolerCoolant"))},"legacy source was replayable"] call _check;
    ''')


def test_native_handoff_preserves_cooler_contents_and_blocks_donor_edits():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    _receiver setVariable ["native",_medic getVariable "native"]; _medic setVariable ["native",[]];
    [_receiver] call ACME_fnc_inventoryLedgerReconcile;call _flush;
    [([_receiver] call ACME_fnc_coolerRows) isEqualTo [[_sid,_state]],"handoff changed cooler freshness"] call _check;
    [([_medic] call ACME_fnc_coolerRows) isEqualTo [],"donor retained virtual cooler"] call _check;
    private _called=false;
    private _accepted=[_medic,_sid,{_called=true;[]}] call ACME_fnc_coolerMutate;
    [!_accepted && {!_called} && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"stale donor could edit or remint cooler"] call _check;
    ''')


def test_mutation_runs_only_after_claim_and_duplicate_reply_cannot_repeat_it():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    private _calls=0;
    [_medic,_sid,{params ["_owner","_sid","_state"];_calls=_calls+1;_state set [2,[]];[false,_state]}] call ACME_fnc_coolerMutate;
    [_calls==0 && {count (_medic getVariable "native")==0},"mutation ran before server custody"] call _check;
    call _broker;private _claimAck=+(_replies select 0);call _flush;
    _claimAck call ACME_fnc_inventoryLedgerReply;call _flush;
    [_calls==1 && {count (_medic getVariable "native")==1},"duplicate acknowledgement repeated mutation or carrier"] call _check;
    [((([_medic] call ACME_fnc_coolerRows) select 0) select 1 select 2) isEqualTo [],"mutation result lost"] call _check;
    ''')


def test_rejected_mutation_returns_exact_freshness_without_refill():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    [_medic,_sid,{[]}] call ACME_fnc_coolerMutate;call _flush;
    [([_medic] call ACME_fnc_coolerRows) isEqualTo [[_sid,_state]],"rejection reset or refilled cooler"] call _check;
    ''')


def test_recovery_replays_journaled_result_after_native_side_effect():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    [_medic,_sid,{params ["_owner","_sid","_state"];_state set [2,[]];[false,_state]}] call ACME_fnc_coolerMutate;
    call _broker;call _reply;
    // Drop the queued terminal message and its retry entry as a locality boundary.
    _queue=[];_medic setVariable ["ACME_inventoryRequests",createHashMap];
    [_medic] call ACME_fnc_coolerRecover;call _flush;
    [((([_medic] call ACME_fnc_coolerRows) select 0) select 1 select 2) isEqualTo [],"recovery restored already withdrawn blood"] call _check;
    ''')


def test_read_only_cooler_projection_does_not_generate_idle_edits():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    for "_i" from 1 to 20 do {[_medic] call ACME_fnc_coolerRows;[_medic] call ACME_fnc_inventoryLedgerReconcile;};
    [count _queue==0 && {count (_medic getVariable "ACME_inventoryRequests")==0} && {count (_medic getVariable "native")==1},"idle projection generated escrow or traffic"] call _check;
    ''')


def test_mutation_completion_runs_after_result_journal_and_terminal_enqueue():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    private _completed=0;
    [_medic,_sid,{params ["_owner","_sid","_state"];_state set [2,[]];[false,_state]},[],[{
        params ["_ok"];
        private _results=(_medic getVariable "ACME_coolerIntents") call _values;
        [_ok && {count _results==1} && {((_results select 0) select 0)=="mutationResult"} && {count (_medic getVariable "ACME_inventoryRequests")==1},"completion preceded durable result and settlement"] call _check;
        _completed=_completed+1;
    },[]]] call ACME_fnc_coolerMutate;
    [_completed==0,"completion preceded custody ACK"] call _check;call _flush;
    [_completed==1,"completion omitted or repeated"] call _check;
    ''')


def test_mutation_completion_reports_rejected_edit_and_missing_custody_once():
    execute(setup()+r'''
    private _completed=[];
    [_medic,"missing",{[false,_state]},[],[{_completed pushBack (_this select 0);},[]]] call ACME_fnc_coolerMutate;
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    [_medic,_sid,{[]},[],[{_completed pushBack (_this select 0);},[]]] call ACME_fnc_coolerMutate;call _flush;
    [_completed isEqualTo [false,false],"failed edits did not report one false completion"] call _check;
    ''')


def test_read_rows_do_not_alias_canonical_nested_blood_entries():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    private _sid=[_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    private _rows=[_medic] call ACME_fnc_coolerRows;
    (((_rows select 0) select 1) select 2 select 0) set [1,0];
    [((([_medic] call ACME_fnc_coolerRows) select 0) select 1 select 2 select 0 select 1)==123,"read projection mutated canonical exposure by reference"] call _check;
    ''')


def test_idle_recovery_does_not_publish_empty_or_unchanged_maps():
    execute(setup()+r'''
    _medic setVariable ["inputItems",[_base]];
    [_medic,_base,_state] call ACME_fnc_coolerIssue;call _flush;
    for "_i" from 1 to 20 do {[_medic] call ACME_fnc_coolerRecover;};
    [_publications==0 && {count _queue==0},"idle recovery published maps or sent server requests"] call _check;
    ''')
