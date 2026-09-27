"""Execute stored tag-editor lifetimes with explicit display/control fixtures.

Actual Open/Done and record-identity code executes. Focus calls and delayed jobs
are recorded, not live Arma UI scheduling, font rendering or input dispatch.
"""
import re
import pytest
from source_scan import lex
from test_menu_death_lifecycle import execute
from test_historical_syringe_identity import setup as identity_setup, source, code as identity_code
from test_historical_procedure_trays import controls, ui_code


def code(text):
    text = text.replace('_list lbSetCurSel -1;', '_listReset=-1;')
    text = identity_code(text)
    return ui_code(text)


def setup():
    # Object ownership is represented by namespace objects only at this VM boundary.
    base = identity_setup().replace('["_owner", ACE_player, [objNull]]',
                                    '["_owner", ACE_player, [missionNamespace]]')
    return base + controls() + '''
        private _layouts=[];
        {_textValues set [str _x,"existing"];} forEach [84460,84461,84462];
        ACME_fnc_skDynamicLayout={_layouts pushBack _this;};
        CBA_fnc_waitAndExecute={_waits pushBack _this;};
        private _deliver={params ["_job"]; (_job select 1) call (_job select 0);};
        uiNamespace setVariable ["ACME_SK_View","body"];
        uiNamespace setVariable ["ACME_SK_TagEditMode",false];
        ["id-b",_rows] call ACME_fnc_skSelectStored;
    ''' + 'private _open={' + code(source('skTagEditOpen')) + '};\n' + \
        'private _done={' + code(source('skTagEditDone')) + '};\n'


