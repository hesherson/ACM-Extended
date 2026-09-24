from historical_source import read_source, assert_release_identity
#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def txt(rel): return read_source(ROOT/rel, encoding='utf-8',errors='ignore')

def test_version():
    assert_release_identity()
    p=txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_tag_25():
    from test_bounded_tag_contracts import tag_limits
    from test_bounded_tag_line_layout import layout_contract
    tag_limits()
    layout_contract()

def test_hover_and_opacity():
    from test_historical_carousel_input import test_hover_is_presentation_only_and_keeps_selection_and_expansion, test_actual_slot_hover_alpha_changes_without_changing_its_geometry
    # Hover no longer expands the layout. It still fades the hovered slot and retains tooltip privacy.
    for expanded in (False,True):
        for hover in (False,True):
            test_hover_is_presentation_only_and_keeps_selection_and_expansion(expanded,hover)
        for slot in range(5):
            test_actual_slot_hover_alpha_changes_without_changing_its_geometry(expanded,slot)
    r=txt('functions/fn_skCarouselRender.sqf')
    assert '_hit ctrlSetTooltip "";' in r
    assert 'ACME_fnc_skSyringeRemembered' in r and '"???"' in r

def test_three_syringe_memory():
    s=txt('functions/fn_skSyringeRemembered.sqf')
    assert '_idx >= ((_n - 3) max 0)' in s
    assert '_color in ["","none"]' in s
    menu=txt('functions/fn_skSyringeSelfMenu.sqf')
    assert 'ACME_fnc_skSyringeRemembered' in menu and '{"???"}' in menu

def test_discard_button():
    i=txt('functions/fn_skInject.sqf')
    assert '84819' in i and '84820' in i and 'ACME_fnc_skBodyActionClick' in i
    r=txt('functions/fn_skBodyActionRender.sqf')
    assert 'Discard Syringe' in r and 'Confirm discard?' in r
    assert '["danger",_a]' in r
    c=txt('functions/fn_skBodyActionClick.sqf')
    assert 'ACME_SK_DiscardArmedId' in c and 'ACME_fnc_skDiscardSelected' in c
    d=txt('functions/fn_skDiscardSelected.sqf')
    assert '_store deleteAt _idx' in d

def test_staged_push():
    s=txt('functions/fn_skBeginInjection.sqf')
    assert 'ACME_SK_PendingInjection' in s
    assert 'ACME_fnc_skConfirmInjection' not in s
    r=txt('functions/fn_skBodyActionRender.sqf')
    assert 'format ["%1 %2 mL in %3",_verb,_mlText,_where]' in r
    assert '_verb = "Push"' in r and 'private _verb = "Inject"' in r
    assert 'ACME_fnc_ivVeinCatalog' in r and 'getOrDefault ["short"' in r
    c=txt('functions/fn_skBodyActionClick.sqf')
    assert 'call ACME_fnc_skConfirmInjection' in c
    q=txt('functions/fn_skConfirmInjection.sqf')
    from test_bounded_staged_push_contracts import assert_staged_contract
    assert_staged_contract(s, q)
    assert 'ACME_SK_PendingInjection",[]' in q

def test_feedback_lingers():
    assert 'Drawn! (%1)' in txt('functions/fn_skCompoundDraw.sqf')
    assert 'Drawn! (%1)' in txt('functions/fn_skWasteDraw.sqf')
    assert '],1.00] call CBA_fnc_waitAndExecute;' in txt('functions/fn_skCompoundDraw.sqf')
    assert '],1.00] call CBA_fnc_waitAndExecute;' in txt('functions/fn_skWasteDraw.sqf')
    # Compound Save now resets in place immediately and keeps only a short nonblocking Saved! flash.
    assert '],0.45] call CBA_fnc_waitAndExecute;' in txt('functions/fn_skCompoundSave.sqf')
    # Flush Save still uses its authored close/reopen acknowledgement delay.
    assert '],1.10] call CBA_fnc_waitAndExecute;' in txt('functions/fn_skFlushSave.sqf')
