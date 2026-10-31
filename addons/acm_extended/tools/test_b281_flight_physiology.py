"""Run actual B281 altitude/oxygen source across teleports, supplies and owners.

This proves SQF decisions and composition, not native collision/rendering or
human physiological calibration. New regression cases preserve historical IDs.
"""
import pytest
from b281_flight_fixture import flight_setup, flight_function, flight_code, execute


@pytest.mark.parametrize('height,expected',[
    (0,1),(11000,22632.06/101325),(20000,5474.889/101325),
    (32000,868.019/101325),(47000,110.906/101325),
    (51000,66.938/101325),(71000,3.95642/101325),(84852,.3734/101325),
])
def test_pressure_matches_independent_standard_atmosphere_layer_boundaries(height,expected):
    execute(flight_setup()+f'''
      private _pressure=[{height}] call ACME_fnc_pressureAtAltitude;
      [abs (_pressure-{expected})<0.000001,"standard pressure boundary disagrees"] call _check;
    ''')


def test_pressure_is_finite_continuous_and_keeps_falling_above_old_cutoff():
    execute(flight_setup()+r'''
      private _previous=1;
      {
        private _p=[_x] call ACME_fnc_pressureAtAltitude;
        [_p>0 && {_p<=_previous},"pressure rose or became zero/nonfinite"] call _check;
        _previous=_p;
      } forEach [0,500,10000,11000,12000,20000,30000,50000,71000,84852,100000,1000000,1e9];
      {private _a=[_x-.01] call ACME_fnc_pressureAtAltitude;private _b=[_x+.01] call ACME_fnc_pressureAtAltitude;
        [abs (_a-_b)<0.00001,"lapse boundary has pressure discontinuity"] call _check;
      } forEach [11000,20000,32000,47000,51000,71000,84852];
      [[-50] call ACME_fnc_pressureAtAltitude==1 && {["invalid"] call ACME_fnc_pressureAtAltitude==1},"invalid/negative altitude became harmful pressure"] call _check;
    ''')


@pytest.mark.parametrize('field',['fixtureGoggles','fixtureHeadgear','fixtureVest'])
def test_registered_oxygen_condition_receives_actual_patient_not_ace_player(field):
    execute(flight_setup()+f'''
      private _seen=objNull;
      private _condition={{_seen=_this;_this getVariable ["hasGas",false]}};
      missionNamespace setVariable ["ace_medical_vitals_oxygenSupplyConditionCache",createHashMapFromArray [["DeclaredEquipment",_condition]]];
      _patient setVariable ["{field}","DeclaredEquipment"];_patient setVariable ["hasGas",true];
      ACE_player=objNull;
      [[_patient] call ACME_fnc_oxygenSupply && {{_seen isEqualTo _patient}},"condition used local player instead of patient"] call _check;
      _patient setVariable ["hasGas",false];
      [!([_patient] call ACME_fnc_oxygenSupply),"depleted condition granted free oxygen"] call _check;
    ''')


@pytest.mark.parametrize('condition',['{false}','{1}','{"true"}','"malformed"'])
def test_cosmetic_or_invalid_supply_conditions_fail_closed(condition):
    execute(flight_setup()+f'''
      _patient setVariable ["fixtureGoggles","HALO_CosmeticMask"];
      [!([_patient] call ACME_fnc_oxygenSupply),"mask appearance granted oxygen"] call _check;
      missionNamespace setVariable ["ace_medical_vitals_oxygenSupplyConditionCache",createHashMapFromArray [["HALO_CosmeticMask",{condition}]]];
      [!([_patient] call ACME_fnc_oxygenSupply),"nontrue equipment condition granted oxygen"] call _check;
    ''')


def test_explicit_device_supply_is_live_and_does_not_depend_on_gear_name():
    execute(flight_setup()+r'''
      _patient setVariable ["ACME_oxygenSupply",{_this getVariable ["gasRemaining",0]>0}];
      _patient setVariable ["gasRemaining",1];
      [[_patient] call ACME_fnc_oxygenSupply,"device oxygen contract ignored"] call _check;
      _patient setVariable ["gasRemaining",0];
      [!([_patient] call ACME_fnc_oxygenSupply),"exhausted device retained oxygen"] call _check;
      _patient setVariable ["ACME_oxygenSupply","mask"];
      [!([_patient] call ACME_fnc_oxygenSupply),"invalid device state granted oxygen"] call _check;
    ''')


