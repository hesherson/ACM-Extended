"""B221: restore the B218 formatter, not another simulated UI redesign.

Native text metrics/rendering are NOT tested here. SHA fixtures identify the
restored functions in c978d539. The real medication generator, consumer and
formatter execute in SQF-VM; Python checks every emitted color attribute instead
of using placeholder colors or substituting the formatter with a mock.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

from medication_inventory import inventory
from test_debug_single_overlay import definition
from test_menu_death_lifecycle import ROOT, PREAMBLE, adapt, execute, read

BASELINE_FUNCTION_SHA256 = {
    '_renderBlock': 'd33001668ac81b56a9b3ef4e3520e6dca8732375271c242e8b248890a73adaad',
    '_padRight': '8cc36779785a77a306cbfa3dedc98114b5826d904a0ba56bfd841315adf56573',
    '_formatRow': 'a6a0a03cdfec0bda6c02ed384db50530aa1494be5956c0aceda90611cae200f2',
    '_renderAll': '181520f140086e0bfb4a3275cb9fca638d16047c2786f3a8844c76cf3c31611b',
}
FORMATTERS = ('_safe', '_padRight', '_alignValue', '_pair', '_one', '_wrapValue', '_formatRow', '_sect')


def helpers(*names):
    return ''.join(definition(n) for n in names)


@pytest.mark.parametrize('name', BASELINE_FUNCTION_SHA256)
def test_presentation_function_is_byte_identical_to_b218(name):
    assert hashlib.sha256(definition(name).encode()).hexdigest() == BASELINE_FUNCTION_SHA256[name]


def test_b220_post_parse_font_resize_and_nonbreaking_padding_are_reverted():
    assert 'ctrlSetFontHeight' not in definition('_renderBlock')
    assert "font='EtelkaMonospacePro' shadow='1'" in definition('_renderBlock')
    assert '_s = _s + " "' in definition('_padRight')
    assert 'toString [160]' not in read('debugMenuClinical')
    assert '_fitPass' not in definition('_renderAll')


@pytest.mark.parametrize('text,width', [('HR',18), ('Calcium Gluconate',18), ('0.00',11), ('7.3 L/min',11), ('37.0 C',11), ('1067 mL/min',11)])
def test_alignment_uses_original_ascii_space_glyph_and_keeps_complete_values(text,width):
    execute(helpers('_padRight') + f'''
        private _s=[{json.dumps(text)},{width}] call _padRight;
        [_s select [0,{len(text)}]=={json.dumps(text)},"reading changed"] call _check;
        [count _s=={width},"field width changed"] call _check;
        [{{_x!=32}} count toArray (_s select [{len(text)}])==0,"padding no longer uses ordinary monospace spaces"] call _check;
    ''')


def capture_rows(code):
    vm = os.environ.get('SQFVM') or shutil.which('sqfvm')
    if not vm:
        pytest.skip('SQF-VM required')
    with tempfile.TemporaryDirectory(prefix='acme-b221-') as d:
        p=Path(d)/'case.sqf'
        p.write_text(PREAMBLE+code+'\ndiag_log "B221_CAPTURE_OK";',encoding='utf-8')
        proc=subprocess.run([vm,'--automated','--suppress-welcome','--no-execute-print','--no-work-print','--input-sqf',str(p)],capture_output=True,text=True,timeout=15)
    output=proc.stdout+proc.stderr
    assert proc.returncode==0 and 'B221_CAPTURE_OK' in output,output
    assert not any(level in output for level in ('[ERR]','[FAT]','[WRN]','MENU_FIX_FAIL')),output
    return [line.split('B221_ROW ',1)[1] for line in output.splitlines() if 'B221_ROW ' in line]


def color_setup():
    return '''private _cLabel="#C0B7A2";private _cSect="#D9A441";private _cMute="#8A8474";private _cGood="#5FB56E";''' + helpers(*FORMATTERS) + 'ACME_fnc_debugMedicationColumns={'+adapt(read('debugMedicationColumns'))+'};'


def emit_rows():
    return '''{if (_x isEqualType []) then {diag_log ("B221_ROW "+([_x,11,[18,18]] call _formatRow));};} forEach _right;'''


def assert_valid_colors(rows):
    for row in rows:
        colors=re.findall(r"<t color='([^']*)'>",row)
        assert colors and all(re.fullmatch(r'#[0-9a-fA-F]{6}',c) for c in colors),row
        assert "color='any'" not in row and "color='nil'" not in row
        assert '<br/>' not in row


@pytest.mark.parametrize('count',[0,1,2,3,4,15,28,29,30,31,32])
def test_real_consumer_and_formatter_emit_only_real_colors_for_even_and_odd_catalogs(count):
    src=read('debugMenuClinical')
    consumer=src[src.index('_right pushBack (["MEDICATIONS"]'):src.index('// Nondrug sedation')]
    entries=[[f'Med {i:02}','0.00','#8A8474'] for i in reversed(range(count))]
    rows=capture_rows(color_setup()+f'private _medicationRows={json.dumps(entries)};private _right=[];'+consumer+emit_rows())
    assert len(rows)==(count+1)//2
    assert_valid_colors(rows)
    if count%2:
        assert rows[-1].count(' :</t>')==1,rows[-1]
    plain='\n'.join(re.sub('<[^>]*>','',r) for r in rows)
    for i in range(count):
        assert plain.count(f'Med {i:02}')==1


def test_pair_helper_itself_preserves_unpaired_triplet_instead_of_undefined_color():
    rows=capture_rows(color_setup()+'''private _right=[];
        private _row=["Ketamine","0.00","#8A8474"] call _pair;
        [count _row==3,"unpaired entry was expanded into missing fields"] call _check;
        _right pushBack _row;'''+emit_rows())
    assert_valid_colors(rows)
    assert len(rows)==1 and rows[0].count(' :</t>')==1


@pytest.mark.parametrize('effect',[0,1.25])
def test_complete_installed_catalog_including_real_route_grouping_has_no_invalid_colors(effect):
    matrix=inventory(ROOT/'addons/core/ACM_Medication.hpp',ROOT/'addons/acm_extended/config.cpp')
    names=[r['classname'] for r in matrix['medication_classes']]
    src=read('debugMenuClinical')
    generator=src[src.index('private _medicationGroups ='):src.index('// Nondrug sedation')]
    generator=re.sub(r'\("true" configClasses .*?\) apply \{configName _x\}', '_catalog',generator)
    generator=generator.replace('finite _value','true') # Engine finite-number check boundary only.
    setup=color_setup()+helpers('_medicationFamily')+f'''
        private _right=[];private _catalog={json.dumps(names)};
        private _queries=[];missionNamespace setVariable ["ACME_debugMedicationGroups",[]];
        ACME_fnc_medicationCountCompat={{_queries pushBack _this;{effect}}};
    '''
    rows=capture_rows(setup+generator+f'''
        [count _queries=={len(names)},"route omitted or queried twice"] call _check;
        [count _medicationRows==29,"installed family catalog changed"] call _check;
    '''+emit_rows())
    assert len(rows)==15
    assert_valid_colors(rows)
    assert rows[-1].count(' :</t>')==1
    assert 'Ketamine' in rows[-1]
    assert ('#5FB56E' if effect else '#8A8474') in rows[-1]


def test_compact_column_alignment_preserves_complete_units_and_same_left_edges():
    source=color_setup()+helpers('_renderAll')+'''
        private _baseFontH=0.0092;private _fontH=_baseFontH;private _gapFactor=0.26;
        private _gap=0;private _totalW=0.4;private _panelBottom=1;private _y=0;private _valueW=11;
        private _ctrlH="head";private _ctrlL="body";
        private _applyFont={};private _measureNaturalWidth={0.3};private _measureRows={0.2};private _layout={};
        private _renderBlock={{diag_log ("B221_ROW "+_x);} forEach (_this select 1);};
        private _header=[];private _top=[];private _network=[];
        private _left=[
            ["HR",77,"#5FB56E","BP","115/77","#5FB56E"] call _pair,
            ["CO","7.3 L/min","#5FB56E","EtCO2","n/a","#8A8474"] call _pair,
            ["Temp","37.0 C","#5FB56E","SpO2","99%","#5FB56E"] call _pair,
            ["Ext","1067 mL/min","#E04141","Junc","0 mL/min","#5FB56E"] call _pair
        ];
        private _right=[
            ["Calcium Gluconate","0.00","#8A8474","Norepinephrine","0.00","#8A8474"] call _pair,
            ["Ketamine","0.00","#8A8474"] call _one
        ];
        call _renderAll;
    '''
    rows=capture_rows(source)
    assert_valid_colors(rows)
    plain=[re.sub('<[^>]*>','',r) for r in rows]
    assert len({r.index(':') for r in plain})==1
    assert len({r.index(':',r.index(':')+1) for r in plain[:-1]})==1
    for reading in ['7.3 L/min','37.0 C','1067 mL/min','0 mL/min','115/77']:
        assert any(reading in r for r in plain)


def test_requested_header_fields_and_order_are_retained():
    src=read('debugMenuClinical')
    assert "size='1.12'" in src and 'private _topPadding = _fontH * 0.75;' in src
    assert '"Faction", _factionName, _sideColor' in src
    assert '"Obtunded"' in src and '"Obtund"' not in src
    for color in ['#4FA3FF','#FF5555','#BD83EA','#64D978']:
        assert color in src
    for label in ['CO','Temp','State']:
        assert f'["{label}"' in src
    assert '"Temp", format ["%1 C", _temp toFixed 1], _tempC, "SpO2"' in src
