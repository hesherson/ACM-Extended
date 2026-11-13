"""Execute the actual visual swap with native allocation/deletion represented explicitly."""
import pytest
from test_b288_clinical_persistence import ref_setup
from test_b308_patient_equipment import raw
from test_menu_death_lifecycle import adapt, execute
from test_historical_vial_execution import map_defaults


def setup():
    s=raw('equipmentVent')
    s=s.replace('createVehicle [_class,ASLToAGL (_pose select 0),[],0,"CAN_COLLIDE"]','[_class] call _spawn')
    s=s.replace('deleteVehicle _old','_deleted pushBack _old')
    s=s.replace('_o setVectorDirAndUp [vectorDir _old,vectorUp _old]', '_o setVariable ["fixtureOrientation",_old getVariable "fixtureOrientation"]')
    s=s.replace('_o setPosWorld getPosWorld _old', '_o setVariable ["fixturePosition",_old getVariable "fixturePosition"]')
    s=s.replace('_o hideObjectGlobal (!isNull objectParent _patient)','_o setVariable ["fixtureHidden",_mounted]')
    return ref_setup()+'''
      private _old=parsingNamespace;private _new=missionNamespace;
      private _deleted=[];private _spawns=[];private _fail=false;private _poseFail=false;private _mounted=false;
      private _spawn={params ["_class"];_spawns pushBack _class;if (_fail) exitWith {objNull};_new};
      ACME_fnc_equipmentPose={if (_poseFail) then {[]} else {[[1,2,3],[0,1,0]]}};
      ACME_fnc_equipmentSeat={};
      ["bind",_old,"vent-A"] call ACME_fnc_clinicalObjectRef;
      _old setVariable ["fixtureOrientation",[[1,0,0],[0,0,1]]];
      _old setVariable ["fixturePosition",[123,456,850]];
      _patient setVariable ["ACME_eq_vent",_old];
      missionNamespace setVariable ["ACME_eqWorldImport",[[1,[["vent-A"]]],[_old]]];
    '''+'ACME_fnc_equipmentVent={'+adapt(map_defaults(s))+'};'


@pytest.mark.parametrize('change',['_fail=true;','_poseFail=true;'])
def test_failed_replacement_keeps_old_object_binding_and_import_evidence(change):
    execute(setup()+change+'''
      [_patient,true] call ACME_fnc_equipmentVent;
      [count _deleted==0,"failed swap deleted existing prop"] call _check;
      [(_patient getVariable "ACME_eq_vent") isEqualTo _old,"failed swap changed patient slot"] call _check;
      [((missionNamespace getVariable "ACME_clinicalObjectBindings") get "vent-A") isEqualTo _old,"failed swap lost durable identity"] call _check;
      [((missionNamespace getVariable "ACME_eqWorldImport") select 1) isEqualTo [_old],"failed swap retired import evidence"] call _check;
    ''')


@pytest.mark.parametrize('oxygen',[False,True])
def test_successful_swap_moves_binding_and_replay_journal_to_correct_model(oxygen):
    execute(setup()+f'''
      _patient setVariable ["ACME_vent_o2Session",{"'supply-A'" if oxygen else "''"}];
      [_patient,true] call ACME_fnc_equipmentVent;
      [count _deleted==1 && {{count _spawns==1}},"swap did not replace exactly once"] call _check;
      [_spawns isEqualTo ["{'ACME_VentwaySparrow_O2Circuit' if oxygen else 'ACME_VentwaySparrow_Circuit'}"],"wrong circuit model"] call _check;
      [((missionNamespace getVariable "ACME_clinicalObjectBindings") get "vent-A") isEqualTo _new,"durable ID stayed on retired prop"] call _check;
      [((missionNamespace getVariable "ACME_eqWorldImport") select 1) isEqualTo [_new],"replay journal lost replacement"] call _check;
      [(_patient getVariable "ACME_eq_vent") isEqualTo _new,"patient slot did not move"] call _check;
      [(_new getVariable "fixturePosition") isEqualTo [123,456,850],"swap moved deployed device"] call _check;
      [(_new getVariable "fixtureOrientation") isEqualTo [[1,0,0],[0,0,1]],"swap discarded player rotation"] call _check;
    ''')


def test_duplicate_ordinary_enrollment_keeps_existing_world_representation():
    execute(setup()+'''
      [_patient] call ACME_fnc_equipmentVent;
      [count _spawns==0 && {count _deleted==0},"duplicate enrollment replaced existing vent"] call _check;
    ''')
