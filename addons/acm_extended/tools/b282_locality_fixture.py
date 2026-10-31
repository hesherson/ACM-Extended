"""Production dependencies for retained Local/registration execution fixtures.

Callers provide their existing object/locality/owner/clock engine adapter. Only
namespace publication and SQF-VM's missing map/finite primitives are adapted
here; the recovery admission and native mutation bodies remain production SQF.
"""
import re

from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT
from test_historical_vial_execution import map_defaults


def native_macros(text, component):
    text = re.sub(r'^#include.*$', '', text, flags=re.M)
    for macro, prefix in (('QACEGVAR', 'ace'), ('QEGVAR', 'ACM')):
        text = re.sub(r'\b' + macro + r'\((\w+),\s*(\w+)\)',
                      lambda m: f'"{prefix}_{m[1]}_{m[2]}"', text)
    text = re.sub(r'\bQGVAR\((\w+)\)',
                  lambda m: f'"ACM_{component}_{m[1]}"', text)
    return text


def vm_primitives(text):
    text = text.replace('canSuspend', 'false')
    text = text.replace(', _public]', ']')
    text = re.sub(r'\bvalues (_\w+)', r'((keys \1) apply {\1 get _x})', text)
    text = map_defaults(text).replace('call _mapDefault', 'call _localityMapDefault')
    tokens = lex(text)
    pairs = matching(tokens)
    edits = []
    for i, token in enumerate(tokens[:-1]):
        if token.kind != 'ident' or token.value != 'finite':
            continue
        end = pairs[i + 1] if tokens[i + 1].value == '(' else i + 1
        operand = text[tokens[i + 1].offset:tokens[end].offset + len(tokens[end].value)]
        edits.append((token.offset, tokens[end].offset + len(tokens[end].value),
                      '(' + operand + ' call _localityFinite)'))
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return text


def definitions(engine, *, predicate_only=False):
    result = '''
        private _localityFinite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _localityMapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
    '''
    names = ('ownerRegisterNeedsRecovery',) if predicate_only else (
        'ownerRegisterNeedsRecovery', 'ventBatteryRequest', 'piggybackRecover',
        'lineWarmerRecover', 'aiProtectionSync',
    )
    for name in names:
        text = (ROOT / 'addons/acm_extended/functions' / f'fn_{name}.sqf').read_text()
        if name == 'piggybackRecover':
            # VM lacks HashMap forEach's _y value; traverse the same real keys.
            text = text.replace('private _held = _y;', 'private _held = _escrow get _x;')
            text = text.replace('} forEach _escrow;', '} forEach keys _escrow;')
        result += f'ACME_fnc_{name}={{' + engine(vm_primitives(text)) + '};\n'
    if not predicate_only:
        for component, name in (
            ('circulation', 'setRuntimeState'), ('breathing', 'setRuntimeState'),
            ('circulation', 'cprRetireAnimLocal'),
        ):
            text = (ROOT / 'addons' / component / 'functions' / f'fnc_{name}.sqf').read_text()
            result += f'ACM_{component}_fnc_{name}={{' + engine(vm_primitives(native_macros(text, component))) + '};\n'
    return result
