"""Source checks for explicitly reviewed request -> owner operation -> writer paths.

This does not authenticate network senders or simulate native Arma transport.
"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]

def assert_owner_route(request, operation, handler, writer, root=ROOT):
    root=Path(root); functions=root/'addons/acm_extended/functions'
    def code(path):
        text=path.read_text()
        return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))
    request_source=code(functions/request)
    dispatch=code(functions/'fn_ownerDispatch.sqf')
    target=code(functions/f'fn_{handler}.sqf')
    assert 'call ACME_fnc_ownerDispatch' in request_source
    assert f'"{operation}"' in request_source
    assert re.search(r'case\s+"'+re.escape(operation)+r'"\s*:\s*\{[^{}]*\bcall\s+ACME_fnc_'+re.escape(handler)+r'\s*;',dispatch)
    assert '!local _patient' in dispatch
    assert re.search(r'\bcall\s+ACME_fnc_'+re.escape(writer)+r'\b',target)
    assert 'class '+handler+' {};' in code(root/'addons/acm_extended/config.cpp')
