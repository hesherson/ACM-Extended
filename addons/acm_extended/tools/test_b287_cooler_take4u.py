"""Execute 4U overload transfers against exact native cargo readback boundaries."""
import re

import pytest

from test_b287_cooler_timing import fixture as timing_fixture
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import adapt, execute, read


def source(name):
    code=read(name)
    code=code.replace('local _owner','(_owner getVariable ["fixtureLocal",true])')
    code=code.replace('alive _owner','(_owner getVariable ["fixtureAlive",true])')
    code=code.replace('objectParent _x','(_x getVariable ["fixtureParent",objNull])')
    code=code.replace('_x isKindOf "CAManBase"','(_x getVariable ["fixtureMan",false])')
    code=code.replace('objectParent _source','(_source getVariable ["fixtureParent",objNull])')
    code=code.replace('_source isKindOf "CAManBase"','(_source getVariable ["fixtureMan",false])')
    code=code.replace('_parent isKindOf "CAManBase"','(_parent getVariable ["fixtureMan",false])')
    code=code.replace('_owner distance _source','_distance')
    code=code.replace('backpackContainer _owner','_worn')
    code=code.replace('vestContainer _owner','objNull').replace('uniformContainer _owner','objNull')
    code=code.replace('magazinesAmmoCargo _container','(_container getVariable ["fixtureMags",[]])')
    code=code.replace('magazinesAmmoCargo _source','(_source getVariable ["fixtureMags",[]])')
    code=code.replace('itemCargo _container','(_container getVariable ["fixtureItems",[]])')
    code=code.replace('itemCargo _source','(_source getVariable ["fixtureItems",[]])')
    code=code.replace('_container addMagazineAmmoCargo [_class,_amount,_token];','[_container,_class,_amount,_token] call _magAdjust;')
    code=code.replace('_container addItemCargoGlobal [_class,_amount];','[_container,_class,_amount] call _itemAdjust;')
    code=re.sub(r'nearestObjects \[_owner,\[[^\n]+\],6\]', '_nearby', code)
    code=re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', code)
    return map_defaults(adapt(code))


def fixture():
    return timing_fixture()+r'''
        private _owner=uiNamespace;
        private _source=profileNamespace;
        private _destination=missionNamespace;
        private _worn=_destination;
        private _nearby=[_source];
        private _removeWorks=true;private _placeWorks=true;private _rollbackWorks=true;
        private _calls=[];
        private _class="ACME_CoolerCarrier_CSWB4U";
        private _base="ACME_BloodCooler_CSWB4U";
        private _token=9;
        _owner setVariable ["fixtureAlive",true];
        _owner setVariable ["fixtureLocal",true];
        _owner setVariable ["ACME_equipmentKitEpoch",0];
        _owner setVariable ["ACME_providerLocalityEpoch",0];
        _source setVariable ["fixtureParent",objNull];_source setVariable ["fixtureMan",false];
        _source setVariable ["fixtureMags",[[_class,_token]]];_source setVariable ["fixtureItems",[]];
        _source setVariable ["ACME_coolerTake4UClaims",createHashMap];
        _destination setVariable ["fixtureMags",[]];_destination setVariable ["fixtureItems",[]];
        private _state=[_base,0,[["ACM_BloodBag_ON_500",700]],100];
        private _record=["cooler","cooler-four",["cooler-four",_state],objNull,"","held",0,createHashMap,_class];
        missionNamespace setVariable ["ACME_inventoryToken_9",_record];
        missionNamespace setVariable ["ACME_coolerTake4UReceipts",createHashMap];
        private _magAdjust={params ["_container","_class","_amount","_token"];
            _calls pushBack [_container,_class,_amount,_token];
            if (_amount<0 && {!_removeWorks}) exitWith {};
            if (_amount>0 && {_container isEqualTo _destination} && {!_placeWorks}) exitWith {};
            if (_amount>0 && {_container isEqualTo _source} && {!_rollbackWorks}) exitWith {};
            private _cargo=+(_container getVariable ["fixtureMags",[]]);
            if (_amount<0) then {private _at=_cargo find [_class,_token];if (_at>=0) then {_cargo deleteAt _at;};}
            else {_cargo pushBack [_class,_token];};
            _container setVariable ["fixtureMags",_cargo];
        };
        private _itemAdjust={params ["_container","_class","_amount"];
            _calls pushBack [_container,_class,_amount];
            if (_amount<0 && {!_removeWorks}) exitWith {};
            if (_amount>0 && {_container isEqualTo _destination} && {!_placeWorks}) exitWith {};
            if (_amount>0 && {_container isEqualTo _source} && {!_rollbackWorks}) exitWith {};
            private _cargo=+(_container getVariable ["fixtureItems",[]]);
            if (_amount<0) then {private _at=_cargo find _class;if (_at>=0) then {_cargo deleteAt _at;};}
            else {_cargo pushBack _class;};
            _container setVariable ["fixtureItems",_cargo];
        };
    '''+'ACME_fnc_coolerFind4U={'+source('coolerFind4U')+'};'+\
      'ACME_fnc_coolerTake4UBroker={'+source('coolerTake4UBroker')+'};'+r'''
        private _args=[_owner,_source,_class,_token,"request-one",0,0,_destination];
    '''


