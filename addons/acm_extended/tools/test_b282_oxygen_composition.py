"""Execute passive oxygen/reserve models with the real native altitude writer.

Position, live cabin config, locality, tank delivery, native getters and state
publication cross explicit engine fixtures. Pressure, ceiling, native saturation
integration, actual NRB flow/uptake and reserve decisions execute from source.
These regressions do not claim native Arma rendering/PhysX acceptance.
"""
import re

import pytest
from b281_flight_fixture import flight_setup, flight_code, execute
from test_historical_medication_rows import iteration_scopes
from test_menu_death_lifecycle import ROOT, adapt, read


def oxygen_code(source):
    source = source.replace("local _u", "_patientLocal").replace("alive _u", "_patientAlive")
    source = source.replace("local _x", "_patientLocal").replace("alive _x", "_patientAlive")
    source = source.replace("objectParent _u", "objNull").replace("_medic distance _u", "1")
    source = source.replace("_medic distance2D _patient", "1")
    source = re.sub(r'alive \(_u getVariable \["ACM_breathing_BVM_Medic",\s*objNull\]\)', "_fixtureBvm", source)
    source = source.replace('(_u getVariable ["ACME_nrb_sfxWanted", false]) != _flowing',
                            '!((_u getVariable ["ACME_nrb_sfxWanted", false]) isEqualTo _flowing)')
    for index in (2, 3):
        source = source.replace(f"finite (_sample select {index})", f"((_sample select {index}) call _flightFinite)")
    return flight_code(iteration_scopes(source))


def setup():
    session = (ROOT / "addons/breathing/functions/fnc_bvmSessionValid.sqf").read_text()
    return flight_setup() + r'''
      private _fixtureBvm=false;
      private _fixtureReach=1;
      ACME_nrb_activePatients=[_patient];ACME_preox_activePatients=[_patient];
      ACME_fnc_nrbAirwayCompatible={true};ACME_fnc_netNotice={};
      ACM_airway_fnc_getAirwayState={1};ACM_breathing_fnc_getBreathingState={1};
      ACM_circulation_fnc_hasPulse={true};
      ace_common_fnc_isAwake={true};
      ACM_core_fnc_setAceMedicalState={params ["_p","_rows"];{_p setVariable ["ace_medical_"+(_x select 0),_x select 1];} forEach _rows;};
      _patient setVariable ["ACME_nrb_on",true];_patient setVariable ["ACME_nrb_hasO2",true];
      _patient setVariable ["ACME_nrb_delivering",true];_patient setVariable ["ACME_nrb_medic",_medic];
      _patient setVariable ["ACME_nrb_lastO2Uptake",100];
      _patient setVariable ["ACME_resp_neuralRR",18];
      _patient setVariable ["ACE_isUnconscious",true];
      CBA_missionTime=100;_patient setVariable ["ACME_nrb_lastTickLocal",100];
    ''' + 'ACM_breathing_fnc_bvmSessionValid={' + oxygen_code(adapt(session, "breathing")) + '};\n' + \
        "".join("ACME_fnc_" + name + "={" + oxygen_code(read(name).replace("_medic distance _patient", "_fixtureReach")) + "};\n"
                for name in ("patientInteractionDistance", "patientInteractionContact")) + \
        "".join("ACME_fnc_" + name + "={" + oxygen_code(read(name)) + "};\n"
                  for name in ("nrbStateCommit", "nrbTick", "preoxygenationTick"))


@pytest.mark.parametrize("height", [30000, 100000, 1000000])
def test_nrb_cannot_reverse_native_hypoxia_in_near_vacuum(height):
    execute(setup() + f'''
      _patient setVariable ["fixturePosASL",[0,0,{height}]];_patient setVariable ["ace_medical_spo2",80];
      private _ceiling=[_patient] call ACME_fnc_altitudeOxygenCeiling;
      for "_i" from 1 to 6 do {{
        CBA_missionTime=100+.5*_i;call ACME_fnc_nrbTick;
        if ((_i%2)==0) then {{[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;}};
      }};
      [_ceiling<10 && {{(_patient getVariable "ace_medical_spo2")<80}},"NRB reversed native extreme-altitude hypoxia"] call _check;
      [(_patient getVariable "ace_medical_spo2")>79,"NRB hard-clamped saturation to atmosphere"] call _check;
      [abs (_fixtureDesired-_ceiling)<.000001,"pressure was applied twice to native oxygen"] call _check;
    ''')


