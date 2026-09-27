"""Execute color selection and its delayed focus with explicit UI fixtures.

The actual writers and callbacks run; control lookup, focus, redraw and scheduling
are recorded. No real UI timing, input capture, network or font rendering claim.
"""
import pytest
from test_bounded_tag_focus import setup as editor_setup, code
from test_historical_syringe_identity import source
from test_menu_death_lifecycle import execute


def setup(kind):
    text = source('skPendingTagColor' if kind == 'pending' else 'skTagColor')
    text = text.replace('_ctrl lbData _row', '_chosenColor')
    text = text.replace('_ctrl lbSetCurSel -1;', '_listReset=-1;')
    text = text.replace('_ctrl ctrlShow false;', '_listShown=false;')
    text = code(text).replace('ctrlSetFocus (84601);', '_focusIds pushBack 84601;')
    return editor_setup() + '''
        ACME_fnc_skPendingTagRender={_renders=_renders+1;};
        uiNamespace setVariable ["ACME_SK_PendingTagText",["one","two","three"]];
        uiNamespace setVariable ["ACME_SK_TagEditMode",true];
        missionNamespace setVariable ["ACME_SK_TagEditEpoch",4];
    ''' + f'uiNamespace setVariable ["ACME_SK_View","{"syringe" if kind == "pending" else "body"}"];' + \
        'private _select={' + text + '};\n'


@pytest.mark.parametrize('kind',['stored','pending'])
@pytest.mark.parametrize('color',['','none','blue_opioid','red_paralytic'])
def test_current_selection_keeps_color_payload_reset_and_authored_focus_delay(kind,color):
    effective=color or 'none'
    scheduled=kind=='stored' or effective!='none'
    target=84601 if kind=='pending' else 84470 if effective=='none' else 84460
    execute(setup(kind)+f'_chosenColor="{color}"; [100,0] call _select;'+'''
        [_listReset==-1 && {!_listShown} && {_renders==1},"selection reset/render changed"] call _check;
        private _saved=+(_medic getVariable "ACME_narcStore");
    '''+f'[count _waits=={int(scheduled)} && {{count _focusIds==0}},"selection scheduled wrong number of focus jobs"] call _check;'+('''
        [((_waits select 0) select 2)==0.01,"color focus delay changed"] call _check;
        [_waits select 0] call _deliver;
    ''' if scheduled else '')+f'[_focusIds isEqualTo {f"[{target}]" if scheduled else "[]"},"wrong color focus target"] call _check;'+'''
        [(_medic getVariable "ACME_narcStore") isEqualTo _saved,"focus changed stored contents"] call _check;
        [(uiNamespace getVariable "ACME_SK_PendingTagText") isEqualTo ["one","two","three"],"color changed prepared tag text"] call _check;
    '''+(f'[(uiNamespace getVariable "ACME_SK_PendingTagColor")=="{effective}","wrong pending color"] call _check;'+
          '[_saved isEqualTo _rows,"pending selector edited stored syringes"] call _check;' if kind=='pending' else f'''
        [((_saved select 1) select 7)=="{effective}","wrong stored color"] call _check;
        [(_saved select 0) isEqualTo _a && {{(_saved select 2) isEqualTo _c}},"another syringe edited"] call _check;
        [((_saved select 1) select [0,7]) isEqualTo (_b select [0,7]) && {{((_saved select 1) select [8,5]) isEqualTo (_b select [8,5])}},"color changed medication/text/identity"] call _check;
    '''))


@pytest.mark.parametrize('kind',['stored','pending'])
@pytest.mark.parametrize('change',['closed','reopened','provider','page'])
def test_obsolete_color_focus_cannot_target_a_different_display_provider_or_page(kind,change):
    changes={
        'closed':'_drawDisplay=objNull;', 'reopened':'_drawDisplay=profileNamespace;',
        'provider':'ACE_player=_patient;',
        'page':f'uiNamespace setVariable ["ACME_SK_View","{"body" if kind=="pending" else "syringe"}"];',
    }
    execute(setup(kind)+'''
        _chosenColor="blue_opioid"; [100,0] call _select;
        private _old=_waits select 0;
    '''+changes[change]+'''
        private _saved=+(_medic getVariable "ACME_narcStore");
        [_old] call _deliver;
        [count _focusIds==0,"obsolete color selection stole focus"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _saved,"obsolete color focus changed payload"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    'uiNamespace setVariable ["ACME_SK_TagEditMode",false];',
    'missionNamespace setVariable ["ACME_SK_TagEditEpoch",5];',
    '["id-c",_rows] call ACME_fnc_skSelectStored;',
    '[_medic,[_a,_c]] call ACME_fnc_narcStoreCommit;',
    'private _now=+(_medic getVariable "ACME_narcStore"); (_now select 1) set [7,"none"]; [_medic,_now] call ACME_fnc_narcStoreCommit;',
])
def test_stored_color_focus_requires_same_editor_selected_identity_and_color(change):
    execute(setup('stored')+'''
        _chosenColor="blue_opioid"; [100,0] call _select;
    '''+change+'''
        [_waits select 0] call _deliver;
        [count _focusIds==0,"retired stored-color focus acted"] call _check;
    ''')


def test_stored_color_focus_follows_selected_identity_after_reordering():
    execute(setup('stored')+'''
        _chosenColor="blue_opioid"; [100,0] call _select;
        private _saved=_medic getVariable "ACME_narcStore";
        [_medic,[_saved select 2,_saved select 0,_saved select 1]] call ACME_fnc_narcStoreCommit;
        [_waits select 0] call _deliver;
        [_focusIds isEqualTo [84460],"reordering broke current color focus"] call _check;
    ''')


@pytest.mark.parametrize('kind',['stored','pending'])
@pytest.mark.parametrize('middle',['blue_opioid','none'])
def test_later_color_selection_retires_earlier_focus_even_when_color_returns(kind,middle):
    target=84601 if kind=='pending' else 84460
    execute(setup(kind)+'''
        _chosenColor="blue_opioid"; [100,0] call _select;
        private _old=_waits select 0;
    '''+f'_chosenColor="{middle}"; [100,0] call _select;'+'''
        _chosenColor="blue_opioid"; [100,0] call _select;
        private _new=_waits select ((count _waits)-1);
        [_old] call _deliver;
        [count _focusIds==0,"earlier same-color focus survived reselection"] call _check;
        [_new] call _deliver;
    '''+f'[_focusIds isEqualTo [{target}],"latest color request lost focus"] call _check;')


@pytest.mark.parametrize('kind',['stored','pending'])
def test_negative_selection_event_does_not_commit_or_schedule(kind):
    execute(setup(kind)+'''
        private _saved=+(_medic getVariable "ACME_narcStore");
        [100,-1] call _select;
        [(_medic getVariable "ACME_narcStore") isEqualTo _saved && {count _waits==0} && {_renders==0},"deselection generated a write or focus job"] call _check;
    ''')
