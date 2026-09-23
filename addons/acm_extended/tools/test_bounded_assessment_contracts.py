"""EMMA identity and debug component contracts, without changing runtime.

Actual EMMA functions and the actual debug row-building block execute in SQF-VM.
Object/UI/vehicle/inventory boundaries are explicit fixtures, not a live Arma test.
"""
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_bounded_pressure_contracts import has


def assert_emma_identity_contract():
    has(read('emmaCanAttachIGel'), '_patient getVariable ["ACME_emma_igelAttached",false]')
    has(read('emmaAttachIGel'), '[_patient,true,CBA_missionTime,getPlayerUID _medic,[_medic,false,true] call ace_common_fnc_getName] call ACME_fnc_emmaIGelStateCommit;')
    has(read('emmaRemoveIGel'), '[_patient,false] call ACME_fnc_emmaIGelStateCommit;')
    has(read('emmaTick'), '_lastContact getVariable ["ACME_emma_igelAttached",false]')
    commit = read('emmaIGelStateCommit')
    for key in ('ACME_emma_igelAttached','ACME_emma_igelAttachedTime','ACME_emma_igelAttachedByUID','ACME_emma_igelAttachedByName'):
        has(commit, '_patient setVariable ["' + key + '",')


def debug_rows():
    text = read('debugMenuClinical')
    start = text.index('([_patient] call ACME_fnc_sedationComponents) params')
    return text[start:text.index('private _szState',start)]


def assert_debug_component_contract():
    has(read('debugMenu'), 'call ACME_fnc_debugMenuClinical;')
    rows = debug_rows()
    has(rows, '([_patient] call ACME_fnc_sedationComponents) params ["_ket","_prop","_mid","_fent","_adjunct","_sed"];')
    has(rows, '["Ket",_ket toFixed 2,_cLabel,"Prop",_prop toFixed 2,_cLabel] call _pair')
    has(rows, '["Mid",_mid toFixed 2,_cLabel,"Fent",_fent toFixed 2,_cLabel] call _pair')


def emma_setup():
    code = '''
        private _isMan = true; private _aboard = false; private _sameVehicleBoundary = false;
        private _inventory = 1; private _hudClears = 0;
        ace_common_fnc_getCountOfItem = {_inventory};
        BIS_fnc_rscLayer = {0};
    '''
    for name in ('emmaAirwayKind','emmaCanAttachIGel','emmaIGelStateCommit','emmaMarkContact','emmaAttachIGel','emmaRemoveIGel'):
        source = read(name)
        for old,new in [
            ('_patient isKindOf "CAManBase"','_isMan'),
            ('_medic isKindOf "CAManBase"','true'),
            ('(vehicle _medic != _medic)','_aboard'),
            ('(vehicle _medic) isEqualTo (vehicle _patient)','_sameVehicleBoundary'),
            ('getPlayerUID _medic','"provider-uid"'),
            ('["ACE_player", player]','["ACE_player", ACE_player]'),
            ('_layer cutText ["", "PLAIN"];','_hudClears = _hudClears + 1;'),
        ]:
            source = source.replace(old,new)
        code += 'ACME_fnc_' + name + ' = {' + adapt(source) + '};\n'
    return code