def test_nrb_gain_stops_at_same_live_altitude_ceiling_as_native_writer():
    execute(setup() + r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      private _ceiling=[_patient] call ACME_fnc_altitudeOxygenCeiling;
      _patient setVariable ["ace_medical_spo2",_ceiling-.01];
      CBA_missionTime=102;call ACME_fnc_nrbTick;
      [_patient getVariable "ace_medical_spo2"<=_ceiling,"NRB gained above the live altitude ceiling"] call _check;
      [_patient getVariable "ace_medical_spo2">_ceiling-.01,"valid metered oxygen stopped supporting saturation"] call _check;
    ''')


def test_live_cabin_venting_descent_and_master_off_are_observed_before_flight_registry():
    execute(setup() + r'''
      _patient setVariable ["fixturePosASL",[0,0,100000]];_framePresent=true;_inside=true;
      _airframe setVariable ["ACME_cabinPressureRatio",1];_patient setVariable ["ace_medical_spo2",80];
      CBA_missionTime=100.5;call ACME_fnc_nrbTick;
      private _pressurized=_patient getVariable "ace_medical_spo2";
      [_pressurized>80,"declared live cabin did not permit NRB support"] call _check;
      _airframe setVariable ["ACME_cabinPressureRatio",0];CBA_missionTime=101;call ACME_fnc_nrbTick;
      [_patient getVariable "ace_medical_spo2"==_pressurized,"vented cabin retained stale NRB gain"] call _check;
      [_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [_patient getVariable "ace_medical_spo2"<_pressurized,"native oxygen ignored live cabin decompression"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,0]];_patient setVariable ["ace_medical_spo2",80];
      CBA_missionTime=101.5;call ACME_fnc_nrbTick;
      [_patient getVariable "ace_medical_spo2">80,"descent did not restore valid passive support"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,100000]];_patient setVariable ["ace_medical_spo2",80];
      missionNamespace setVariable ["ACME_sys_flight",false];CBA_missionTime=102;call ACME_fnc_nrbTick;
      [_patient getVariable "ace_medical_spo2">80,"master OFF left altitude limiting NRB"] call _check;
    ''')


@pytest.mark.parametrize("edge", [
    '_patient setVariable ["ACME_nrb_hasO2",false];',
    '_patient setVariable ["ACME_nrb_drawPending",["session",1,90]];',
    '_patient setVariable ["ACME_resp_neuralRR",0];',
])
def test_absent_delayed_or_apneic_nrb_delivery_cannot_add_saturation(edge):
    execute(setup() + edge + r'''
      _patient setVariable ["ace_medical_spo2",80];CBA_missionTime=100.5;call ACME_fnc_nrbTick;
      [_patient getVariable "ace_medical_spo2"==80,"non-delivered NRB gas raised saturation"] call _check;
    ''')


@pytest.mark.parametrize("height,expected", [(0, True), (10000, True), (30000, False), (100000, False)])
def test_reserve_building_uses_current_pressure_and_literal_supply_provider(height, expected):
    execute(setup() + f'''
      _patient setVariable ["ACME_nrb_on",false];_patient setVariable ["ACME_nrb_hasO2",false];
      _patient setVariable ["ACME_nrb_delivering",false];_patient setVariable ["ACME_oxygenSupply",true];
      _patient setVariable ["ACME_preox_reserve",.3];_patient setVariable ["ace_medical_spo2",99];
      _patient setVariable ["ACME_alt_pRatio",1];_patient setVariable ["fixturePosASL",[0,0,{height}]];
      call ACME_fnc_preoxygenationTick;CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      [((_patient getVariable "ACME_preox_reserve")>.3) isEqualTo {str(expected).lower()},"preoxygenation used a stale pressure or ignored actual supplied oxygen"] call _check;
    ''')


def test_preoxygenation_live_cabin_venting_stops_building_and_descent_restores_it():
    execute(setup() + r'''
      _patient setVariable ["ACME_preox_reserve",.3];_patient setVariable ["ace_medical_spo2",99];
      _patient setVariable ["fixturePosASL",[0,0,100000]];_patient setVariable ["ACME_alt_pRatio",1];
      _framePresent=true;_inside=true;_airframe setVariable ["ACME_cabinPressureRatio",1];
      call ACME_fnc_preoxygenationTick;CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      private _before=_patient getVariable "ACME_preox_reserve";
      [_before>.3,"actual pressurized cabin did not build reserve"] call _check;
      _airframe setVariable ["ACME_cabinPressureRatio",0];CBA_missionTime=102;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ACME_preox_reserve"==_before,"cached pressure replenished reserve after decompression"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,0]];CBA_missionTime=103;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ACME_preox_reserve">_before,"descent did not restore reserve replenishment"] call _check;
      private _afterDescent=_patient getVariable "ACME_preox_reserve";
      _patient setVariable ["fixturePosASL",[0,0,100000]];missionNamespace setVariable ["ACME_sys_flight",false];
      CBA_missionTime=104;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ACME_preox_reserve">_afterDescent,"master OFF retained reserve pressure attenuation"] call _check;
    ''')


@pytest.mark.parametrize("supply", ["false", "1", '"mask"', "{false}"])
def test_cosmetic_or_non_boolean_provider_cannot_preoxygenate_room_air(supply):
    execute(setup() + f'''
      _patient setVariable ["ACME_nrb_on",false];_patient setVariable ["ACME_nrb_hasO2",false];
      _patient setVariable ["ACME_nrb_delivering",false];_patient setVariable ["ACME_oxygenSupply",{supply}];
      _patient setVariable ["ACME_preox_reserve",.3];_patient setVariable ["ACE_isUnconscious",true];
      call ACME_fnc_preoxygenationTick;CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ACME_preox_reserve"==.3,"cosmetic/nontrue provider manufactured reserve"] call _check;
    ''')


@pytest.mark.parametrize("edge", ["_fixtureOwner=8;", '_patient setVariable ["ACME_clinicalEpoch",2];', "CBA_missionTime=400;"])
def test_preoxygenation_does_not_restore_stale_saturation_after_handoff_reset_or_stall(edge):
    execute(setup() + r'''
      _patient setVariable ["ACME_nrb_on",false];_patient setVariable ["ACME_nrb_hasO2",false];
      _patient setVariable ["ACME_nrb_delivering",false];_patient setVariable ["ACME_preox_reserve",.8];
      _patient setVariable ["ACME_resp_neuralRR",0];_patient setVariable ["ace_medical_spo2",99];
      call ACME_fnc_preoxygenationTick;CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      _patient setVariable ["ace_medical_spo2",40];CBA_missionTime=102;
    ''' + edge + r'''
      call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ace_medical_spo2"==40,"stale saturation history became a synthetic oxygen bolus"] call _check;
    ''')


def test_fresh_owner_local_native_loss_still_receives_finite_reserve_buffering():
    execute(setup() + r'''
      _patient setVariable ["ACME_nrb_on",false];_patient setVariable ["ACME_nrb_hasO2",false];
      _patient setVariable ["ACME_nrb_delivering",false];_patient setVariable ["ACME_preox_reserve",.8];
      _patient setVariable ["ACME_resp_neuralRR",0];_patient setVariable ["ace_medical_spo2",99];
      call ACME_fnc_preoxygenationTick;_patient setVariable ["ace_medical_spo2",98];
      CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ace_medical_spo2">98 && {_patient getVariable "ace_medical_spo2"<99},"valid reserve buffering disappeared or erased all native loss"] call _check;
      [_patient getVariable "ACME_preox_reserve"<.8,"reserve buffering created unlimited oxygen"] call _check;
    ''')


@pytest.mark.parametrize("enriched", [False, True])
def test_active_bvm_requires_an_actual_recent_oxygenated_breath_to_build_reserve(enriched):
    execute(setup() + f'''
      _patient setVariable ["ACME_nrb_on",false];_patient setVariable ["ACME_nrb_hasO2",false];
      _patient setVariable ["ACME_nrb_delivering",false];_patient setVariable ["ACME_preox_reserve",.3];
      _fixtureBvm=true;_patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",{str(enriched).lower()}];
      _patient setVariable ["ACM_breathing_BVM_provider",_medic];_patient setVariable ["ACM_breathing_BVM_Medic",_medic];
      _patient setVariable ["ACM_breathing_BVM_lastBreathOxygen",100];
      call ACME_fnc_preoxygenationTick;CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      [((_patient getVariable "ACME_preox_reserve")>.3) isEqualTo {str(enriched).lower()},"room-air or stale BVM granted supplemental preoxygenation"] call _check;
    ''')


def hand_bvm_setup():
    return setup() + r'''
      _patient setVariable ["ACME_nrb_on",false];_patient setVariable ["ACME_nrb_hasO2",false];
      _patient setVariable ["ACME_nrb_delivering",false];
      _patient setVariable ["ACM_breathing_BVM_provider",_medic];_patient setVariable ["ACM_breathing_BVM_Medic",_medic];
      _patient setVariable ["ACM_breathing_BVM_session",[_medic,5]];
      _patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",true];
      _patient setVariable ["ACM_breathing_BVM_lastBreathOxygen",100];
      _patient setVariable ["ACME_bvm_lastBreathServer",100];
      _patient setVariable ["ACME_resus_bvm",[_medic,"session",0,7,0,5,200,true,100,1,100]];
      _fixtureMultiplayer=true;
    '''


@pytest.mark.parametrize("height,normal", [(10000, True), (30000, False), (100000, False)])
def test_actual_recent_oxygenated_hand_bvm_uses_same_native_ceiling_and_no_vacuum_immunity(height, normal):
    execute(hand_bvm_setup() + f'''
      _patient setVariable ["fixturePosASL",[0,0,{height}]];
      private _exposure=[_patient] call ACME_fnc_flightExposure;
      [[_patient,_exposure] call ACME_fnc_flightDeliveredFiO2==95,"verified hand BVM did not provide measured oxygen fraction"] call _check;
      private _ceiling=[_patient,_exposure] call ACME_fnc_altitudeOxygenCeiling;
      [(_ceiling==99) isEqualTo {str(normal).lower()},"hand BVM ignored supplied gas or granted vacuum immunity"] call _check;
      [_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [abs (_fixtureDesired-_ceiling)<.000001,"native oxygen did not consume the hand BVM ceiling exactly once"] call _check;
    ''')


@pytest.mark.parametrize("edge", [
    '_patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",false];',
    '_patient setVariable ["ACM_breathing_BVM_lastBreathOxygen",69];',
    '_patient setVariable ["ACM_breathing_BVM_lastBreathOxygen",101];',
    '_patient setVariable ["ACM_breathing_BVM_lastBreathOxygen","invalid"];',
    '_patient setVariable ["ACME_bvm_lastBreathServer",69];',
    '_patient setVariable ["ACME_bvm_lastBreathServer",101];',
    '_patient setVariable ["ACM_breathing_BVM_session",[_medic,6]];',
    '_patient setVariable ["ACM_breathing_BVM_Medic",objNull];',
    '_patient setVariable ["ACM_breathing_BVM_provider",objNull];',
    '_patient setVariable ["ACM_breathing_BVM_provider","invalid"];',
    '_patient setVariable ["ACM_breathing_BVM_provider",_patient];',
    '_patient setVariable ["ACME_clinicalEpoch",1];',
    '_fixtureReach=4;',
])
def test_missing_expired_future_depleted_or_mismatched_hand_bvm_cannot_supply_oxygen(edge):
    execute(hand_bvm_setup() + edge + r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      private _exposure=[_patient] call ACME_fnc_flightExposure;
      [[_patient,_exposure] call ACME_fnc_flightDeliveredFiO2==21,"stale/mismatched BVM provided free oxygen"] call _check;
      [[_patient,_exposure] call ACME_fnc_altitudeOxygenCeiling<78,"room air hand BVM received enriched altitude ceiling"] call _check;
    ''')