@pytest.mark.parametrize('color,expected', [('none',84470), ('',84470), ('blue_opioid',84460)])
@pytest.mark.parametrize('reorder', [False,True])
def test_current_editor_focus_keeps_delay_color_choice_and_stable_syringe(color,expected,reorder):
    execute(setup() + f'_b set [7,"{color}"]; [_medic,_rows] call ACME_fnc_narcStoreCommit;' + '''
        [call _open,"editor failed to open"] call _check;
        [count _focusIds==0 && {count _waits==1},"focus was not deferred exactly once"] call _check;
        [((_waits select 0) select 2)==0.14,"authored focus delay changed"] call _check;
    ''' + ('[_medic,[_c,_a,_b]] call ACME_fnc_narcStoreCommit;' if reorder else '') + '''
        private _before=+(_medic getVariable "ACME_narcStore");
        [_waits select 0] call _deliver;
    ''' + f'[_focusIds isEqualTo [{expected}],"wrong initial focus"] call _check;' + '''
        [(_medic getVariable "ACME_narcStore") isEqualTo _before,"focus changed drug or tag data"] call _check;
        [_layouts isEqualTo [[0.12]] && {_renders==1} && {_hotspots==1},"editor presentation changed"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_drawDisplay=objNull;',
    '_drawDisplay=profileNamespace;',
    'uiNamespace setVariable ["ACME_SK_View","syringe"];',
    'uiNamespace setVariable ["ACME_SK_TagEditMode",false];',
    'ACE_player=_patient; _patient setVariable ["ACME_narcStore",+_rows];',
    '["id-c",_rows] call ACME_fnc_skSelectStored;',
    '[_medic,[_a,_c]] call ACME_fnc_narcStoreCommit;',
    'missionNamespace setVariable ["ACME_SK_TagEditEpoch",999];',
])
def test_retired_editor_callback_cannot_focus_a_different_context(change):
    execute(setup() + '''
        call _open;
        private _old=_waits select 0;
    ''' + change + '''
        private _before=+(_medic getVariable "ACME_narcStore");
        private _chosen=uiNamespace getVariable "ACME_SK_SelectedSyringeId";
        [_old] call _deliver;
        [count _focusIds==0,"retired editor stole focus"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _before,"retired editor changed contents"] call _check;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")==_chosen,"retired editor changed selection"] call _check;
    ''')


@pytest.mark.parametrize('finish', [False,True])
def test_same_display_reentry_retires_the_old_focus_job(finish):
    execute(setup() + '''
        call _open;
        private _old=_waits select 0;
    ''' + ('call _done;' if finish else '') + '''
        call _open;
        private _new=_waits select 1;
        [_old] call _deliver;
        [count _focusIds==0,"earlier editor generation stole focus"] call _check;
        [_new] call _deliver;
        [_focusIds isEqualTo [84470],"current editor lost initial focus"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['display','page','empty'])
def test_invalid_open_cannot_enqueue_focus_or_change_edit_mode(invalid):
    change={'display':'_drawDisplay=objNull;', 'page':'uiNamespace setVariable ["ACME_SK_View","syringe"];',
            'empty':'[_medic,[]] call ACME_fnc_narcStoreCommit;'}[invalid]
    execute(setup()+change+'''
        [!(call _open),"invalid editor opened"] call _check;
        [count _waits==0 && {count _layouts==0} && {_renders==0},"invalid editor scheduled presentation"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_TagEditMode",false]),"invalid editor changed mode"] call _check;
    ''')


def test_done_commits_tag_and_restores_compact_body_map_before_old_job_runs():
    execute(setup()+'''
        _b set [7,"blue_opioid"]; [_medic,_rows] call ACME_fnc_narcStoreCommit;
        call _open;
        _textValues set ["84460","new line one"];
        _textValues set ["84461","Second"];
        _textValues set ["84462","Third"];
        [call _done,"Done failed"] call _check;
        private _store=_medic getVariable "ACME_narcStore";
        [((_store select 1) select [8,3]) isEqualTo ["new line one","Second","Third"],"Done did not commit selected tag"] call _check;
        [(_store select 0) isEqualTo _a && {(_store select 2) isEqualTo _c},"Done changed another syringe"] call _check;
        [!(uiNamespace getVariable "ACME_SK_TagEditMode") && {!(uiNamespace getVariable "ACME_SK_CarouselExpanded")},"Done did not leave editor"] call _check;
        [(uiNamespace getVariable "ACME_SK_CarouselCollapseAt")==0,"Done left a collapse timer"] call _check;
        [_waits select 0] call _deliver;
        [count _focusIds==0,"Done left an active focus job"] call _check;
    ''')


def assert_native_editor_contract(render=None, opener=None, done=None):
    def tokens(text): return [(t.kind,t.value) for t in lex(text)]
    def contains(text, needle):
        hay=tokens(text); pat=tokens(needle)
        return any(hay[i:i+len(pat)]==pat for i in range(len(hay)-len(pat)+1))
    render=source('skCarouselRender') if render is None else render
    opener=source('skTagEditOpen') if opener is None else opener
    done=source('skTagEditDone') if done is None else done
    for needle in ['private _editSize = (_store select _idx) param [1,10,[0]];',
                   '84010 + 3 * (([10,5,3,1] find _editSize) max 0) + 2',
                   '_fullW = _editNative select 2;', '_fullH = _editNative select 3;']:
        assert contains(render,needle),needle
    assert contains(opener,'ctrlSetFocus _focusCtrl;')
    assert contains(opener,'if (_color in ["","none"]) then {84470} else {84460}')
    for needle in ['call ACME_fnc_skTagCommit;', 'setVariable ["ACME_SK_TagEditMode", false]',
                   'setVariable ["ACME_SK_CarouselExpanded", false]']:
        assert contains(done,needle),needle


@pytest.mark.parametrize('which,old,new',[
    ('render','_fullW = _editNative select 2;','_fullW = 0.1;'),
    ('opener','then {84470} else {84460}','then {84460} else {84470}'),
    ('done','call ACME_fnc_skTagCommit;','call ACME_fnc_skBuildHotspots;'),
])
def test_native_editor_contract_rejects_mutations_and_comment_decoys(which,old,new):
    name={'render':'skCarouselRender','opener':'skTagEditOpen','done':'skTagEditDone'}[which]
    original=source(name); assert original.count(old)==1
    with pytest.raises(AssertionError):
        assert_native_editor_contract(**{which:original.replace(old,new)+'\n// '+old})
