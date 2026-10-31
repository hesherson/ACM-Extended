"""Execute the unchanged visual registration block after extracting it from postInit."""
import pytest
from test_menu_death_lifecycle import F, adapt, execute


def setup(interface=True):
    text=(F/'fn_registerVisualEffectsRuntime.sqf').read_text()
    text=text.replace('hasInterface','_interface').replace('_patient != player','!(_patient isEqualTo _localPlayer)')
    return f'private _interface={str(interface).lower()};'+r'''
        private _localPlayer=_medic;private _events=[];private _workers=[];
        CBA_fnc_addEventHandler={_events pushBack _this;};
        CBA_fnc_addPerFrameHandler={_workers pushBack _this;42};
    '''+adapt(text)


@pytest.mark.parametrize('interface',[False,True])
def test_registration_is_client_only_and_retains_single_handler_and_worker(interface):
    execute(setup(interface)+f'''
        [count _events=={int(interface)} && {{count _workers=={int(interface)}}},"duplicate/server-only visual registration"] call _check;
    '''+(r'''
        [(_events select 0 select 0)=="ace_medical_treatment_medicationLocal","wrong dose listener"] call _check;
        [(_workers select 0 select 1)==0.12,"visual update interval changed"] call _check;
    ''' if interface else ''))


@pytest.mark.parametrize('drug,local,expected',[
    ('Ketamine',True,True),('Ketamine_IV',True,True),('Esketamine',True,True),
    ('Morphine',True,False),('Ketamine',False,False)])
def test_visual_receipt_updates_only_local_ketamine_perception_window(drug,local,expected):
    target='_medic' if local else '_patient'
    execute(setup()+f'''
        [{target},"body","{drug}",1,false] call (_events select 0 select 1);
        [(!isNil {{uiNamespace getVariable "ACME_VFX_KetLastDoseAt"}})=={str(expected).lower()},"wrong patient's/drug's window refreshed"] call _check;
    ''')