@pytest.mark.parametrize("fio2", [21, 25, 40])
def test_mechanical_ventilator_sentinel_and_external_gear_do_not_override_measured_mixture(fio2):
    execute(hand_bvm_setup() + f'''
      _patient setVariable ["ACME_oxygenSupply",true];_patient setVariable ["ACME_vent_driving",true];
      _patient setVariable ["ACME_vent_onPatient",true];_patient setVariable ["ACM_breathing_BVM_provider",_patient];
      _patient setVariable ["fixtureFiO2",{fio2}];_patient setVariable ["fixturePosASL",[0,0,10000]];
      private _exposure=[_patient] call ACME_fnc_flightExposure;
      [[_patient,_exposure] call ACME_fnc_flightDeliveredFiO2=={fio2},"patient sentinel or gear replaced measured ventilator mixture"] call _check;
      private _ceiling=[_patient,_exposure] call ACME_fnc_altitudeOxygenCeiling;
      private _expected=[_patient,_exposure,{fio2}] call ACME_fnc_altitudeOxygenCeiling;
      [abs (_ceiling-_expected)<.000001,"measured ventilator gas received a second source of oxygen"] call _check;
    ''')


def test_side_effectful_boolean_oxygen_provider_is_evaluated_once_per_live_exposure():
    execute(setup() + r'''
      private _providerCalls=0;
      _patient setVariable ["ACME_oxygenSupply",{_providerCalls=_providerCalls+1;true}];
      private _exposure=[_patient] call ACME_fnc_flightExposure;
      [_providerCalls==1,"exposure evaluated a provider more than once"] call _check;
      [[_patient,_exposure] call ACME_fnc_flightDeliveredFiO2==100,"literal true provider did not supply oxygen"] call _check;
      [_patient,_exposure] call ACME_fnc_altitudeOxygenCeiling;
      [_providerCalls==1,"ceiling re-evaluated and double-charged a supply provider"] call _check;
    ''')


