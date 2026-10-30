"""Run imported ocular treatment, recovery and lifecycle decisions in SQF-VM.

Arma item slots, controls, CBA transport and effect commands are explicit boundaries.
The production owner/epoch checks, side selection, recovery and cleanup execute unchanged.
"""
import json
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute
from test_bounded_selector_lifetime import ui_commands
from test_historical_vial_execution import map_defaults


OCULAR = ROOT / "addons/ophthalmology"


def source(name, component="ophthalmology"):
    folder = ROOT / "addons" / component.lower()
    path = folder / (name if name.endswith(".sqf") else f"functions/fnc_{name}.sqf")
    text = path.read_text()
    text = re.sub(r"^TRACE_.*$", "", text, flags=re.M)
    text = re.sub(r"\bLINKFUNC\((\w+)\)", lambda m: f"ACM_{component}_fnc_{m[1]}", text)
    text = re.sub(r"\bGET_DUST_INJURY\((\w+)\)", lambda m: f'(({m[1]} getVariable ["ACM_ophthalmology_dustInjuryLight",0])+({m[1]} getVariable ["ACM_ophthalmology_dustInjuryHeavy",0]))', text)
    text = re.sub(r"\bACELSTRING\([^)]*\)", '"text"', text)
    for var in ("_patient", "_unit", "_player", "ACE_player", "_x"):
        text = text.replace(f"local {var}", "_patientLocal")
        text = text.replace(f"alive {var}", "_livePatient")
        text = text.replace(f"hmd {var}", "_hmd")
    text = text.replace("finite _x", "(_x isEqualType 0)")
    text = re.sub(r"\bfinite (_\w+)", r"(\1 isEqualType 0)", text)
    text = text.replace("canSuspend", "false").replace("serverTime", "_serverClock")
    text = text.replace("clientOwner", "_machineOwner")
    text = text.replace("isDamageAllowed _unit", "_damageAllowed")
    text = text.replace("local _medic", "_medicLocal")
    text = text.replace("_medic != _patient", "!(_medic isEqualTo _patient)")
    text = text.replace("_unit == ACE_player", "(_unit isEqualTo ACE_player)")
    text = text.replace("_patient unlinkItem _existingHmd;", '_unlinked pushBack _existingHmd;_hmd="";')
    text = text.replace("_patient unlinkItem _shield;", '_unlinked pushBack _shield;_hmd="";')
    text = text.replace("_patient linkItem _shieldItem;", "_linked pushBack _shieldItem;_hmd=_shieldItem;")
    text = text.replace("allUnits", "_allUnits")
    text = text.replace("allDeadMen", "_allDeadMen")
    text = text.replace('_patient isKindOf "CAManBase"', "true")
    # SQF-VM lacks this native command; preserve its interpolation/clamping exactly.
    text = re.sub(r"\blinearConversion (\[[^\n;]*?\])", r"(\1 call _linear)", text)
    return map_defaults(adapt(text, component))


def function(name):
    return f"ACM_ophthalmology_fnc_{name}={{" + source(name) + "};\n"


SETUP = r'''
private _patientLocal=true;private _livePatient=true;private _hmd="";private _damageAllowed=true;private _medicLocal=true;
private _serverClock=100;
private _machineOwner=7;
private _unit=_patient;private _events=[];private _linked=[];private _unlinked=[];private _stowed=[];
private _triage=[];private _logs=[];private _evacs=[];private _shown=[];private _hidden=0;
private _visualReset=0;private _dustEffects=[];private _traumaEffects=[];private _blinks=[];
private _allUnits=[];private _allDeadMen=[];private _handlers=[];private _classHandlers=[];private _pfhs=[];
private _ownerEvents=[];private _removedPFHs=[];
private _linear={params ["_lo","_hi","_value","_a","_b",["_clamp",false]];
    private _fraction=(_value-_lo)/(_hi-_lo);
    if (_clamp) then {_fraction=(_fraction max 0) min 1;};_a+(_b-_a)*_fraction;};
private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
    if (_key in _map) then {_map get _key} else {_default}};
CBA_missionTime=100;
ACM_ophthalmology_enable=true;ACM_ophthalmology_structuralRecoveryMinutes=1;
ACM_ophthalmology_activePatients=[];
ACM_ophthalmology_fnc_showEyeShieldOverlay={_shown pushBack (_this select 0);};
ACM_ophthalmology_fnc_hideEyeShieldOverlay={_hidden=_hidden+1;};
ACM_ophthalmology_fnc_resetVisualEffects={_visualReset=_visualReset+1;};
ACM_ophthalmology_fnc_effectEyeInjury={_dustEffects pushBack _this;};
ACM_ophthalmology_fnc_effectHurtEye={_traumaEffects pushBack _this;};
ACM_ophthalmology_fnc_effectEyeBlink={_blinks pushBack _this;};
ACM_ophthalmology_fnc_getEyeProtection={0};
ACM_ophthalmology_fnc_shieldSource={};
ACM_ophthalmology_fnc_shieldRecover={};
CBA_fnc_targetEvent={_events pushBack _this;};
CBA_fnc_ownerEvent={_ownerEvents pushBack _this;};
CBA_fnc_addEventHandler={_handlers pushBack _this;count _handlers;};
CBA_fnc_addClassEventHandler={_classHandlers pushBack _this;count _classHandlers;};
CBA_fnc_addPerFrameHandler={_pfhs pushBack _this;count _pfhs;};
CBA_fnc_removePerFrameHandler={_removedPFHs pushBack _this;};
ace_common_fnc_addToInventory={_stowed pushBack (_this select 1);[false,missionNamespace]};
ace_medical_treatment_fnc_addToTriageCard={_triage pushBack _this;};
ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
ACME_fnc_evacuationRequirementCommit={
    _evacs pushBack _this;(_this select 0) setVariable ["ACME_requiresEvac",true];
};
_patient setVariable ["ACME_clinicalEpoch",7];
_patient setVariable ["ACME_equipmentKitEpoch",3];
_patient setVariable ["ACM_ophthalmology_eyeInjuries",[1,1]];
_patient setVariable ["ACM_ophthalmology_eyeShieldItem",""];
_patient setVariable ["ACM_ophthalmology_eyeShieldIndex",-1];
'''


