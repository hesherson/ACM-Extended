"""Execute the configured nasal spray callback and native medication wrapper.

Config reads use the checked-out item's real display name. ACE's log/triage
storage and CBA transport are captured boundaries; their engine/network
implementation and medication physiology are not simulated by these tests.
"""
import json
import re

import pytest

from medication_inventory import subtree
from test_menu_death_lifecycle import ROOT, adapt, execute


def spray_config():
    source = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    action = subtree(source, 'ace_medical_treatment_actions')['classes']['ACME_Esketamine_IN']['props']
    item = subtree(source, 'CfgWeapons')['classes']['ACME_Spray_Esketamine']['props']
    return action, item


def native_medication():
    source = (ROOT / 'addons/core/overrides/fnc_medication.sqf').read_text()
    source = re.sub(r'ACELSTRING\((\w+),\s*(\w+)\)', r'"STR_ACE_\1_\2"', source)
    # The spray is a CfgWeapons item; configuration is the only adapted code.
    source = source.replace('isClass (configFile >> "CfgMagazines" >> _usedItem)', '(_usedItem in _magazines)')
    source = source.replace('getText (configFile >> _cfg >> _usedItem >> "displayName")', '(_itemNames get _usedItem)')
    return adapt(source)


@pytest.mark.parametrize('donor', ['_medic', '_patient'])
@pytest.mark.parametrize('administrations', [1, 2])
def test_esketamine_success_logs_actual_product_once_per_administration(donor, administrations):
    action, item = spray_config()
    assert action['items'] == ['ACME_Spray_Esketamine']
    callback = action['callbackSuccess']
    display_name = json.dumps(item['displayName'])
    execute('''
        private _logs=[]; private _triage=[]; private _nameRequests=[];
        private _magazines=[];
        ace_common_fnc_getName={_nameRequests pushBack _this; "Provider name"};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        ace_medical_treatment_fnc_addToTriageCard={_triage pushBack _this;};
        CBA_fnc_targetEvent={_events pushBack _this;};
    ''' + 'private _itemNames=createHashMapFromArray [["ACME_Spray_Esketamine",' + display_name + ']];' +
        'ace_medical_treatment_fnc_medication={' + native_medication() + '};' +
        # ACE treatmentSuccess supplies these variables and calls the configured callback.
        'private _success={params ["_medic","_patient","_bodyPart","_classname","_itemUser","_usedItem","_createLitter"];' + callback + '};' +
        f'for "_n" from 1 to {administrations} do {{[_medic,_patient,"Head","ACME_Esketamine_IN",{donor},"ACME_Spray_Esketamine",false] call _success;}};' + f'''
        [count _logs=={administrations},"spray activity entry missing or duplicated"] call _check;
        [count _triage=={administrations},"spray triage entry missing or duplicated"] call _check;
        [count _events=={administrations},"spray effect event missing or duplicated"] call _check;
        [count _nameRequests=={administrations},"provider name not resolved once per administration"] call _check;
        {{[_x isEqualTo [_medic,false,true],"inventory donor replaced actual provider"] call _check;}} forEach _nameRequests;
        {{[_x isEqualTo [_patient,"activity","STR_ACE_medical_treatment_Activity_usedItem",["Provider name",{display_name}]],
            "activity entry lost patient, provider, product name, route or dose"] call _check;}} forEach _logs;
        {{[_x isEqualTo [_patient,{display_name}],"triage entry used wrong product"] call _check;}} forEach _triage;
        {{[_x isEqualTo ["ace_medical_treatment_medicationLocal",[_patient,"Head","Esketamine",1,false],_patient],
            "effect class, product-unit dose, route, body part or patient owner changed"] call _check;}} forEach _events;
    ''')