def test_nil_supply_condition_fails_closed_without_repeated_evaluation():
    execute(setup() + r'''
      private _providerCalls=0;
      _patient setVariable ["ACME_nrb_on",false];_patient setVariable ["ACME_nrb_hasO2",false];
      _patient setVariable ["ACME_nrb_delivering",false];
      _patient setVariable ["ACME_oxygenSupply",{_providerCalls=_providerCalls+1;nil}];
      private _exposure=[_patient] call ACME_fnc_flightExposure;
      [[_patient,_exposure] call ACME_fnc_flightDeliveredFiO2==21 && {_providerCalls==1},"nil provider granted oxygen or was repeatedly charged"] call _check;
    ''')


@pytest.mark.parametrize("load,edema", [(.8, .4), (0, .9)])
def test_ventilator_oxygen_model_reads_atomic_aspiration_even_when_mirrors_are_missing(load, edema):
    execute(setup() + f'''
      private _healthy=[_patient,1,5,100,0] call ACME_fnc_ventOxygenation;
      _patient setVariable ["ACME_aspiration_State",[0,"processed",{load},{edema},1]];
      _patient setVariable ["ACME_aspiration_load",0];_patient setVariable ["ACME_aspiration_edema",0];
      private _injured=[_patient,1,5,100,0] call ACME_fnc_ventOxygenation;
      [_injured<_healthy-10,"ventilator ignored authoritative injury before scalar mirrors arrived"] call _check;
    ''')


