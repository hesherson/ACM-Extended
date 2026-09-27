"""Execute successful-pull feedback and its existing deferred reset.

Controls, sound and stock availability are explicit fixtures. This is not a live
inventory debit, compound-save test, pixel check or mouse-input simulation.
"""
import re
import pytest
from source_scan import lex
from test_menu_death_lifecycle import F, adapt, execute
from test_historical_medication_rows import iteration_scopes


def assert_draw_feedback(begin, draw):
    def require(text, snippet):
        tokens=[t.value for t in lex(text)]
        wanted=[t.value for t in lex(snippet)]
        assert any(tokens[i:i+len(wanted)]==wanted for i in range(len(tokens)-len(wanted)+1)),snippet
    require(begin, '["ACME_SK_CompoundDrawCount", 0]')
    for snippet in (
        'private _drawCount = count _components;',
        'uiNamespace setVariable ["ACME_SK_CompoundDrawCount", _drawCount];',
        '_drawBtn ctrlSetText format ["Drawn! (%1)",_drawCount];',
        '["success",0.88] call ACME_fnc_a11yColor',
        '_b ctrlSetText format ["Draw (%1)",_count];',
        '[_dlg,_gen,_drawCount],1.00] call CBA_fnc_waitAndExecute;',
        '!(_live isEqualTo _oldDisplay)',
        '(_live getVariable ["ACME_SK_DrawFeedbackGen",0]) != _expectedGen',
        '(uiNamespace getVariable ["ACME_SK_WasteStage",""]) != "compound"',
    ):require(draw,snippet)


def setup():
    text=(F/'fn_skCompoundDraw.sqf').read_text().replace('findDisplay 84000','_drawDisplay')
    text=re.sub(r'_(?:dlg|live) displayCtrl (\d+)',r'\1',text)
    for command,record in [('ctrlSetText','_texts'),('ctrlSetBackgroundColor','_backgrounds'),('ctrlEnable','_enables'),('ctrlCommit','_commits')]:
        text=re.sub(r'(_\w+) '+command+r' ([^;]+);',lambda m:f'{record} pushBack [{m[1]},{m[2]}];',text)
    return r'''
        private _drawDisplay=missionNamespace;
        private _texts=[]; private _backgrounds=[]; private _enables=[]; private _commits=[];
        private _available=10;
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        ACM_circulation_SyringeDraw_DrawnAmount=0;
        uiNamespace setVariable ["ACME_SK_WasteStage","compound"];
        uiNamespace setVariable ["ACME_SK_WasteCap",10];
        uiNamespace setVariable ["ACME_SK_WasteFloorMl",0];
        uiNamespace setVariable ["ACME_SK_WasteFill",1];
        uiNamespace setVariable ["ACME_SK_CompoundComponents",[]];
        uiNamespace setVariable ["ACME_SK_CompoundVials",[]];
        ACME_fnc_vialClass={"vial_"+(_this select 0)};
        ACME_fnc_infusionVialVolume={_available};
        ACME_fnc_a11yColor={+_this};
        CBA_fnc_waitAndExecute={_waits pushBack +_this;};
        private _runWait={private _w=_waits select _this;(_w select 1) call (_w select 0);};
    '''+'private _draw={'+adapt(iteration_scopes(text))+'};\n'


@pytest.mark.parametrize('same_drug',[False,True])
@pytest.mark.parametrize('draws',[1,2,3])
def test_success_count_tracks_locked_pulls_and_only_latest_feedback_can_reset(same_drug,draws):
    code=setup()
    expected=[]
    for i in range(draws):
        med='Ketamine' if same_drug or i%2==0 else 'Propofol'
        expected.append(f'["{med}",1]')
        code+=f'''
            ACM_circulation_SyringeDraw_Medication="{med}";
            uiNamespace setVariable ["ACME_SK_WasteFill",{i+1}];
            call _draw;
            [(uiNamespace getVariable ["ACME_SK_CompoundDrawCount",-1])=={i+1},"successful pull count changed"] call _check;
            [(_texts select ((count _texts)-1)) isEqualTo [84003,"Drawn! ({i+1})"],"success caption changed"] call _check;
            [((_waits select {i}) select 2)==1,"feedback reset delay changed"] call _check;
        '''
    code+='[(uiNamespace getVariable ["ACME_SK_CompoundComponents",[]]) isEqualTo ['+','.join(expected)+'],"component plan changed"] call _check;'
    if draws>1:
        code+='private _textCount=count _texts;0 call _runWait;[count _texts==_textCount,"old feedback overwrote newer draw"] call _check;'
    code+=f'''
        {draws-1} call _runWait;
        [(_texts select ((count _texts)-1)) isEqualTo [84003,"Draw ({draws})"],"current reset lost count"] call _check;
        [(uiNamespace getVariable ["ACME_SK_WasteFloorMl",-1])=={draws},"floor changed during feedback"] call _check;
        [count _backgrounds=={draws+1},"feedback repaint count changed"] call _check;
    '''
    execute(code)


@pytest.mark.parametrize('change',[
    '_drawDisplay=parsingNamespace;',
    '_drawDisplay=objNull;',
    'uiNamespace setVariable ["ACME_SK_WasteStage",""];',
    '_drawDisplay setVariable ["ACME_SK_DrawFeedbackGen",99];',
])
def test_obsolete_feedback_does_not_repaint_another_context(change):
    execute(setup()+'''
        call _draw;private _oldTexts=+_texts;private _oldBackgrounds=+_backgrounds;
    '''+change+'''
        0 call _runWait;
        [_texts isEqualTo _oldTexts && {_backgrounds isEqualTo _oldBackgrounds},"obsolete feedback repainted"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    'uiNamespace setVariable ["ACME_SK_WasteFill",0.05];',
    '_available=0;',
    'ACM_circulation_SyringeDraw_Medication="";',
    'uiNamespace setVariable ["ACME_SK_WasteStage",""];',
])
def test_rejected_draw_does_not_count_or_schedule_success(change):
    execute(setup()+change+'''
        call _draw;
        [count _texts==0 && {count _waits==0},"rejected draw announced success"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CompoundComponents",[]]) isEqualTo [],"rejected draw stored component"] call _check;
    ''')


@pytest.mark.parametrize('old,new',[
    ('private _drawCount = count _components;', 'private _drawCount = 1;'),
    ('Drawn! (%1)','Drawn!'),
    ('[_dlg,_gen,_drawCount],1.00]', '[_dlg,_gen,_drawCount],0.45]'),
    ('!(_live isEqualTo _oldDisplay)','false'),
    ('(_live getVariable ["ACME_SK_DrawFeedbackGen",0]) != _expectedGen','false'),
])
def test_current_feedback_contract_rejects_regression_despite_comment_decoy(old,new):
    begin=(F/'fn_skCompoundBegin.sqf').read_text();draw=(F/'fn_skCompoundDraw.sqf').read_text()
    assert_draw_feedback(begin,draw)
    assert old in draw
    changed=draw.replace(old,new,1)+'\n/* '+old+' */\n'
    with pytest.raises(AssertionError):assert_draw_feedback(begin,changed)