def definitions(*names):
    return SETUP + "".join(function(name) for name in names)


def funded_shield():
    refund = (ROOT / 'addons/acm_extended/functions/fn_treatmentSupplyRefund.sqf').read_text()
    refund = refund.replace('_vehicle addItemCargoGlobal [_item, 1];', '_vehicleReturns pushBack [_vehicle,_item,1];_realStock=_realStock+1;')
    return definitions("eyeShieldCondition", "shieldStart", "shieldProgress", "shieldCancel", "shieldSource", "shieldCommit", "treatmentAdvanced_eyeShield") + '''
        private _realStock=4;private _debits=0;private _returns=[];private _serial=0;
        private _reserveVehicle=objNull;private _vehicleReturns=[];
        ACME_fnc_patientInteractionDistance={1};
        ace_common_fnc_getName={"name"};
        ace_common_fnc_addToInventory={
            _stowed pushBack (_this select 1);
            if ((_this select 1)=="kat_eyecovers") then {_realStock=_realStock+1;_returns pushBack _this;};
            [false,missionNamespace]
        };
        ACME_fnc_treatmentSupplyTake={
            params ["_m","_p","_items"];
            if (_realStock<=0) exitWith {[]};
            _realStock=_realStock-1;_debits=_debits+1;_serial=_serial+1;
            private _receipt=[_m,"kat_eyecovers",_reserveVehicle,format ["7:%1",_serial]];
            private _ledger=missionNamespace getVariable ["ACME_supplyReceipts",createHashMap];
            _ledger set [_receipt select 3,+_receipt];missionNamespace setVariable ["ACME_supplyReceipts",_ledger];
            _receipt
        };
        ACME_fnc_treatmentSupplyRefund={''' + map_defaults(adapt(refund)) + '''};
        private _args=[_medic,_patient,"Head","EyeShield",objNull,"",false];
        private _start={_args call ACM_ophthalmology_fnc_shieldStart;};
        private _finish={_args call ACM_ophthalmology_fnc_treatmentAdvanced_eyeShield;};
        private _dispatch={
            private _message=(_events select ((count _events)-1)) select 1;
            _message call ACM_ophthalmology_fnc_shieldCommit;
        };
        private _ack={
            private _results=_ownerEvents select {(_x select 0)=="ACM_ophthalmology_shieldResult"};
            private _message=(_results select ((count _results)-1)) select 1;
            ["result",_message] call ACM_ophthalmology_fnc_shieldSource;
            {
                private _p=_x select 1;
                ["settled",_p select 0,0,_p select 1] call ACM_ophthalmology_fnc_shieldCommit;
            } forEach +(_events select {(_x select 0)=="ACM_ophthalmology_shieldSettled"});
            {["closed",_x select 1] call ACM_ophthalmology_fnc_shieldSource;} forEach +(_ownerEvents select {(_x select 0)=="ACM_ophthalmology_shieldClosed"});
        };
    '''


@pytest.mark.parametrize("eyes,index,item", [([0, 1], 0, "kat_eyecovers_right"), ([1, 0], 1, "kat_eyecovers_left"), ([0, 0], 0, "kat_eyecovers_right"), ([0.6, 0.2], 1, "kat_eyecovers_left")])
def test_shield_callback_dispatches_the_correct_anatomical_eye_with_its_epoch(eyes, index, item):
    execute(funded_shield() + f'''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",{json.dumps(eyes)}];
        call _start;call _finish;
        [count _events==1,"shield did not produce one owner request"] call _check;
        private _request=((_events select 0) select 1) select 1;
        [(_request select 10)=={index} && {{(_request select 3)==7}} && {{(_request select 4)==3}},"shield side or clinical/kit epoch inverted"] call _check;
        [count _linked==0,"provider mutated remote HMD slot"] call _check;
        call _dispatch;call _ack;
        [_linked isEqualTo ["{item}"],"owner equipped wrong anatomical shield"] call _check;
    ''')


def shield_handler():
    return 'private _applyShield={_this call ACM_ophthalmology_fnc_shieldCommit;};'


@pytest.mark.parametrize("invalid", ["epoch", "kit_epoch", "healthy", "remote", "dead", "index", "wrong_item", "already_shielded"])
def test_owner_refuses_stale_or_invalid_shield_application(invalid):
    changes = {
        "epoch": '_patient setVariable ["ACME_clinicalEpoch",8];', "kit_epoch": '_patient setVariable ["ACME_equipmentKitEpoch",4];', "healthy": '_patient setVariable ["ACM_ophthalmology_eyeInjuries",[1,1]];',
        "remote": "_patientLocal=false;", "dead": "_livePatient=false;", "index": "_request set [10,2];",
        "wrong_item": '_request set [8,[_medic,"wrong",objNull,"7:1"]];', "already_shielded": '_hmd="kat_eyecovers_left";',
    }
    execute(funded_shield() + shield_handler() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;
        private _request=+(((_events select 0) select 1) select 1);
    ''' + changes[invalid] + '''
        ["apply",_request,0] call _applyShield;
        [count _linked==0 && {count _stowed==0},"invalid request changed equipment"] call _check;
        [(_patient getVariable ["ACM_ophthalmology_eyeShieldItem",""])=="","invalid request applied shield state"] call _check;
    ''')


def test_owner_application_is_idempotent_and_uses_ace_full_inventory_fallback():
    execute(funded_shield() + shield_handler() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _hmd="NVG_modded";
        call _start;call _finish;call _dispatch;call _dispatch;
        call _ack;call _ack;
        [_linked isEqualTo ["kat_eyecovers_right"],"duplicate event equipped twice"] call _check;
        [_stowed isEqualTo ["NVG_modded"],"displaced HMD skipped ACE inventory/holder handling"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeShieldIndex")==0,"right-eye index changed"] call _check;
        [ACM_ophthalmology_activePatients isEqualTo [_patient],"patient not registered once"] call _check;
        [_debits==1 && {count _returns==0} && {_realStock==3},"accepted duplicate did not consume exactly one funded shield"] call _check;
    ''')


