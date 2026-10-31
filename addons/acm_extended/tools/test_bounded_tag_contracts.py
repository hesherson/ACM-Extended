"""Current three-line syringe tags, not the retired final-name field.

SQF runs through existing explicit display/inventory fixtures. Source checks
ignore comments. No rendering or Unicode grapheme-count claim is made.
"""
import pytest
from source_scan import lex, matching, render
from test_menu_death_lifecycle import ROOT, execute
from test_historical_syringe_identity import setup, function

F = ROOT / 'addons/acm_extended/functions'


def source(name):
    return (F / ('fn_' + name + '.sqf')).read_text()


def tokens(text):
    return render(lex(text))


def require(text, fragment):
    assert tokens(fragment) in tokens(text), fragment


def tag_limits(config=None, writers=None):
    config = config if config is not None else (ROOT / 'addons/acm_extended/config.cpp').read_text()
    ts = lex(config); pairs = matching(ts)
    starts = [i for i in range(len(ts)-3) if ts[i].value == 'class' and ts[i+1].value == 'ACME_SK_TagEdit' and ts[i+2].value == ':']
    assert len(starts) == 1
    opening = next(i for i in range(starts[0],len(ts)) if ts[i].value == '{')
    block = config[ts[opening].offset:ts[pairs[opening]].offset+1]
    require(block, 'maxChars = 25;')
    writers = writers if writers is not None else {n: source(n) for n in ('skPendingTagCommit','skApplyPendingTag','skTagCommit')}
    for name, text in writers.items():
        require(text, 'select [0,25]')
        assert 'select [ 0 , 17 ]' not in tokens(text), name
    require(writers['skPendingTagCommit'], 'for "_i" from 0 to 2 do')
    require(writers['skApplyPendingTag'], '_out set [8 + _i,')
    require(writers['skTagCommit'], '_entry set [8 + _n,')


def editor_wiring(text=None):
    text = source('skInject') if text is None else text
    for f in ('for "_line" from 0 to 2 do',
              '_display ctrlCreate ["ACME_SK_TagEdit",84460 + _line]',
              '_e ctrlAddEventHandler ["KillFocus", {call ACME_fnc_skTagCommit}]',
              '_e ctrlAddEventHandler ["KeyUp", {call ACME_fnc_skTagCommit}]',
              '_colorBtn ctrlSetText "Edit Syringe Tag";',
              '_colorList ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_skTagColor}]'):
        require(text, f)
    for color in ('none','yellow_induction','orange_benzodiazepine','blue_opioid','blue_stripe_reversal',
                  'red_paralytic','red_stripe_reversal','violet_vasopressor','violet_stripe_hypotensive',
                  'green_anticholinergic','gray_local_anesthetic','salmon_antiemetic','white_saline_flush'):
        require(text, '[' + '"' + color + '",')
    assert 'ctrlCreate [ "ACME_SK_NameEdit" , 84161 ]' not in tokens(text)


def test_live_tag_controls_match_all_three_defensive_writers():
    tag_limits(); editor_wiring()


@pytest.mark.parametrize('length',[0,17,24,25,26,80])
@pytest.mark.parametrize('editing',[False,True])
def test_three_line_roundtrip_preserves_case_payload_identity_and_other_syringes(length, editing):
    value = ('Ab9_' * 20)[:length]; clipped = value[:25]
    execute(setup()+f'''
        _textValues set ["84601","{value}"]; _textValues set ["84602","Mixed Case"];
        _textValues set ["84603","<tag> dose"];
        call ACME_fnc_skPendingTagCommit;
        private _saved=[_c] call ACME_fnc_skApplyPendingTag;
        [(_saved select [8,3]) isEqualTo ["{clipped}","Mixed Case","<tag> dose"],"pending tag roundtrip"] call _check;
        [(_saved select [0,7]) isEqualTo (_c select [0,7]) && {{(_saved select [11,2]) isEqualTo (_c select [11,2])}},"pending changed drug or identity"] call _check;
        ["id-b",_rows] call ACME_fnc_skSelectStored;
        [_medic,[_c,_a,_b]] call ACME_fnc_narcStoreCommit;
        _textValues set ["84460","{value}"]; _textValues set ["84461","Mixed Case"];
        _textValues set ["84462","<tag> dose"]; _textWrites=[];
        uiNamespace setVariable ["ACME_SK_TagEditMode",{str(editing).lower()}];
        call ACME_fnc_skTagCommit;
        private _store=_medic getVariable ["ACME_narcStore",[]];
        private _selected=_store select 2;
        [(_selected select [8,3]) isEqualTo ["{clipped}","Mixed Case","<tag> dose"],"stored tag roundtrip"] call _check;
        [(_store select [0,2]) isEqualTo [_c,_a],"another syringe edited"] call _check;
        [(_selected select [0,8]) isEqualTo (_b select [0,8]) && {{(_selected select [11,2]) isEqualTo (_b select [11,2])}},"stored drug or identity changed"] call _check;
        [count _textWrites=={int(length>25)},"unneeded text rewrite"] call _check;
        [_refreshes=={int(not editing)} && {{_renders==0}},"active editor repainted"] call _check;
    ''')


def test_retired_final_name_shim_does_not_change_prepared_metadata():
    editor_wiring()
    execute(setup()+function('skFinalName')+'''
        private _before=+(_medic getVariable ["ACME_narcStore",[]]);
        private _result=call ACME_fnc_skFinalName;
        [_result isEqualTo "","retired final name returned content"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo _before,"retired name changed records"] call _check;
        [count _textWrites==0 && {_renders==0},"retired name created UI writes"] call _check;
    ''')


@pytest.mark.parametrize('target',['config','skPendingTagCommit','skApplyPendingTag','skTagCommit'])
def test_limit_contract_rejects_17_character_regression_and_comment_decoys(target):
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    writers={n:source(n) for n in ('skPendingTagCommit','skApplyPendingTag','skTagCommit')}
    if target=='config':
        config=config.replace('maxChars = 25;', 'maxChars = 17; /* maxChars = 25; */')
    else:
        writers[target]=writers[target].replace('select [0,25]','select [0,17] /* select [0,25] */')
    with pytest.raises(AssertionError):
        tag_limits(config,writers)


def test_wiring_contract_rejects_removed_third_editor_even_with_comment_decoy():
    text=source('skInject').replace('for "_line" from 0 to 2 do','for "_line" from 0 to 1 do /* for "_line" from 0 to 2 do */')
    with pytest.raises(AssertionError): editor_wiring(text)
