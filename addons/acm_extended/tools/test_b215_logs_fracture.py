"""Execute B215 log formatting and fracture findings in production SQF.

SQF-VM uses explicit engine/UI/transport boundaries. The actual inspection
selection, descriptor resolver, log helper and DP claim/controller execute;
these tests do not certify Arma display or network transport itself.
"""
import pytest

from test_menu_death_lifecycle import adapt, execute, read
from test_b211_direct_pressure_inputs import setup as pressure_setup
from test_b213_respiration_observation import setup as respiration_setup


def production(name):
    source = read(name)
    # SQF-VM lacks this map lookup primitive. Keep the real map and contents.
    source = source.replace('_map getOrDefault [toLower _key, ""]',
                            'if ((toLower _key) in _map) then {_map get (toLower _key)} else {""}')
    return f'ACME_fnc_{name}={{' + adapt(source) + '};\n'


def logging():
    return r'''
        private _activity=[];
        ace_medical_treatment_fnc_addToLog={
            params ["_target","_kind","_format","_arguments"];
            _activity pushBack [_target,_kind,format ([_format]+_arguments)];
        };
        ACM_core_fnc_getBodyPartString={
            ["Head","Torso","Left Arm","Right Arm","Left Leg","Right Leg"] select
                (["head","body","leftarm","rightarm","leftleg","rightleg"] find (_this select 0))
        };
    ''' + production('bodyPartName') + production('medLog')


@pytest.mark.parametrize('hardcore', [False, True])
@pytest.mark.parametrize('part,label', [
    ('leftarm', 'LUE'), ('rightarm', 'RUE'), ('leftleg', 'LLE'),
    ('rightleg', 'RLE'), ('body', 'Torso'), ('head', 'Head'),
])
def test_pressure_accepted_start_logs_exact_selected_body_part_once_in_both_registers(hardcore, part, label):
    execute(pressure_setup() + logging() + f'''
        missionNamespace setVariable ["ACME_hc_descriptors",{str(hardcore).lower()}];
        ["{part}"] call _start;
        [_activity isEqualTo [[_patient,"activity","Provider applied direct pressure to {label}"]],
            "accepted application has wrong wording, patient or duplicate log"] call _check;
        [_medic,_patient,"{part}"] call ACME_fnc_directPressureStart;
        // Duplicate transport acknowledgment cannot log a second application.
        ((_acknowledgments select 0) select 1) call ACME_fnc_directPressureClaimAck;
        [count _activity==1,"repeated start/ack logged the application twice"] call _check;
        _animation="acme_directpressurehold"; _inputActions=["MoveForward"];
        CBA_missionTime=CBA_missionTime+0.2; call _pressTick;
        call _finishPressureExit; _inputActions=[];
        _animation="amovpknlmstpsnonwnondnon"; call _pressTick;
        [count _activity==1,"moving and resuming logged a second application"] call _check;
        [false,_medic] call ACME_fnc_directPressureStop;
        [count _activity==2,"stop did not retain its single distinct release log"] call _check;
        [false,_medic] call ACME_fnc_directPressureStop;
        [count _activity==2,"repeat stop duplicated release log"] call _check;
    ''')


def test_self_pressure_uses_same_format_and_own_patient_log():
    execute(pressure_setup() + logging() + r'''
        ["rightleg",true] call _start;
        [_activity isEqualTo [[_medic,"activity","Provider applied direct pressure to RLE"]],
            "self pressure used different wording or another patient's log"] call _check;
    ''')


