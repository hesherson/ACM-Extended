"""Execute restored burn intake, care and owner lifecycle in SQF-VM.

Object locality/aliveness, CBA scheduling and replication are explicit engine
boundaries. Burden, recovery, source separation and registry decisions execute
the production source. Native ACE inventory/treatment remains its own boundary.
"""
import re
import xml.etree.ElementTree as ET

import pytest

import test_menu_death_lifecycle as lifecycle
from test_menu_death_lifecycle import ROOT, execute
from test_historical_cardiac_execution import code as vm_primitives
from test_historical_vial_execution import map_defaults


BURNS = ROOT / "addons/burns"


def source(path):
    text = (BURNS / path).read_text()
    for variable in ("_patient", "_unit", "_x"):
        text = re.sub(rf"\blocal {variable}\b", "_burnLocal", text)
        text = re.sub(rf"\balive {variable}\b", "_burnAlive", text)
    text = text.replace("allUnits", "_testAllUnits")
    text = text.replace("isDamageAllowed _unit", "_burnDamageAllowed")
    text = text.replace("VAR_OPEN_WOUNDS", '"ace_medical_openWounds"')
    text = text.replace("VAR_BANDAGED_WOUNDS", '"ace_medical_bandagedWounds"')
    text = text.replace("BURN_WRONG_DRESSING_PAIN", "0.25")
    text = re.sub(r"LINKFUNC\((\w+)\)", r"ACM_burns_fnc_\1", text)
    text = text.replace('[_name,_value,_public]', '[_name,_value]')
    return map_defaults(vm_primitives(text, component="burns"))


def setup():
    text = '''
        private _burnLocal=true;private _burnAlive=true;private _burnDamageAllowed=true;
        private _burnEvents=createHashMap;private _burnWorker={};
        private _burnRegistrations=[];private _burnWorkerStarts=0;
        private _burnPublishes=[];private _burnEvacs=[];private _burnPain=[];
        private _burnWounds=[];private _testAllUnits=[_patient];
        private _linear={params ["_lo","_hi","_value","_a","_b",["_clamp",false]];
            private _fraction=(_value-_lo)/(_hi-_lo);
            if (_clamp) then {_fraction=(_fraction max 0) min 1;};_a+(_fraction*(_b-_a))};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        CBA_missionTime=1000;_nowTime=1000;
        ACM_burns_burnsEnabled=true;ACM_burns_sourcesEnabled=true;
        ACM_burns_headBurnAirwayChance=0;ACM_burns_igniteChanceMul=1;
        ACM_burns_fieldRecoveryMinutes=10;ACM_burns_hardcoreEvacBurden=0.4;
        ACME_hcEff_burns=false;ACM_burns_activePatients=[];
        ACME_circ_activePatients=[];
        ace_medical_damage_woundClassNames=["Abrasion","Burn1","Burn2","Burn3"];
        CBA_fnc_addEventHandler={_burnRegistrations pushBack (_this select 0);_burnEvents set [_this select 0,_this select 1];};
        CBA_fnc_addPerFrameHandler={_burnWorkerStarts=_burnWorkerStarts+1;_burnWorker=_this select 0;0};
        CBA_fnc_addClassEventHandler={};
        CBA_fnc_localEvent={_burnWounds pushBack _this;};
        ace_medical_status_fnc_adjustPainLevel={_burnPain pushBack _this;};
        ACME_fnc_setVarNetApprox={params ["_p","_key","_value","_epsilon","_age"];
            _burnPublishes pushBack [_key,_value,_epsilon,_age];
            _p setVariable [_key,_value];};
        ACME_fnc_evacuationRequirementCommit={params ["_p"];
            _burnEvacs pushBack _this;_p setVariable ["ACME_requiresEvac",true];};
    '''
    for name in ("resetVariables", "initUnit", "handleRespawn", "fullHealLocal",
                 "tickPatient", "applyBurnWound", "handleExplosion", "canTreatBurnCream", "reconcile"):
        text += f"ACM_burns_fnc_{name}={{" + source(f"functions/fnc_{name}.sqf") + "};"
    return text + "[] call {" + source("XEH_postInit.sqf") + "};"


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def test_burn_intake_weights_regions_preserves_worst_depth_and_requires_real_deep_burn():
    execute(setup() + '''
        private _intake=_burnEvents get "ACM_burns_burnApplied";
        [_patient,"body","Burn3",1] call _intake;
        private _surface=+(_patient getVariable "ACM_burns_BurnSurface");
        [abs ((_patient getVariable "ACM_burns_BurnBurden")-0.36)<0.00001
            && {(_surface select 1)==1},"burn region was not weighted exactly once"] call _check;
        [_patient,"body","Burn2",0.1] call _intake;
        [(_patient getVariable "ACM_burns_BurnSurface") isEqualTo _surface,
            "a repeated shallower burn reduced or duplicated existing anatomy"] call _check;
        [_patient,"leftarm","Abrasion",1] call _intake;
        [(_patient getVariable "ACM_burns_BurnSurface") isEqualTo _surface,
            "an unrelated wound created systemic burn burden"] call _check;
    ''')


