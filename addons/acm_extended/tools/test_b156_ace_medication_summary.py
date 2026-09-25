"""Execute the ACE summary bridge against the actual fork medication readers."""
import pytest

from test_historical_medication_effects import function, setup
from test_menu_death_lifecycle import execute


def summary_setup():
    return setup() + function("getAllMedicationCount", "core", override=True) + """
        ace_medical_status_fnc_getAllMedicationCount=ACM_core_fnc_getAllMedicationCount;
    """


@pytest.mark.parametrize("raw", [False, True])
def test_empty_summary_keeps_native_array_contract(raw):
    execute(summary_setup() + f"""
        private _result=[_patient,{str(raw).lower()}] call ace_medical_status_fnc_getAllMedicationCount;
        [_result isEqualTo [],"empty medication summary must be an empty array"] call _check;
    """)


@pytest.mark.parametrize("raw, expected", [(False, 2), (True, 2.5)])
def test_duplicate_classes_sum_concentration_and_forward_effect_mode(raw, expected):
    execute(summary_setup() + """
        _patient setVariable ["ace_medical_medications",[
            ["Foreign_Drug",.5,1,"new",2,100] call _record,
            ["Other_Drug",.75,0,"other",3,80] call _record,
            ["Foreign_Drug",2,1,"old",2,80] call _record
        ]];
        private _before=+(_patient getVariable ["ace_medical_medications",[]]);
    """ + f"""
        private _result=[_patient,{str(raw).lower()}] call ace_medical_status_fnc_getAllMedicationCount;
        [count _result==2,"duplicate class emitted more than one summary row"] call _check;
        [(_result select 0) isEqualTo ["Foreign_Drug",2.5,{expected}],"dose, onset, mode or first-seen order changed"] call _check;
        [(_result select 1) isEqualTo ["Other_Drug",.75,.75],"administration route was mistaken for dose"] call _check;
        [(_patient getVariable ["ace_medical_medications",[]]) isEqualTo _before,"summary mutated medication records"] call _check;
    """)


@pytest.mark.parametrize("raw, expected", [(False, 1), (True, 2)])
def test_bound_medication_keeps_recorded_dose_separate_from_effect(raw, expected):
    execute(summary_setup() + """
        _patient setVariable ["ace_medical_medications",[["Rocuronium_IV",2,1,"roc"] call _record]];
        _patient setVariable ["ACME_sug_bindings",[["roc",1]]];
    """ + f"""
        private _result=[_patient,{str(raw).lower()}] call ace_medical_status_fnc_getAllMedicationCount;
        [_result isEqualTo [["Rocuronium_IV",2,{expected}]],"bound effect replaced recorded dose or effect mode was ignored"] call _check;
    """)


def test_default_mode_keeps_undecayed_dose_separate_from_decaying_count():
    execute(summary_setup() + """
        _patient setVariable ["ace_medical_medications",[["Foreign_Drug",1.4,1,"old",2,50] call _record]];
        private _result=[_patient] call ace_medical_status_fnc_getAllMedicationCount;
        private _row=_result select 0;
        [abs ((_row select 1)-1.4)<.000001,"recorded dose decayed with effective count"] call _check;
        [abs ((_row select 2)-1)<.000001,"default mode did not use the native decaying count"] call _check;
        [_result isEqualTo ([_patient,true] call ace_medical_status_fnc_getAllMedicationCount),"default mode differs from true"] call _check;
    """)