def test_neutral_authority_ignores_late_old_aspiration_mirrors_in_ventilation_and_reserves():
    execute(setup() + r'''
      _patient setVariable ["ACME_aspiration_State",[0,"",0,0,0]];
      _patient setVariable ["ACME_aspiration_load",.8];_patient setVariable ["ACME_aspiration_edema",.9];
      [[_patient,1,5,100,0] call ACME_fnc_ventOxygenation==99,"late old mirrors reintroduced ventilator aspiration shunt"] call _check;
      _patient setVariable ["ACME_preox_reserve",.8];call ACME_fnc_preoxygenationTick;
      CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ACME_preox_reserve">.8,"late old mirror restricted current body reserve"] call _check;
    ''')


def test_preoxygenation_defers_missing_authority_without_touching_reserves_or_native_oxygen():
    execute(setup() + r'''
      _patient setVariable ["ACME_aspiration_load",.8];_patient setVariable ["ACME_aspiration_edema",.9];
      _patient setVariable ["ACME_preox_reserve",.8];_patient setVariable ["ace_medical_spo2",40];
      call ACME_fnc_preoxygenationTick;CBA_missionTime=103;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ACME_preox_reserve"==.8 && {_patient getVariable "ace_medical_spo2"==40},"missing authority mutated reserve or actual oxygen"] call _check;
      [isNil {_patient getVariable "ACME_aspiration_State"},"reader guessed an authority from partial mirrors"] call _check;
    ''')


def test_preoxygenation_uses_atomic_load_before_mirror_arrives():
    execute(setup() + r'''
      _patient setVariable ["ACME_aspiration_State",[0,"processed",.8,.4,1]];
      _patient setVariable ["ACME_aspiration_load",0];_patient setVariable ["ACME_aspiration_edema",0];
      _patient setVariable ["ACME_preox_reserve",.9];call ACME_fnc_preoxygenationTick;
      CBA_missionTime=101;call ACME_fnc_preoxygenationTick;
      [_patient getVariable "ACME_preox_reserve"<.8,"missing mirror bypassed actual body-reserve lung penalty"] call _check;
    ''')


