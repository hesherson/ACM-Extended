"""Execute current edit and airway writers with explicit native-control boundaries.

These are SQF-VM tests, not native UI-focus, locality, or multiplayer acceptance.
"""
import pytest
from test_push_seconds_execution import edit_handler, execute as edit_execute
from test_b156_reset_lifecycle import setup, execute as lifecycle_execute


@pytest.mark.parametrize("live_display", [True, False])
@pytest.mark.parametrize("initial_drafts", ['createHashMap', '"invalid-old-value"'])
def test_typed_drafts_are_separate_per_syringe_and_do_not_repaint(live_display,initial_drafts):
    display='profileNamespace' if live_display else 'objNull'
    edit_execute('''
        private _ok=true;
        private _repaints=0;
        private _ctrl=missionNamespace;
        ACME_fnc_skBodyActionRender={_repaints=_repaints+1;};
        uiNamespace setVariable ["ACME_SK_PushDurationEditing",false];
        uiNamespace setVariable ["ACME_SK_PushDurationDrafts",'''+initial_drafts+'''];
        private _testDisplay='''+display+''';
        private _edit={'''+edit_handler()+'''};
        {
            _x params ["_id","_testInput","_expected","_expectedWrites"];
            private _writes=0;
            _ctrl setVariable ["ACME_SK_PushDurationFor",_id];
            private _result=[_ctrl] call _edit;
            private _drafts=uiNamespace getVariable ["ACME_SK_PushDurationDrafts",createHashMap];
            if (!(_result isEqualTo false) || {_drafts get _id != _expected}
                || {_writes!=_expectedWrites}) then {_ok=false;};
        } forEach [["first","300","300",0],["second","7s","7",1],["first","","",0],["first","120","120",0]];
        private _drafts=uiNamespace getVariable ["ACME_SK_PushDurationDrafts",createHashMap];
        if (!((_drafts get "first")=="120" && {(_drafts get "second")=="7"})
            || {_repaints!=0} || {!(uiNamespace getVariable ["ACME_SK_PushDurationEditing",false])}) then {_ok=false;};
        diag_log (if (_ok) then {"PUSH_SECONDS_OK"} else {"PUSH_SECONDS_FAIL"});
    ''')


@pytest.mark.parametrize("live_display", [True, False])
@pytest.mark.parametrize("typed", ["", "12x3", "0", "301"])
def test_edit_with_no_syringe_id_never_overwrites_another_draft(live_display,typed):
    display='profileNamespace' if live_display else 'objNull'
    clean=''.join(c for c in typed if c.isascii() and c.isdigit())
    edit_execute('''
        private _ok=true;
        private _writes=0;
        private _ctrl=missionNamespace;
        private _testDisplay='''+display+''';
        private _testInput="'''+typed+'''";
        private _drafts=createHashMapFromArray [["existing","30"]];
        uiNamespace setVariable ["ACME_SK_PushDurationDrafts",_drafts];
        _ctrl setVariable ["ACME_SK_PushDurationFor",""];
        [_ctrl] call {'''+edit_handler()+'''};
        private _after=uiNamespace getVariable ["ACME_SK_PushDurationDrafts",createHashMap];
        if (count _after!=1 || {(_after get "existing")!="30"} || {_testInput!="'''+clean+'''"}) then {_ok=false;};
        diag_log (if (_ok) then {"PUSH_SECONDS_OK"} else {"PUSH_SECONDS_FAIL"});
    ''')


@pytest.mark.parametrize("old,new,reset", [(0,1,True),(1,2,False),(2,0,True)])
@pytest.mark.parametrize("vomit_pool", [True,False])
def test_actual_native_airway_writer_retires_only_the_correct_partial_pool(old,new,reset,vomit_pool):
    pool='[[1,1],50]' if vomit_pool else '[[0,1],50]'
    expected_remaining='[]' if reset else '["partial",25]'
    expected_pool='[]' if reset and not vomit_pool else pool
    lifecycle_execute(setup()+f'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",{old}];
        _patient setVariable ["ACME_laryngo_bloodRemaining",["partial",25]];
        _patient setVariable ["ACME_laryngo_pool",{pool}];
        private _applied=[_patient,[["blood",{new}]],true] call ACM_airway_fnc_setAirwayState;
        [_applied==1,"native writer lost applied-field count"] call _check;
        [(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",-1])=={new},"native writer did not update the compartment"] call _check;
        [(_patient getVariable ["ACME_laryngo_bloodRemaining",["missing"]]) isEqualTo {expected_remaining},"incorrect partial blood ledger retention"] call _check;
        [(_patient getVariable ["ACME_laryngo_pool",["missing"]]) isEqualTo {expected_pool},"wrong shared/vomit pool retired"] call _check;
    ''')