def test_find_identified_native_carrier_and_reject_unavailable_or_worn_source():
    execute(fixture()+r'''
        [([_owner] call ACME_fnc_coolerFind4U) isEqualTo [_source,_class,_token],"native 4U not found"] call _check;
        _record set [5,"reserved"];
        [([_owner] call ACME_fnc_coolerFind4U) isEqualTo [],"reserved cooler offered"] call _check;
        _record set [5,"held"];
        _source setVariable ["fixtureMan",true];
        [([_owner] call ACME_fnc_coolerFind4U) isEqualTo [],"another person offered as cargo"] call _check;
        _source setVariable ["fixtureMan",false];
        _owner setVariable ["fixtureMan",true];_source setVariable ["fixtureParent",_owner];
        [([_owner] call ACME_fnc_coolerFind4U) isEqualTo [],"worn personal container offered"] call _check;
    ''')


def test_native_transfer_preserves_identity_payload_other_cargo_and_replay():
    execute(fixture()+r'''
        private _unchanged=str _record;
        _source setVariable ["fixtureMags",[[_class,_token],["OtherMagazine",17]]];
        _source setVariable ["fixtureItems",["OtherItem"]];
        _args call ACME_fnc_coolerTake4UBroker;
        [(_source getVariable "fixtureMags") isEqualTo [["OtherMagazine",17]],"wrong native source removed"] call _check;
        [(_destination getVariable "fixtureMags") isEqualTo [[_class,_token]],"exact token not placed"] call _check;
        [str _record==_unchanged && {(_source getVariable "fixtureItems") isEqualTo ["OtherItem"]},"payload or other cargo changed"] call _check;
        private _nativeCalls=count _calls;
        _args call ACME_fnc_coolerTake4UBroker;
        [count _calls==_nativeCalls,"replayed successful request repeated native operations"] call _check;
        [count (_source getVariable "ACME_coolerTake4UClaims")==0,"success left source save fence"] call _check;
    ''')


