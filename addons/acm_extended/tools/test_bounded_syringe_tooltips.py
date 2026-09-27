"""Actual active-syringe tooltip and memory decisions, with explicit UI fixtures.

Localization is a lookup fixture, not Arma stringtable resolution. No rendered
hover events, mouse hit-testing, font metrics or Unicode grapheme claims.
"""
import json
import pytest
from test_menu_death_lifecycle import adapt, execute
from test_historical_procedure_trays import controls, ui_code
from test_bounded_medication_presentation import source, require


def literal(value):
    if isinstance(value,str): return '"'+value.replace('"','""')+'"'
    if isinstance(value,list): return '['+','.join(literal(v) for v in value)+']'
    return json.dumps(value)


def tooltip_contract(text=None):
    text=source('skCarouselRender') if text is None else text
    for fragment in ('_hit ctrlSetTooltip "";',
                     'private _remembered = [_store,_idx] call ACME_fnc_skSyringeRemembered;',
                     'private _activeTip = if (_curHasTag) then',
                     '[_cur param [8,"",[""]],_cur param [9,"",[""]],_cur param [10,"",[""]]] joinString (toString [10])',
                     'if (_remembered) then {[_cur] call _fnc_noTagTip} else {"???"}',
                     '_activeHit ctrlSetTooltip _activeTip;',
                     'private _start = ((count _components) - 2) max 0;',
                     'format ["%1mL of %2",[_ml] call _fnc_mlText,[_m] call _fnc_medName]'):
        require(text,fragment)


def setup():
    text=source('skCarouselRender')
    helpers=text[text.index('private _fnc_medName = '):text.index('private _zone = ')]
    # Only the engine localization lookup is substituted. Fallback arithmetic runs.
    original='localize (format ["STR_ACM_Circulation_Medication_%1",_med])'
    assert helpers.count(original)==1
    helpers=helpers.replace(original,'([_med] call _translate)')
    start=text.index('private _cur = +(_store select _idx);')
    end=text.index('\n',text.index('private _curHasTag = ',start))
    identity=text[start:end]
    active=text[text.index('private _remembered = '):text.index('private _hitW = ')]
    return controls()+'''
        private _activeHit=84480; private _store=[]; private _idx=0;
        private _dictionary=createHashMapFromArray [["Ketamine","Ketamine label"],["Other",""]];
        private _translate={params ["_med"];
            if (_med in _dictionary) then {_dictionary get _med} else {format ["STR_ACM_Circulation_Medication_%1",_med]}};
    '''+adapt(helpers)+'ACME_fnc_skSyringeRemembered={'+adapt(source('skSyringeRemembered'))+'};'+\
        'private _renderTip={'+adapt(identity)+ui_code(active)+'};'


def entry(color='none',lines=None,components=None,med='Ketamine',amount=2):
    return [med,10,amount,'internal label',0,[] if components is None else components,'',color,*(lines or ['','','']),'stable-id','barrel']


@pytest.mark.parametrize('lines', [['Line One','Mixed Case','<dose>'], ['','',''],['','','Only third']])
@pytest.mark.parametrize('index',[0,4])
def test_tagged_active_tooltip_is_exactly_three_written_lines_not_a_medication_summary(lines,index):
    record=entry('yellow_induction',lines)
    execute(setup()+f'''
        _store={literal([record]*5)}; _idx={index}; private _before=+_store;
        call _renderTip;
        [(_controlValues get "84480:ctrlSetTooltip") isEqualTo ({literal(lines)} joinString (toString [10])),"tag lines changed or internal summary leaked"] call _check;
        [_store isEqualTo _before,"tooltip changed record payload"] call _check;
        [count _uiWrites==1,"tooltip painted competing targets"] call _check;
    ''')


@pytest.mark.parametrize('count,index,known',[(1,0,True),(3,0,True),(4,0,False),(4,1,True),(5,1,False),(5,2,True),(5,4,True)])
@pytest.mark.parametrize('written_mark',[False,True])
def test_untagged_tooltip_only_reveals_recent_or_written_marked_syringes(count,index,known,written_mark):
    record=entry(lines=['Identified' if written_mark else '','',''])
    expected='2mL of Ketamine label' if known or written_mark else '???'
    execute(setup()+f'''
        _store={literal([record]*count)}; _idx={index}; private _before=+_store;
        call _renderTip;
        [(_controlValues get "84480:ctrlSetTooltip")=={literal(expected)},"syringe memory disclosure boundary changed"] call _check;
        [_store isEqualTo _before,"memory lookup changed medication"] call _check;
    ''')


@pytest.mark.parametrize('components,med,amount,expected',[
    ([], 'Ketamine', 1, ['1mL of Ketamine label']),
    ([], 'Unknown', 1.2, ['1.2mL of Unknown']),
    ([], 'Other', 1.23, ['1.23mL of Other']),
    ([], '', 0, ['']),
    ([['Ketamine',0.25]], 'Other', 9, ['0.25mL of Ketamine label']),
    ([['Other',1],['Unknown',2]], 'Ketamine', 9, ['1mL of Other','2mL of Unknown']),
    ([['Old secret',9],['Other',1.5],['Ketamine',2]], 'Unknown', 9, ['1.5mL of Other','2mL of Ketamine label']),
    ([['Old secret',9],[],['Unknown',0.01]], 'Ketamine', 9, ['0.01mL of Unknown']),
    ([['Old secret',9],'invalid row',['Other',0]], 'Ketamine', 9, ['0mL of Other']),
])
def test_unlabelled_summary_uses_last_two_positions_and_localization_fallback(components,med,amount,expected):
    record=entry(components=components,med=med,amount=amount)
    execute(setup()+f'''
        _store=[{literal(record)}]; private _before=+_store;
        call _renderTip;
        [(_controlValues get "84480:ctrlSetTooltip") isEqualTo ({literal(expected)} joinString (toString [10])),"pull history or label fallback changed"] call _check;
        [_store isEqualTo _before,"summary changed source components"] call _check;
    ''')


@pytest.mark.parametrize('index',[-1,0,3])
def test_invalid_memory_indices_fail_closed(index):
    execute(setup()+f'''
        [!([[],{index}] call ACME_fnc_skSyringeRemembered),"empty-store memory accepted index"] call _check;
    ''')


def test_neighbor_tooltip_clearing_is_separate_from_active_content():
    text=source('skCarouselRender')
    start=text.index('_hit ctrlSetTooltip "";')
    block=text[start:start+len('_hit ctrlSetTooltip "";')]
    execute(controls()+'private _hit=0; for "_slot" from 0 to 4 do {_hit=84408+10*_slot;'+ui_code(block)+'''};
        [count _uiWrites==5,"neighbor tooltips not cleared independently"] call _check;
        { [(_x select 1)=="ctrlSetTooltip" && {(_x select 2)==""},"neighbor disclosed content"] call _check; } forEach _uiWrites;
    ''')
    tooltip_contract()


@pytest.mark.parametrize('old,new',[
    ('_cur param [10,"",[""]]','_cur param [9,"",[""]]'),
    ('if (_remembered) then','if (true) then'),
    ('((count _components) - 2) max 0','((count _components) - 3) max 0'),
    ('_activeHit ctrlSetTooltip _activeTip;','_hit ctrlSetTooltip _activeTip;'),
])
def test_tooltip_contract_rejects_disclosure_and_target_regressions_even_with_comments(old,new):
    text=source('skCarouselRender'); assert old in text
    with pytest.raises(AssertionError): tooltip_contract(text.replace(old,new+' /* '+old+' */'))
