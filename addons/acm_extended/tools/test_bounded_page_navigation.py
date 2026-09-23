"""Execute the current three-page routing and navigation-label block.

Display/control operations are recorded. No rendering, real dialog teardown,
server handoff or inventory delivery is simulated. A/D execution is retained in
historical_carousel_input rather than duplicating its behavioral model here.
"""
import pytest
from source_scan import lex, render
from test_menu_death_lifecycle import execute
from test_historical_carousel_input import setup as carousel_setup, code as carousel_code
from test_historical_syringe_identity import source
from test_historical_procedure_trays import ui_code


def require(text, fragment):
    assert render(lex(fragment)) in render(lex(text)), fragment


def bindings_contract(inject=None):
    inject=source('skInject') if inject is None else inject
    for fragment in (
        '_display ctrlCreate ["ACME_SK_PulseButton", 84150]',
        '_display ctrlCreate ["ACME_SK_PulseButton", 84152]',
        '_toggleBtn ctrlAddEventHandler ["ButtonClick", {["left"] call ACME_fnc_skPageNavigate;}]',
        '_toggleBtnR ctrlAddEventHandler ["ButtonClick", {["right"] call ACME_fnc_skPageNavigate;}]',
        'case 30: {-1}', 'case 32: {1}',
        '[_dir] call ACME_fnc_skCarouselMove;',
        'private _focus = focusedCtrl _d;', 'ctrlType _focus == 2',
    ): require(inject,fragment)


def labels_contract(view=None):
    view=source('skSetView') if view is None else view
    for fragment in (
        '_leftPage ctrlSetText "< Narc Box";', '_rightPage ctrlSetText "Transfuse >";',
        '_leftPage ctrlSetText "< Transfuse";', '_rightPage ctrlSetText "Body Map >";',
        'if (!_infusion) then',
        '{(_display displayCtrl _x) ctrlShow false;} forEach [84150,84152,84153,84157];',
    ): require(view,fragment)


def retired_toggle_contract(inject=None,view=None,renderer=None):
    inject=source('skInject') if inject is None else inject
    view=source('skSetView') if view is None else view
    renderer=source('skCarouselRender') if renderer is None else renderer
    for text in (inject,view,renderer):
        assert not any(t.kind=='number' and t.value=='84170' for t in lex(text))
    require(inject,'private _viewY = safeZoneY + (safeZoneH / 1.08);')
    labels_contract(view)


def typing_contract(inject=None):
    inject=source('skInject') if inject is None else inject
    # Both press and release must leave arbitrary edit controls, not only tag IDs, alone.
    from test_historical_carousel_input import block_at
    for event in ('KeyDown','KeyUp'):
        text=block_at(inject,f'_display displayAddEventHandler ["{event}",')
        for fragment in ('private _focus = focusedCtrl _d;',
                         'if (!isNull _focus && {ctrlType _focus == 2}) exitWith',
                         'setVariable ["ACME_SK_CarouselHeldDir",0]',
                         'setVariable ["ACME_SK_CarouselRepeatAt",0]',
                         'false'):
            require(text,fragment)
        assert render(lex(text)).index(render(lex('ctrlType _focus == 2'))) < render(lex(text)).index(render(lex('case 30')))


def setup():
    base=carousel_setup().replace('["_owner", ACE_player, [objNull]]',
                                  '["_owner", ACE_player, [missionNamespace]]')
    text=source('skPageNavigate').replace('findDisplay 84000','_drawDisplay').replace('findDisplay 86000','_txDisplay')
    text=text.replace('closeDialog 0;', '_closes=_closes+1;')
    return base + '''
        private _txDisplay=objNull; private _closes=0; private _transfuse=[];
        ACME_fnc_skOpenDraw={_opens pushBack _this;};
        ACM_circulation_fnc_openTransfusionMenu={_transfuse pushBack _this;};
        CBA_fnc_execNextFrame={_waits pushBack _this;};
        uiNamespace setVariable ["ACME_SK_Patient",_patient];
        uiNamespace setVariable ["ACME_SK_BodyPart","rightarm"];
    ''' + 'private _navigate={' + carousel_code(text) + '};\n'


