"""Execute actual journal source-to-milligram proof for plain and mixed syringes.

Config concentrations and route policy are explicit boundaries. Production
source matching, component validation, aggregation and dose arithmetic execute.
"""
import pytest

from test_b209_narc_store_owner import function
from test_historical_vial_execution import setup as math_setup
from test_menu_death_lifecycle import execute


def setup():
    return math_setup() + function('syringeDeliveryDelta') + function('syringeDeliveryDoseValid') + r'''
        private _concentrations=createHashMapFromArray [["Ketamine",50],["Propofol",10],["EpinephrineCardiac",0.1],["Epinephrine",1]];
        _configNumber={params ["_source","_field"]; [_concentrations,[_source,0]] call _mapDefault};
        private _routes=[]; private _rejected=[];
        ACME_fnc_medicationRouteAllowed={_routes pushBack +_this; !((_this select 0) in _rejected)};
        private _row=["Ketamine",10,3,"label",2,[["Ketamine",1],["Propofol",2]],"compoundB13","none","","","","stable","barrel","inventoryB279"];
        private _delta=[0.75,0.5,[[0,"Ketamine",0.25],[1,"Propofol",0.5]]];
        private _doses=[["Ketamine_IV",12.5,true,"label",1,true,["hcPush",3,"session",750]],
            ["Propofol_IV",5,true,"label",1,true,["hcPush",3,"session",300]]];
        private _original=+_row; private _originalDelta=+_delta;
    '''


def test_compound_dose_matches_each_actual_source_and_preserves_inputs():
    execute(setup() + r'''
        [[_row,_delta,_doses] call ACME_fnc_syringeDeliveryDoseValid,"funded compound dose rejected"] call _check;
        [_row isEqualTo _original && {_delta isEqualTo _originalDelta},"dose validation mutated source evidence"] call _check;
        [_routes isEqualTo [["Ketamine_IV",true,true,true],["Propofol_IV",true,true,true]],"dose proof skipped route policy or changed prepared flag"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"dose proof wrote source inventory"] call _check;
    ''')


@pytest.mark.parametrize('iv', [True, False])
def test_plain_four_field_dose_uses_actual_source_concentration(iv):
    execute(setup() + f'private _iv={str(iv).lower()};' + r'''
        _row set [5,[]]; _row set [6,""];
        private _class=if (_iv) then {"Ketamine_IV"} else {"Ketamine"};
        [[_row,[0.25,0,[]],[[_class,12.5,_iv,"label"]]] call ACME_fnc_syringeDeliveryDoseValid,"plain route dose rejected"] call _check;
        [_routes isEqualTo [[_class,_iv,true,false]],"plain route policy received wrong preparation context"] call _check;
    ''')


@pytest.mark.parametrize('split_actual', [True, False])
def test_repeated_source_components_and_split_actual_doses_aggregate_once(split_actual):
    execute(setup() + f'private _splitActual={str(split_actual).lower()};' + r'''
        _row set [5,[["Ketamine",1],["Ketamine",2]]];
        private _slice=[0.75,0,[[0,"Ketamine",0.25],[1,"Ketamine",0.5]]];
        private _actual=if (_splitActual) then {[["Ketamine_IV",12.5,true,"a"],["Ketamine_IV",25,true,"b"]]} else {[["Ketamine_IV",37.5,true,"a"]]};
        [[_row,_slice,_actual] call ACME_fnc_syringeDeliveryDoseValid,"repeated source mass was dropped or counted twice"] call _check;
    ''')


@pytest.mark.parametrize('class_name,label', [
    ('Epinephrine_IV', 'B13_MEASURED_EPI'),
    ('EpinephrineCardiac_IV', 'B13_MEASURED_EPI'),
])
def test_measured_epinephrine_uses_cardiac_source_strength_for_both_delivery_workers(class_name, label):
    execute(setup() + f'private _class="{class_name}"; private _label="{label}";' + r'''
        _row set [0,"EpinephrineCardiac"]; _row set [2,1]; _row set [4,9];
        _row set [5,[]]; _row set [6,"epiMixB12"];
        [[_row,[0.1,0.9,[]],[[_class,0.01,true,_label,3]]] call ACME_fnc_syringeDeliveryDoseValid,"measured epinephrine lost cardiac-source concentration"] call _check;
        [!([_row,[0.1,0.9,[]],[[_class,0.1,true,_label,3]]] call ACME_fnc_syringeDeliveryDoseValid),"measured epinephrine used tenfold native concentration"] call _check;
    ''')