@pytest.mark.parametrize("remote", [False, True])
def test_wash_clears_irritants_on_owner_without_healing_structural_trauma(remote):
    execute(definitions("clearEyeInjury") + f'''
        _patientLocal={str(not remote).lower()};
        _patient setVariable ["ACM_ophthalmology_dustInjuryLight",3];
        _patient setVariable ["ACM_ophthalmology_dustInjuryHeavy",2];
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        [_patient] call ACM_ophthalmology_fnc_clearEyeInjury;
    ''' + ('''
        [count _events==1,"remote wash not dispatched"] call _check;
        [(_patient getVariable "ACM_ophthalmology_dustInjuryLight")==3,"provider wrote remote state"] call _check;
        _patientLocal=true;((_events select 0) select 1) call ACM_ophthalmology_fnc_clearEyeInjury;
    ''' if remote else '') + '''
        [(_patient getVariable "ACM_ophthalmology_dustInjuryLight")==0 && {(_patient getVariable "ACM_ophthalmology_dustInjuryHeavy")==0},"wash did not clear both irritants"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [0,1],"wash healed structural trauma"] call _check;
    ''')


def test_delayed_wash_cannot_clear_replacement_clinical_episode():
    execute(definitions("clearEyeInjury") + '''
        _patient setVariable ["ACM_ophthalmology_dustInjuryLight",3];
        [_patient,6] call ACM_ophthalmology_fnc_clearEyeInjury;
        [(_patient getVariable "ACM_ophthalmology_dustInjuryLight")==3,"old epoch cleared replacement eye injury"] call _check;
    ''')


@pytest.mark.parametrize("shield", [False, True])
def test_normal_recovery_is_faster_only_for_the_protected_eye(shield):
    execute(definitions("structuralTick") + f'''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,0]];
        _patient setVariable ["ACM_ophthalmology_structuralLastTick",99];
        _patient setVariable ["ACM_ophthalmology_eyeShieldItem","kat_eyecovers_right"];
        _patient setVariable ["ACM_ophthalmology_eyeShieldIndex",0];
        _hmd={json.dumps('kat_eyecovers_right' if shield else '')};
        [_patient] call ACM_ophthalmology_fnc_structuralTick;
        private _eyes=_patient getVariable "ACM_ophthalmology_eyeInjuries";
        [abs ((_eyes select 0)-{1/60 if shield else 1/120})<0.000001,"protected/unprotected recovery mismatch"] call _check;
        [abs ((_eyes select 1)-{1/120})<0.000001,"uncovered eye recovered at wrong speed"] call _check;
        [!(_patient getVariable ["ACME_requiresEvac",false]),"normal recovery created permanent evacuation"] call _check;
    ''')