def test_actual_ventilator_keeps_breathing_and_paid_gas_while_aspiration_model_waits_for_authority():
    from test_b276_vent_oxygen import delivery_setup
    execute(delivery_setup() + r'''
      private _targetWrites=[];
      ACM_core_fnc_setTargetVitalsState={params ["_p","_changes"];
        {_targetWrites pushBack _x;if ((_x select 0)=="oxygenSaturation") then {_p setVariable ["ACM_core_TargetVitals_OxygenSaturation",_x select 1];};} forEach _changes;
      };
      missionNamespace setVariable ["ACME_vent_simpleMode",true];
      _patient setVariable ["ACM_core_TargetVitals_OxygenSaturation",72];
      _patient setVariable ["ACME_vent_shunt",.44];
      _patient setVariable ["ACME_o2Drain_mainstem",4];_patient setVariable ["ACME_o2Drain_vili",5];
      _patient setVariable ["ACME_aspiration_load",.8];_patient setVariable ["ACME_aspiration_edema",.4];
      call _attach;call _prepay;private _before=_patient getVariable "ACME_vent_o2Credit";
      for "_i" from 1 to 3 do {[_patient] call ACME_fnc_ventDriveTick;};
      [_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"==72 && {_patient getVariable "ACME_vent_shunt"==.44},"partial authority changed composed target/shunt or compounded drains"] call _check;
      [count _targetWrites==0,"unknown aspiration model published a fabricated oxygen target"] call _check;
      [_patient getVariable "ACME_vent_vti">0 && {_patient getVariable "ACME_vent_mvDelivered">0} && {_patient getVariable "ACME_vent_o2Credit"<_before},"missing model authority stopped mechanical ventilation or paid inspiratory gas"] call _check;
      _patient setVariable ["ACME_aspiration_State",[1,"processed",.8,.4,1]];
      [_patient] call ACME_fnc_ventDriveTick;
      [count _targetWrites==1 && {_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"<90},"valid atomic authority did not resume exactly one model target publication"] call _check;
    ''')


@pytest.mark.parametrize("state,height", [
    ("unknown", 0), ("unknown", 100000), ("valid", 30000), ("valid", 100000),
])
def test_actual_cpap_recruitment_cannot_add_oxygen_above_live_or_unknown_model_ceiling(state, height):
    from test_b276_vent_oxygen import delivery_setup
    authority = ('_patient setVariable ["ACME_aspiration_load",.8];' if state == "unknown" else
                 '_patient setVariable ["ACME_aspiration_State",[1,"",0,0,0]];')
    execute(delivery_setup() + authority + f'''
      private _actualOxygenWrites=0;
      ACM_core_fnc_setAceMedicalState={{params ["_p","_changes"];{{if ((_x select 0)=="spo2") then {{_actualOxygenWrites=_actualOxygenWrites+1;_p setVariable ["ace_medical_spo2",_x select 1];}};}} forEach _changes;}};
      ACM_core_fnc_setTargetVitalsState={{params ["_p","_changes"];{{if ((_x select 0)=="oxygenSaturation") then {{_p setVariable ["ACM_core_TargetVitals_OxygenSaturation",_x select 1];}};}} forEach _changes;}};
      ACM_circulation_fnc_setRuntimeState={{params ["_p","_changes"];{{if ((_x select 0)=="overloadVolume") then {{_p setVariable ["ACM_circulation_Overload_Volume",_x select 1];}};}} forEach _changes;}};
      missionNamespace setVariable ["ACME_vent_simpleMode",false];
      _patient setVariable ["ACME_ETT_Inserted",false];_patient setVariable ["ACME_vent_nivMask",true];
      _patient setVariable ["ACME_vent_mode","CPAP PS HF"];_patient setVariable ["ACME_vent_iface","NON-INVASIVE"];
      _patient setVariable ["ACME_vent_psup",0];_patient setVariable ["ACME_resp_neuralRR",18];
      _patient setVariable ["ACM_circulation_Overload_Volume",1];
      _patient setVariable ["ACM_core_TargetVitals_OxygenSaturation",72];_patient setVariable ["ace_medical_spo2",80];
      _patient setVariable ["fixturePosASL",[0,0,{height}]];
      call _attach;call _prepay;
      for "_i" from 1 to 3 do {{[_patient] call ACME_fnc_ventDriveTick;}};
      [_patient getVariable "ACME_vent_driving" && {{_patient getVariable "ACME_vent_vti">0}},"CPAP stopped breathing while model was limited or pending"] call _check;
      [_actualOxygenWrites==0 && {{_patient getVariable "ace_medical_spo2"==80}},"CPAP recruitment bypassed live/unknown oxygen ceiling"] call _check;
      [_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"{('==72' if state == 'unknown' else '<10')},"CPAP lost prior target during defer or ignored altitude"] call _check;
    ''')