def test_airframe_has_ambient_pressure_until_explicit_verified_cabin_contract():
    execute(flight_setup()+r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];_framePresent=true;_inside=true;
      private _ambient=([_patient] call ACME_fnc_flightExposure) select 1;
      [([_patient] call ACME_fnc_flightExposure) select 2==_ambient,"arbitrary aircraft was assumed pressurized"] call _check;
      _config set ["AnyModdedAirframe:ACME_cabinPressureRatio",.8];
      [([_patient] call ACME_fnc_flightExposure) select 2==.8,"declared cabin pressure ignored"] call _check;
      _inside=false;
      [([_patient] call ACME_fnc_flightExposure) select 2==_ambient,"roof/wing received cabin pressure"] call _check;
      _inside=true;_framePresent=false;
      [([_patient] call ACME_fnc_flightExposure) select 2==_ambient,"freefall retained aircraft pressure"] call _check;
    ''')


def test_live_cabin_altitude_overrides_static_ratio_and_decompression_returns_ambient():
    execute(flight_setup()+r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];_framePresent=true;_inside=true;
      _config set ["AnyModdedAirframe:ACME_cabinPressureRatio",.9];
      _airframe setVariable ["ACME_cabinAltitude",5000];
      private _p5=[5000] call ACME_fnc_pressureAtAltitude;
      [abs ((([_patient] call ACME_fnc_flightExposure) select 2)-_p5)<.000001,"static ratio overrode live cabin altitude"] call _check;
      _airframe setVariable ["ACME_cabinPressureRatio",0];
      private _e=[_patient] call ACME_fnc_flightExposure;
      [(_e select 1)==(_e select 2),"explicit vent-to-ambient lost to static cabin config"] call _check;
      _airframe setVariable ["ACME_cabinPressureRatio",.7];
      [([_patient] call ACME_fnc_flightExposure) select 2==.7,"live ratio lost precedence"] call _check;
    ''')


@pytest.mark.parametrize('setup,expected',[
    ('_worldBase=2000;',12000),
    ('missionNamespace setVariable ["ace_common_mapAltitude",2000];',12000),
    ('missionNamespace setVariable ["ace_common_mapAltitude","invalid"];_worldBase=1500;',11500),
    ('missionNamespace setVariable ["ACME_ElevationOverride_Active",true];missionNamespace setVariable ["ACME_ElevationOverride_Base",-6000];',4000),
    ('missionNamespace setVariable ["ACME_altitude_datumMode",6000];_worldBase=2000;',4000),
    ('missionNamespace setVariable ["ACME_altitude_datumMode",0];_worldBase=2000;',10000),
])
def test_datum_precedence_honors_live_additive_bases_and_explicit_raw_asl_mode(setup,expected):
    execute(flight_setup()+r'''
      missionNamespace setVariable ["ACME_altitude_datumMode",-1];
      _patient setVariable ["fixturePosASL",[0,0,10000]];
    '''+setup+f'''
      [[_patient] call ACME_fnc_altitudeTrue=={expected},"elevation precedence disagrees"] call _check;
    ''')


def test_auto_datum_caches_only_terrain_and_rechecks_mode_base_threshold_and_world():
    execute(flight_setup()+r'''
      missionNamespace setVariable ["ACME_altitude_datumMode",-1];_terrainMinimum=6000;
      _patient setVariable ["fixturePosASL",[0,0,16000]];
      [[_patient] call ACME_fnc_altitudeTrue==10000,"authored high plate datum missed"] call _check;
      private _firstReads=_terrainReads;
      [[_patient] call ACME_fnc_altitudeTrue==10000 && {_terrainReads==_firstReads},"terrain minimum resampled unchanged world"] call _check;
      missionNamespace setVariable ["ACME_altitude_datumThreshold",7000];
      [[_patient] call ACME_fnc_altitudeTrue==16000 && {_terrainReads==_firstReads},"threshold cached stale"] call _check;
      missionNamespace setVariable ["ACME_altitude_datumMode",0];
      [[_patient] call ACME_fnc_altitudeTrue==16000,"explicit raw mode cached stale"] call _check;
      missionNamespace setVariable ["ACME_altitude_datumMode",-1];
      missionNamespace setVariable ["ACME_ElevationOverride_Active",true];missionNamespace setVariable ["ACME_ElevationOverride_Base",-6000];
      [[_patient] call ACME_fnc_altitudeTrue==10000,"module double-corrected terrain offset"] call _check;
      missionNamespace setVariable ["ACME_ElevationOverride_Base",-5000];
      [[_patient] call ACME_fnc_altitudeTrue==11000,"live module update ignored"] call _check;
      missionNamespace setVariable ["ACME_ElevationOverride_Active",false];missionNamespace setVariable ["ace_common_mapAltitude",0];
      _world="Terrain_B";_terrainMinimum=-100;
      [[_patient] call ACME_fnc_altitudeTrue==16000 && {_terrainReads>_firstReads},"world change retained old minimum"] call _check;
      private _secondReads=_terrainReads;_worldSize=200;
      [[_patient] call ACME_fnc_altitudeTrue==16000 && {_terrainReads>_secondReads},"world size change retained old minimum"] call _check;
    ''')