def test_hardcore_latch_survives_setting_changes_until_definitive_full_heal():
    execute(definitions("structuralTick", "fullHealLocal") + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        missionNamespace setVariable ["ACME_hcEff_ophthalmology",true];
        [_patient] call ACM_ophthalmology_fnc_structuralTick;
        missionNamespace setVariable ["ACME_hcEff_ophthalmology",false];
        CBA_missionTime=105;
        [_patient] call ACM_ophthalmology_fnc_structuralTick;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [0,1],"setting toggle healed hardcore trauma"] call _check;
        [_patient getVariable ["ACM_ophthalmology_ocularPermanent",false],"hardcore latch cleared"] call _check;
        [_patient getVariable ["ACME_requiresEvac",false],"evacuation requirement missing"] call _check;
        [count _evacs==1,"evacuation commit repeated unnecessarily"] call _check;
        [_patient] call ACM_ophthalmology_fnc_fullHealLocal;
        [!(_patient getVariable ["ACM_ophthalmology_ocularPermanent",false]),"definitive reset retained ocular latch"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [1,1],"definitive reset failed"] call _check;
    ''')


@pytest.mark.parametrize("boundary", ["dead", "remote"])
def test_structural_tick_cannot_mutate_non_owned_or_dead_patient(boundary):
    execute(definitions("structuralTick") + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
    ''' + ('_livePatient=false;' if boundary == 'dead' else '_patientLocal=false;') + '''
        [_patient] call ACM_ophthalmology_fnc_structuralTick;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [0,1],"invalid owner advanced injury"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["handleDustInjury", "handleExplosion"])
def test_disabled_setting_rejects_new_injury_even_for_already_registered_handlers(kind):
    execute(definitions(kind) + '''
        ACM_ophthalmology_enable=false;
        [_patient,''' + ('"dust"' if kind == "handleDustInjury" else '1') + '''] call ACM_ophthalmology_fnc_''' + kind + ''';
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [1,1],"disabled setting created eye injury"] call _check;
        [count _blinks==0,"disabled setting created presentation"] call _check;
    ''')


@pytest.mark.parametrize("index,idc", [(0, 17102), (1, 17103)])
def test_visual_worker_follows_actual_shield_and_clears_on_unconsciousness(index, idc):
    item = ["kat_eyecovers_right", "kat_eyecovers_left"][index]
    execute(definitions("updateVisualEffects") + f'''
        missionNamespace setVariable ["ACE_player",_patient];
        missionNamespace setVariable ["ACM_ophthalmology_visualPlayer",_patient];
        _patient setVariable ["ACM_ophthalmology_eyeShieldItem","{item}"];
        _patient setVariable ["ACM_ophthalmology_eyeShieldIndex",{index}];_hmd="{item}";
        [] call ACM_ophthalmology_fnc_updateVisualEffects;
        [_shown isEqualTo [{idc}],"shield overlay covered wrong eye"] call _check;
        _patient setVariable ["ACE_isUnconscious",true];
        [] call ACM_ophthalmology_fnc_updateVisualEffects;
        [_visualReset==1,"unconscious patient retained old presentation"] call _check;
    ''')


def test_postinit_registers_only_one_worker_and_live_setting_handlers():
    execute(definitions("clearEyeInjury", "handleDustInjury", "handleExplosion", "fullHealLocal", "updateVisualEffects", "structuralTick", "shieldCommit", "shieldSource") +
            'ACM_ophthalmology_fnc_gui_updateInjuryListPart={};private _postinit={' + source("XEH_postInit.sqf") + '''};
        call _postinit;call _postinit;
        [count _pfhs==2,"postinit duplicated physiology or presentation worker"] call _check;
        private _settings=(_handlers select {(_x select 0)=="CBA_settingsInitialized"}) select 0;
        ACM_ophthalmology_enable=false;call (_settings select 1);call (_settings select 1);
        [count _classHandlers==1,"settings initialization duplicated blast handler"] call _check;
        [count (_handlers select {(_x select 0)=="ace_goggles_effect"})==1,"disabled initial setting prevented later activation"] call _check;
    ''')


def test_build_identity_and_native_item_consumption_are_declared():
    config = (OCULAR / "config.cpp").read_text()
    actions = (OCULAR / "ACE_Medical_Treatment_Actions.hpp").read_text()
    assert 'ACME_BUILD_CONFIG("ophthalmology")' in config
    assert 'consumeItem = 1;' in actions
    assert 'items[] = {"KAT_Eyewasher"};' in actions
    assert '"kat_eyecovers"' in actions
    assert '[true],' in (OCULAR / "initSettings.inc.sqf").read_text().split('QGVAR(enable)', 1)[1].split('call CBA_fnc_addSetting', 1)[0]


@pytest.mark.parametrize("start", [0.9989, 0.9991, 0.9999])
def test_normal_recovery_reaches_exact_healthy_state_before_worker_retirement(start):
    execute(definitions("structuralTick") + f'''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[{start},1]];
        _patient setVariable ["ACM_ophthalmology_structuralLastTick",99];
        [_patient] call ACM_ophthalmology_fnc_structuralTick;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [1,1],"recovery tolerance stranded an injury label"] call _check;
    ''')


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("irritant", ["dustInjuryLight", "dustInjuryHeavy"])
def test_cbrn_water_actions_discover_ocular_irritation_without_requiring_chemical_exposure(enabled, irritant):
    execute(SETUP + 'private _canWash={' + source("canWashEyes", "CBRN") + '};' + f'''
        ACM_ophthalmology_enable={str(enabled).lower()};
        _patient setVariable ["ACM_ophthalmology_{irritant}",2];
        [([_patient] call _canWash) isEqualTo {str(enabled).lower()},"water action ignored enabled ocular irritation"] call _check;
        _patient setVariable ["ACM_CBRN_Chemical_CS_WasExposed",true];
        [([_patient] call _canWash),"ocular setting suppressed existing chemical water treatment"] call _check;
    ''')


@pytest.mark.parametrize("bottle,replacement", [("ACE_Canteen", "ACE_Canteen_Half"), ("ACE_WaterBottle_Half", "ACE_WaterBottle_Empty"), ("ACE_salineIV", "")])
def test_cbrn_wash_clears_ocular_irritants_preserves_chemical_blindness_and_returns_only_real_bottle_types(bottle, replacement):
    execute(definitions("clearEyeInjury") + 'private _wash={' + source("washEyes", "CBRN") + '};' + f'''
        _medic=_patient;private _blindChanges=[];
        ace_common_fnc_getName={{"name"}};ace_common_fnc_displayTextStructured={{}};
        ACM_CBRN_fnc_setBlind={{_blindChanges pushBack _this;}};
        _patient setVariable ["ACM_ophthalmology_dustInjuryLight",2];
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _patient setVariable ["ACM_CBRN_Chemical_Chlorine_Blindness",true];
        [_medic,_patient,"{bottle}",objNull] call _wash;
        [(_patient getVariable "ACM_ophthalmology_dustInjuryLight")==0,"CBRN wash did not invoke ocular owner clear"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [0,1],"CBRN wash cured structural injury"] call _check;
        [count _blindChanges==0,"CBRN wash removed permanent chemical blindness"] call _check;
        [_stowed isEqualTo {json.dumps([replacement] if replacement else [])},"unrecognized consumed class fabricated bottle replacement"] call _check;
    ''')


def test_overlay_repeated_refresh_keeps_one_display_and_changes_both_sides_consistently():
    text = source("showEyeShieldOverlay")
    text = text.replace('_display displayCtrl _x', '_x').replace('_display displayCtrl _eyeDisplay', '_eyeDisplay')
    text = text.replace('(_x) ctrlShow', '_x ctrlShow')
    text = ui_commands(text)
    execute(SETUP + 'private _show={' + text + '''};
        private _writes=[];private _write={_writes pushBack _this;};
        uiNamespace setVariable ["ACM_EyeShield",_patient];
        [17102] call _show;private _count=count _writes;
        [17102] call _show;
        [count _writes==_count,"unchanged overlay was repainted/recreated"] call _check;
        [17103] call _show;
        [[17102,"ctrlShow",false] in _writes && {[17103,"ctrlShow",true] in _writes},"eye switch retained wrong shield side"] call _check;
    ''')


def blink_source():
    text = source("effectEyeBlink").replace('isNull objNull', 'false')
    text = re.sub(r"\bQPATHTOF\([^)]*\)", '"texture"', text)
    text = re.sub(r"ppEffectCreate \[[^]]*\]", "17", text)
    text = re.sub(r"ACM_ophthalmology_ppBlurBlink (ppEffect\w+) ([^;]+);", lambda m: f'["{m[1]}",{m[2]}] call _effect;', text)
    text = text.replace('objNull ctrlCreate ["RscPicture", -1]', 'missionNamespace')
    for old, new in [("safeZoneXAbs", "0"), ("safeZoneWAbs", "1"), ("safeZoneY", "0"), ("safeZoneH", "1")]:
        text = text.replace(old, new)
    return ui_commands(text)


def reset_visual_source():
    text = source("resetVisualEffects")
    text = text.replace('ctrlDelete _x;', '_deleted pushBack _x;')
    return re.sub(r"ACM_ophthalmology_ppBlurBlink (ppEffect\w+) ([^;]+);", lambda m: f'["{m[1]}",{m[2]}] call _effect;', text)


def test_new_blink_and_reset_retire_old_delayed_open_and_blur_callbacks():
    execute(SETUP + 'private _blink={' + blink_source() + '};ACM_ophthalmology_fnc_resetVisualEffects={' + reset_visual_source() + '''};
        private _writes=[];private _write={_writes pushBack _this;};
        private _effects=[];private _effect={_effects pushBack _this;};
        private _deleted=[];
        private _scheduled=[];CBA_fnc_waitAndExecute={_scheduled pushBack _this;};
        uiNamespace setVariable ["ACM_ophthalmology_blinkControls",[_patient,_medic]];
        [0.2,true] call _blink;
        private _first=_scheduled select 0;
        [0.2,true] call _blink;
        private _second=_scheduled select 1;
        private _before=count _writes;
        (_first select 1) call (_first select 0);
        [count _writes==_before && {count _scheduled==2},"old blink opened or disabled the replacement blink"] call _check;
        (_second select 1) call (_second select 0);
        [count _scheduled==3,"current blink failed to schedule blur release"] call _check;
        private _release=_scheduled select 2;
        [] call ACM_ophthalmology_fnc_resetVisualEffects;
        [count _deleted==2,"reset left the previous blink controls alive"] call _check;
        [(_effects select ((count _effects)-1)) isEqualTo ["ppEffectEnable",false],"reset left shock blur enabled"] call _check;
        [(_dustEffects select 0) isEqualTo [false,0] && {(_traumaEffects select 0) isEqualTo [false,[1,1]]},"reset failed to clear persistent eye presentation"] call _check;
        private _effectsBefore=count _effects;
        (_release select 1) call (_release select 0);
        [count _effects==_effectsBefore,"old blur callback disabled a newer generation"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["handleDustInjury", "handleExplosion"])
