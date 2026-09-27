"""Execute actual click/flush or click/stage/push paths at UI ownership boundaries.

Displays and input delivery are stand-ins; access, inventory removal and network
requests use the prior explicit fixtures. This is not live Arma click scheduling.
"""
import pytest
from test_menu_death_lifecycle import F, execute
from test_bounded_flush_patient_context import setup as flush_setup
from test_bounded_normal_push_lifetime import source as push_source, setup as push_setup


def setup(flush):
    if flush:
        code = flush_setup()
    else:
        site = push_source('skSiteClick').replace('ctrlParent _ctrl', '_clickedDisplay')
        code = push_setup() + r'''
            private _ctrl=parsingNamespace; private _clickedDisplay=_drawDisplay;
            private _requests=[]; private _removedItems=[]; private _logs=[]; private _access=[];
            private _stock=2;
            ACM_circulation_fnc_hasIV={_access pushBack +_this;_hasAccess};
            ACM_circulation_fnc_hasIO={_access pushBack +_this;_hasAccess};
            ACME_fnc_skFlushSite={_requests pushBack +_this;};
        ''' + 'ACME_fnc_skSiteClick={' + site + '};\n'
    return code + r'''
        // Valid already-injected Body Map with a settled layout.
        uiNamespace setVariable ["ACME_SK_CloseEpoch",7];
        _drawDisplay setVariable ["ACME_SK_CloseEpoch",7];
        _drawDisplay setVariable ["ACME_SK_LayoutBusyUntil",0];
        uiNamespace setVariable ["ACME_SK_View","body"];
        uiNamespace setVariable ["ACME_SK_Route","vascular"];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
        uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
        uiNamespace setVariable ["ACME_SK_TagEditMode",false];
        uiNamespace setVariable ["ACME_SK_SiteIdx",1];
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",1,"vascular"]];
        _ctrl setVariable ["ACME_SK_Target",["rightleg",2,9000,true]];
    ''' + ('uiNamespace setVariable ["ACME_SK_SelFlush",""];' if not flush else '')


DENIALS = {
    'replaced-display': '_drawDisplay=profileNamespace; _drawDisplay setVariable ["ACME_SK_ReturnPatient",_patient];',
    'closed-display': '_drawDisplay=objNull;',
    'retired-generation': 'uiNamespace setVariable ["ACME_SK_CloseEpoch",8];',
    'unregistered-display': '_drawDisplay=parsingNamespace; _clickedDisplay=_drawDisplay;',
    'preparation-page': 'uiNamespace setVariable ["ACME_SK_View","syringe"];',
    'normal-push': 'uiNamespace setVariable ["ACME_SK_InjectionBusy",true];',
    'carousel-transition': 'uiNamespace setVariable ["ACME_SK_CarouselBusy",true];',
    'tag-editor': 'uiNamespace setVariable ["ACME_SK_TagEditMode",true];',
    'layout-transition': '_drawDisplay setVariable ["ACME_SK_LayoutBusyUntil",_nowTime+0.1];',
    'old-vascular-icon': 'uiNamespace setVariable ["ACME_SK_Route","im"];',
    'old-im-icon': '_ctrl setVariable ["ACME_SK_Target",["rightleg",-1,9000,false]];',
}


@pytest.mark.parametrize('flush', [False, True], ids=['medication','flush'])
@pytest.mark.parametrize('denial', list(DENIALS))
def test_rejected_site_event_has_no_shared_writes_or_treatment_handoff(flush, denial):
    execute(setup(flush) + DENIALS[denial] + r'''
        private _beforeBusy=uiNamespace getVariable ["ACME_SK_InjectionBusy",false];
        private _beforeCarousel=uiNamespace getVariable ["ACME_SK_CarouselBusy",false];
        private _beforeRoute=uiNamespace getVariable ["ACME_SK_Route",""];
        private _beforeFlush=uiNamespace getVariable ["ACME_SK_SelFlush",""];
        private _beforeStore=+(_medic getVariable ["ACME_narcStore",[]]);
        [_ctrl] call ACME_fnc_skSiteClick;
        [(uiNamespace getVariable ["ACME_SK_SiteIdx",-9])==1,"rejected click changed selected site"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["leftarm",1,"vascular"],"rejected click replaced staged target"] call _check;
        [count _requests==0 && {count _removedItems==0} && {_stock==2},"rejected click flushed/consumed"] call _check;
        [count _access==0 && {count _logs==0} && {count _sounds==0} && {_refreshes==0},"rejected click reached mutable delegates"] call _check;
        [count _waits==0,"rejected click queued treatment"] call _check;
        [(uiNamespace getVariable ["ACME_SK_InjectionBusy",false]) isEqualTo _beforeBusy,"click changed push lock"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CarouselBusy",false]) isEqualTo _beforeCarousel,"click changed carousel lock"] call _check;
        [(uiNamespace getVariable ["ACME_SK_Route",""])==_beforeRoute,"click changed route"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SelFlush",""])==_beforeFlush,"click changed flush selection"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo _beforeStore,"click changed syringe store"] call _check;
    ''')