def test_public_base_transfer_and_replay_move_only_one_item():
    execute(fixture()+r'''
        _class=_base;_token=0;_args set [2,_class];_args set [3,0];
        _source setVariable ["fixtureMags",[]];_source setVariable ["fixtureItems",[_base,_base,"OtherItem"]];
        _args call ACME_fnc_coolerTake4UBroker;_args call ACME_fnc_coolerTake4UBroker;
        [(_source getVariable "fixtureItems") isEqualTo [_base,"OtherItem"],"base source debit repeated or removed other cargo"] call _check;
        [(_destination getVariable "fixtureItems") isEqualTo [_base],"base source not placed once"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_record set [5,"reserved"];',
    '_record set [5,"packing"];',
    '_record set [5,"spent"];',
    '_record set [0,"prepared"];',
    '_record set [8,"WrongClass"];',
    '_source setVariable ["fixtureMags",[]];',
    '_source setVariable ["fixtureMan",true];',
    '_owner setVariable ["fixtureMan",true];_source setVariable ["fixtureParent",_owner];',
    '_owner setVariable ["fixtureAlive",false];',
    '_owner setVariable ["ACME_equipmentKitEpoch",1];',
    '_owner setVariable ["ACME_providerLocalityEpoch",1];',
    '_worn=objNull;',
    '_distance=7;',
])
def test_invalid_source_or_admission_never_touches_native_cargo(change):
    execute(fixture()+change+r'''
        _args call ACME_fnc_coolerTake4UBroker;
        [count _calls==0 && {(_destination getVariable "fixtureMags") isEqualTo []},"invalid pickup mutated cargo"] call _check;
        [count (_source getVariable "ACME_coolerTake4UClaims")==0,"rejected pickup left source save fence"] call _check;
    ''')


def test_failed_source_debit_does_not_place_or_leave_source_claim():
    execute(fixture()+r'''
        _removeWorks=false;_args call ACME_fnc_coolerTake4UBroker;
        [(_source getVariable "fixtureMags") isEqualTo [[_class,_token]] && {(_destination getVariable "fixtureMags") isEqualTo []},"failed debit funded a destination"] call _check;
        [count (_source getVariable "ACME_coolerTake4UClaims")==0,"failed debit left source save fence"] call _check;
    ''')


def test_failed_placement_restores_source_and_replay_does_not_remint():
    execute(fixture()+r'''
        _placeWorks=false;_args call ACME_fnc_coolerTake4UBroker;
        [(_source getVariable "fixtureMags") isEqualTo [[_class,_token]] && {(_destination getVariable "fixtureMags") isEqualTo []},"failed placement lost source"] call _check;
        private _nativeCalls=count _calls;
        _placeWorks=true;_args call ACME_fnc_coolerTake4UBroker;
        [count _calls==_nativeCalls,"terminal rollback replay reminted a carrier"] call _check;
        [count (_source getVariable "ACME_coolerTake4UClaims")==0,"successful rollback left source save fence"] call _check;
    ''')


def test_failed_placement_and_rollback_hold_one_funding_receipt_for_retry():
    execute(fixture()+r'''
        _placeWorks=false;_rollbackWorks=false;_args call ACME_fnc_coolerTake4UBroker;
        [(_source getVariable "fixtureMags") isEqualTo [] && {(_destination getVariable "fixtureMags") isEqualTo []},"fault fixture unexpectedly placed token"] call _check;
        private _receipts=missionNamespace getVariable "ACME_coolerTake4UReceipts";
        [((_receipts get "request-one") select 1)=="held","failed rollback discarded funded custody"] call _check;
        [count (_source getVariable "ACME_coolerTake4UClaims")==1,"retained escrow allowed source save"] call _check;
        _placeWorks=true;_args call ACME_fnc_coolerTake4UBroker;
        [(_source getVariable "fixtureMags") isEqualTo [] && {(_destination getVariable "fixtureMags") isEqualTo [[_class,_token]]},"funded retry failed or debited source again"] call _check;
        [count (_source getVariable "ACME_coolerTake4UClaims")==0,"completed retry left source save fence"] call _check;
        [({_x select 2<0} count _calls)==1,"funded retry repeated original source debit"] call _check;
    ''')


def test_same_request_cannot_be_rebound_to_other_source_or_epoch():
    execute(fixture()+r'''
        _placeWorks=false;_rollbackWorks=false;_args call ACME_fnc_coolerTake4UBroker;
        private _before=count _calls;
        private _changed=+_args;_changed set [5,99];
        _changed call ACME_fnc_coolerTake4UBroker;
        [count _calls==_before,"existing request accepted changed immutable admission"] call _check;
    ''')