def test_pending_or_remote_provider_does_not_create_application_log():
    execute(pressure_setup() + logging() + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        [count _activity==0,"pending request logged before acceptance"] call _check;
        call _deliver;
        [count _activity==0,"patient acceptance logged before provider activation"] call _check;
        _medic setVariable ["TEST_owner",8];
        call _deliver;
        [count _activity==0,"stale provider logged after locality transfer"] call _check;
    ''')


@pytest.mark.parametrize('count', [0, 1, 7, 20])
def test_completed_respiration_activity_has_rr_units_and_exact_watch_count(count):
    execute(respiration_setup() + logging() + f'''
        _patient setVariable ["ACM_breathing_RespirationRate",{count * 4}];
        [_medic,_patient] call ACME_fnc_respirationStart; call _ready;
        _nowTime=25; call _frame; _nowTime=27; call _frame;
        [_activity isEqualTo [
            [_patient,"activity","Provider measured respirations @ {count * 4} RR/min~ ({count} breaths in 15 seconds)"],
            [_patient,"quick_view","Provider measured respirations @ {count * 4} RR/min~ ({count} breaths in 15 seconds)"]],
            "completed watch activity has wrong units, count or duplication"] call _check;
        [true,false] call ACME_fnc_respirationStop;
        [count _activity==2,"repeated completion logged twice"] call _check;
    ''')


def fracture_setup():
    callback = read('inspectForFracture').replace(
        'localize "STR_ACM_Disability_InspectForFracture_ActionLog"', '"%1 inspected %2: %3"')
    return logging() + r'''
        private _hints=[]; private _nativeCalls=[];
        ace_common_fnc_displayTextStructured={_hints pushBack _this;};
        ACM_disability_fnc_inspectForFracture={_nativeCalls pushBack _this;};
        ACME_fnc_medDescriptor={"unused other descriptor"};
        missionNamespace setVariable ["ACME_hc_descriptors",true];
        private _setLimb={
            params ["_state","_damage","_splint","_ace","_prepared",["_index",2]];
            {
                _x params ["_name","_value","_default"];
                private _values=[_default,_default,_default,_default,_default,_default];
                _values set [_index,_value]; _patient setVariable [_name,_values];
            } forEach [
                ["ACM_disability_Fracture_State",_state,0],
                ["ace_medical_bodyPartDamage",_damage,0],
                ["ACM_disability_SplintStatus",_splint,0],
                ["ace_medical_fractures",_ace,0],
                ["ACM_disability_Fracture_Prepared",_prepared,false]
            ];
        };
    ''' + production('clinTerm') + 'ACME_fnc_inspectForFracture={' + adapt(callback) + '};'


@pytest.mark.parametrize('part,index', [('leftarm', 2), ('rightarm', 3), ('leftleg', 4), ('rightleg', 5)])
@pytest.mark.parametrize('state,ace', [(1, 1), (2, 1), (3, 1), (0, 1), (1, 0), (4, 1)])
def test_every_confirmed_unsplinted_fracture_reports_crepitus_on_captured_limb(part, index, state, ace):
    execute(fracture_setup() + f'''
        [{state},0,0,{ace},false,{index}] call _setLimb;
        [_medic,_patient,"{part}"] call ACME_fnc_inspectForFracture;
        [count _hints==1 && {{count _activity==1}},"inspection did not emit one hint and entry"] call _check;
        private _hint=toLower ((_hints select 0) select 0);
        private _log=toLower ((_activity select 0) select 2);
        [(_hint find "crepitus")>=0 && {{(_hint find "no crepitus")<0}},"fractured limb reported absent crepitus"] call _check;
        [(_log find "crepitus present")>=0,"fracture quick view did not report crepitus"] call _check;
        [((_activity select 0) select 1)=="quick_view","inspection changed log category"] call _check;
        [count _nativeCalls==0,"hardcore emitted second native result"] call _check;
    ''')


@pytest.mark.parametrize('damage', [0, 1, 1.01, 100])
def test_contusion_without_fracture_does_not_gain_crepitus(damage):
    execute(fracture_setup() + f'''
        [0,{damage},0,0,false] call _setLimb;
        [_medic,_patient,"leftarm"] call ACME_fnc_inspectForFracture;
        [(((_hints select 0) select 0) find "no crepitus found")>=0,"damage alone invented crepitus"] call _check;
        [(((_activity select 0) select 2) find "no crepitus found")>=0,"bruise log invented crepitus"] call _check;
    ''')


@pytest.mark.parametrize('splint,ace,expected', [(1, 1, 'splinted'), (2, 1, 'splinted'), (0, -1, 'stabilized'), (1, -1, 'splinted')])
def test_stabilization_and_realignment_precedence_remain_visible(splint, ace, expected):
    execute(fracture_setup() + f'''
        [3,100,{splint},{ace},true] call _setLimb;
        [_medic,_patient,"leftarm"] call ACME_fnc_inspectForFracture;
        private _hint=toLower ((_hints select 0) select 0);
        [(_hint find "{expected}")>=0,"stabilization finding was overwritten"] call _check;
        [(_hint find "realignment previously performed")>=0,"realignment history disappeared"] call _check;
        [(_hint find "crepitus present")<0 && {{(_hint find "has crepitus")<0}},"assessed through stabilization"] call _check;
    ''')


def test_unknown_unconfirmed_grade_remains_indeterminate_and_off_delegates():
    execute(fracture_setup() + r'''
        [4,0,0,0,false] call _setLimb;
        [_medic,_patient,"leftarm"] call ACME_fnc_inspectForFracture;
        [(((_hints select 0) select 0) find "indeterminate")>=0,"unknown state fabricated a finding"] call _check;
        missionNamespace setVariable ["ACME_hc_descriptors",false];
        [1,3,0,1,false] call _setLimb;
        [_medic,_patient,"leftarm"] call ACME_fnc_inspectForFracture;
        [_nativeCalls isEqualTo [[_medic,_patient,"leftarm"]],"non-hardcore stopped delegating to ACM"] call _check;
        [count _hints==1 && {count _activity==1},"disabled descriptors emitted an extra result"] call _check;
    ''')


@pytest.mark.parametrize('ace_fracture,expected_pain', [(0, 0), (1, 1), (-1, 1)])
def test_fracture_pressure_retains_clinical_pain_and_cooldown_without_second_log(ace_fracture, expected_pain):
    execute(logging() + r'''
        private _pain=[];
        ace_medical_fnc_adjustPainLevel={_pain pushBack _this;};
        ACM_core_fnc_isForcedUnconscious={true};
    ''' + production('directPressureHasFracture') + production('directPressureFracturePain') + f'''
        _patient setVariable ["ace_medical_fractures",[0,0,{ace_fracture},0,0,0]];
        [_patient,"leftarm",_medic] call ACME_fnc_directPressureFracturePain;
        [_patient,"leftarm",_medic] call ACME_fnc_directPressureFracturePain;
        [count _pain=={expected_pain},"pain response/cooldown changed"] call _check;
        [count _activity==0,"pain generated the removed duplicate activity line"] call _check;
    ''')
