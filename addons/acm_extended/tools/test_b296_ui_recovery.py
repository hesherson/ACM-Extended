"""B296 recovery: pin restored surfaces and execute time-independent ACME cues."""
import hashlib
import json
import re
import subprocess
import pytest
from test_menu_death_lifecycle import ROOT, execute, read

MANIFEST = ROOT / 'tools/b296-restored-surfaces.json'

@pytest.mark.parametrize('path,expected', json.loads(MANIFEST.read_text()).items())
def test_b295_surface_exactly_restored_or_removed(path, expected):
    p = ROOT / path
    if expected is None:
        assert not p.exists(), f'B295-only surface remains: {path}'
    else:
        # B297 intentionally updates only these ACME surfaces. Keep the recovery
        # provenance check on the actual B296 commit; current behavior has B297 execution tests.
        updated={'addons/acm_extended/config.cpp',
                 'addons/acm_extended/functions/fn_reactMedicalSnapshot.sqf',
                 'addons/acm_extended/ui/react/index.html',
                 'addons/acm_extended/tools/test_b293_react_bridge.py'}
        content=subprocess.check_output(['git','show','4ef4d3fdcdd4cb6c49bdb27a3b46fcc0641bb824:'+path],cwd=ROOT) if path in updated else p.read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected, path


def declaration(source, name):
    return re.search(r'private '+re.escape(name)+r' = [^;]+;', source).group()


def test_acme_navigation_selection_done_and_discard_stay_steady_over_time():
    tick = read('skUiTick')
    nav = (ROOT / 'addons/circulation/functions/fnc_openTransfusionMenu.sqf').read_text()
    discard = read('skBodyActionRender')
    declarations = '\n'.join([
        declaration(tick, '_navColor'), declaration(tick, '_alpha'),
        declaration(tick, '_a').replace('_a =', '_doneAlpha ='),
        declaration(nav, '_navColor').replace('_navColor =', '_transfuseNav ='),
        declaration(discard, '_a').replace('_a =', '_discardAlpha ='),
    ])
    execute('ACME_fnc_a11yColor={_this};\n'+r'''
        private _first=[];
        {
            private _now=_x; private _nowTime=_x;
    '''+declarations+r'''
            private _colors=[_navColor,_alpha,_doneAlpha,_transfuseNav,_discardAlpha];
            if (_first isEqualTo []) then {_first=+_colors;};
            [_colors isEqualTo _first,"ACME cue changed with time"] call _check;
            [_navColor isEqualTo _transfuseNav,"navigation mismatch"] call _check;
            [_doneAlpha>0 && {_discardAlpha>0} && {_alpha>0},"lost state visibility"] call _check;
        } forEach [0,0.04,0.12,0.25,0.5,1,1.75,2.5,10,99];
    ''')


@pytest.mark.parametrize('primed,dirty,blood,kind,expected',[
    (False,False,False,'',[0.35,1,0.45,1]),
    (True,True,False,'',[1,0.3,0.3,1]),
    (True,True,True,'',[1,1,1,1]),
    (True,True,False,'flush',[1,1,1,1]),
    (False,False,False,'prime',[1,1,1,1]),
])
def test_service_states_keep_semantic_colors_without_flashing(primed,dirty,blood,kind,expected):
    source=read('transfusionServicePaint')
    cue=source[source.index('private _indicated'):source.index('if !(_flush getVariable')]
    cue=cue.replace('_flush ctrlSetTextColor ', '_textColor = ').replace('_flush ctrlSetBackgroundColor ', '_background = ')
    cue=cue.replace('_flush setVariable ["ACME_txSkinTint",','_surface = (').replace('\n}];','\n});')
    values=json.dumps([primed,dirty,blood,kind,expected])
    execute(values+r''' params ["_primed","_dirty","_blood","_kind","_expected"];
        private _first=[];
        {
            private _nowTime=_x; private _textColor=[]; private _surface=[]; private _background=[];
    '''+cue+r'''
            [_textColor isEqualTo _expected,"wrong service text color"] call _check;
            if (_first isEqualTo []) then {_first=+_surface;};
            [_surface isEqualTo _first,"service surface flashed"] call _check;
            [_background isEqualTo [0,0,0,0],"square native corners repainted"] call _check;
        } forEach [0,0.04,0.1,0.5,1,1.5,2.3,19];
    ''')


def test_salinity_hint_steady_and_native_actions_retained():
    cue=read('updateTransfusionControls')
    assert '[0.45,0.95,0.55,0.85]' in cue
    assert 'sin (' not in cue
    assert 'ACME_serviceRightClick' in read('transfusionServicePaint')
    assert '["cancel"] call ACME_fnc_transfusionFlushLine;' in read('transfusionServicePaint')
    assert 'Requires two presses.' in read('skBodyActionRender')


def test_rejected_selection_shows_one_steady_cue_then_clears():
    red=declaration(read('skUiTick'), '_red')
    execute(r'''
        private _flash=10;
        {
            private _elapsed=_x;
    '''+red+r'''
            [_red isEqualTo (_elapsed<0.36),"rejection cue blinked or persisted"] call _check;
        } forEach [0,0.04,0.09,0.12,0.17,0.18,0.24,0.27,0.30,0.35,0.36,1];
    ''')
