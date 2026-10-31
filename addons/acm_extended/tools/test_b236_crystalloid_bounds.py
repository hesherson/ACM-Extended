"""Execute the real dispatch case, with object/writer and finite-number VM boundaries."""
import pytest
from test_b232_iv_finish import run,ROOT
F=ROOT/"addons/acm_extended/functions"
from source_scan import lex,matching

def block():
    text=(F/'fn_ownerDispatch.sqf').read_text()
    start=text.index('case "crystalloidCredit":')
    opening=text.index('{',start)
    tokens=lex(text); index=next(i for i,t in enumerate(tokens) if t.offset==opening)
    return text[opening+1:tokens[matching(tokens)[index]].offset]

@pytest.mark.parametrize('args,expected',[
    ('[-1]',0),('[0]',0),('[0.010]',1),('[0.030]',1),('[0.250]',1),('[0.251]',0),('[1]',0),('[1000000]',0),('[0.010,7]',0)
])
def test_small_bolus_range_and_exact_argument_arity(args,expected):
    # SQF-VM does not implement finite SCALAR. Numeric fixtures here are finite;
    # source coverage below retains the production non-finite guard explicitly.
    code=block().replace('finite _liters','true')
    run('private _writes=[];ACM_circulation_fnc_setRuntimeState={_writes pushBack _this;};'+f'private _args={args};'+code+f'[count _writes=={expected},"raw bolus admission bound"] call _check;')

def test_nonfinite_guard_and_legitimate_callers_retained():
    assert 'finite _liters' in block()
    assert 'crystalloidCredit",[0.010]' in (F/'fn_ivFinishCommit.sqf').read_text()
    osmo=(F/'fn_tbiOsmoBolus.sqf').read_text()
    assert 'crystalloidCredit' in osmo and '_fluidMl / 1000' in osmo
    assert '250' in osmo and '30' in osmo