def test_enabled_injury_handlers_register_real_structural_casualty_for_recovery(kind):
    execute(definitions(kind) + '''
        ACE_player=_patient;
        ACM_ophthalmology_probability_dust=100;ACM_ophthalmology_probability_dust_heavy=100;
        _patient setVariable ["ACM_ophthalmology_dustInjuryLight",4];
        _patient setVariable ["ACM_ophthalmology_dustInjuryHeavy",4];
        [_patient,''' + ('"dust"' if kind == "handleDustInjury" else '1') + '''] call ACM_ophthalmology_fnc_''' + kind + ''';
        [({_x<1} count (_patient getVariable "ACM_ophthalmology_eyeInjuries"))>0,"enabled handler failed to create structural trauma"] call _check;
        [ACM_ophthalmology_activePatients isEqualTo [_patient],"injury left patient outside recovery worker"] call _check;
        [(_patient getVariable "ACM_ophthalmology_structuralLastTick")==100,"new injury inherited an old owner clock"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["handleDustInjury", "handleExplosion"])
@pytest.mark.parametrize("protection", ["engine", "ace"])
def test_injury_handlers_respect_training_and_scenario_invulnerability(kind, protection):
    execute(definitions(kind) + '''
        ACE_player=_patient;
        ACM_ophthalmology_probability_dust=100;ACM_ophthalmology_probability_dust_heavy=100;
    ''' + ('_damageAllowed=false;' if protection == 'engine' else '_patient setVariable ["ace_medical_allowDamage",false];') + '''
        [_patient,''' + ('"dust"' if kind == "handleDustInjury" else '1') + '''] call ACM_ophthalmology_fnc_''' + kind + ''';
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [1,1],"invulnerable casualty received ocular trauma"] call _check;
        [count _blinks==0,"invulnerable casualty received injury presentation"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["shield", "wash"])
def test_locality_rerouting_is_bounded_and_never_refreshes_original_epochs(kind):
    execute((funded_shield() if kind == "shield" else definitions("clearEyeInjury")) + shield_handler() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _patient setVariable ["ACM_ophthalmology_dustInjuryLight",2];
    ''' + ('''
        call _start;call _finish;
        private _request=((_events select 0) select 1) select 1;
        _events=[];_patientLocal=false;
        ["apply",_request,0] call _applyShield;
        private _packet=(_events select 0) select 1;
        [_packet isEqualTo ["apply",_request,1,[]],"reroute changed original shield epoch"] call _check;
        _packet set [2,4];_events=[];_packet call _applyShield;
        [count _events==0,"shield reroute has no hop bound"] call _check;
        _patientLocal=true;_packet call _applyShield;
        [_linked isEqualTo ["kat_eyecovers_right"],"new owner failed to apply original valid shield"] call _check;
    ''' if kind == "shield" else '''
        _patientLocal=false;
        [_patient,7,0] call ACM_ophthalmology_fnc_clearEyeInjury;
        private _packet=(_events select 0) select 1;
        [_packet isEqualTo [_patient,7,1],"reroute refreshed wash epoch"] call _check;
        _packet set [2,4];_events=[];_packet call ACM_ophthalmology_fnc_clearEyeInjury;
        [count _events==0,"wash reroute has no hop bound"] call _check;
        _patientLocal=true;_packet call ACM_ophthalmology_fnc_clearEyeInjury;
        [(_patient getVariable "ACM_ophthalmology_dustInjuryLight")==0,"new owner did not apply valid wash"] call _check;
    '''))


def test_native_reconcile_adopts_a_new_owner_clock_without_catchup_and_retires_only_membership():
    execute(definitions("structuralTick", "reconcile") + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _patient setVariable ["ACM_ophthalmology_structuralLastTick",-900];
        [_patient,true] call ACM_ophthalmology_fnc_reconcile;
        [(_patient getVariable "ACM_ophthalmology_structuralLastTick")==100,"new owner retained old machine clock"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [0,1],"owner adoption fabricated elapsed recovery"] call _check;
        [ACM_ophthalmology_activePatients isEqualTo [_patient],"restored trauma not enrolled"] call _check;
        [_patient,false,true] call ACM_ophthalmology_fnc_reconcile;
        [ACM_ophthalmology_activePatients isEqualTo [],"retire did not remove local membership"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [0,1],"retirement erased durable eye injury"] call _check;
    ''')