def test_altitude_invalid_inputs_and_below_sea_level_stay_neutral():
    execute(flight_setup()+r'''
      _patient setVariable ["fixturePosASL",[0,0,-100]];
      [[_patient] call ACME_fnc_altitudeTrue==0,"negative altitude inverted pressure"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,"invalid"]];
      [[_patient] call ACME_fnc_altitudeTrue==0,"invalid engine height propagated"] call _check;
      missionNamespace setVariable ["ACME_altitude_datumMode","invalid"];_worldSize=0;
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      [[_patient] call ACME_fnc_altitudeTrue==10000,"invalid world/datum failed safe fallback"] call _check;
    ''')


def test_healthy_teleport_is_seen_by_native_oxygen_without_prior_clinical_enrollment():
    execute(flight_setup()+r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      private _base=_patient getVariable "ACM_core_TargetVitals_OxygenSaturation";
      private _actual=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [_actual<99 && {_actual>98.8},"pristine player was immune or instantly knocked out"] call _check;
      [_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"==_base,"altitude overwrote native target"] call _check;
      private _a=[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling;
      _patient setVariable ["fixturePosASL",[0,0,30000]];
      private _b=[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling;
      [_b<_a && {_a<78} && {_b>0},"severe altitude retained old oxygen plateau"] call _check;
    ''')


def test_supplied_gas_protects_halo_but_is_not_vacuum_immunity_or_cabin_pressure():
    execute(flight_setup()+r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];_patient setVariable ["ACME_oxygenSupply",true];
      private _e=[_patient] call ACME_fnc_flightExposure;
      [[_patient,_e] call ACME_fnc_altitudeOxygenCeiling==99,"supplied HALO oxygen failed at 10km"] call _check;
      [(_e select 2)==(_e select 1),"personal oxygen falsely pressurized trapped gas"] call _check;
      private _actual=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [_actual>=99 && {_fixtureDesired==99},"native oxygen reapplied altitude below supplied gas"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,30000]];
      [[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling<78,"oxygen mask granted vacuum immunity"] call _check;
    ''')


@pytest.mark.parametrize('delivering',[False,True])
def test_nrb_ceiling_requires_real_metered_delivery(delivering):
    execute(flight_setup()+f'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      _patient setVariable ["ACME_nrb_on",true];_patient setVariable ["ACME_nrb_hasO2",true];
      _patient setVariable ["ACME_nrb_delivering",{str(delivering).lower()}];
      private _sat=[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling;
      [_sat{'>78' if delivering else '<78'},"NRB flow condition ignored"] call _check;
    ''')


def test_descent_and_master_disable_remove_only_altitude_not_clinical_target_or_device_drains():
    execute(flight_setup()+r'''
      _patient setVariable ["ACM_core_TargetVitals_OxygenSaturation",85];
      _patient setVariable ["ACME_o2Drain_suction",2];_patient setVariable ["ACME_o2Drain_mainstem",3];_patient setVariable ["ACME_o2Drain_vili",4];
      _patient setVariable ["ace_medical_spo2",76];
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      private _low=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [_low<76,"altitude ceiling did not constrain concurrent clinical/drain target"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,0]];_patient setVariable ["ace_medical_spo2",76];
      private _ground=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [_ground>=76 && {_fixtureDesired==76},"descent erased unrelated target/drains"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,10000]];missionNamespace setVariable ["ACME_sys_flight",false];
      missionNamespace setVariable ["ACM_breathing_altitudeAffectOxygen",true];
      private _off=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [_off>=76 && {_fixtureDesired==76} && {_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"==85},"master OFF retained altitude or replaced unrelated target"] call _check;
    ''')


def test_altitude_and_suction_penalties_compose_once_when_altitude_is_lower_than_clinical_target():
    execute(flight_setup()+r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      _patient setVariable ["ACME_o2Drain_suction",10];
      private _ceiling=[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling;
      _patient setVariable ["ace_medical_spo2",_ceiling-10];
      private _actual=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [abs (_fixtureDesired-(_ceiling-10))<.000001 && {_actual>=_fixtureDesired},"suction vanished under altitude or was deducted twice"] call _check;
    ''')


def test_ventilator_fio2_shunt_and_pressure_use_one_ceiling_without_duplicate_device_drains():
    execute(flight_setup()+r'''
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      _patient setVariable ["ACME_vent_driving",true];_patient setVariable ["fixtureFiO2",21];
      private _room=[_patient,1,5,21,0] call ACME_fnc_ventOxygenation;
      private _oxygen=[_patient,1,5,100,0] call ACME_fnc_ventOxygenation;
      [_room<78 && {_oxygen==99},"vent altitude or delivered oxygen ignored"] call _check;
      _patient setVariable ["ACM_circulation_Overload_Volume",1.6];
      private _lowPeep=[_patient,1,4,100,0] call ACME_fnc_ventOxygenation;
      private _highPeep=[_patient,1,15,100,0] call ACME_fnc_ventOxygenation;
      [_highPeep>_lowPeep && {_highPeep<99},"PEEP recruitment or shunt target was erased"] call _check;
      _patient setVariable ["fixtureFiO2",100];
      _patient setVariable ["ACME_o2Drain_mainstem",3];_patient setVariable ["ACME_o2Drain_vili",4];
      _patient setVariable ["ACM_core_TargetVitals_OxygenSaturation",_highPeep-7];
      _patient setVariable ["ace_medical_spo2",_highPeep-7];
      private _actual=[_patient,0,0,0,1,false] call ace_medical_vitals_fnc_updateOxygen;
      [abs (_fixtureDesired-(_highPeep-7))<.000001 && {_actual>=_fixtureDesired},"native writer duplicated ventilator device drains"] call _check;
    ''')


def test_pressure_observation_is_stationary_inert_deduplicated_and_owner_reset_aware():
    execute(flight_setup()+r'''
      _patient setVariable ["ACME_ptx_state",[1,1,0,0,0,0,0,1,1]];
      [_patient] call ACME_fnc_altitudeTick;
      _patient setVariable ["fixturePosASL",[0,0,10000]];CBA_missionTime=11;
      [_patient] call ACME_fnc_altitudeTick;
      [count _ptxPublications==1,"teleport pressure failed to adjust existing trapped gas once"] call _check;
      private _after=+(_patient getVariable "ACME_ptx_state");
      [_patient] call ACME_fnc_altitudeTick;
      [count _ptxPublications==1,"same-clock second worker repeated expansion"] call _check;
      for "_i" from 12 to 20 do {CBA_missionTime=_i;[_patient] call ACME_fnc_altitudeTick;};
      [_patient getVariable "ACME_ptx_state" isEqualTo _after,"stationary altitude accrued gas"] call _check;
      _fixtureOwner=8;_patient setVariable ["fixturePosASL",[0,0,0]];CBA_missionTime=21;
      [_patient] call ACME_fnc_altitudeTick;
      [_patient getVariable "ACME_ptx_state" isEqualTo _after,"new owner replayed old pressure travel"] call _check;
      [_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"==99,"pressure worker overwrote clinical oxygen target"] call _check;
    ''')


def test_pressure_never_creates_ptx_in_healthy_player_and_disable_cleans_only_flight_state():
    execute(flight_setup()+r'''
      [_patient] call ACME_fnc_altitudeTick;
      _patient setVariable ["fixturePosASL",[0,0,50000]];CBA_missionTime=11;[_patient] call ACME_fnc_altitudeTick;
      [count _ptxPublications==0 && {(_patient getVariable "ACME_ptx_state" select 1)==0},"healthy altitude created pleural air"] call _check;
      _patient setVariable ["ACM_core_TargetVitals_OxygenSaturation",73];
      _patient setVariable ["ACME_flightG_stress",.8];_patient setVariable ["ACME_flightG_resistAdd",-20];
      missionNamespace setVariable ["ACME_sys_flight",false];[_patient] call ACME_fnc_altitudeTick;
      [(_patient getVariable "ACME_alt_pRatio")==1 && {(_patient getVariable "ACME_alt_hypoxia")==0} && {(_patient getVariable "ACME_flightG_resistAdd")==0},"OFF retained flight effects"] call _check;
      [_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"==73,"OFF restored99 over unrelated clinical target"] call _check;
    ''')


def test_maneuver_stress_uses_actual_airframe_motion_and_volume_not_teleport_distance():
    execute(flight_setup()+r'''
      _framePresent=true;_airframe setVariable ["fixtureEngine",true];
      _patient setVariable ["fixturePosASL",[0,0,1000]];
      [_patient] call ACME_fnc_altitudeTick;
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      _patient setVariable ["ACM_circulation_Blood_Volume",4];CBA_missionTime=11;
      [_patient] call ACME_fnc_altitudeTick;
      [(_patient getVariable "ACME_flightG_resistAdd")==0,"teleport height was mistaken for flight acceleration"] call _check;
      _airframe setVariable ["fixtureVelocity",[0,0,10]];CBA_missionTime=12;
      [_patient] call ACME_fnc_altitudeTick;
      [(_patient getVariable "ACME_flightG_stress")==1 && {(_patient getVariable "ACME_flightG_resistAdd")==-18},"real hypovolemic climb lost stress/delta scaling"] call _check;
      [_patient] call ACME_fnc_altitudeTick;
      [(_patient getVariable "ACME_flightG_resistAdd")==-18,"same-clock replay integrated stress twice"] call _check;
      missionNamespace setVariable ["ACME_flightG_enable",false];CBA_missionTime=13;
      [_patient] call ACME_fnc_altitudeTick;
      [(_patient getVariable "ACME_flightG_stress")==0 && {(_patient getVariable "ACME_flightG_resistAdd")==0},"G toggle retained stress residue"] call _check;
      missionNamespace setVariable ["ACME_flightG_enable",true];_patient setVariable ["ACM_circulation_Blood_Volume",6];CBA_missionTime=14;
      [_patient] call ACME_fnc_altitudeTick;
      [(_patient getVariable "ACME_flightG_resistAdd")==0,"normal blood volume acquired flight hypotension"] call _check;
    ''')


def test_stationary_descent_reverses_existing_gas_without_replacing_other_clinical_targets():
    execute(flight_setup()+r'''
      _patient setVariable ["ACME_ptx_state",[1,1,0,0,0,0,0,1,1]];
      _patient setVariable ["ACM_core_TargetVitals_OxygenSaturation",81];
      [_patient] call ACME_fnc_altitudeTick;
      _patient setVariable ["fixturePosASL",[0,0,10000]];CBA_missionTime=11;[_patient] call ACME_fnc_altitudeTick;
      [_patient getVariable "ACME_ptx_state" select 1>3,"ascent did not expand actual trapped gas"] call _check;
      _patient setVariable ["fixturePosASL",[0,0,0]];CBA_missionTime=12;[_patient] call ACME_fnc_altitudeTick;
      [abs ((_patient getVariable "ACME_ptx_state" select 1)-1)<.000001 && {(_patient getVariable "ACME_alt_hypoxia")==0},"descent failed to contract gas/clear altitude hypoxia"] call _check;
      [_patient getVariable "ACM_core_TargetVitals_OxygenSaturation"==81,"descent replaced unrelated clinical oxygen target"] call _check;
    ''')


def test_ground_exposure_does_not_query_aircraft_surfaces_without_a_relevant_patient():
    execute(flight_setup()+r'''
      private _lookups=0;ACME_fnc_flightAirframe={_lookups=_lookups+1;objNull};
      for "_i" from 1 to 100 do {[_patient] call ACME_fnc_flightExposure;};
      [_lookups==0,"healthy ground vital updates queried aircraft surfaces"] call _check;
      _patient setVariable ["ACM_breathing_Pneumothorax_State",1];
      [_patient] call ACME_fnc_flightExposure;
      [_lookups==1,"low-altitude trapped gas skipped airframe exposure"] call _check;
    ''')


def test_legacy_altitude_option_is_one_exposure_policy_under_the_master_flight_switch():
    execute(flight_setup()+r'''
      missionNamespace setVariable ["ACME_altitude_enable",false];
      _patient setVariable ["fixturePosASL",[0,0,10000]];
      [[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling==99,"disabled altitude still constrained oxygen"] call _check;
      missionNamespace setVariable ["ACM_breathing_altitudeAffectOxygen",true];
      [[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling<78,"legacy native altitude option ignored"] call _check;
      missionNamespace setVariable ["ACME_sys_flight",false];
      [[_patient,[_patient] call ACME_fnc_flightExposure] call ACME_fnc_altitudeOxygenCeiling==99,"legacy option bypassed master OFF"] call _check;
      [[_patient,1,5,21,0] call ACME_fnc_ventOxygenation==99,"vent pressure policy disagrees with master OFF"] call _check;
    ''')


def chill_setup():
    return flight_setup()+r'''
      ACME_fnc_vehicleOpenness={_airframe getVariable ["fixtureOpen",0]};
      _patient setVariable ["fixtureVehicle",_airframe];
      _airframe setVariable ["fixtureIsAir",true];
    '''+flight_function('flightChill')


def test_flight_chill_applies_actual_sea_level_climb_lapse():
    execute(chill_setup()+r'''
      _airframe setVariable ["fixturePosASL",[0,0,10000]];
      _airframe setVariable ["fixturePosATL",[0,0,10000]];
      [[_patient] call ACME_fnc_flightChill==65,"10km sea-level climb lost its altitude lapse"] call _check;
    ''')


def test_flight_chill_does_not_double_count_high_plateau_ground_elevation():
    execute(chill_setup()+r'''
      _airframe setVariable ["fixturePosASL",[0,0,6000]];
      _airframe setVariable ["fixturePosATL",[0,0,0]];
      [[_patient] call ACME_fnc_flightChill==0,"ground plateau was penalized a second time"] call _check;
    ''')


def test_flight_chill_same_climb_has_same_lapse_over_different_terrain():
    execute(chill_setup()+r'''
      _airframe setVariable ["fixturePosATL",[0,0,3000]];
      _airframe setVariable ["fixturePosASL",[0,0,3000]];
      private _sea=[_patient] call ACME_fnc_flightChill;
      _airframe setVariable ["fixturePosASL",[0,0,9000]];
      private _plateau=[_patient] call ACME_fnc_flightChill;
      [_sea==19.5 && {_plateau==_sea},"terrain changed the same 3km flight lapse"] call _check;
    ''')


def test_flight_chill_master_disable_removes_wind_and_lapse_immediately():
    execute(chill_setup()+r'''
      _airframe setVariable ["fixturePosATL",[0,0,10000]];
      _airframe setVariable ["fixtureOpen",1];_airframe setVariable ["fixtureSpeed",200];
      [([_patient] call ACME_fnc_flightChill)>65,"fixture failed to expose flight airflow"] call _check;
      missionNamespace setVariable ["ACME_sys_flight",false];
      [[_patient] call ACME_fnc_flightChill==0,"master OFF retained flight cooling"] call _check;
    ''')


def test_flight_chill_hpmk_wrapped_factor_preserves_open_blanket_exposure():
    execute(chill_setup()+r'''
      _airframe setVariable ["fixturePosATL",[0,0,10000]];
      _patient setVariable ["ACME_hpmk_on",true];_patient setVariable ["ACME_hpmk_state","wrapped"];
      [abs (([_patient] call ACME_fnc_flightChill)-9.75)<.000001,"wrapped blanket lost thermal protection"] call _check;
      _patient setVariable ["ACME_hpmk_state","exposed"];
      [[_patient] call ACME_fnc_flightChill==65,"open blanket retained wrapped protection"] call _check;
    ''')


def test_flight_chill_negative_height_is_clamped_and_on_foot_has_no_vehicle_penalty():
    execute(chill_setup()+r'''
      _airframe setVariable ["fixturePosATL",[0,0,-100]];
      [[_patient] call ACME_fnc_flightChill==0,"negative ATL reversed cabin lapse"] call _check;
      _airframe setVariable ["fixturePosATL",[0,0,10000]];
      _patient setVariable ["fixtureVehicle",_patient];
      [[_patient] call ACME_fnc_flightChill==0,"on-foot ambient received aircraft penalty"] call _check;
    ''')
