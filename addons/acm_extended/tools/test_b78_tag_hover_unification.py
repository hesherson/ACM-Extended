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

def test_tag_font_and_capacity():
    c=txt('config.cpp')
    tag=c[c.index('class ACME_SK_TagEdit'):c.index('class ACME_SK_TagText')]
    assert 'maxChars = 25;' in tag
    for rel in ['functions/fn_skPendingTagCommit.sqf','functions/fn_skApplyPendingTag.sqf','functions/fn_skTagCommit.sqf','functions/fn_skPendingTagRender.sqf','functions/fn_skCarouselRender.sqf']:
        s=txt(rel)
        assert 'select [0,17]' not in s and 'select [0, 17]' not in s
    p=txt('functions/fn_skPendingTagRender.sqf')
    r=txt('functions/fn_skCarouselRender.sqf')
    assert '_lineFontH = 0.031' in p and '_lineFontH = 0.031' in r
    assert '_lineH = 0.038' in p and '_lineH = 0.038' in r
    assert '_w*0.245' in p and '_w*0.245' in r and '_aw*0.245' in r

def test_selector_geometry_unified():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()

def test_click_only_dropdowns():
    pend=txt('functions/fn_skPendingTagEnsure.sqf')
    inj=txt('functions/fn_skInject.sqf')
    assert '_button ctrlAddEventHandler ["ButtonClick"' in pend
    assert 'B74: click is the ONLY toggle' in pend
    assert '_colorBtn ctrlAddEventHandler ["ButtonClick"' in inj
    # Neither selector gets a hover handler that opens/closes its list.
    assert '_button ctrlAddEventHandler ["MouseEnter"' not in pend
    color_chunk=inj[inj.index('private _colorBtn'):inj.index('private _colorList')]
    assert 'ctrlShow true' not in color_chunk or 'ButtonClick' in color_chunk

def test_hover_is_visual_only():
    h=txt('functions/fn_skCarouselHover.sqf')
    r=txt('functions/fn_skCarouselRender.sqf')
    i=txt('functions/fn_skInject.sqf')
    assert 'ACME_SK_CarouselExpanded",true' not in h
    assert 'skDynamicLayout' not in h
    assert 'skCarouselRender' in h
    assert 'ACME_SK_CarouselHoverOffset' in i and 'ACME_SK_CarouselHoverOffset' in r
    assert 'if (!_editMode && {_off == _hoverOffset}) then {_alpha = 1;};' in r
    assert '_hit ctrlSetTooltip "";' in r
    assert '_activeHit ctrlSetTooltip _activeTip;' in r

def test_expansion_still_click_or_ad():
    from test_historical_carousel_input import test_center_click_toggles_browsing_but_keeps_a_staged_target_promoted, test_keydown_hold_and_keyup_preserve_existing_repeat_cadence
    for pending in (False,True):
        test_center_click_toggles_browsing_but_keeps_a_staged_target_promoted(pending)
    for key,expected in ((30,'id-c'),(32,'id-b')):
        test_keydown_hold_and_keyup_preserve_existing_repeat_cadence(key,expected)

if __name__=='__main__':
    tests=[v for k,v in sorted(globals().items()) if k.startswith('test_')]
    for f in tests: f()
    print(f'B78 focused contracts: {len(tests)}/{len(tests)} passed')