@pytest.mark.parametrize("state", ["healthy", "dust", "remote", "dead"])
def test_native_reconcile_handles_non_structural_and_unowned_states_without_rewriting_durable_state(state):
    changes = {"healthy": "", "dust": '_patient setVariable ["ACM_ophthalmology_dustInjuryLight",2];', "remote": '_patientLocal=false;', "dead": '_livePatient=false;'}
    execute(definitions("structuralTick", "reconcile") + '''
        private _before=str (_patient getVariable "ACM_ophthalmology_eyeInjuries");
        private _ticks=0;ACM_ophthalmology_fnc_structuralTick={_ticks=_ticks+1;};
    ''' + changes[state] + '''
        [_patient,true] call ACM_ophthalmology_fnc_reconcile;
        [_ticks==0,"non-structural or unowned state ran structural physiology"] call _check;
        [str (_patient getVariable "ACM_ophthalmology_eyeInjuries")==_before,"adoption rewrote durable eye state"] call _check;
    ''')


def test_two_funded_medics_consume_one_shield_and_refund_only_the_rejected_donor_once():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;
        private _args2=[missionNamespace,_patient,"Head","EyeShield",objNull,"",false];
        _args2 call ACM_ophthalmology_fnc_shieldStart;
        call _finish;_args2 call ACM_ophthalmology_fnc_treatmentAdvanced_eyeShield;
        private _first=(_events select 0) select 1;private _second=(_events select 1) select 1;
        _first call ACM_ophthalmology_fnc_shieldCommit;
        _second call ACM_ophthalmology_fnc_shieldCommit;
        { ["result",_x select 1] call ACM_ophthalmology_fnc_shieldSource; } forEach +_ownerEvents;
        _second call ACM_ophthalmology_fnc_shieldCommit;call _ack;
        [_debits==2 && {count _returns==1} && {_realStock==3},"race did not spend one and refund one exact reservation"] call _check;
        [((_returns select 0) select 0) isEqualTo missionNamespace,"rejected shield refunded the wrong donor"] call _check;
        [_linked isEqualTo ["kat_eyecovers_right"],"race equipped extra shields"] call _check;
        [count (missionNamespace getVariable ["ACME_supplyReceipts",createHashMap])==0,"settled race retained a real supply receipt"] call _check;
    ''')


def test_cancellation_before_finish_refunds_native_receipt_and_old_success_cannot_send_apply():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;_args call ACM_ophthalmology_fnc_shieldCancel;call _finish;
        [_realStock==4 && {count _returns==1},"cancel did not return exactly the reserved shield"] call _check;
        [count (_events select {(_x select 0)=="ACM_ophthalmology_applyEyeShield"})==0,"late success sent an unfunded placement"] call _check;
        [count _linked==0,"cancelled reservation equipped a shield"] call _check;
    ''')


@pytest.mark.parametrize("first", ["cancel", "apply"])
def test_apply_cancel_order_has_one_immutable_owner_outcome_and_late_packets_cannot_create_free_equipment(first):
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;
        private _apply=(_events select 0) select 1;
        _args call ACM_ophthalmology_fnc_shieldCancel;
        private _cancel=(_events select 1) select 1;
    ''' + ('_cancel call ACM_ophthalmology_fnc_shieldCommit;' if first == 'cancel' else '_apply call ACM_ophthalmology_fnc_shieldCommit;') + '''
        call _ack;
        _apply call ACM_ophthalmology_fnc_shieldCommit;_cancel call ACM_ophthalmology_fnc_shieldCommit;
        call _ack;call _ack;
    ''' + ('''
        [_realStock==4 && {count _returns==1} && {count _linked==0},"late apply created equipment after a funded refund"] call _check;
    ''' if first == 'cancel' else '''
        [_realStock==3 && {count _returns==0} && {count _linked==1},"late cancel refunded an already applied shield"] call _check;
    '''))


@pytest.mark.parametrize("boundary", ["clinical", "patient_kit", "medic_kit", "provider_period"])
def test_stale_owner_rejection_refunds_its_actual_supply_once(boundary):
    change = {
        "clinical": '_patient setVariable ["ACME_clinicalEpoch",8];',
        "patient_kit": '_patient setVariable ["ACME_equipmentKitEpoch",4];',
        "medic_kit": '_medic setVariable ["ACME_equipmentKitEpoch",1];',
        "provider_period": '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    }[boundary]
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;
    ''' + change + '''
        call _dispatch;call _ack;call _ack;
        [_realStock==4 && {count _returns==1} && {count _linked==0},"stale request lost or duplicated its funded item"] call _check;
        [count (_medic getVariable ["ACM_ophthalmology_shieldBindings",[]])==0,"settled rejected shield still blocks checkpoint"] call _check;
    ''')


def test_owner_waits_for_funding_replication_and_unfunded_packet_cannot_place_or_refund():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;
        private _bindings=_medic getVariable "ACM_ophthalmology_shieldBindings";
        _medic setVariable ["ACM_ophthalmology_shieldBindings",[]];
        call _dispatch;
        [count _linked==0 && {count _ownerEvents==0} && {count _returns==0},"missing funding was treated as authority or refundable failure"] call _check;
        _medic setVariable ["ACM_ophthalmology_shieldBindings",_bindings];
        call _dispatch;call _ack;
        [_realStock==3 && {count _linked==1},"replicated funded retry did not settle once"] call _check;
    ''')


def test_result_settles_at_original_funding_machine_after_medic_locality_change():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;call _dispatch;
        _medicLocal=false;call _ack;call _ack;
        [_realStock==3 && {count _returns==0},"medic handoff stranded or duplicated the original receipt"] call _check;
        [count (missionNamespace getVariable ["ACME_supplyReceipts",createHashMap])==0,"original machine retained settled source receipt"] call _check;
        _medicLocal=true;["cleanup",[_medic]] call ACM_ophthalmology_fnc_shieldSource;
        [count (_medic getVariable ["ACM_ophthalmology_shieldBindings",[]])==0,"new provider owner did not retire terminal binding"] call _check;
    ''')