@pytest.mark.parametrize('airway',['ett','igel'])
@pytest.mark.parametrize('patient_alive',[False,True])
@pytest.mark.parametrize('from_bvm',[False,True])
def test_emma_attach_and_detach_preserve_identity_and_provider_bvm(airway, patient_alive, from_bvm):
    state = '_patient setVariable ["ACME_ETT_Inserted",true];' if airway == 'ett' else '_patient setVariable ["ACM_airway_AirwayItem_Oral","SGA"];'
    execute(emma_setup() + state + f'''
        _patientAlive = {str(patient_alive).lower()};
        _medic setVariable ["ACME_emma_bvmAttached",{str(from_bvm).lower()}];
        [_medic,_patient,"head","{airway}"] call ACME_fnc_emmaAttachIGel;
        [_patient getVariable ["ACME_emma_igelAttached",false],"attachment lost"] call _check;
        [(_patient getVariable ["ACME_emma_igelAttachedTime",-1]) == 10,"attachment time lost"] call _check;
        [(_patient getVariable ["ACME_emma_igelAttachedByUID",""]) == "provider-uid","provider identity lost"] call _check;
        [(_patient getVariable ["ACME_emma_igelAttachedByName",""]) == "Provider","provider name lost"] call _check;
        [(_medic getVariable ["ACME_emma_lastContactPatient",objNull]) isEqualTo _patient,"contact route lost"] call _check;
        [!(_medic getVariable ["ACME_emma_bvmAttached",true]),"old BVM route survived transfer"] call _check;
        // A later own-BVM route must not be detached by removal of the patient-side route.
        _medic setVariable ["ACME_emma_bvmAttached",true];
        [_medic,_patient] call ACME_fnc_emmaRemoveIGel;
        [!(_patient getVariable ["ACME_emma_igelAttached",true]),"detach left attachment"] call _check;
        {{[isNil {{_patient getVariable _x}},"detach kept identity: " + _x] call _check;}}
            forEach ["ACME_emma_igelAttachedTime","ACME_emma_igelAttachedByUID","ACME_emma_igelAttachedByName"];
        [_medic getVariable ["ACME_emma_bvmAttached",false],"detach erased own BVM route"] call _check;
        [_inventory == 1,"device inventory unexpectedly consumed"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_isMan=false;',
    '_patient setVariable ["ACME_ETT_Inserted",false];',
    '_inventory=0;', '_distance=5.01;',
    'missionNamespace setVariable ["ACME_sys_emma",false];',
])
def test_rejected_emma_attachment_does_not_write_identity_or_move_provider_route(change):
    execute(emma_setup() + '''
        _patient setVariable ["ACME_ETT_Inserted",true];
        _medic setVariable ["ACME_emma_route","sentinel"];
    ''' + change + '''
        [_medic,_patient,"head","ett"] call ACME_fnc_emmaAttachIGel;
        [isNil {_patient getVariable "ACME_emma_igelAttached"},"rejected attach wrote identity"] call _check;
        [(_medic getVariable ["ACME_emma_route",""]) == "sentinel","rejected attach changed provider route"] call _check;
    ''')


@pytest.mark.parametrize('distance,aboard,same,expected',[(5,False,False,True),(5.01,False,False,False),(100,True,True,True),(100,True,False,False)])
def test_emma_range_and_same_vehicle_boundary(distance,aboard,same,expected):
    execute(emma_setup() + f'''
        _patient setVariable ["ACME_ETT_Inserted",true];
        _distance={distance}; _aboard={str(aboard).lower()}; _sameVehicleBoundary={str(same).lower()};
        [([_medic,_patient,"ett"] call ACME_fnc_emmaCanAttachIGel) isEqualTo {str(expected).lower()},"wrong EMMA eligibility"] call _check;
    ''')


@pytest.mark.parametrize('values',[[0,0,0,0,1,0],[.3,.7,.2,.9,1.2,1.5],[0,0,0,1,1.35,0],[2,0,0,0,1,2]])
def test_clinical_debug_keeps_each_normalized_component_in_its_own_column(values):
    execute('''
        private _right=[]; private _cLabel="label"; private _cGood="good";
        private _cWarn="warn"; private _cMute="mute"; private _cCrit="critical";
        private _pair={_this}; private _sect={_this}; private _yn={_this select 0};
        ACME_fnc_rocuroniumOnBoard={0};
    ''' + 'ACME_fnc_sedationComponents = {' + str(values) + '};' + debug_rows() + f'''
        [count _right == 5,"debug rows missing"] call _check;
        [(_right select 2) isEqualTo ["Ket",({values[0]}) toFixed 2,"label","Prop",({values[1]}) toFixed 2,"label"],"ketamine and propofol columns mixed"] call _check;
        [(_right select 3) isEqualTo ["Mid",({values[2]}) toFixed 2,"label","Fent",({values[3]}) toFixed 2,"label"],"midazolam and fentanyl columns mixed"] call _check;
        [((_right select 1) select 1) == (({values[5]}) toFixed 2),"total not supplied component result"] call _check;
    ''')


def test_component_contract_uses_executable_rows_not_full_name_labels():
    assert_debug_component_contract()
    assert_emma_identity_contract()
