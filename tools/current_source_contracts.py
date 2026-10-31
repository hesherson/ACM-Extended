"""Reviewed inline-owner source routes, using balanced SQF tokens.

This validates source linkage, not native transport or sender authentication.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addons/acm_extended/tools'))
from source_scan import lex,matching

def _has(source,fragment):
    tokens=[(t.kind,t.value) for t in lex(source)]
    needle=[(t.kind,t.value) for t in lex(fragment)]
    return any(tokens[i:i+len(needle)]==needle for i in range(len(tokens)-len(needle)+1))

def inline_case(source,operation):
    tokens=lex(source); pairs=matching(tokens)
    matches=[i for i in range(len(tokens)-3) if tokens[i].value=='case' and tokens[i+1].kind=='string'
             and tokens[i+1].value==operation and tokens[i+2].value==':' and tokens[i+3].value=='{']
    assert len(matches)==1, (operation,'missing or duplicated owner case')
    start=matches[0]+3;end=pairs[start]
    return source[tokens[start].offset+1:tokens[end].offset]

def assert_inline_owner_route(request,operation,writer,root=ROOT):
    root=Path(root);fun=root/'addons/acm_extended/functions'
    req=(fun/f'fn_{request}.sqf').read_text();dispatch=(fun/'fn_ownerDispatch.sqf').read_text()
    assert _has(req,'call ACME_fnc_ownerDispatch;')
    assert any(t.kind=='string' and t.value==operation for t in lex(req))
    assert _has(dispatch,'if (!local _patient) exitWith')
    block=inline_case(dispatch,operation)
    assert _has(block,f'call ACME_fnc_{writer};')
    assert _has((root/'addons/acm_extended/config.cpp').read_text(),f'class {writer} {{}};')
    assert _has((fun/f'fn_{writer}.sqf').read_text(),'if (!local _patient) exitWith')
