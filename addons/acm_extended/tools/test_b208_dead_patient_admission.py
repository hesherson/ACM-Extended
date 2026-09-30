"""Execute corpse admission and equipment commits with explicit engine boundaries.

Config reads, world geometry and ACE interaction/trait primitives are fixtures;
production policy, epoch checks, item receipts and state transitions execute in SQF.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b206_rpt_callback_execution import hpmk_setup


def config_adapter(source):
    source = source.replace('alive _caller', '_alive')
    source = source.replace('_target isKindOf "CAManBase"', '_isMan').replace('_patient isKindOf "CAManBase"', '_isMan')
    source = source.replace('objectParent _caller', '_providerVehicle').replace('objectParent _target', '_patientVehicle')
    source = source.replace('_caller isEqualTo player', '_isCurator').replace('findDisplay 312', '_curatorDisplay')
    source = source.replace('configFile >> "ace_medical_treatment_actions" >> _className', '_configValues')
    source = source.replace('isClass _config', '_classExists')
    source = re.sub(r'getArray \(_config >> "(\w+)"\)', r'(_config get "\1")', source)
    source = re.sub(r'getNumber \(_config >> "(\w+)"\)', r'(_config get "\1")', source)
    source = re.sub(r'_config >> "(\w+)"', r'_config get "\1"', source)
    source = source.replace('isText _entry', '(_entry isEqualType "")').replace('getText _entry', '_entry').replace('getNumber _entry', '_entry')
    return adapt(source)


def eligibility_source():
    return config_adapter((ROOT / 'addons/core/overrides/fnc_canTreatCached.sqf').read_text())


def native_policy():
    # Unmodified native ACE function from the user-supplied ACE3-master snapshot, bundled as a test fixture.
    # Replace only config/engine boundaries and macros, never its eligibility Boolean chain.
    source=(ROOT/'tools/fixtures/ace_canTreat.sqf.txt').read_text()
    source=source.replace('QGVAR(actions)', '"ace_medical_treatment_actions"')
    source=source.replace('_classname;', '_className;', 1)
    source=source.replace('"_classname"', '"_className"')
    source=source.replace('GET_FUNCTION(_condition,_config >> "condition");', 'private _condition = {_stockAllows && {missionNamespace getVariable ["ACM_airway_enable",true]}};')
    source=re.sub(r'GET_NUMBER_ENTRY\(_config >> "(\w+)"\)', r'([_config >> "\1"] call _numberFixture)',source)
    source=re.sub(r'IN_MED_VEHICLE\((_\w+)\)',r'(\1 call ace_medical_treatment_fnc_isInMedicalVehicle)',source)
    source=re.sub(r'IN_MED_FACILITY\((_\w+)\)',r'(\1 call ace_medical_treatment_fnc_isInMedicalFacility)',source)
    for suffix,value in [('VEHICLES_AND_FACILITIES',3),('VEHICLES',1),('FACILITIES',2),('ALL',0)]:
        source=source.replace('TREATMENT_LOCATIONS_'+suffix,str(value))
    source=re.sub(r'FUNC\((\w+)\)',r'ace_medical_treatment_fnc_\1',source)
    source=source.replace('EFUNC(common,isSwimming)','ace_common_fnc_isSwimming')
    source=source.replace('_medic isEqualTo player','_isCurator').replace('findDisplay 312','_curatorDisplay').replace('_medic != _patient','_medic isNotEqualTo _patient')
    return config_adapter(source)


def admission_setup():
    return '''
        _patientAlive=false;
        private _isMan=true; private _classExists=true; private _isCurator=false;
        private _curatorDisplay=objNull; private _providerVehicle=objNull; private _patientVehicle=objNull;
        private _interactive=true; private _skill=2; private _holster=true; private _inventory=true;
        private _vehicle=false; private _facility=false; private _swimming=false;
        private _procedure=true; private _stockAllows=true; private _stockCalls=0;
        private _numberFixture={params ["_value"]; if (_value isEqualType "") then {missionNamespace getVariable [_value,0]} else {_value}};
        private _configValues=createHashMapFromArray [
            ["allowedSelections",["head","body","leftarm","rightarm","leftleg","rightleg"]],
            ["allowSelfTreatment",0], ["medicRequired",1], ["items",["item"]],
            ["treatmentLocations",0], ["allowedUnderwater",0]
        ];
        ace_common_fnc_canInteractWith={_interactive};
        ACME_fnc_patientInteractionDistance={_distance};
        ACME_fnc_procedureActionAllowed={_procedure};
        ace_medical_treatment_fnc_isMedic={_skill >= (_this select 1)};
        ace_medical_treatment_fnc_canTreat_holsterCheck={_holster};
        ace_medical_treatment_fnc_hasItem={_inventory};
        ace_medical_treatment_fnc_isInMedicalVehicle={_vehicle};
        ace_medical_treatment_fnc_isInMedicalFacility={_facility};
        ace_common_fnc_isSwimming={_swimming};
    ''' + 'ace_medical_treatment_fnc_canTreat={_stockCalls=_stockCalls+1;' + native_policy() + '};ace_medical_treatment_fnc_canTreatCached={' + eligibility_source() + '};'


@pytest.mark.parametrize('invalid', [
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_interactive=false;', '_distance=4;', '_isMan=false;', '_classExists=false;',
    '_skill=0;', '_holster=false;', '_inventory=false;', '_procedure=false;',
    '_swimming=true;', '_configValues set ["treatmentLocations",1];',
    '_configValues set ["treatmentLocations",2];', '_configValues set ["treatmentLocations",4];',
    '_configValues set ["allowedSelections",["body"]];',
    '_patient setVariable ["ACME_hpmk_state","wrapped"]; _part="body";',
    '_patient setVariable ["ACME_hpmk_state","exposed"]; _part="rightarm";',
])
def test_dead_evidence_exception_preserves_provider_inventory_skill_and_access_guards(invalid):
    execute(admission_setup() + 'private _part="head";' + invalid + '''
        [!([_medic,_patient,_part,"CheckAirway"] call ace_medical_treatment_fnc_canTreatCached),
            "corpse exception bypassed actual access restriction"] call _check;
    ''')


@pytest.mark.parametrize('valid', [
    '', '_configValues set ["treatmentLocations",1];_vehicle=true;',
    '_configValues set ["treatmentLocations",2];_facility=true;',
    '_configValues set ["treatmentLocations",3];_vehicle=true;',
    '_configValues set ["treatmentLocations",3];_facility=true;',
    '_swimming=true;_configValues set ["allowedUnderwater",1];',
    '_configValues set ["medicRequired","testSkill"];missionNamespace setVariable ["testSkill",1];',
    '_distance=100;_providerVehicle=missionNamespace;_patientVehicle=missionNamespace;',
])
def test_dead_evidence_retains_native_allowed_contexts(valid):
    execute(admission_setup() + valid + '''
        [[_medic,_patient,"head","CheckAirway"] call ace_medical_treatment_fnc_canTreatCached,
            "valid corpse evidence action rejected"] call _check;
    ''')


@pytest.mark.parametrize('state,part,expected',[('wrapped','body',False),('exposed','rightarm',False),('exposed','leftarm',True),('','body',True)])
def test_corpse_equipment_exceptions_obey_partial_and_full_hpmk_coverage(state,part,expected):
    execute(admission_setup() + f'''
        _patient setVariable ["ACME_hpmk_state","{state}"];
        _patient setVariable ["ACME_nrb_on",true];
        private _result=[_medic,_patient,"{part}","ACME_RemoveNRB"] call ace_medical_treatment_fnc_canTreatCached;
        [_result isEqualTo {str(expected).lower()},"HPMK coverage bypassed"] call _check;
    ''')


def test_dead_patient_hpmk_prep_wrap_and_remove_use_real_owner_transactions():
    execute(hpmk_setup() + 'private _wrap={' + adapt(read('hpmkWrap')) + '};' + '''
        _patientAlive=false;
        _patient setVariable ["ACE_isUnconscious",false];
        _patient setVariable ["ACM_core_Lying_State",false];
        [_medic,_patient,"body","ACME_PrepHPMK",_medic,"",false] call ACME_fnc_hpmkPrep;
        [(_patient getVariable ["ACME_hpmk_state",""])=="prepped", "corpse kit prep rejected"] call _check;
        [count _settled==1 && {!(((_settled select 0) select 1) select 1)}, "accepted corpse prep refunded supply"] call _check;
        CBA_fnc_serverEvent={_events pushBack _this;};
        [_medic,_patient,"body","ACME_WrapHPMK"] call _wrap;
        [(_patient getVariable "ACME_hpmk_state")=="wrapped", "corpse wrap removed kit"] call _check;
        [_medic,_patient,"body","ACME_RemoveHPMK",_medic,"",false] call ACME_fnc_hpmkRemove;
        [(_patient getVariable "ACME_hpmk_state")=="", "corpse kit could not be recovered"] call _check;
        [count _moves==0, "corpse kit operation animated patient"] call _check;
    ''')


@pytest.mark.parametrize('dead,unconscious,expected',[(True,False,True),(False,False,False),(False,True,True)])
def test_hpmk_menu_matches_immobile_callback_eligibility(dead,unconscious,expected):
    execute(admission_setup() + f'''
        _patientAlive={str(not dead).lower()};_stockAllows=true;
        _patient setVariable ["ACE_isUnconscious",{str(unconscious).lower()}];
        private _result=[_medic,_patient,"body","ACME_PrepHPMK"] call ace_medical_treatment_fnc_canTreatCached;
        [_result isEqualTo {str(expected).lower()},"HPMK menu/callback mismatch"] call _check;
    ''')


@pytest.mark.parametrize('alive,expected', [(False,True),(True,False)])
def test_manual_carrier_corpse_without_unconscious_flag_remains_mechanically_accessible(alive,expected):
    source=read('manualPlateCarrierCanToggle').replace('_patient isKindOf "CAManBase"','true').replace('vest _patient','_worn').replace('attachedTo _patient','objNull')
    execute('private _toggle={'+adapt(source)+'};' + f'''
        _patientAlive={str(alive).lower()}; private _worn="vest";
        ace_common_fnc_isAwake={{true}};ACME_fnc_chestAccessManeuverActive={{false}};
        [[_medic,_patient,false] call _toggle isEqualTo {str(expected).lower()},"carrier remove availability wrong"] call _check;
        _worn="";_patient setVariable ["ACME_manualPlateCarrierState","off"];
        _patient setVariable ["ACME_manualPlateCarrierLease","manual:one"];
        _patient setVariable ["ACME_chestAccess_vestLoadout",["vest",[]]];
        [[_medic,_patient,true] call _toggle,"carrier recovery rejected"] call _check;
    ''')


@pytest.mark.parametrize('invalid,accepted', [('',True),('_alive=false;',False),('_medic setVariable ["ACE_isUnconscious",true];',False),('_distance=6;',False),('_epoch=2;',False)])
def test_pressure_cuff_corpse_commit_keeps_provider_epoch_and_distance_guards(invalid,accepted):
    source=adapt(read('pressureInfuserCommit')).replace('_receipts getOrDefault [_id, []]', '(if (_id in _receipts) then {_receipts get _id} else {[]})')
    # SQF-VM lacks hashmap forEach; enumerate its real keys/values while preserving the production loop body.
    source=source.replace('private _i = _y findIf', 'private _y = _x select 1; private _i = _y findIf')
    source=source.replace('forEach (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap])', 'forEach ((keys (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap])) apply {[_x, (_patient getVariable "ACM_circulation_IV_Bags") get _x]})')
    execute('private _commit={'+source+'};' + '''
        _patientAlive=false;private _epoch=1;private _acks=[];private _writes=[];
        ACME_fnc_clinicalEpoch={1};ACME_fnc_treatmentSupplyCount={1};
        ACME_fnc_pressureInfuserStateCommit={params ["_p","_key","_value"];_writes pushBack _key;
            _p setVariable [["ACME_piCuffs","ACME_piReceipts"] select (_key=="receipts"),_value];};
        CBA_fnc_targetEvent={_acks pushBack _this;};
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",500,0,0,0,0,0,0,"bag-one"]]]]];
    '''+invalid+'''
        [_patient,_medic,"bag-one",_epoch,"request-one",0,true] call _commit;
        [_patient,_medic,"bag-one",_epoch,"request-one",0,true] call _commit;
    '''+f'''
        [count _acks==2 && {{(((_acks select 0) select 1) select 1) isEqualTo {str(accepted).lower()}}},"wrong corpse cuff acknowledgement"] call _check;
        [({{_x=="cuffs"}} count _writes)=={int(accepted)},"cuff accepted twice or guard bypassed"] call _check;
    ''')


def test_treatment_execution_and_delayed_preparation_use_same_uncached_policy():
    source=(ROOT/'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    entry=source[:source.index('private _config =')]
    execute(admission_setup()+'private _entry={'+adapt(entry)+'true};'+'''
        [[_medic,_patient,"head","CheckAirway"] call _entry,"native executor discarded corpse exception"] call _check;
        _inventory=false;
        [!([_medic,_patient,"head","CheckAirway"] call _entry),"native executor discarded item checks"] call _check;
    ''')
    wrapper=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    assert 'private _stillTreatable = _args call ace_medical_treatment_fnc_canTreatCached;' in wrapper
    assert '_classKey == "checkbreathing" && {!alive _p}' not in wrapper


def test_assessment_config_conditions_accept_dead_patient_without_reanimation():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    airway=config.split('class CheckAirway {',1)[1].split('class RecoveryPosition:',1)[0]
    breathing=config.split('class CheckBreathing {',1)[1].split('class UseStethoscope',1)[0]
    conditions=[re.search(r'condition = "([^"]+)";',source)[1] for source in (airway,breathing)]
    execute('ACM_airway_enable=true;ace_common_fnc_isAwake={false};_patientAlive=false;'+''.join(
        '[call {'+adapt(condition)+'},"dead assessment config rejected"] call _check;' for condition in conditions))


@pytest.mark.parametrize('invalid', ['', '_alive=false;', '_distance=4;', '_inventory=false;'])
def test_exposed_hpmk_cpr_normalization_keeps_common_corpse_guards(invalid):
    execute(admission_setup()+'''
        _stockAllows=true;_patient setVariable ["ACME_hpmk_state","exposed"];
        _configValues set ["allowedSelections",["body"]];
    '''+invalid+f'''
        private _allowed=[_medic,_patient,"rightleg","CPR"] call ace_medical_treatment_fnc_canTreatCached;
        [_allowed isEqualTo {str(not invalid).lower()},"CPR normalization bypassed corpse guards"] call _check;
    ''')


@pytest.mark.parametrize('action',["ACME_InsertChestTube","ACME_CloseIncision"])
@pytest.mark.parametrize('eligible',[False,True])
def test_dead_thoracic_actions_preserve_current_per_side_and_tube_conditions(action,eligible):
    execute(admission_setup()+f'''
        _stockAllows={str(eligible).lower()};
        private _result=[_medic,_patient,"body","{action}"] call ace_medical_treatment_fnc_canTreatCached;
        [_result isEqualTo {str(eligible).lower()},"corpse action discarded current treatment condition"] call _check;
        [_stockCalls==1,"current action condition not evaluated"] call _check;
    ''')


def test_dead_airway_evidence_keeps_mission_feature_setting():
    execute(admission_setup()+'''
        missionNamespace setVariable ["ACM_airway_enable",false];
        [!([_medic,_patient,"head","CheckAirway"] call ace_medical_treatment_fnc_canTreatCached),"disabled airway assessment remained usable"] call _check;
        _patient setVariable ["ACM_airway_AirwayItem_Oral","OPA"];
        [!([_medic,_patient,"head","RemoveOPA"] call ace_medical_treatment_fnc_canTreatCached),"disabled airway removal remained usable"] call _check;
    ''')
