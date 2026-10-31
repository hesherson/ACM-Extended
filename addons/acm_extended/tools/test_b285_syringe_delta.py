"""Execute production syringe journal arithmetic without inventory/network writes.

The established B209 loader preserves real SQF branching, copies and arithmetic;
its finite-number adapter is the shared SQF-VM math boundary.
"""
import pytest

from test_b209_narc_store_owner import function
from test_historical_vial_execution import setup as math_setup
from test_menu_death_lifecycle import execute


def setup():
    return math_setup() + function('syringeDeliveryDelta') + r'''
        private _row=["compound",10,3,"label",2,[["Ketamine",1],["Propofol",2]],
            "compoundB13","none","metadata",["nested",1],"tag","stable-source","barrel","inventoryB279"];
        private _original=+_row;
        private _delta=[0.75,0.5,[[1,"Propofol",0.5],[0,"Ketamine",0.25]]];
    '''


def test_subtract_restore_conserves_every_component_and_source_metadata():
    execute(setup() + r'''
        private _left=[_row,_delta] call ACME_fnc_syringeDeliveryDelta;
        [count _left==14 && {(_left select 2)==2.25} && {(_left select 4)==1.5},"journal subtraction changed total volume"] call _check;
        [(_left select 5) isEqualTo [["Ketamine",0.75],["Propofol",1.5]],"journal subtraction changed component identity or amount"] call _check;
        [(_left select [6,8]) isEqualTo (_row select [6,8]),"journal arithmetic changed source metadata"] call _check;
        private _restored=[_left,_delta,true] call ACME_fnc_syringeDeliveryDelta;
        [_restored isEqualTo _original && {_row isEqualTo _original},"round-trip lost solution or mutated original row"] call _check;
        private _leftParts=_left select 5;
        (_leftParts select 0) set [1,0];
        [_row isEqualTo _original && {_restored isEqualTo _original},"returned components alias another row"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"pure arithmetic wrote provider supplies"] call _check;
    ''')


@pytest.mark.parametrize('size', [1, 3, 5, 10])
def test_plain_syringe_empty_endpoint_and_zero_delta_are_valid(size):
    execute(setup() + f'private _size={size};' + r'''
        private _plain=["Ketamine",_size,_size,"label",0,[],"","",[],"","","plain-id"];
        private _zero=[_plain,[0,0,[]]] call ACME_fnc_syringeDeliveryDelta;
        [_zero isEqualTo _plain,"zero delta changed ordinary syringe"] call _check;
        private _empty=[_plain,[_size,0,[]]] call ACME_fnc_syringeDeliveryDelta;
        [count _empty==12 && {(_empty select 2)==0} && {(_empty select 5) isEqualTo []},"empty endpoint was rejected or created components"] call _check;
        private _full=[_empty,[_size,0,[]],true] call ACME_fnc_syringeDeliveryDelta;
        [_full isEqualTo _plain && {(_plain select 2)==_size},"plain restore failed or source changed"] call _check;
    ''')


def test_compound_zero_endpoint_keeps_zero_components_and_accepts_zero_delta():
    execute(setup() + r'''
        private _empty=[_row,[3,2,[[0,"Ketamine",1],[1,"Propofol",2]]]] call ACME_fnc_syringeDeliveryDelta;
        [(_empty select 2)==0 && {(_empty select 4)==0} && {(_empty select 5) isEqualTo [["Ketamine",0],["Propofol",0]]},"compound empty endpoint changed identities"] call _check;
        private _same=[_empty,[0,0,[]]] call ACME_fnc_syringeDeliveryDelta;
        [_same isEqualTo _empty,"zero delta rejected zero-valued component rows"] call _check;
    ''')


