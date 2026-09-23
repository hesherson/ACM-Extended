"""The historical B69 push check follows explicit confirmation and native rhythm ownership."""
import pytest
from source_scan import lex
from test_bounded_staged_push_contracts import contains, assert_staged_contract
from test_bounded_normal_push_lifetime import F, test_current_push_retains_duration_route_target_and_stable_id as verify_push
from test_historical_cardiac_execution import test_threshold_observer_never_clears_native_critical_rhythm_without_treatment as observe_native


def texts():
    return {name:(F/('fn_'+name+'.sqf')).read_text() for name in
            ['skBeginInjection','skConfirmInjection','rhythmThresholdTick','postInit']}


def assert_contract(source=None):
    s=texts() if source is None else source
    assert_staged_contract(s['skBeginInjection'],s['skConfirmInjection'])
    # Do not restore the retired Extended HR floor or an independent arrest dispatch.
    assert not any(t.kind=='ident' and t.value=='ACME_tbi_nonterminalMinHR' for t in lex(s['postInit']))
    assert not contains(s['rhythmThresholdTick'],'call ACME_fnc_arrestLocal')
    assert not contains(s['rhythmThresholdTick'],'setVariable ["ace_medical_heartRate",')


@pytest.mark.parametrize('native',[-1,1,2,3,4])
def test_current_observer_does_not_override_native_critical_rhythm(native):
    observe_native(native)


@pytest.mark.parametrize('name,addition',[
    ('skBeginInjection','call ACME_fnc_skInjectSite;'),
    ('rhythmThresholdTick','call ACME_fnc_arrestLocal;'),
    ('rhythmThresholdTick','_u setVariable ["ace_medical_heartRate",42];'),
    ('postInit','ACME_tbi_nonterminalMinHR=42;'),
])
def test_contract_rejects_early_delivery_or_independent_hr_authority(name,addition):
    s=texts();s[name]+='\n'+addition+'\n'
    with pytest.raises(AssertionError):assert_contract(s)


def historical_combined_check():
    assert_contract()
    # Keep behavior in this retained historical identity, not only source spellings.
    for route,site in [('vascular',1),('vascular',-1),('im',-1)]:
        verify_push(route,site,'')
    for native in [-1,1,2,3,4]:observe_native(native)