def test_timeout_cancels_through_owner_before_refunding_and_late_apply_stays_rejected():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;private _apply=(_events select 0) select 1;
        _serverClock=140;["tick",[]] call ACM_ophthalmology_fnc_shieldSource;
        private _cancel=(_events select ((count _events)-1)) select 1;
        [(_cancel select 0)=="cancel","expired delivery did not request owner cancellation"] call _check;
        [count _returns==0,"timeout refunded before authoritative outcome"] call _check;
        _cancel call ACM_ophthalmology_fnc_shieldCommit;call _ack;
        _apply call ACM_ophthalmology_fnc_shieldCommit;call _ack;
        [_realStock==4 && {count _returns==1} && {count _linked==0},"timeout refund enabled late free shield"] call _check;
    ''')


def test_no_stock_start_cannot_progress_or_manufacture_failure_refund():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _realStock=0;call _start;
        [!([_args,0,2,-1] call ACM_ophthalmology_fnc_shieldProgress),"unfunded start progressed"] call _check;
        _args call ACM_ophthalmology_fnc_shieldCancel;call _finish;
        [_realStock==0 && {_debits==0} && {count _returns==0} && {count _linked==0},"empty stock manufactured shield or refund"] call _check;
    ''')


def test_native_callback_array_keeps_exact_reservation_and_configuration_disables_ace_second_debit():
    text=(ROOT/'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    assert '_callbackArgs call _callbackStart;' in text
    assert text.index('_callbackArgs call _callbackStart;') < text.index('    _callbackArgs,\n')
    actions=(OCULAR/'ACE_Medical_Treatment_Actions.hpp').read_text().split('class EyeShield:',1)[1]
    assert 'consumeItem = 0;' in actions
    for callback in ('shieldStart','shieldProgress','shieldCancel'):
        assert f'QFUNC({callback})' in actions


def test_rejected_vehicle_supply_returns_to_its_original_vehicle_once():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _reserveVehicle=missionNamespace;call _start;call _finish;
        _patient setVariable ["ACME_clinicalEpoch",8];
        call _dispatch;call _ack;call _ack;
        [_vehicleReturns isEqualTo [[missionNamespace,"kat_eyecovers",1]],"vehicle-funded rejection changed donor or refunded twice"] call _check;
        [_realStock==4 && {count _returns==0},"vehicle reservation became provider stock"] call _check;
    ''')


def test_native_progress_failure_after_reset_returns_only_the_reserved_item():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;
        [[_args,0,2,-1] call ACM_ophthalmology_fnc_shieldProgress,"funded treatment did not progress"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",8];
        [!([_args,1,2,-1] call ACM_ophthalmology_fnc_shieldProgress),"clinical reset left native progress valid"] call _check;
        _args call ACM_ophthalmology_fnc_shieldCancel;_args call ACM_ophthalmology_fnc_shieldCancel;call _finish;
        [_realStock==4 && {count _returns==1} && {count _linked==0},"native progress cancellation lost or duplicated reservation"] call _check;
    ''')


def test_early_cleanup_event_waits_for_late_settled_publication_then_prunes_key_and_worker():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;call _dispatch;
        private _request=((_events select 0) select 1) select 1;
        _medicLocal=false;call _ack;
        private _key="ACM_ophthalmology_shieldFunding_7_1";
        _medic setVariable [_key,[_request,"sent"]];
        _medicLocal=true;["cleanup",[_medic]] call ACM_ophthalmology_fnc_shieldSource;
        [count (_medic getVariable "ACM_ophthalmology_shieldBindings")==1,"early cleanup removed unresolved binding"] call _check;
        [!isNil "ACM_ophthalmology_shieldCleanupPFH","early cleanup did not keep reconciliation alive"] call _check;
        _medic setVariable [_key,[_request,"settled"]];
        ["cleanupTick",[]] call ACM_ophthalmology_fnc_shieldSource;
        [count (_medic getVariable "ACM_ophthalmology_shieldBindings")==0,"late terminal state stranded checkpoint binding"] call _check;
        [isNil {_medic getVariable _key},"settled per-request funding property leaked"] call _check;
        [isNil "ACM_ophthalmology_shieldCleanupPFH","empty cleanup worker stayed alive"] call _check;
    ''')


@pytest.mark.parametrize("reset", [False, True])
def test_applied_before_ack_handoff_adopts_original_decision_even_after_definitive_reset(reset):
    execute(funded_shield() + function("fullHealLocal") + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;call _dispatch;
        private _request=((_events select 0) select 1) select 1;
        private _original=missionNamespace getVariable "ACM_ophthalmology_shieldDecisions";
    ''' + ('''
        [_patient] call ACM_ophthalmology_fnc_fullHealLocal;
        _patient setVariable ["ACME_clinicalEpoch",8];
    ''' if reset else '') + '''
        _patient setVariable ["ACM_ophthalmology_shieldReceipts",createHashMap];
        missionNamespace setVariable ["ACM_ophthalmology_shieldDecisions",createHashMap];
        _patient setVariable ["ACME_providerLocalityEpoch",1];_machineOwner=9;
        ["cancel",_request,0] call ACM_ophthalmology_fnc_shieldCommit;
        [count _returns==0,"new owner guessed negative and refunded an applied shield"] call _check;
        [count (_ownerEvents select {(_x select 0)=="ACM_ophthalmology_shieldDecisionQuery"})==1,"new period did not query original decision authority"] call _check;
        _machineOwner=7;_patientLocal=false;
        missionNamespace setVariable ["ACM_ophthalmology_shieldDecisions",_original];
        ["proofQuery",_request] call ACM_ophthalmology_fnc_shieldCommit;
        _machineOwner=9;_patientLocal=true;
        missionNamespace setVariable ["ACM_ophthalmology_shieldDecisions",createHashMap];
        ["proof",_request,0,true] call ACM_ophthalmology_fnc_shieldCommit;
        _machineOwner=7;
        private _results=_ownerEvents select {(_x select 0)=="ACM_ophthalmology_shieldResult"};
        ["result",(_results select ((count _results)-1)) select 1] call ACM_ophthalmology_fnc_shieldSource;
        [_realStock==3 && {count _returns==0} && {count _linked==1},"original applied outcome was refunded or applied twice"] call _check;
    ''' + ('[_stowed isEqualTo ["kat_eyecovers_right"],"definitive reset lost the real previously fitted shield"] call _check;' if reset else ''))


