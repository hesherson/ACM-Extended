"""Protect current split-route backing colors and flush-forced vascular selection."""
import pytest
from source_scan import lex
from test_menu_death_lifecycle import ROOT

P=ROOT/'addons/acm_extended/functions/fn_skBuildHotspots.sqf'

def require(text,snippet):
    a=[x.value for x in lex(text)]; b=[x.value for x in lex(snippet)]
    assert any(a[i:i+len(b)]==b for i in range(len(a)-len(b)+1)),snippet

def contract(text):
    for s in (
        'private _green = [0.20,0.65,0.20,0.92];',
        'private _gray = [0.20,0.20,0.20,0.72];',
        'if (_flush != "") then {_route = "vascular"; uiNamespace setVariable ["ACME_SK_Route", _route];};',
        'if (_route == "vascular") then {_green} else {_gray}',
        'if (_route == "im") then {_green} else {_gray}',
        '_imBtn ctrlEnable (_flush == "");',
    ): require(text,s)

def test_current_route_selector_contract():
    contract(P.read_text())

@pytest.mark.parametrize('old,new',[
    ('[0.20,0.65,0.20,0.92]','[0.12,0.62,0.24,0.92]'),
    ('_route = "vascular"; uiNamespace setVariable ["ACME_SK_Route", _route];','_route = "vascular";'),
    ('_imBtn ctrlEnable (_flush == "");','_imBtn ctrlEnable true;'),
])
def test_contract_rejects_regression_despite_comment(old,new):
    t=P.read_text(); assert old in t
    with pytest.raises(AssertionError): contract(t.replace(old,new,1)+'\n/* '+old+' */\n')