def test_post_init_replay_does_not_duplicate_treatment_callbacks_or_worker():
    execute(setup() + '''private _before=count _burnRegistrations;'''
            + "[] call {" + source("XEH_postInit.sqf") + "};" + '''
        [count _burnRegistrations==_before && {_burnWorkerStarts==1},
            "post-init replay duplicated burn callbacks or physiology worker"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_burnLocal=false;", "_burnAlive=false;", "ACM_burns_burnsEnabled=false;",
])
def test_ineligible_burn_intake_does_not_mutate_anatomy(change):
    execute(setup() + change + '''
        [_patient,"body","Burn3",1] call (_burnEvents get "ACM_burns_burnApplied");
        [isNil {_patient getVariable "ACM_burns_BurnBurden"}
            && {ACM_burns_activePatients isEqualTo []},"ineligible intake changed burn anatomy"] call _check;
    ''')


def test_first_owner_tick_uses_one_interval_and_settled_normal_burns_retire_without_anatomy_loss():
    execute(setup() + '''
        _patient setVariable ["ACM_burns_BurnBurden",0.5];
        _patient setVariable ["ACM_burns_SystemicBurden",0.3];
        _patient setVariable ["ACM_burns_LastBurnAt",0];
        _patient setVariable ["ACM_burns_LastTickLocal",-1];
        [_patient] call ACM_burns_fnc_tickPatient;
        [abs ((_patient getVariable "ACM_burns_SystemicBurden")-(0.3-2/600))<0.00001,
            "new owner integrated the reset sentinel as elapsed mission time"] call _check;
        _patient setVariable ["ACM_burns_SystemicBurden",0.001];
        CBA_missionTime=1002;ACM_burns_activePatients=[_patient];ACM_burns_lastDiscovery=-1;
        [] call _burnWorker;
        [ACM_burns_activePatients isEqualTo []
            && {(_patient getVariable "ACM_burns_BurnBurden")==0.5}
            && {(_patient getVariable "ACM_burns_SystemicBurden")==0}
            && {(_patient getVariable "ACM_burns_HR_Adjust")==0},
            "settled normal burns were destroyed or repeatedly enrolled"] call _check;
        [(_burnPublishes findIf {(_x select 3)!=0})<0,
            "steady burn state requested periodic heartbeat replication"] call _check;
        [(_burnPublishes findIf {(_x select 1)==0 && {(_x select 2)!=0}})<0,
            "a neutral endpoint could remain stranded behind its scalar deadband"] call _check;
    ''')


def test_proper_coverage_reduces_risk_and_new_burn_removes_only_its_regional_protection():
    execute(setup() + '''
        [_patient,"leftarm","Burn3",1] call (_burnEvents get "ACM_burns_burnApplied");
        private _before=_patient getVariable "ACM_burns_InfectionRiskMult";
        [_patient,"leftarm","ACM_SilverNylonDressing"] call (_burnEvents get "ace_medical_treatment_bandageLocal");
        CBA_missionTime=1002;[_patient] call ACM_burns_fnc_tickPatient;
        [(_patient getVariable "ACM_burns_InfectionRiskMult")<_before
            && {(_patient getVariable "ACM_burns_BurnProtected") select 2},
            "proper coverage did not reduce the exposed skin-barrier burden"] call _check;
        [_patient,"rightarm","ACM_SilverNylonDressing"] call (_burnEvents get "ace_medical_treatment_bandageLocal");
        [_patient,"leftarm","Burn2",0.2] call (_burnEvents get "ACM_burns_burnApplied");
        private _protected=_patient getVariable "ACM_burns_BurnProtected";
        [!(_protected select 2) && {_protected select 3},
            "a new burn preserved its old cover or erased another region's protection"] call _check;
    ''')


@pytest.mark.parametrize("bandage", ["ACM_BurnCream", "ACM_SilverNylonDressing"])
def test_mixed_or_partial_deep_burn_care_cannot_protect_the_whole_region(bandage):
    execute(setup() + f'''
        [_patient,"body","Burn3",1] call (_burnEvents get "ACM_burns_burnApplied");
        private _before=_patient getVariable "ACM_burns_InfectionRiskMult";
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["body",[[11,0,0,0.1],[21,0.5,0,0.2]]]]];
        [_patient,"body","{bandage}"] call (_burnEvents get "ace_medical_treatment_bandageLocal");
        CBA_missionTime=1002;[_patient] call ACM_burns_fnc_tickPatient;
        [!((_patient getVariable "ACM_burns_BurnProtected") select 1)
            && {{(_patient getVariable "ACM_burns_InfectionRiskMult")==_before}},
            "cream or partial coverage protected a remaining open deep burn"] call _check;
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["body",[[11,0,0,0.1],[21,0,0,0.2]]]]];
        [_patient,"body","ACM_SilverNylonDressing"] call (_burnEvents get "ace_medical_treatment_bandageLocal");
        CBA_missionTime=1004;[_patient] call ACM_burns_fnc_tickPatient;
        [((_patient getVariable "ACM_burns_BurnProtected") select 1)
            && {{(_patient getVariable "ACM_burns_InfectionRiskMult")<_before}},
            "completed native coverage did not protect the deep burn"] call _check;
    ''')


@pytest.mark.parametrize("bandage,expected", [
    ("FieldDressing", 1), ("ACM_SilverNylonDressing", 0), ("ACM_BurnCream", 0),
])
def test_dressing_pain_respects_existing_native_bandage_callback_and_owner(bandage, expected):
    execute(setup() + f'''
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["body",[[21,1,0,0.2]]]]];
        [_patient,"body","{bandage}"] call (_burnEvents get "ace_medical_treatment_bandageLocal");
        [count _burnPain=={expected},"burn dressing consequence was lost or duplicated"] call _check;
        _burnPain=[];_burnLocal=false;
        [_patient,"body","FieldDressing"] call (_burnEvents get "ace_medical_treatment_bandageLocal");
        [count _burnPain==0,"another patient's owner was bypassed by dressing care"] call _check;
    ''')


@pytest.mark.parametrize("wound,allowed", [(11, True), (21, False), (31, False), (1, False)])
def test_cream_condition_is_specific_to_open_superficial_burns(wound, allowed):
    execute(setup() + f'''
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["body",[[{wound},1,0,0.2]]]]];
        [([_medic,_patient,"Body"] call ACM_burns_fnc_canTreatBurnCream) isEqualTo {str(allowed).lower()},
            "burn cream allowed an incompatible injury"] call _check;
    ''')


def test_exhausted_native_wound_rows_do_not_offer_cream_or_invent_dressing_pain():
    execute(setup() + '''
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["body",[[11,0,0,0.2],[21,0,0,0.3],[1,1,0.1,0.1]]]]];
        [!([_medic,_patient,"Body"] call ACM_burns_fnc_canTreatBurnCream),
            "an exhausted Burn1 row still authorized another cream item"] call _check;
        [_patient,"body","FieldDressing"] call (_burnEvents get "ace_medical_treatment_bandageLocal");
        [_burnPain isEqualTo [],"an exhausted deep-burn row added pain to unrelated wound care"] call _check;
    ''')


@pytest.mark.parametrize("disabled", [False, True])
def test_disabled_or_cleared_sources_neutralize_old_drives_once_without_erasing_anatomy(disabled):
    execute(setup() + f'''
        ACM_burns_burnsEnabled={str(not disabled).lower()};
        private _burden={0.5 if disabled else 0};
        _patient setVariable ["ACM_burns_BurnBurden",_burden];
        _patient setVariable ["ACM_burns_SystemicBurden",_burden];
        _patient setVariable ["ACM_CBRN_AirwayInflammation",70];
        private _fields=["EffectiveVolumeDeficitL","HeatLossDrive","HR_Adjust","Resistance_Delta","ShockSeverity"];
        {{_patient setVariable ["ACM_burns_"+_x,0.5];}} forEach _fields;
        _patient setVariable ["ACM_burns_InfectionRiskMult",1.7];
        [_patient] call ACM_burns_fnc_tickPatient;
        [(_fields findIf {{(_patient getVariable ["ACM_burns_"+_x,-1])!=0}})<0
            && {{(_patient getVariable "ACM_burns_InfectionRiskMult")==1}}
            && {{(_patient getVariable "ACM_burns_BurnBurden")==_burden}}
            && {{(_patient getVariable "ACM_CBRN_AirwayInflammation")==70}},
            "a cleared/disabled burn source left stale physiology or erased anatomy"] call _check;
        private _count=count _burnPublishes;[_patient] call ACM_burns_fnc_tickPatient;
        [count _burnPublishes==_count,"neutral burn state emitted another set of packets"] call _check;
    ''')


def test_restored_systemic_burden_drives_physiology_without_an_anatomical_burden_field():
    execute(setup() + '''
        _patient setVariable ["ACM_burns_SystemicBurden",0.5];
        _patient setVariable ["ACM_burns_LastBurnAt",1000];
        [_patient] call ACM_burns_fnc_tickPatient;
        [(_patient getVariable ["ACM_burns_EffectiveVolumeDeficitL",0])>0
            && {(_patient getVariable ["ACM_burns_HR_Adjust",0])==9},
            "restored systemic burden was ignored without anatomical burn metadata"] call _check;
    ''')


def test_airway_edema_progresses_then_recovers_without_touching_cbrn_inflammation():
    execute(setup() + '''
        ACM_burns_headBurnAirwayChance=1;
        _patient setVariable ["ACM_CBRN_AirwayInflammation",70];
        [_patient,"head","Burn3",1] call (_burnEvents get "ACM_burns_burnApplied");
        private _first=_patient getVariable "ACM_burns_AirwayInflammation";
        CBA_missionTime=1002;[_patient] call ACM_burns_fnc_tickPatient;
        [(_patient getVariable "ACM_burns_AirwayInflammation")>_first,
            "head burn did not progressively develop its own edema"] call _check;
        CBA_missionTime=2500;[_patient] call ACM_burns_fnc_tickPatient;
        [(_patient getVariable "ACM_burns_AirwayInflammation")==0
            && {!(_patient getVariable "ACM_burns_AirwayBurned")}
            && {(_patient getVariable "ACM_CBRN_AirwayInflammation")==70},
            "resolved burn edema left an airway flag or erased chemical inflammation"] call _check;
    ''')


def test_hardcore_evacuation_is_latched_until_definitive_reset_and_cbrn_is_source_separate():
    execute(setup() + '''
        ACME_hcEff_burns=true;
        _patient setVariable ["ACM_CBRN_AirwayInflammation",70];
        _patient setVariable ["ACM_burns_BurnBurden",0.5];
        _patient setVariable ["ACM_burns_SystemicBurden",0.5];
        _patient setVariable ["ACM_burns_LastBurnAt",0];
        [_patient] call ACM_burns_fnc_tickPatient;
        [(_patient getVariable "ACM_burns_PermanentInjury") && {count _burnEvacs==1},
            "hardcore burn did not latch its evacuation requirement"] call _check;
        ACME_hcEff_burns=false;_patient setVariable ["ACME_requiresEvac",false];
        _patient setVariable ["ACM_burns_SystemicBurden",0.05];CBA_missionTime=1002;
        [_patient] call ACM_burns_fnc_tickPatient;
        [(_patient getVariable "ACM_burns_PermanentInjury")
            && {(_patient getVariable "ACM_burns_SystemicBurden")>=0.18}
            && {_patient getVariable "ACME_requiresEvac"} && {count _burnEvacs==2},
            "existing permanent injury silently recovered or lost its evacuation latch"] call _check;
        [_patient] call ACM_burns_fnc_fullHealLocal;
        [!(_patient getVariable "ACM_burns_PermanentInjury")
            && {(_patient getVariable "ACM_burns_BurnBurden")==0}
            && {(_patient getVariable "ACM_CBRN_AirwayInflammation")==70}
            && {_patient getVariable "ACME_requiresEvac"},
            "burn reset erased another source or left permanent anatomy"] call _check;
    ''')


def test_initialization_replay_preserves_restored_state_but_respawn_resets_the_same_object():
    execute(setup() + '''
        _patient setVariable ["ACM_burns_BurnSurface",[0,0.7,0,0,0,0]];
        _patient setVariable ["ACM_burns_BurnBurden",0.252];
        _patient setVariable ["ACM_burns_SystemicBurden",0.2];
        [_patient] call ACM_burns_fnc_initUnit;
        [(_patient getVariable "ACM_burns_BurnBurden")==0.252
            && {(_patient getVariable "ACM_burns_SystemicBurden")==0.2}
            && {_patient in ACM_burns_activePatients},
            "JIP initialization erased restored burn anatomy"] call _check;
        _burnLocal=false;[_patient] call ACM_burns_fnc_resetVariables;
        [(_patient getVariable "ACM_burns_BurnBurden")==0.252,
            "nonowner reset erased another owner's burn anatomy"] call _check;
        _burnLocal=true;[_patient] call ACM_burns_fnc_handleRespawn;
        [(_patient getVariable "ACM_burns_BurnBurden")==0
            && {!(_patient in ACM_burns_activePatients)},
            "same-object respawn retained the previous life burn state"] call _check;
    ''')


def test_native_reconciliation_adopts_one_owner_period_then_preserves_its_live_clock():
    execute(setup() + '''
        _patient setVariable ["ACM_burns_BurnBurden",0.5];
        _patient setVariable ["ACM_burns_SystemicBurden",0.3];
        _patient setVariable ["ACM_burns_LastBurnAt",0];
        _patient setVariable ["ACM_burns_LastTickLocal",50];
        [_patient,true,false] call ACM_burns_fnc_reconcile;
        [ACM_burns_activePatients isEqualTo [_patient]
            && {(_patient getVariable "ACM_burns_LastTickLocal")==1000}
            && {(_patient getVariable "ACM_burns_SystemicBurden")==0.3},
            "new owner inherited elapsed time or missed native burn enrollment"] call _check;
        CBA_missionTime=1002;[_patient,false,false] call ACM_burns_fnc_reconcile;
        [ACM_burns_activePatients isEqualTo [_patient]
            && {abs ((_patient getVariable "ACM_burns_SystemicBurden")-(0.3-2/600))<0.00001},
            "same-period reconciliation reset its live burn clock"] call _check;
    ''')


def test_native_reconciliation_retires_after_locality_loss_without_erasing_anatomy():
    execute(setup() + '''
        _patient setVariable ["ACM_burns_BurnBurden",0.5];
        _patient setVariable ["ACM_burns_PermanentInjury",true];
        _patient setVariable ["ACM_burns_LastTickLocal",123];
        ACM_burns_activePatients=[_patient];_burnLocal=false;
        [_patient,true,true] call ACM_burns_fnc_reconcile;
        [ACM_burns_activePatients isEqualTo []
            && {(_patient getVariable "ACM_burns_BurnBurden")==0.5}
            && {_patient getVariable "ACM_burns_PermanentInjury"}
            && {(_patient getVariable "ACM_burns_LastTickLocal")==123}
            && {_burnPublishes isEqualTo []},
            "retiring a runtime changed durable burn state or its old clock"] call _check;
    ''')


def test_native_reconciliation_keeps_settled_anatomy_dormant_and_clears_old_derived_effects():
    execute(setup() + '''
        _patient setVariable ["ACM_burns_BurnBurden",0.5];
        _patient setVariable ["ACM_burns_SystemicBurden",0];
        _patient setVariable ["ACM_burns_HR_Adjust",9];
        _patient setVariable ["ACM_burns_LastTickLocal",123];
        [_patient,true,false] call ACM_burns_fnc_reconcile;
        [ACM_burns_activePatients isEqualTo []
            && {(_patient getVariable "ACM_burns_BurnBurden")==0.5}
            && {(_patient getVariable "ACM_burns_SystemicBurden")==0}
            && {(_patient getVariable "ACM_burns_HR_Adjust")==0},
            "settled anatomy was reactivated or retained old systemic drives"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_burnLocal=false;", "_burnAlive=false;", "ACM_burns_burnsEnabled=false;",
])
def test_explicit_burn_application_honors_owner_liveness_and_enabled_setting(change):
    execute(setup() + change + '''
        [_patient,0.4,"body"] call ACM_burns_fnc_applyBurnWound;
        [_burnWounds isEqualTo [],"ineligible application emitted a native burn wound"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_burnDamageAllowed=false;", '_patient setVariable ["ace_medical_allowDamage",false];',
])
def test_explosion_sources_respect_engine_and_ace_invulnerability(change):
    execute(setup() + change + '''
        [_patient,1] call ACM_burns_fnc_handleExplosion;
        [_patient,0.5,"body"] call ACM_burns_fnc_applyBurnWound;
        [_burnWounds isEqualTo [],"thermal source bypassed unit invulnerability"] call _check;
    ''')


def test_explosion_uses_the_native_ace_wound_packet_once_and_obeys_source_toggle():
    execute(setup() + '''
        [_patient,1] call ACM_burns_fnc_handleExplosion;
        [count _burnWounds==1,"one accepted explosion failed or duplicated native wound intake"] call _check;
        private _packet=(_burnWounds select 0) select 1;
        [count _packet==4 && {(_packet select 0) isEqualTo _patient}
            && {(_packet select 3)=="burn"} && {count (_packet select 1)==1}
            && {count (_packet select 1 select 0)==3},"thermal source changed ACE's woundReceived packet"] call _check;
        ACM_burns_sourcesEnabled=false;[_patient,1] call ACM_burns_fnc_handleExplosion;
        [count _burnWounds==1,"disabled explosion source emitted another wound"] call _check;
    ''')


def test_burn_names_resolve_for_every_native_wound_size_and_uses_the_native_treatment_stock_path():
    keys = {key.attrib["ID"]: key for key in ET.parse(BURNS / "stringtable.xml").iter("Key")}
    for depth in (1, 2, 3):
        for size in ("Minor", "Medium", "Large"):
            assert keys[f"STR_ACE_Medical_Damage_Burn{depth}_{size}"].findtext("English")
    actions = (BURNS / "ACE_Medical_Treatment_Actions.hpp").read_text()
    for name in ("ACM_SilverNylonDressing", "ACM_BurnCream"):
        assert f"class {name}: PressureBandage" in actions
        assert f'items[]             = {{"{name}"}};' in actions