def test_patient_custody_survives_deleted_provider_and_orphan_peer_retires_spent_without_free_stock():
    execute(funded_shield() + function("shieldRecover") + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;call _dispatch;
        private _request=((_events select 0) select 1) select 1;
        [count (_patient getVariable ["ACM_ophthalmology_shieldIncoming",createHashMap])==1,"physical write lacked patient-side custody fence"] call _check;
        // Original peer is gone; its private escrow/proof namespaces cannot be replayed.
        missionNamespace setVariable ["ACM_ophthalmology_shieldPending",createHashMap];
        missionNamespace setVariable ["ACME_supplyReceipts",createHashMap];
        missionNamespace setVariable ["ACM_ophthalmology_shieldDecisions",createHashMap];
        _patient setVariable ["ACM_ophthalmology_shieldReceipts",createHashMap];
        _patient setVariable ["ACME_providerLocalityEpoch",1];_machineOwner=9;
        _serverClock=170;[_patient] call ACM_ophthalmology_fnc_shieldRecover;
        ["cleanup",[_medic]] call ACM_ophthalmology_fnc_shieldSource;
        [count (_patient getVariable "ACM_ophthalmology_shieldIncoming")==0,"orphaned patient fence blocked capture forever"] call _check;
        [count (_medic getVariable "ACM_ophthalmology_shieldBindings")==0,"disconnected funding peer stranded provider binding"] call _check;
        ["apply",_request,0] call ACM_ophthalmology_fnc_shieldCommit;
        ["result",[_request,false]] call ACM_ophthalmology_fnc_shieldSource;
        [_realStock==3 && {count _returns==0} && {count _linked==1},"orphan retirement granted stock or resurrected late equipment"] call _check;
    ''')


def test_expired_unknown_owner_proof_retires_live_source_receipt_as_spent_and_closes_patient_fence():
    execute(funded_shield() + function("shieldRecover") + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _patientLocal=false;_patient setVariable ["ACME_vent_batterySwapOwnerPeriod",[9,0]];
        call _start;call _finish;
        private _request=((_events select 0) select 1) select 1;
        _patientLocal=true;_machineOwner=9;_medicLocal=false;
        _medic setVariable ["ACME_vent_batterySwapOwnerPeriod",[7,0]];
        call _dispatch;
        missionNamespace setVariable ["ACM_ophthalmology_shieldDecisions",createHashMap];
        _patient setVariable ["ACM_ophthalmology_shieldReceipts",createHashMap];
        _patient setVariable ["ACME_providerLocalityEpoch",1];_machineOwner=10;
        _serverClock=170;[_patient] call ACM_ophthalmology_fnc_shieldRecover;
        _machineOwner=7;_medicLocal=true;
        ["result",[_request,true]] call ACM_ophthalmology_fnc_shieldSource;
        [_realStock==3 && {count _returns==0},"unknown completed write minted a speculative refund"] call _check;
        _machineOwner=10;["settled",_request,0,"spent"] call ACM_ophthalmology_fnc_shieldCommit;
        _machineOwner=7;["closed",[_request,"spent"]] call ACM_ophthalmology_fnc_shieldSource;
        [count (missionNamespace getVariable ["ACME_supplyReceipts",createHashMap])==0,"conservative spent retirement retained supply receipt"] call _check;
        [count (missionNamespace getVariable ["ACM_ophthalmology_shieldPending",createHashMap])==0,"conservative retirement blocked source capture forever"] call _check;
        [count (_patient getVariable "ACM_ophthalmology_shieldIncoming")==0,"confirmed retirement retained patient fence"] call _check;
    ''')


def test_remote_provider_uses_public_owner_period_not_another_machines_private_counter():
    execute(funded_shield() + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        _medic setVariable ["ACME_providerLocalityEpoch",4];
        _medic setVariable ["ACME_vent_batterySwapOwnerPeriod",[7,4]];
        call _start;call _finish;
        // On the casualty owner this private value belongs to a different local machine.
        _medicLocal=false;_medic setVariable ["ACME_providerLocalityEpoch",0];
        call _dispatch;call _ack;
        [_realStock==3 && {count _returns==0} && {_linked isEqualTo ["kat_eyecovers_right"]},"remote local-counter mismatch rejected a valid public provider period"] call _check;
    ''')


def test_public_terminal_as_ack_closes_archive_and_replayed_settlement_cannot_downgrade_it():
    execute(funded_shield() + function("shieldRecover") + '''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0,1]];
        call _start;call _finish;call _dispatch;
        private _request=((_events select 0) select 1) select 1;
        private _results=_ownerEvents select {(_x select 0)=="ACM_ophthalmology_shieldResult"};
        ["result",(_results select 0) select 1] call ACM_ophthalmology_fnc_shieldSource;
        ["settled",_request,0,"applied"] call ACM_ophthalmology_fnc_shieldCommit;
        // Lose the explicit shieldClosed ACK; the source observes the public terminal instead.
        _serverClock=101;["tick",[]] call ACM_ophthalmology_fnc_shieldSource;
        [count (_events select {(_x select 0)=="ACM_ophthalmology_shieldTerminalClosed"})==1,"implicit publication ACK skipped terminal-close notice"] call _check;
        ["terminalClosed",_request,0,"applied"] call ACM_ophthalmology_fnc_shieldCommit;
        ["settled",_request,0,"applied"] call ACM_ophthalmology_fnc_shieldCommit;
        private _terminal=(_patient getVariable "ACM_ophthalmology_shieldTerminal") get (_request select 2);
        [count _terminal==3 && {_terminal select 2},"replayed settlement downgraded closed archive"] call _check;
        _serverClock=170;[_patient] call ACM_ophthalmology_fnc_shieldRecover;
        [count (_patient getVariable "ACM_ophthalmology_shieldTerminal")==0,"completed terminal archive did not retire"] call _check;
    ''')
