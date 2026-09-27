# Timed normal push owns dosing-relevant syringe contents captured at confirmation.
import pytest
from test_bounded_normal_push_lifetime import setup
from test_menu_death_lifecycle import execute

MUTATIONS={
    "med": '_r set [0,"Propofol"];',
    "size": '_r set [1,5];',
    "drug_ml": '_r set [2,1.5];',
    "diluent_ml": '_r set [4,0.5];',
    "components": '_r set [5,[["Ketamine",1],["Propofol",1]]];',
    "recipe": '_r set [6,"dilutionB13"];',
}

@pytest.mark.parametrize("boundary",["settle","complete"])
@pytest.mark.parametrize("mutation",list(MUTATIONS))
def test_same_id_changed_dose_content_cannot_complete_old_push(boundary,mutation):
    execute(setup()+'''[call ACME_fnc_skConfirmInjection,"start failed"] call _check;'''+
        ('0 call _runWait;' if boundary=="complete" else '')+'''
        private _s=+(_medic getVariable ["ACME_narcStore",[]]);
        private _r=+(_s select 0);
    '''+MUTATIONS[mutation]+'''
        _s set [0,_r]; [_medic,_s] call ACME_fnc_narcStoreCommit;
    '''+f'''{1 if boundary=="complete" else 0} call _runWait;
        [count _delivered==0,"changed contents were administered by old push"] call _check;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo [],"changed-content job did not retire"] call _check;
    ''')

@pytest.mark.parametrize("boundary",["settle","complete"])
def test_cosmetic_label_change_does_not_cancel_confirmed_dose(boundary):
    execute(setup()+'''call ACME_fnc_skConfirmInjection;'''+
        ('0 call _runWait;' if boundary=="complete" else '')+'''
        private _s=+(_medic getVariable ["ACME_narcStore",[]]);
        private _r=+(_s select 0); _r set [3,"renamed label"]; _s set [0,_r];
        [_medic,_s] call ACME_fnc_narcStoreCommit;
    '''+f'''{1 if boundary=="complete" else 0} call _runWait;
    '''+('''
        [count _delivered==0 && {count _waits==2},"settle did not continue after cosmetic change"] call _check;
        1 call _runWait;
    ''' if boundary=="settle" else '')+'''
        [count _delivered==1,"cosmetic label incorrectly cancelled dose"] call _check;
    ''')
