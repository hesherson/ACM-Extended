"""Execute site click -> staging -> confirmation with a recorded administration boundary.

No drug events, access creation, actual inventory or rendered hotspot input is simulated.
"""
import pytest
from test_menu_death_lifecycle import adapt, execute
from test_bounded_normal_push_lifetime import F, setup as push_setup
from test_bounded_staged_push_contracts import contains, assert_staged_contract


def assert_site_contract(site, inject, hot):
    assert contains(site, '[_part] call ACME_fnc_skBeginInjection;')
    assert not contains(site, 'call ACME_fnc_skInjectSite')
    assert not contains(site, 'call ACME_fnc_skConfirmInjection')
    assert contains(site, 'uiNamespace setVariable ["ACME_SK_SiteIdx", _site];')
    assert contains(site, '[_p, _part, 0, _site] call ACM_circulation_fnc_hasIV')
    assert contains(site, '[_p, _part, 0] call ACM_circulation_fnc_hasIO')
    assert contains(site, '[_part] call ACME_fnc_skFlushSite;')
    assert contains(inject, 'private _storeIdx = [_store] call ACME_fnc_skSelectedIndex;')
    assert contains(hot, 'private _carouselBusy = uiNamespace getVariable ["ACME_SK_CarouselBusy", false];')
    assert contains(hot, '_body && {!_tagEditMode} && {!_carouselBusy} && {_layoutReady} && {_deliveryReady} && {_route == "vascular"}')
    assert contains(hot, '_body && {!_tagEditMode} && {!_carouselBusy} && {_layoutReady} && {_route == "im"}')


def setup():
    site = (F/'fn_skSiteClick.sqf').read_text().replace('ctrlParent _ctrl','_drawDisplay').replace('findDisplay 84000','_drawDisplay')
    return push_setup()+'''
        private _control=parsingNamespace; private _flushes=[]; private _accessCalls=[];
        ACME_fnc_skFlushSite={_flushes pushBack +_this;};
        ACM_circulation_fnc_hasIV={_accessCalls pushBack ["IV",+_this];_hasAccess};
        ACM_circulation_fnc_hasIO={_accessCalls pushBack ["IO",+_this];_hasAccess};
    '''+'private _click={'+adapt(site)+'};\n'


@pytest.mark.parametrize('route,site',[('vascular',1),('vascular',-1),('im',-1)])
@pytest.mark.parametrize('change_selection',[False,True])
def test_click_stages_only_then_confirmation_uses_the_current_syringe(route,site,change_selection):
    execute(setup()+f'''
        uiNamespace setVariable ["ACME_SK_Route","{route}"];
        _control setVariable ["ACME_SK_Target",["rightleg",{site},9000,{str(route=='vascular').lower()}]];
        [_control] call _click;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightleg",{site},"{route}"],"wrong staged site"] call _check;
        [count _delivered==0 && {{count _waits==0}} && {{count _flushes==0}},"click started medication"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",false]),"staging locked syringe selection"] call _check;
    '''+('''["id-two",_medic getVariable ["ACME_narcStore",[]]] call ACME_fnc_skSelectStored;''' if change_selection else '')+'''
        [call ACME_fnc_skConfirmInjection,"confirmation rejected"] call _check;
        [count _delivered==0,"confirmation handed off before its delays"] call _check;
        0 call _runWait;
        [count _delivered==0,"settle handed off early"] call _check;
        [((_waits select 1) select 2)==3,"default duration changed"] call _check;
        1 call _runWait;
    '''+f'''
        [_delivered isEqualTo [[_medic,_patient,"{'id-two' if change_selection else 'id-one'}",["rightleg",3],{site},"{route}"]],"wrong final handoff"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo [_row,_other],"UI handoff altered fixture inventory"] call _check;
    '''+('''[(_accessCalls select 0) isEqualTo ["IV",[_patient,"rightleg",0,1]],"IV click validated a different access"] call _check;''' if site==1 else '''[(_accessCalls select 0) isEqualTo ["IO",[_patient,"rightleg",0]],"IO click validated a different limb"] call _check;''' if route=='vascular' else '''[count _accessCalls==0,"IM required vascular access"] call _check;'''))


@pytest.mark.parametrize('site',[1,-1])
def test_removed_vascular_access_does_not_stage_or_administer(site):
    execute(setup()+f'''
        _hasAccess=false;
        _control setVariable ["ACME_SK_Target",["rightleg",{site},9000,true]];
        [_control] call _click;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["leftarm",1,"vascular"],"stale icon changed staged target"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SiteIdx",-9])==1,"stale icon changed selected site"] call _check;
        [count _delivered==0 && {{count _waits==0}} && {{count _flushes==0}},"stale icon delivered"] call _check;
    ''')


@pytest.mark.parametrize('site',[1,-1])
def test_selected_flush_keeps_its_separate_dispatch(site):
    execute(setup()+f'''
        uiNamespace setVariable ["ACME_SK_SelFlush","ACM_SalineFlush_10"];
        _control setVariable ["ACME_SK_Target",["rightleg",{site},9000,true]];
        [_control] call _click;
        [_flushes isEqualTo [["rightleg"]],"flush bypass changed"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SiteIdx",-9])=={site},"flush site changed"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["leftarm",1,"vascular"],"flush staged a medication"] call _check;
        [count _delivered==0 && {{count _waits==0}},"flush entered staged medication path"] call _check;
    ''')


@pytest.mark.parametrize('target,old,new',[
    ('site','[_part] call ACME_fnc_skBeginInjection;','[_part] call ACME_fnc_skInjectSite;'),
    ('site','[_p, _part, 0, _site]','[_p, _part, 0, 0]'),
    ('site','[_part] call ACME_fnc_skFlushSite;','[_part] call ACME_fnc_skBeginInjection;'),
    ('hot','{!_carouselBusy}','{true}'),
])
def test_contract_rejects_immediate_administration_wrong_access_and_lost_busy_guard(target,old,new):
    texts={k:(F/('fn_'+n+'.sqf')).read_text() for k,n in [('site','skSiteClick'),('inject','skInjectSite'),('hot','skBuildHotspots')]}
    assert_site_contract(**texts)
    assert old in texts[target]
    texts[target]=texts[target].replace(old,new,1)+'\n/* '+old+' */\n'
    with pytest.raises(AssertionError):
        assert_site_contract(**texts)
