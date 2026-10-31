"""B222: execute actual suction input, SALAD placement and the EFAK count bridge.

Engine displays/controls, raw mouse delivery and the external EFAK API are fixtures.
This does NOT run EFAK networking or assert that the Workshop build matches GitHub.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import execute, read, adapt
from test_b156_procedure_supplies import suction_setup, primitives
from test_historical_procedure_trays import ui_code


def block(text, marker):
    start=text.index(marker)+len(marker)
    ts=lex(text[start:]); pairs=matching(ts)
    opening=next(i for i,t in enumerate(ts) if t.value=='{')
    return text[start+ts[opening].offset+1:start+ts[pairs[opening]].offset]


def input_setup(efak=True):
    priority=block(read('laryngoInit'),'_display setVariable ["ACME_InputMousePriority",')
    mouseup=block(read('laryngoInit'),'_display displayAddEventHandler ["MouseButtonUp",')
    mouse=read('minigameInputMouse')
    # Display/control normalization is an engine boundary; this fixture supplies a display namespace.
    a=mouse.index('private _display = displayNull;');b=mouse.index('if (isNull _display) exitWith')
    mouse=mouse[:a]+'private _display = _source;\n'+mouse[b:]
    source=suction_setup()+'''
        private _display=missionNamespace;
        private _generic=0; private _pumpStarts=0; private _pumpStops=0;
        private _notices=[];
        ACME_fnc_minigameInput={if !(_this select 5) then {_generic=_generic+1;};true};
        ACME_fnc_suctionSfxStart={_pumpStarts=_pumpStarts+1;};
        ACME_fnc_suctionSfxStop={_pumpStops=_pumpStops+1;};
        ACME_fnc_worldSfxNearby={};
        ace_common_fnc_displayTextStructured={_notices pushBack (_this select 0);};
        uiNamespace setVariable ["ACME_laryngo_cur",[0.502,0.172]];
        uiNamespace setVariable ["ACME_laryngo_rect",[0,0,1,1]];
        uiNamespace setVariable ["ACME_laryngo_frame",[0,0,1,1]];
    '''
    if efak:
        source+='''
        efak_medical_fnc_countItem={params ["_u","_item"];
            ({_x==_item} count (_u getVariable ["fixtureStock",[]]))+
            ({_x==_item} count (_u getVariable ["fixtureKitStock",[]]))
        };
        '''
    # itemCount's CAManBase predicate is an engine type check; all units here are men.
    item=read('itemCount').replace('_unit isKindOf "CAManBase"','true')
    source+='ACME_fnc_itemCount={'+adapt(item)+'};'
    for name,text in [('minigameInputMouse',mouse),('laryngoClick',read('laryngoClick')),
                      ('laryngoSuctionPin',read('laryngoSuctionPin')),('laryngoCuffDeflate',read('laryngoCuffDeflate'))]:
        source+='ACME_fnc_'+name+'={'+primitives(ui_code(text))+'};'
    return source+'_display setVariable ["ACME_InputMousePriority",{'+adapt(priority)+'}];private _mouseUp={'+adapt(mouseup)+'};'


@pytest.mark.parametrize('efak',[False,True],ids=['loose-stock','kit-api'])
@pytest.mark.parametrize('generic_first',[False,True],ids=['procedure-first','generic-first'])
def test_park_and_unpark_once_despite_duplicate_handlers_and_remapped_mmb(efak,generic_first):
    field='fixtureKitStock' if efak else 'fixtureStock'
    generic='[[_display,2],"down"] call ACME_fnc_minigameInputMouse;'
    click='[_display,2] call ACME_fnc_laryngoClick;'
    down=generic+click if generic_first else click+generic
    execute(input_setup(efak)+f'_medic setVariable ["{field}",["ACM_ACCUVAC"]];'+down+down+'''
        [uiNamespace getVariable ["ACME_laryngo_sucPinned",false],"MMB did not park"] call _check;
        [(uiNamespace getVariable ["ACME_laryngo_held","bad"])=="","parking did not free hands"] call _check;
        [_pumpStarts==1 && {_generic==0},"duplicate toggle or generic MMB stole suction"] call _check;
        [count _debits==0,"reusable ACCUVAC debited"] call _check;
        [_display,2] call _mouseUp;
    '''+down+down+'''
        [!(uiNamespace getVariable ["ACME_laryngo_sucPinned",true]),"second press failed to unpark"] call _check;
        [!(uiNamespace getVariable ["ACME_laryngo_sucOn",true]),"unpark left suction running"] call _check;
        [_pumpStops==1 && {_generic==0},"unpark duplicated or generic input leaked"] call _check;
    ''')


@pytest.mark.parametrize('reason',['empty-kit','manual-bag','outside-mouth','sharing-disabled'])
def test_parking_never_invents_a_device_or_bypasses_anatomy_and_sharing(reason):
    setup={
        'empty-kit':'',
        'manual-bag':'_medic setVariable ["fixtureKitStock",["ACM_SuctionBag"]];',
        'outside-mouth':'_medic setVariable ["fixtureKitStock",["ACM_ACCUVAC"]];uiNamespace setVariable ["ACME_laryngo_cur",[0,0]];',
        'sharing-disabled':'_patient setVariable ["fixtureKitStock",["ACM_ACCUVAC"]];ace_medical_treatment_allowSharedEquipment=2;',
    }[reason]
    execute(input_setup()+setup+'''
        [_display,2] call ACME_fnc_laryngoClick;
        [!(uiNamespace getVariable ["ACME_laryngo_sucPinned",false]),"invalid SALAD park succeeded"] call _check;
        [_pumpStarts==0 && {count _debits==0},"invalid park started pump or consumed supply"] call _check;
        [count _notices==1,"failed park did not explain why"] call _check;
    ''')


def test_lost_mouseup_does_not_latch_parking_forever():
    execute(input_setup()+'''
        _medic setVariable ["fixtureKitStock",["ACM_ACCUVAC"]];
        [_display,2] call ACME_fnc_laryngoClick;
        _nowTime=_nowTime+2;
        [_display,2] call ACME_fnc_laryngoClick;
        [!(uiNamespace getVariable ["ACME_laryngo_sucPinned",true]),"lost release trapped SALAD"] call _check;
    ''')


@pytest.mark.parametrize('held',["",'suction','tube','blade','collar'])
def test_right_click_outside_syringe_is_not_a_cuff_deflation(held):
    execute(input_setup()+f'uiNamespace setVariable ["ACME_laryngo_held","{held}"];'+'''
        // No generic binding on RMB in this fixture.
        ACME_fnc_minigameInput={false};
        [_display,1] call ACME_fnc_laryngoClick;
        ["start"] call ACME_fnc_laryngoCuffDeflate;
        [count _notices==0,"unrelated tool reported cuff already down"] call _check;
        [isNil {uiNamespace getVariable "ACME_laryngo_deflateT0"},"unrelated click started cuff work"] call _check;
    ''')


@pytest.mark.parametrize('inflated',[False,True])
def test_syringe_retains_real_cuff_diagnostics_and_start(inflated):
    execute(input_setup()+f'_patient setVariable ["ACME_ETT_CuffInflated",{str(inflated).lower()}];'+'''
        _patient setVariable ["ACME_ETT_Inserted",true];
        uiNamespace setVariable ["ACME_laryngo_held","syringe"];
        ACME_fnc_minigameInput={false};
        [_display,1] call ACME_fnc_laryngoClick;
    '''+('''[(uiNamespace getVariable ["ACME_laryngo_deflateT0",-1])>=0,"valid cuff deflation rejected"] call _check;''' if inflated else '''[_notices isEqualTo ["The cuff is already down."],"real cuff feedback lost"] call _check;'''))


def test_generic_mmb_remains_available_without_suction():
    execute(input_setup()+'''
        uiNamespace setVariable ["ACME_laryngo_held","blade"];
        [_display,2] call ACME_fnc_laryngoClick;
        [_generic==1 && {_pumpStarts==0},"generic mouse binding removed globally"] call _check;
    ''')
