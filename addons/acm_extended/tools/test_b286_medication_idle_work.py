"""Execute toxicity with native medication kinetics and counted config reads.

Only engine config access and native syndrome creation are boundaries. Empty
history must be quiet; a later admitted dose must still reach the same onset,
family threshold and generation latch in the production toxicity function.
"""
import re

import pytest

from test_historical_medication_effects import F, code, function, setup
from test_menu_death_lifecycle import execute


def fixture():
    text = (F / 'fn_medicationToxicityTick.sqf').read_text()
    assert 'configFile >> "ACM_Medication" >> "Medications" >> _x' in text
    text = text.replace('configFile >> "ACM_Medication" >> "Medications" >> _x', '_x')
    text, count = re.subn(r'getNumber \(_cfg >> "(maxDose|maxEffectDose|weightEffect)"\)',
                          r'([_cfg,"\1"] call _configNumber)', text)
    assert count == 3
    text = text.replace('GET_BODYWEIGHT(_patient)', '70').replace('IDEAL_BODYWEIGHT', '70')
    # VM lacks triangular random arrays. Fix only the syndrome's randomized
    # target at its configured mode; onset/burden/generation logic stays live.
    text = re.sub(r'random \[([^\]]+)\]', lambda m: m[1].split(',')[1].strip(), text)
    return setup() + function('medicationToxicityFiredCommit', extended=True) + r'''
        private _configReads=0;
        private _configNumber={params ["_class","_field"];
            _configReads=_configReads+1;
            if (_field=="weightEffect") then {0} else {10}
        };
        private _kineticsReads=0;
        private _nativeCount=ace_medical_status_fnc_getMedicationCount;
        ace_medical_status_fnc_getMedicationCount={
            _kineticsReads=_kineticsReads+1;_this call _nativeCount
        };
        private _syndromes=[];
        ace_medical_status_fnc_addMedicationAdjustment={_syndromes pushBack +_this;};
        _patient setVariable ["ACME_medicationGenerations",createHashMapFromArray [["opioid",3],["ketamine",3],["Amiodarone_IV",3],["Penthrox",3]]];
        _patient setVariable ["ACME_medicationToxicityFired",createHashMapFromArray [["other",7]]];
    ''' + 'ACME_fnc_medicationToxicityTick={' + code(text) + '};'


def test_untreated_unconscious_casualty_does_no_config_or_kinetics_work():
    execute(fixture() + r'''
        _patient setVariable ["ACE_isUnconscious",true];
        private _before=str (_patient getVariable "ACME_medicationToxicityFired");
        for "_i" from 1 to 120 do {CBA_missionTime=100+_i;[_patient] call ACME_fnc_medicationToxicityTick;};
        [_configReads==0 && {_kineticsReads==0},"empty history performed toxicity lookups"] call _check;
        [count _syndromes==0 && {str (_patient getVariable "ACME_medicationToxicityFired")==_before},
            "historical generations created or consumed an exposure"] call _check;
    ''')


@pytest.mark.parametrize('drug,family,syndrome', [
    ('Morphine_IV', 'opioid', 'Overdose_Opioid'),
    ('Ketamine_IV', 'ketamine', 'Overdose_Ketamine'),
    ('Amiodarone_IV', 'Amiodarone_IV', 'Overdose_Amiodarone'),
    ('Penthrox', 'Penthrox', 'Overdose_Penthrox'),
])
def test_later_admission_preserves_onset_and_fires_current_generation_once(drug, family, syndrome):
    execute(fixture() + r'''
        [_patient] call ACME_fnc_medicationToxicityTick;
    ''' + f'''
        _patient setVariable ["ace_medical_medications",[["{drug}",2,1,"new",2,100] call _record]];
        [_patient] call ACME_fnc_medicationToxicityTick;
        [count _syndromes==0,"new dose skipped native onset"] call _check;
        CBA_missionTime=120;
        [_patient] call ACME_fnc_medicationToxicityTick;
        [count _syndromes==1 && {{((_syndromes select 0) select 1)=="{syndrome}"}},"later exposure failed family threshold"] call _check;
        [((_patient getVariable "ACME_medicationToxicityFired") get "{family}")==3,"wrong generation committed"] call _check;
        [_patient] call ACME_fnc_medicationToxicityTick;
        [count _syndromes==1,"same generation fired twice"] call _check;
        [(_patient getVariable "ACME_medicationToxicityFired") get "other"==7,"unrelated latch changed"] call _check;
    ''')
