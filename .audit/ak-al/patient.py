"""Execute Body Map click, flush dispatch and saline worker with recorded boundaries.

Inventory removal, access queries, activity logging and medicationRequest are
explicit fixtures. No engine inventory, line contents, network or UI is rendered.
"""
import re
import pytest
from test_menu_death_lifecycle import F, adapt, execute


def source(name):
    text=(F/f'fn_{name}.sqf').read_text()
    text=text.replace('findDisplay 84000','_drawDisplay')
    text=text.replace('ctrlParent _ctrl','_clickedDisplay')
    # Preserve dynamic locality rather than the general harness's true stand-in.
    text=text.replace('local _medic','_isLocal')
    text=text.replace('objectParent _medic','_medicVehicle').replace('objectParent _patient','_patientVehicle')
    text=text.replace('_medicVehicle != _patientVehicle','!(_medicVehicle isEqualTo _patientVehicle)')
    text=text.replace('_medic removeItem "ACM_SalineFlush_10";', '_removedItems pushBack "ACM_SalineFlush_10"; _stock=_stock-1;')
    text=re.sub(r'playSound ("[^"]*");',r'_sounds pushBack \1;',text)
    return adapt(text)


def setup():
    return r'''
        private _drawDisplay=missionNamespace; private _clickedDisplay=_drawDisplay;
        private _ctrl=parsingNamespace; private _otherPatient=parsingNamespace;
        private _stock=2; private _removedItems=[]; private _requests=[]; private _logs=[];
        private _sounds=[]; private _access=[]; private _refreshes=0; private _staged=[];
        private _iv=true; private _io=true; private _exactIV=true;
        private _isLocal=true; private _medicVehicle=objNull; private _patientVehicle=objNull;
        _drawDisplay setVariable ["ACME_SK_ReturnPatient",_patient];
        uiNamespace setVariable ["ACME_SK_Patient",_patient];
        uiNamespace setVariable ["ACME_SK_SelFlush","ACM_SalineFlush_10"];
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",0,"vascular"]];
        _medic setVariable ["ACME_narcStore",["untouched"]];
        ACM_circulation_fnc_hasIV={_access pushBack ["IV",+_this]; if (count _this>3) then {_exactIV} else {_iv}};
        ACM_circulation_fnc_hasIO={_access pushBack ["IO",+_this];_io};
        ace_common_fnc_getCountOfItem={_stock};
        ace_common_fnc_getName={"Provider"};
        ace_common_fnc_displayTextStructured={};
        ACME_fnc_medicationRequest={_requests pushBack +_this;};
        ace_medical_treatment_fnc_addToLog={_logs pushBack +_this;};
        ACME_fnc_skBuildHotspots={_refreshes=_refreshes+1;};
        ACME_fnc_skBeginInjection={_staged pushBack +_this;};
    '''+''.join('ACME_fnc_'+n+'={'+source(n)+'};\n' for n in ['salineFlush','skFlushSite','skSiteClick'])


@pytest.mark.parametrize('site',[1,-1])
@pytest.mark.parametrize('shared',['current','missing','other'])
@pytest.mark.parametrize('patient_alive',[True,False])
def test_flush_uses_the_patient_shown_and_checked_by_the_actual_site_click(site,shared,patient_alive):
    value={'current':'_patient','missing':'objNull','other':'_otherPatient'}[shared]
    execute(setup()+f'''
        _patientAlive={str(patient_alive).lower()};
        uiNamespace setVariable ["ACME_SK_Patient",{value}];
        _ctrl setVariable ["ACME_SK_Target",["rightleg",{site},9000,true]];
        [_ctrl] call ACME_fnc_skSiteClick;
        [_requests isEqualTo [[_medic,_patient,"rightleg",[],"flush",{site}]],"flush request targeted a different patient or line"] call _check;
        [_stock==1 && {{count _removedItems==1}},"flush debit count changed"] call _check;
        [count _logs==1 && {{(_logs select 0 select 0) isEqualTo _patient}},"activity log patient differs"] call _check;
        [(_access findIf {{!((_x select 1 select 0) isEqualTo _patient)}})<0,"access checks changed patient"] call _check;
        [count _staged==0 && {{count _waits==0}},"flush staged medication or a delay"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["leftarm",0,"vascular"],"flush mutated pending medication"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo ["untouched"],"flush mutated prepared syringes"] call _check;
        [(uiNamespace getVariable ["ACME_SK_Patient",objNull]) isEqualTo {value},"flush rewrote shared patient state"] call _check;
    ''')


@pytest.mark.parametrize('shared',['objNull','_otherPatient'])
def test_self_display_uses_the_same_self_fallback_as_hotspot_validation(shared):
    execute(setup()+f'''
        _drawDisplay setVariable ["ACME_SK_ReturnPatient",objNull];
        uiNamespace setVariable ["ACME_SK_Patient",{shared}];
        _ctrl setVariable ["ACME_SK_Target",["leftarm",2,9000,true]];
        [_ctrl] call ACME_fnc_skSiteClick;
        [_requests isEqualTo [[_medic,_medic,"leftarm",[],"flush",2]],"self view flushed another patient"] call _check;
    ''')


def test_missing_display_cannot_consume_a_flush_or_publish_a_request():
    execute(setup()+'''
        _drawDisplay=objNull;
        ["leftarm"] call ACME_fnc_skFlushSite;
        [_stock==2 && {count _requests==0} && {count _removedItems==0},"closed workspace flushed"] call _check;
        [count _logs==0 && {count _sounds==0} && {_refreshes==0},"closed workspace produced UI or activity work"] call _check;
    ''')


@pytest.mark.parametrize('state',[
    '_exactIV=false;',
    '_stock=0;',
    '_isLocal=false;',
    '_distance=6;',
    '_distance=6; _medicVehicle=missionNamespace;',
    '_distance=6; _medicVehicle=missionNamespace; _patientVehicle=parsingNamespace;',
])
def test_selected_site_stock_locality_and_distance_denials_preserve_inventory(state):
    execute(setup()+state+'''
        private _beforeStock=_stock;
        uiNamespace setVariable ["ACME_SK_SiteIdx",2];
        ["leftarm"] call ACME_fnc_skFlushSite;
        [_stock==_beforeStock && {count _requests==0} && {count _removedItems==0} && {count _logs==0},"rejected flush consumed or requested"] call _check;
    ''')


@pytest.mark.parametrize('stock',[1,2])
def test_same_vehicle_distance_exception_and_remaining_flush_selection_are_retained(stock):
    execute(setup()+f'''
        _stock={stock}; _distance=6;
        _medicVehicle=missionNamespace; _patientVehicle=missionNamespace;
        uiNamespace setVariable ["ACME_SK_SiteIdx",-1];
        ["leftarm"] call ACME_fnc_skFlushSite;
        [_stock=={stock-1} && {{count _requests==1}},"same vehicle flush was rejected"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SelFlush",""])=="{'ACM_SalineFlush_10' if stock>1 else ''}","remaining flush selection changed"] call _check;
    ''')
