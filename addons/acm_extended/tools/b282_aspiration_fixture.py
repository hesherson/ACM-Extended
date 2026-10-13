"""Actual aspiration helpers with explicit object/locality/finite/linear engine boundaries."""
import re
from test_menu_death_lifecycle import read, adapt
from test_historical_medication_rows import iteration_scopes
from source_scan import lex, matching


def boundary(source, component="core"):
    source = re.sub(r"\blocal (_\w+)", r'(\1 getVariable ["testLocal",true])', source)
    source = re.sub(r"\balive (_\w+)", r'(\1 getVariable ["testAlive",true])', source)
    source = source.replace("toUpperANSI", "toUpper")
    tokens=lex(source); pairs=matching(tokens); edits=[]
    for i,t in enumerate(tokens[:-1]):
        if t.value not in ("finite","linearConversion"): continue
        a=i+1
        b=pairs[a] if tokens[a].value in ("[","(") else a
        expression=source[tokens[a].offset:tokens[b].offset+len(tokens[b].value)]
        name="ACME_fixture_fnc_finite" if t.value=="finite" else "ACME_fixture_fnc_linear"
        edits.append((t.offset,tokens[b].offset+len(tokens[b].value),"("+expression+" call "+name+")"))
    for a,b,v in reversed(edits): source=source[:a]+v+source[b:]
    return adapt(iteration_scopes(source),component).replace(", _syncValue]", "]").replace(",_public]", "]").replace(", _public]", "]")


def definitions(names=("aspirationState","aspirationEventKey","aspirationRestore","clinicalTickDelta")):
    out=r'''ACME_fixture_fnc_finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    ACME_fixture_fnc_linear={params ["_a","_b","_x","_c","_d",["_clip",false]];private _p=(_x-_a)/(_b-_a);if (_clip) then {_p=(_p max 0) min 1};_c+(_d-_c)*_p};'''
    out += 'if (isNil "ACME_fnc_clinicalEpoch") then {ACME_fnc_clinicalEpoch={'+boundary(read("clinicalEpoch"))+'};};'
    return out+"".join("ACME_fnc_"+name+"={"+boundary(read(name))+"};" for name in names)
