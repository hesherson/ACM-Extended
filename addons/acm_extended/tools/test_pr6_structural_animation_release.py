"""Execute the guarded structural releases with presentation disabled; native moves are recorded boundaries."""
import pytest

from test_b210_ai_protection import engine
from test_b225_pose_regression import getup_setup
from test_menu_death_lifecycle import execute, read


def test_actual_get_up_and_both_backstops_escape_isolated_lying_when_theatre_is_off():
    execute(getup_setup() + 'ACME_fnc_doAnim={' + engine(read('doAnim')) + '};' + r'''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        _patient setVariable ["TEST_animation","acm_lyingstate"];
        [_patient,true,_medic] call ACM_core_fnc_getUp;
        [!(_patient getVariable ["ACM_core_Lying_State",true]),"Get Up retained lying flag"] call _check;
        [_moves isEqualTo [[_patient,"UnconsciousOutProne",2]],"Get Up structural escape suppressed"] call _check;
        _patient setVariable ["TEST_animation","unconscious"];
        private _first=_waits select 0; (_first select 1) call (_first select 0);
        _patient setVariable ["TEST_animation","deadstate"];
        private _last=_waits select 1; (_last select 1) call (_last select 0);
        [_moves isEqualTo [[_patient,"UnconsciousOutProne",2],[_patient,"UnconsciousOutProne",2],[_patient,"AmovPpneMstpSnonWnonDnon",2]],"structural backstop order changed"] call _check;
        [_patient,"OptionalTreatmentMove",2] call ACME_fnc_doAnim;
        [count _moves==3,"structural release enabled general presentation"] call _check;
    ''')


@pytest.mark.parametrize('state',[
    '_patient setVariable ["TEST_vehicle",missionNamespace];',
    '_patient setVariable ["TEST_attached",missionNamespace];',
])
def test_disabled_get_up_does_not_force_structural_escape_in_vehicle_or_carry(state):
    execute(getup_setup() + r'''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        _patient setVariable ["TEST_animation","acm_lyingstate"];
    ''' + state + r'''
        [_patient,true,_medic] call ACM_core_fnc_getUp;
        {(_x select 1) call (_x select 0);} forEach +_waits;
        [count _moves==0,"Get Up forced a seated or carried body"] call _check;
    ''')


def full_heal_release():
    # Run the complete current full-heal grounded-state release. The unrelated chemical/inventory reset preceding
    # this block is covered by its own lifecycle suite; no release eligibility or move branch is reconstructed here.
    block=read('clearAllAilments').split('// the forced animation and lying-state release.',1)[1]
    block=block.split('[_patient, "finish", _preserveDeathInterventions]',1)[0]
    block='// the forced animation and lying-state release.'+block
    block=block.replace('attachedTo _patient','(_patient getVariable ["TEST_attached",objNull])')
    block=engine(block)
    for field in ('TEST_vehicle','TEST_attached'):
        block=block.replace(f'isNull (_patient getVariable ["{field}",objNull])',
                            f'((_patient getVariable ["{field}",objNull]) isEqualTo objNull)')
    return 'ACME_test_fullHealRelease={params ["_patient"];'+block+'};'


@pytest.mark.parametrize('state,expected',[
    ('',1),
    ('_patient setVariable ["ACE_isUnconscious",true];',0),
    ('_patient setVariable ["TEST_alive",false];',0),
    ('_patient setVariable ["TEST_vehicle",missionNamespace];',0),
    ('_patient setVariable ["TEST_attached",missionNamespace];',0),
    ('_dragged=true;',0),
    ('_carried=true;',0),
    ('_patient setVariable ["TEST_animation","amovppnemstpsnonwnondnon"];',0),
    ('_patient setVariable ["TEST_animation","unconsciousoutprone"];',0),
])
def test_full_heal_release_off_retains_grounded_awake_and_transport_guards(state,expected):
    execute(getup_setup()+full_heal_release()+r'''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _dragged=false;private _carried=false;
        ace_common_fnc_isBeingDragged={_dragged};ace_common_fnc_isBeingCarried={_carried};
        ACM_core_fnc_setLyingState={(_this select 0) setVariable ["ACM_core_Lying_State",false];};
        _patient setVariable ["TEST_animation","acm_lyingstate"];
    '''+state+f'''
        [_patient] call ACME_test_fullHealRelease;
        [count _moves=={expected},"incorrect full-heal release eligibility"] call _check;
        [!(_patient getVariable ["ACM_core_Lying_State",true]),"full heal did not clear logical lying"] call _check;
    '''+(r'''
        [_moves isEqualTo [[_patient,"UnconsciousOutProne",2]],"full heal lost exact structural escape"] call _check;
    ''' if expected else ''))
