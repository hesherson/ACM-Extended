"""Execute actual treatment config conditions with the shared inventory readers.

Namespaces stand in for objects; inventory and role lookup are engine fixtures.
The config expressions and production supply priority/count logic run in SQF-VM.
"""
import json

import pytest

from medication_inventory import subtree
from test_menu_death_lifecycle import ROOT, adapt, execute, read


CONFIG = (ROOT / 'addons/acm_extended/config.cpp').read_text()
ACTIONS = subtree(CONFIG, 'ace_medical_treatment_actions')['classes']
CASES = {
    'ACME_CheckTemperature': (['ACM_Thermometer'], ''),
    'ACME_ReadCoreTemp': (['ACM_Thermometer'], ''),
    'ACME_IntubateStart': (['ACME_Laryngoscope', 'ACME_ETTube'], ''),
    'ACME_ConnectETVent': (['ACME_Ventilator'], '_patient setVariable ["ACME_ETT_Inserted",true];'),
    'ACME_PrepHPMK': (['ACM_HPMK'], '_patient setVariable ["ACE_isUnconscious",true];'),
    'ACME_AttachEMMA': (['ACM_EMMA'], ''),
    'ACME_FlushLine': (['ACM_SalineFlush_10'], ''),
    'ACME_ApplyXStat': (['ACME_XStat'], '_patient setVariable ["ACME_Junc_leftarm","open"];'),
    'ACME_ApplyNRB': (['ACM_NRBMask'], ''),
}


def setup(name):
    items, state = CASES.get(name, (['ACME_Ventilator'], '_patient setVariable ["ACME_vent_configured",true];'))
    definitions = ''
    for helper in ('treatmentSupplyOrder', 'treatmentSupplyCount'):
        source = read(helper).replace('objectParent _x', 'objNull').replace('itemCargo _vehicle', '[]')
        definitions += 'ACME_fnc_' + helper + '={' + adapt(source) + '};'
    return definitions + '''
        private _trained=false;
        private _roleAllowed=true;
        private _bodyPart="leftarm";
        ace_medical_treatment_fnc_isMedic={_trained};
        ace_common_fnc_getCountOfItem={params ["_unit","_item"]; {_x==_item} count (_unit getVariable ["items",[]])};
        ACME_fnc_procedureActionAllowed={_roleAllowed};
        ACM_circulation_fnc_hasIV={true};
        ACM_circulation_fnc_hasIO={false};
        ACME_fnc_aajtOccludes={false};
        ACME_fnc_nrbAirwayCompatible={true};
        _medic setVariable ["items",[]];
    ''' + '_patient setVariable ["items",' + json.dumps(items) + '];' + state


@pytest.mark.parametrize('name', CASES)
@pytest.mark.parametrize('mode,trained,allowed', [(0,False,True), (1,False,True), (2,False,False), (3,False,True), (3,True,True)])
def test_patient_only_supplies_follow_the_actual_ace_equipment_mode(name, mode, trained, allowed):
    condition = adapt(ACTIONS[name]['props']['condition'])
    execute(setup(name) + f'ace_medical_treatment_allowSharedEquipment={mode}; _trained={str(trained).lower()};' +
        'private _condition={' + condition + '};' +
        f'[(call _condition)=={str(allowed).lower()},"patient-only config gate disagrees with equipment mode"] call _check;' + '''
        _patient setVariable ["items",[]];
        [!(call _condition),"config gate ignored missing supply"] call _check;
    ''')


@pytest.mark.parametrize('name', ['ACME_IntubateStart', 'ACME_ConnectETVent', 'ACME_VentOpenPatient'])
def test_shared_supplies_do_not_bypass_existing_procedure_role_gates(name):
    condition = adapt(ACTIONS[name]['props']['condition'])
    supply = '_medic setVariable ["items",["ACME_Ventilator"]];' if name == 'ACME_VentOpenPatient' else ''
    execute(setup(name) + supply + 'ace_medical_treatment_allowSharedEquipment=0; _roleAllowed=false;' +
        '[!(call {' + condition + '}),"patient supply bypassed procedure role"] call _check;')


def test_manually_consumed_minigame_supplies_are_not_debited_by_ace_first():
    empty = ('ACME_IVMinigameStart', 'ACME_EstablishEJ', 'ACME_IntubateStart',
             'ACME_OpenAirwayView', 'ACME_PrepHPMK', 'ACME_FlushLine', 'ACME_ConnectETVent')
    for name in empty:
        assert ACTIONS[name]['props']['items'] == [], name
    for name in ('ACME_PerformThoracostomy', 'ACME_InsertChestTube', 'ACME_ApplyChestSeal',
                 'ACME_PerformNARSPEAR', 'UseSuctionBag'):
        assert ACTIONS[name]['props']['consumeItem'] == 0, name
    # UseAccuvac inherits the explicitly non-consuming UseSuctionBag action.
    assert ACTIONS['UseAccuvac']['parent'] == 'UseSuctionBag'


def test_reopen_airway_and_affixed_ventilator_still_need_no_new_disposable():
    assert 'ACME_ETTube' not in ACTIONS['ACME_OpenAirwayView']['props']['condition']
    condition = adapt(ACTIONS['ACME_VentOpenPatient']['props']['condition'])
    execute(setup('ACME_VentOpenPatient') + '''
        ace_medical_treatment_allowSharedEquipment=2;
        _patient setVariable ["items",[]];
        _patient setVariable ["ACME_vent_onPatient",true];
    ''' + '[call {' + condition + '},"affixed device incorrectly requires a second carried ventilator"] call _check;')


@pytest.mark.parametrize('mode', [0,1,2,3])
def test_nonaffixed_ventilator_presets_require_the_provider_device(mode):
    # An inventory preset panel stores settings on the provider. Shared devices are
    # acquired by Connect ET > Ventilator before opening their deployed panel.
    condition = adapt(ACTIONS['ACME_VentOpenPatient']['props']['condition'])
    execute(setup('ACME_VentOpenPatient') + f'ace_medical_treatment_allowSharedEquipment={mode};' +
        'private _condition={' + condition + '};' + '''
        [!(call _condition),"patient-only undeployed device opened provider presets"] call _check;
        _medic setVariable ["items",["ACME_Ventilator"]];
        [call _condition,"personal ventilator preset flow blocked"] call _check;
    ''')