@pytest.mark.parametrize('site',[1,-1])
@pytest.mark.parametrize('flush',[False,True],ids=['medication','flush'])
def test_current_settled_site_still_stages_or_flushes_at_layout_deadline(flush,site):
    execute(setup(flush) + f'''
        _drawDisplay setVariable ["ACME_SK_LayoutBusyUntil",_nowTime];
        _ctrl setVariable ["ACME_SK_Target",["rightleg",{site},9000,true]];
        [_ctrl] call ACME_fnc_skSiteClick;
    ''' + (f'''
        [_requests isEqualTo [[_medic,_patient,"rightleg",[],"flush",{site}]],"current flush rejected or wrong site"] call _check;
        [_stock==1 && {{count _removedItems==1}},"current flush debit changed"] call _check;
    ''' if flush else f'''
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightleg",{site},"vascular"],"current stage rejected"] call _check;
        [call ACME_fnc_skConfirmInjection,"current confirmation rejected"] call _check;
        0 call _runWait; 1 call _runWait;
        [_delivered isEqualTo [[_medic,_patient,"id-one",["rightleg",3],{site},"vascular"]],"current staged push changed"] call _check;
    '''))


def test_im_current_route_still_stages_without_access_queries():
    execute(setup(False) + r'''
        uiNamespace setVariable ["ACME_SK_Route","im"];
        _hasAccess=false;
        _ctrl setVariable ["ACME_SK_Target",["rightleg",-1,9000,false]];
        [_ctrl] call ACME_fnc_skSiteClick;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightleg",-1,"im"],"IM stage rejected"] call _check;
        [count _access==0,"IM queried a line"] call _check;
    ''')


@pytest.mark.parametrize('control,parent', [('objNull','missionNamespace'),('parsingNamespace','objNull')])
def test_destroyed_control_or_parent_is_rejected(control,parent):
    # Only candidate is expected to avoid querying null control parents. The fixture
    # gives that engine boundary its normal null result rather than parsing an RTM/UI.
    execute(setup(False) + f'''
        _ctrl={control}; _clickedDisplay={parent};
        [_ctrl] call ACME_fnc_skSiteClick;
        [(uiNamespace getVariable ["ACME_SK_SiteIdx",-9])==1 && {{count _access==0}},"destroyed control dispatched"] call _check;
    ''')


@pytest.mark.parametrize('settled',[False,True])
def test_late_flush_click_cannot_interrupt_an_actual_normal_push(settled):
    execute(setup(False)+r'''
        [call ACME_fnc_skConfirmInjection,"normal push rejected"] call _check;
        private _job=+(uiNamespace getVariable ["ACME_SK_NormalPush",[]]);
    '''+('0 call _runWait;' if settled else '')+r'''
        uiNamespace setVariable ["ACME_SK_SelFlush","ACM_SalineFlush_10"];
        [_ctrl] call ACME_fnc_skSiteClick;
        [count _requests==0,"late click flushed during normal push"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SiteIdx",-9])==1,"late click retargeted actual push"] call _check;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo _job,"late click replaced actual push"] call _check;
    '''+('' if settled else '0 call _runWait;')+r'''
        1 call _runWait;
        [_delivered isEqualTo [[_medic,_patient,"id-one",["leftarm",3],1,"vascular"]],"original push handoff changed"] call _check;
    ''')