@pytest.mark.parametrize('mutation', [
    '_doses=[];', '_doses="invalid";', '_doses=[["Ketamine_IV",12.5,true]];',
    '_doses deleteAt 1;',
    '_doses pushBack ["Epinephrine_IV",1,true,"extra"];',
    '(_doses select 0) set [0,"EpinephrineCardiac_IV"];',
    '(_doses select 0) set [0,12];',
    '(_doses select 0) set [1,12.4];', '(_doses select 0) set [1,12.6];',
    '(_doses select 0) set [1,-1];', '(_doses select 0) set [1,0];',
    '(_doses select 0) set [1,"12.5"];',
    '(_doses select 0) set [2,1];', '(_doses select 0) set [3,true];',
    '(_doses select 0) set [4,0];', '(_doses select 0) set [4,-1];',
    '(_doses select 0) set [4,"1"];',
    '(_doses select 0) set [5,"true"];', '(_doses select 0) set [6,"metadata"];',
    '_rejected=["Propofol_IV"];',
    '_concentrations set ["Ketamine",0];', '_concentrations deleteAt "Ketamine";',
    '_row set [5,[["Ketamine",0.9],["Propofol",2]]];',
    '_delta=[0.75,0.5,[[0,"Ketamine",0.35],[1,"Propofol",0.5]]];',
    '_delta=[3.1,0,[[0,"Ketamine",1],[1,"Propofol",2.1]]];',
    '_row set [6,true];',
    '_doses=[nil];', '(_doses select 0) set [0,nil];',
    '(_doses select 0) set [1,nil];', '(_doses select 0) set [2,nil];',
    '(_doses select 0) set [3,nil];', '(_doses select 0) set [4,nil];',
    '(_doses select 0) set [5,nil];', '(_doses select 0) set [6,nil];',
])
def test_mismatched_missing_extra_or_malformed_dose_rejects_entire_batch(mutation):
    execute(setup() + mutation + r'''
        private _savedRow=str _row; private _savedDelta=str _delta; private _savedDoses=str _doses;
        [!([_row,_delta,_doses] call ACME_fnc_syringeDeliveryDoseValid),"unfunded or unsupported dose accepted"] call _check;
        [(str _row)==_savedRow && {(str _delta)==_savedDelta} && {(str _doses)==_savedDoses},"rejected dose changed evidence"] call _check;
    ''')


@pytest.mark.parametrize('kind,iv,label', [
    ('compoundB13', True, 'B13_MEASURED_EPI'),
    ('epiMixB12', False, 'B13_MEASURED_EPI'),
    ('epiMixB12', True, 'ordinary'),
])
def test_cardiac_to_native_epinephrine_alias_requires_exact_measured_recipe_context(kind, iv, label):
    execute(setup() + f'_row set [6,"{kind}"]; private _iv={str(iv).lower()}; private _label="{label}";' + r'''
        _row set [0,"EpinephrineCardiac"]; _row set [2,1]; _row set [4,9]; _row set [5,[]];
        [!([_row,[0.1,0.9,[]],[["Epinephrine_IV",0.01,_iv,_label]]] call ACME_fnc_syringeDeliveryDoseValid),"native epinephrine alias escaped measured recipe context"] call _check;
    ''')


@pytest.mark.parametrize('factor,accepted', [(1.000005, True), (1.00002, False), (0.99998, False)])
def test_mass_comparison_uses_small_relative_float_tolerance(factor, accepted):
    execute(setup() + f'(_doses select 0) set [1,12.5*{factor}];' +
            f'[([_row,_delta,_doses] call ACME_fnc_syringeDeliveryDoseValid) isEqualTo {str(accepted).lower()},"dose tolerance admitted a mismatch or rejected float noise"] call _check;')


@pytest.mark.parametrize('arguments', [
    '"invalid"', '[]', '[_row,_delta]', '[_row,_delta,_doses,true]',
    '[nil,_delta,_doses]', '[_row,nil,_doses]', '[_row,_delta,nil]',
])
def test_invalid_call_shape_fails_closed(arguments):
    execute(setup() + f'[!({arguments} call ACME_fnc_syringeDeliveryDoseValid),"invalid call shape accepted"] call _check;')