@pytest.mark.parametrize('mutation', [
    '_row="not a row";', '_row=[];', '_row resize 5;',
    '_row set [1,"10"];', '_row set [1,2];', '_row set [1,-1];',
    '_row set [2,"3"];', '_row set [2,-0.01];', '_row set [2,true];',
    '_row set [4,"2"];', '_row set [4,-0.01];', '_row set [4,8];',
    '_row set [5,"parts"];', '_row set [5,[["Ketamine",3,"extra"]]];',
    '_row set [5,[["",3]]];', '_row set [5,[[true,3]]];',
    '_row set [5,[["Ketamine","3"]]];', '_row set [5,[["Ketamine",-1]]];',
    '_row set [5,[["Ketamine",2.9]]];',
    '_delta="not a delta";', '_delta=[];', '_delta=[0.75,0.5,[],"extra"];',
    '_delta set [0,"0.75"];', '_delta set [0,-0.01];', '_delta set [0,true];',
    '_delta set [1,"0.5"];', '_delta set [1,-0.01];', '_delta set [1,[]];',
    '_delta set [2,"parts"];', '_delta set [2,[[0,"Ketamine"]]];',
    '_delta set [2,[[0,"Ketamine",0.75,"extra"]]];',
    '_delta set [2,[["0","Ketamine",0.75]]];',
    '_delta set [2,[[0.5,"Ketamine",0.75]]];',
    '_delta set [2,[[-1,"Ketamine",0.75]]];',
    '_delta set [2,[[2,"Ketamine",0.75]]];',
    '_delta set [2,[[0,"",0.75]]];', '_delta set [2,[[0,true,0.75]]];',
    '_delta set [2,[[0,"Fentanyl",0.75]]];',
    '_delta set [2,[[0,"Ketamine","0.75"]]];',
    '_delta set [2,[[0,"Ketamine",-0.75]]];',
    '_delta set [2,[[0,"Ketamine",0.25],[0,"Ketamine",0.5]]];',
    '_delta set [2,[[0,"Ketamine",0.7]]];',
    '_delta=[1.25,0,[[0,"Ketamine",1.25]]];',
    '_delta=[3.5,0,[[0,"Ketamine",1],[1,"Propofol",2.5]]];',
    '_delta set [1,2.01];',
    '_row set [5,[]]; _delta=[0,0,[[0,"Ketamine",0]]];',
    '_row set [2,nil];', '_row set [4,nil];', '_row set [5,nil];',
    '_row set [5,[nil]];', '_row set [5,[[nil,3]]];', '_row set [5,[["Ketamine",nil]]];',
    '_delta=[nil,0,[]];', '_delta=[0,nil,[]];', '_delta=[0,0,nil];',
    '_delta=[0,0,[nil]];', '_delta=[0,0,[[nil,"Ketamine",0]]];',
    '_delta=[0,0,[[0,nil,0]]];', '_delta=[0,0,[[0,"Ketamine",nil]]];',
])
def test_invalid_input_rejects_whole_delta_without_writes(mutation):
    execute(setup() + mutation + r'''
        private _savedRow=str _row; private _savedDelta=str _delta;
        private _result=[_row,_delta] call ACME_fnc_syringeDeliveryDelta;
        [_result isEqualTo [],"malformed or overdrawn syringe accepted"] call _check;
        [(str _row)==_savedRow && {(str _delta)==_savedDelta},"rejected arithmetic mutated evidence"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"invalid delta wrote supplies"] call _check;
    ''')


@pytest.mark.parametrize('arguments', [
    '"invalid"', '[]', '[_row]', '[_row,_delta,false,"extra"]',
    '[_row,_delta,"false"]', '[_row,_delta,0]',
    '[nil,_delta]', '[_row,nil]', '[_row,_delta,nil]',
])
def test_invalid_call_shape_or_restore_type_cannot_default_into_valid_work(arguments):
    execute(setup() + f'private _result={arguments} call ACME_fnc_syringeDeliveryDelta;' + r'''
        [_result isEqualTo [] && {_row isEqualTo _original},"invalid call shape became valid syringe work"] call _check;
    ''')


def test_restore_rejects_over_capacity_and_cannot_mask_a_corrupt_current_component_sum():
    execute(setup() + r'''
        private _tooMuch=[_row,[4,2,[[0,"Ketamine",2],[1,"Propofol",2]]],true] call ACME_fnc_syringeDeliveryDelta;
        [_tooMuch isEqualTo [],"restore exceeded barrel capacity"] call _check;
        _row set [5,[["Ketamine",0.9],["Propofol",2]]];
        private _masked=[_row,[0.75,0.5,[[0,"Ketamine",0.35],[1,"Propofol",0.5]]],true] call ACME_fnc_syringeDeliveryDelta;
        [_masked isEqualTo [],"opposite malformed component totals cancelled into valid work"] call _check;
    ''')
