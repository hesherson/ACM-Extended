"""Validate every declared patient-field row, not just selected field names.

The same unchanged tests can target B236 with ACME_B237_REFERENCE_ROOT.
"""
import json
import os
from pathlib import Path
import re
from test_menu_death_lifecycle import ROOT, adapt, execute
from source_scan import lex, matching
F=Path(os.environ.get('ACME_B237_REFERENCE_ROOT',str(ROOT)))/'addons/acm_extended/functions'


def registry():
    return json.loads(re.sub(r'/\*.*?\*/|//[^\n]*','',(F/'fn_clinicalFields.sqf').read_text(),flags=re.S))


def test_all_registry_rows_have_valid_names_clocks_and_boolean_flags():
    seen=set()
    for row in registry():
        assert isinstance(row,list) and len(row) in (3,4),row
        assert isinstance(row[0],str) and row[0] and row[0].casefold() not in seen,row
        seen.add(row[0].casefold())
        assert row[1] in ('','time','cba'),row
        assert type(row[2]) is bool,row
        assert len(row)==3 or type(row[3]) is bool,row


def test_detached_bags_and_disconnected_markers_have_independent_reset_rows():
    rows={row[0]:row for row in registry()}
    for key in ('ACME_detachedBags','ACME_IV_DisconnectedBagUIDs'):
        assert rows.get(key)==[key,'',True],rows.get(key)


def test_actual_clinical_reset_registry_loop_reaches_end_and_clears_both_bag_states():
    # Extract the entire real registry-consumer block. Native teardown before/after
    # it is not stubbed into this assertion; this reproduces the exact failing block.
    text=(F/'fn_clinicalReset.sqf').read_text()
    end=text.index('} forEach (call ACME_fnc_clinicalFields);')
    tokens=lex(text);pairs=matching(tokens)
    close=next(i for i,t in enumerate(tokens) if t.offset==end)
    opening=next(i for i,j in pairs.items() if j==close)
    block=text[tokens[opening].offset:end+len('} forEach (call ACME_fnc_clinicalFields);')]
    execute('ACME_fnc_clinicalFields={'+(F/'fn_clinicalFields.sqf').read_text()+'};'+r'''
        private _junctionalEvidence=[];
        _patient setVariable ["ACME_detachedBags",["bag-A"]];
        _patient setVariable ["ACME_IV_DisconnectedBagUIDs",["bag-A"]];
    '''+adapt(block)+r'''
        [isNil {_patient getVariable "ACME_detachedBags"},"detached bag ledger survived full heal"] call _check;
        [isNil {_patient getVariable "ACME_IV_DisconnectedBagUIDs"},"disconnected marker survived full heal"] call _check;
    ''')
