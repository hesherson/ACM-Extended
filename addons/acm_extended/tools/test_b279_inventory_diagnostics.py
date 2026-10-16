"""Execute terminal inventory diagnostics and duplicate ACKs; engine log emission is captured."""
from test_menu_death_lifecycle import F, execute
from test_b279_inventory_ledger import setup, adapted
from source_scan import lex

def capture_logs(source):
    for token in reversed(lex(source)):
        if token.kind=="ident" and token.value=="diag_log":
            source=source[:token.offset]+"_diagnostics pushBack"+source[token.offset+len(token.value):]
    return source

def diagnostic_setup():
    source=setup()
    for name in ("inventoryLedgerBroker","inventoryLedgerReply"):
        raw=(F/f"fn_{name}.sqf").read_text()
        if name=="inventoryLedgerReply":
            raw=raw.replace('_owner setVariable ["ACME_inventoryPending",_pending,true];','_pendingWrites=_pendingWrites+1;_owner setVariable ["ACME_inventoryPending",_pending,true];')
        source+=f"ACME_fnc_{name}={{"+adapted(raw)+"};"
    return 'private _diagnostics=[];private _pendingWrites=0;missionNamespace setVariable ["ACME_inventoryExhaustionReported",false];'+capture_logs(source)

def assert_inventory_failure_diagnostics_bounded():
    execute(diagnostic_setup()+r'''
        missionNamespace setVariable ["ACME_inventoryTokenSequence",65534];
        [_medic,"prepared",[_payload]]call ACME_fnc_inventoryLedgerCommit;call _broker;
        [count _replies==1 && {(_replies select 0 select 4)==0} && {!(_replies select 0 select 6)},"exhaustion did not send exactly one unallocated-token failure ACK"]call _check;
        private _failure=+(_replies select 0);call _reply;
        [count _diagnostics==1 && {_pendingWrites==1},"terminal allocation did not report once/block once"]call _check;
        _failure call ACME_fnc_inventoryLedgerReply;_failure call ACME_fnc_inventoryLedgerReply;
        [count _diagnostics==1 && {_pendingWrites==1},"duplicate failure ACK logged or republished blocked state"]call _check;
        for "_replay" from 0 to 3 do {
            ["register",_medic,"prepared","set1",_payload,""]call ACME_fnc_inventoryLedgerBroker;
            [count _replies==1,"replayed exhaustion sent duplicate ACKs"]call _check;call _reply;
        };
        // Repeating unchanged funded metadata keeps the terminal row blocked.
        [_medic,"prepared",[_payload]]call ACME_fnc_inventoryLedgerCommit;
        [count _queue==0,"unchanged metadata re-queued a blocked allocation"]call _check;
        call _flush;
        [count _diagnostics==1 && {_pendingWrites==1},"unchanged funding repeated diagnostics or blocked-state publication"]call _check;
        [count (_medic getVariable "ACME_inventoryPending")==1 && {((_medic getVariable "ACME_inventoryPending")get "prepared:set1" select 2)isEqualTo _payload},"exhaustion lost funded contents"]call _check;
        [(missionNamespace getVariable "ACME_inventoryTokenSequence")==65534 && {count (missionNamespace getVariable "ACME_inventoryLedgerIndex")==0},"failed allocation advanced token state"]call _check;
        [count (_medic getVariable "native")==0 && {count (_holder getVariable "native")==0} && {(missionNamespace getVariable ["ACME_inventoryToken_0",[]])isEqualTo []} && {(missionNamespace getVariable ["ACME_inventoryToken_65535",[]])isEqualTo []},"invalid token materialized or acquired a ledger entry"]call _check;
    ''')

def test_terminal_inventory_diagnostic_is_once_and_duplicate_failure_ack_is_inert():
    assert_inventory_failure_diagnostics_bounded()

def test_normal_issue_full_inventory_spill_and_invalid_pending_are_quiet():
    execute(diagnostic_setup()+r'''
        _medic setVariable ["capacity",false];call _issue;
        [count _diagnostics==0 && {(_holder getVariable "native")isEqualTo [[1,"prepared"]]},"ordinary capacity spill logged or changed identity"]call _check;
        missionNamespace setVariable ["ACME_inventoryTokenSequence",65534];
        ["register",_medic,"prepared","missing",[],""]call ACME_fnc_inventoryLedgerBroker;
        [count _diagnostics==0 && {count _replies==0},"unfunded registration entered terminal diagnostics"]call _check;
    ''')
