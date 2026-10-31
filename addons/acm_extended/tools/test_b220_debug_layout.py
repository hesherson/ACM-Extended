"""B220 executes production debug formatting/fitting; native font metrics are explicit fixtures.

B221 removes the superseded NBSP/fitting assertions; see test_b221_debug_rollback.py.
These checks are not Arma rendering tests. The integration cases include the real
column-major medication builder AND its consumer, including an odd final row.
"""
import json

import pytest

from test_debug_single_overlay import definition
from test_menu_death_lifecycle import adapt, execute, read


def helpers(*names):
    return ''.join(definition(name) for name in names)


FORMATTING = ('_safe', '_padRight', '_alignValue', '_pair', '_one', '_wrapValue', '_formatRow', '_sect')


@pytest.mark.parametrize('count', [0, 1, 2, 3, 4, 8, 15, 29, 30, 31, 32, 63])
def test_complete_medication_pipeline_has_no_missing_second_field_or_ghost_colon(count):
    rows = [[f'Med {n:02}', f'{n}.00', 'color'] for n in reversed(range(count))]
    source = read('debugMenuClinical')
    consumer = source[source.index('_right pushBack (["MEDICATIONS"]'):source.index('// Nondrug sedation')]
    execute('private _cLabel="label";private _cSect="gold";private _cMute="muted";' + helpers(*FORMATTING) +
        'ACME_fnc_debugMedicationColumns={' + adapt(read('debugMedicationColumns')) + '};' +
        f'private _medicationRows={json.dumps(rows)};private _right=[];' + consumer + f'''
        private _data=_right select {{_x isEqualType []}};
        [count _data=={(count+1)//2},"medication integration lost or duplicated a row"] call _check;
        private _leftNames=[];private _rightNames=[];
        {{
            private _row=_x;
            [count _row in [3,6],"malformed medication row"] call _check;
            _leftNames pushBack (_row select 0);
            if (count _row==6) then {{_rightNames pushBack (_row select 3);}};
            private _text=[_row,11,[18,18]] call _formatRow;
            [(_text find "<br/>")==-1,"ordinary medication acquired an explicit blank line"] call _check;
            private _firstColon=_text find " :</t>";
            private _rest=_text select [_firstColon+6];
            if (count _row==3) then {{[(_rest find " :</t>")==-1,"singleton printed a ghost right-hand colon"] call _check;}};
        }} forEach _data;
        [_leftNames+_rightNames isEqualTo {json.dumps(sorted(row[0] for row in rows))},"rendered order is not down-left then down-right"] call _check;
    ''')


def test_section_spacing_does_not_add_a_second_blank_row_before_sedation():
    source=read('debugMenuClinical')
    between=source[source.index('// Nondrug sedation'):source.index('// Cerebral seizure state')]
    assert 'pushBack ""' not in between
    assert '["SEDATION / AWARENESS"] call _sect' in between