@pytest.mark.parametrize('view,dir,target',[
    ('syringe','left','transfuse'),('syringe','right','body'),
    ('body','left','syringe'),('body','right','transfuse'),
    ('transfuse','left','body'),('transfuse','right','syringe'),
])
@pytest.mark.parametrize('empty',[False,True])
def test_three_page_routes_preserve_patient_part_and_inventory(view,dir,target,empty):
    config=f'uiNamespace setVariable ["ACME_SK_View","{view}"];'
    if view=='transfuse':
        config+='''_drawDisplay=objNull; _txDisplay=missionNamespace;
            missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
            missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","rightarm"];
            ACME_infusion_pendingContext=["prepared","stale"];
            missionNamespace setVariable ["ACME_infusion_bagTally",["old tally"]];'''
    local=view!='transfuse' and target!='transfuse'
    execute(setup()+config+('[_medic,[]] call ACME_fnc_narcStoreCommit;' if empty else '')+'''
        private _before=+(_medic getVariable "ACME_narcStore");
    '''+f'["{dir}"] call _navigate;'+f'''
        [_closes=={int(not local)} && {{count _waits=={int(not local)}}},"wrong dialog handoff count"] call _check;
        [count _opens==0 && {{count _transfuse==0}},"dialog creation was not deferred"] call _check;
    '''+('''
        [_viewCalls==1,"local page switch did not repaint in place"] call _check;
    '''+f'[(uiNamespace getVariable "ACME_SK_View")=="{target}","wrong in-place page"] call _check;'
        if local else '''
        // A close handler can reintroduce transient prep context before next frame.
        ACME_infusion_pendingContext=["prepared","late unload"];
        missionNamespace setVariable ["ACME_infusion_bagTally",["late tally"]];
        call _drain;
    '''+(f'''
        [_transfuse isEqualTo [[_medic,_patient,"rightarm"]],"transfusion target changed"] call _check;
        [uiNamespace getVariable ["ACME_SK_suppressReturn",false],"old return handler was not suppressed"] call _check;
    ''' if target=='transfuse' else f'''
        [_opens isEqualTo [[10,_patient,"rightarm"]],"draw target changed"] call _check;
        [(uiNamespace getVariable "ACME_SK_RequestedView")=="{target}","requested page lost"] call _check;
        [isNil "ACME_infusion_pendingContext","normal page inherited prep context"] call _check;
        [(missionNamespace getVariable "ACME_infusion_bagTally") isEqualTo [],"normal page inherited tally"] call _check;
    '''))+'''
        [(_medic getVariable "ACME_narcStore") isEqualTo _before,"navigation changed syringe contents"] call _check;
        [(_patient getVariable "ACME_narcStore") isEqualTo [["patient kit"]],"navigation changed patient equipment"] call _check;
    ''')


@pytest.mark.parametrize('fallback',['display','self'])
def test_in_place_navigation_uses_display_return_patient_then_self(fallback):
    execute(setup()+'''
        uiNamespace setVariable ["ACME_SK_View","syringe"];
        uiNamespace setVariable ["ACME_SK_Patient",objNull];
        uiNamespace setVariable ["ACME_SK_BodyPart",""];
    '''+('_drawDisplay setVariable ["ACME_SK_ReturnPatient",_patient];' if fallback=='display' else '')+'''
        ["left"] call _navigate; call _drain;
    '''+f'[_transfuse isEqualTo [[_medic,{"_patient" if fallback=="display" else "_medic"},"leftarm"]],"patient/body-part fallback changed"] call _check;')


@pytest.mark.parametrize('body',[False,True])
@pytest.mark.parametrize('infusion',[False,True])
def test_navigation_labels_match_page_and_are_hidden_for_infusion(body,infusion):
    text=source('skSetView'); start=text.index('if (!_infusion) then {'); end=text.index('// B59 mini-carousel',start)
    execute(setup()+f'private _body={str(body).lower()};private _infusion={str(infusion).lower()};private _display=_drawDisplay;'+ui_code(text[start:end])+('''
        { [(_controlValues get ((str _x)+":ctrlShow")) isEqualTo false,"infusion retained navigation"] call _check; } forEach [84150,84152,84153,84157];
    ''' if infusion else f'''
        [(_controlValues get "84150:ctrlSetText")=="{'< Narc Box' if body else '< Transfuse'}","wrong left label"] call _check;
        [(_controlValues get "84152:ctrlSetText")=="{'Transfuse >' if body else 'Body Map >'}","wrong right label"] call _check;
        {{ [(_controlValues get ((str _x)+":ctrlShow")) && {{_controlValues get ((str _x)+":ctrlEnable")}},"page button not usable"] call _check; }} forEach [84150,84152];
    '''))


@pytest.mark.parametrize('kind', ['direction','typing','label','retired'])
def test_source_contracts_reject_regressions_even_with_comment_decoys(kind):
    if kind=='direction':
        text=source('skInject'); old='_toggleBtnR ctrlAddEventHandler ["ButtonClick", {["right"] call ACME_fnc_skPageNavigate;}]'
        assert old in text
        with pytest.raises(AssertionError): bindings_contract(text.replace(old,old.replace('"right"','"left"'))+'\n// '+old)
    elif kind=='typing':
        text=source('skInject'); old='ctrlType _focus == 2'
        with pytest.raises(AssertionError): typing_contract(text.replace(old,'ctrlType _focus == 1')+'\n// '+old)
    elif kind=='label':
        text=source('skSetView');old='_rightPage ctrlSetText "Body Map >";'
        with pytest.raises(AssertionError): labels_contract(text.replace(old,'_leftPage ctrlSetText "Body Map >";')+'\n// '+old)
    else:
        with pytest.raises(AssertionError): retired_toggle_contract(inject=source('skInject')+'\n_display displayCtrl 84170;')
