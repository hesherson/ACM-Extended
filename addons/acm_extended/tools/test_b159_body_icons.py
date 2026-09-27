"""Run real overlay functions against a shared control registry in SQF-VM.

The registry models control identity, creation and retained properties, which is
essential to reproduce EJ/junctional aliasing. Arma rendering is not simulated.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute
from test_historical_procedure_trays import ui_code, controls


def source(path):
    return (ROOT / path).read_text()


def overlay_code(text):
    text = re.sub(r'_ctrlGroup controlsGroupCtrl (_\w+|\d+)', r'([\1] call _lookup)', text)
    text = re.sub(r'\(ctrlParent _ctrlGroup\) ctrlCreate \["RscPicture", (_\w+), _ctrlGroup\]', r'([\1] call _create)', text)
    text = re.sub(r'ctrlPosition _\w+', '[0,0,1,1]', text)
    text = text.replace('ctrlText _source', '"tourniquet"').replace('ctrlShown _source', 'false')
    text = text.replace('_x ctrlSetFade 0;', '[_x,"ctrlSetFade",0] call _controlWrite;')
    return ui_code(text)


def setup():
    code = controls().replace('(str _c)', '(_c toFixed 0)') + r'''
        private _created=[70113];
        private _lookup={params ["_id"];if (_id in _created) then {_id} else {objNull}};
        private _create={params ["_id"];_created pushBack _id;_id};
        ACME_fnc_a11yColor={[0.2,0.65,0.2,1]};
        ACME_fnc_ejTexturePath={format ["ej-%1",_this select 0]};
    '''
    for name in ('updateEJImage', 'updateJunctionalImage'):
        code += 'ACME_fnc_' + name + '={' + overlay_code(source('addons/acm_extended/functions/fn_' + name + '.sqf')) + '};'
    return code


@pytest.mark.parametrize('ej_first', [False, True])
@pytest.mark.parametrize('packed', [False, True])
def test_bilateral_ej_zone3_and_junctional_packing_keep_separate_artwork(ej_first, packed):
    order = ['updateEJImage', 'updateJunctionalImage']
    if not ej_first:
        order.reverse()
    draw = ''.join('[uiNamespace,_patient] call ACME_fnc_' + name + ';' for name in order)
    execute(setup() + r'''
        _patient setVariable ["ACM_circulation_IV_Placement",[[16,18,0]]];
        _patient setVariable ["ACME_AAJT_zone3",true];
    ''' + f'{{_patient setVariable ["ACME_Junc_"+_x,"{"packed" if packed else ""}"];}} forEach ["leftarm","rightarm","leftleg","rightleg"];' +
        'private _draw={' + draw + '};for "_n" from 1 to 3 do {call _draw;};' + r'''
        [(_controlValues get "7290020:ctrlSetText")=="ej-0","left EJ was replaced by packing art"] call _check;
        [(_controlValues get "7290021:ctrlSetText")=="ej-1","right EJ was replaced by packing art"] call _check;
        [(_controlValues get "7290020:ctrlShow") && {_controlValues get "7290021:ctrlShow"},"bilateral EJ visibility lost"] call _check;
        [_controlValues get "7290013:ctrlShow","Zone 3 REBOA disappeared"] call _check;
    ''' + f'{{[(_controlValues get (_x+":ctrlShow")) isEqualTo {str(packed).lower()},"packing was driven by EJ placement"] call _check;}} forEach ["7290040","7290041","7290042","7290043"];' + r'''
        _patient setVariable ["ACM_circulation_IV_Placement",[[0,18,0]]];call _draw;
        [!(_controlValues get "7290020:ctrlShow") && {_controlValues get "7290021:ctrlShow"},"removing left EJ changed the right EJ"] call _check;
        _patient=missionNamespace;call _draw;
        { [!(_controlValues get (_x+":ctrlShow")),"previous patient icon leaked into new patient"] call _check; }
            forEach ["7290020","7290021","7290040","7290041","7290042","7290043","7290013"];
        [count _created==count (_created arrayIntersect _created),"duplicate controls created during refresh"] call _check;
        [count _events==0 && {count _moves==0},"overlay changed patient state"] call _check;
    ''')


def chest_code():
    text = source('addons/gui/functions/fnc_updateBodyImage.sqf')
    ids = dict(re.findall(r'#define\s+(IDC_\w+)\s+(\d+)', source('addons/gui/script_component.hpp')))
    text = re.sub(r'\bIDC_\w+\b', lambda m: ids[m[0]], text)
    text = re.sub(r'GET_IV\(_target\)', '[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]', text)
    text = text.replace('GET_IO(_target)', '[0,0,0,0,0,0]')
    text = re.sub(r'HAS_\w+\([^)]*\)', 'false', text)
    # Native controls already exist in the config; keep their IDs in the fixture.
    text = re.sub(r'_ctrlGroup controlsGroupCtrl (\d+)', r'\1', text)
    return ui_code(text)


@pytest.mark.parametrize('state, expected', [
    ('', False),
    ('_patient setVariable ["ACM_breathing_ChestSeal_State",true];', True),
    ('_patient setVariable ["ACME_CS_holeData",[["front",0.2,0.3,true,true,"hole"]]];', True),
    ('_patient setVariable ["ACME_CS_holeData",[["back",0.2,0.3,true,true,"hole"]]];', True),
    ('_patient setVariable ["ACME_CS_holeData",[["front",0.2,0.3,true,false,"hole"]]];', False),
    ('_patient setVariable ["ACME_CS_wastedData",[["front",0.2,0.3]]];', False),
    ('_patient setVariable ["ACME_thora_sealed_left",true];', True),
    ('_patient setVariable ["ACME_thora_sealed_right",true];', True),
    ('_patient setVariable ["ACME_thora_sealed_left",true];_patient setVariable ["ACME_thora_sealed_right",true];', True),
    ('_patient setVariable ["ACME_thora_closed_left",true];', False),
    ('_patient setVariable ["ACME_thora_sealed_left",true];_patient setVariable ["ACME_thora_tube_left",true];', False),
    ('_patient setVariable ["ACME_thora_sealed_left",true];_patient setVariable ["ACME_thora_tube_left",true];_patient setVariable ["ACME_thora_sealed_right",true];', True),
])
def test_body_diagram_reads_physical_chest_seals_without_changing_physiology(state, expected):
    execute(controls() + 'private _draw={' + chest_code() + '};' + state + r'''
        [uiNamespace,_patient,1] call _draw;
    ''' + f'[(_controlValues get "70111:ctrlShow") isEqualTo {str(expected).lower()},"wrong chest seal visibility"] call _check;' + r'''
        [count _events==0,"display sent clinical changes"] call _check;
        { _patient setVariable [_x,false]; } forEach ["ACM_breathing_ChestSeal_State","ACME_thora_sealed_left","ACME_thora_sealed_right"];
        _patient setVariable ["ACME_CS_holeData",[]];
        [uiNamespace,_patient,1] call _draw;
        [!(_controlValues get "70111:ctrlShow"),"removed seals still shown"] call _check;
    ''')
