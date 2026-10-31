"""B241 linkage and mutation checks for canonical native write boundaries.

These are source contracts, not caller authentication or native transport tests.
"""
from pathlib import Path
import pytest
from current_source_contracts import _has
from audit_acme_native_owner_writes import PREFIXES, scan_directory
from run_sharded_regressions import current_selection

ROOT=Path(__file__).resolve().parents[1]
F='addons/acm_extended/functions/'


def read(path):
    return (ROOT/path).read_text()


def require(path,*fragments):
    text=read(path)
    for fragment in fragments:
        assert _has(text,fragment),(path,fragment)
    return text


def wound_routes():
    require('addons/damage/XEH_PREP.hpp','PREP(setWoundState);')
    setter=require('addons/damage/functions/fnc_setWoundState.sqf',
        'if (isNull _patient || {!local _patient}) exitWith {0};',
        '_value isEqualType createHashMap', 'count _x == 2',
        '!isNil {_x select 0}', '!isNil {_x select 1}',
        'case "clottedWounds": {QGVAR(ClottedWounds)};',
        'case "bandageProgress": {QGVAR(BandageProgress)};',
        '_patient setVariable [_key, _value, _public];')
    assert not any(_has(setter,x) for x in ('bandagedWounds','wrappedWounds','stitchedWounds','call CBA_fnc_targetEvent'))
    require(F+'fn_popClots.sqf','[_unit, [["clottedWounds", _clotted]], true] call ACM_damage_fnc_setWoundState;',
        '_fraction = (_fraction max 0.05) min 0.25;', 'private _move = _fraction min _camt;')
    reconciler=require(F+'fn_transientStateReconcile.sqf',
        'if (isNull _patient || {!local _patient}) exitWith {0};',
        '[_patient, [["bandageProgress", _progress]], true] call ACM_damage_fnc_setWoundState;',
        '[["cprProvider", objNull], ["cprMedic", objNull], ["cprSession", []]]')
    assert reconciler.count('call ACM_damage_fnc_setWoundState;')==2
    require('addons/circulation/functions/fnc_setRuntimeState.sqf',
        'case "cprProvider": { _accepted = [QACEGVAR(medical,CPR_provider), _value] call _publish; };')


def gui_routes():
    require('addons/gui/XEH_PREP.hpp','PREP(retireMedicalMenuPFH);')
    require('addons/gui/functions/fnc_retireMedicalMenuPFH.sqf',
        '_acePFH isEqualType 0 && {_acePFH >= 0} && {_acePFH != _protectedPFH}',
        '[_acePFH] call CBA_fnc_removePerFrameHandler;',
        'missionNamespace setVariable ["ace_medical_gui_menuPFH", -1];')
    require(F+'fn_registerMedicalMenuOpenRuntime.sqf',
        '_epoch != (uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", -1])',
        '_rendererPFH != (uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -1])',
        'private _acePFH = [_rendererPFH] call ACM_GUI_fnc_retireMedicalMenuPFH;',
        'call CBA_fnc_execNextFrame;')


def integration_routes():
    require('addons/core/XEH_PREP.hpp', 'PREP(registerDownedProtectionReason);',
        'PREP(setCargoLoadCapability);','PREP(suppressPhysicalBandageReopening);')
    require(F+'fn_aiProtectionInit.sqf','if !(call ACM_core_fnc_registerDownedProtectionReason) exitWith {};')
    require('addons/core/functions/fnc_registerDownedProtectionReason.sqf',
        'isServer && {!(_reasons isEqualTo [])} && {!("acme_medical_downed" in _reasons)}',
        '_reasons = +_reasons;', '_reasons pushBack "acme_medical_downed";',
        'missionNamespace setVariable ["ace_common_statusEffects_setHidden", _reasons, true];')
    require(F+'fn_carrierInventoryCreate.sqf',
        '[_cargo, false, false, true] call ACM_core_fnc_setDraggingCapability;',
        '[_cargo, false, true] call ACM_core_fnc_setCargoLoadCapability;')
    require('addons/core/functions/fnc_setCargoLoadCapability.sqf',
        'if (isNull _object) exitWith {false};','_object setVariable ["ace_cargo_canLoad", _canLoad, _public];')
    require('addons/core/functions/fnc_suppressPhysicalBandageReopening.sqf',
        'missionNamespace setVariable ["ace_medical_treatment_woundReopenChance", -1, false];')
    startup=require(F+'fn_initForkStartupRuntime.sqf','["CBA_settingsInitialized", { call ACM_core_fnc_suppressPhysicalBandageReopening; }] call CBA_fnc_addEventHandler;')
    assert startup.count('call ACM_core_fnc_suppressPhysicalBandageReopening;')==2


def oxygen_routes():
    require(F+'fn_preoxygenationTick.sqf','!local _u',
        '[_u, [["spo2", (_buffered min 100), true, true]]] call ACM_core_fnc_setAceMedicalState;')
    require(F+'fn_aspirationTick.sqf','!local _u',
        '[_u, [["spo2",_new,true,true]]] call ACM_core_fnc_setAceMedicalState;')


@pytest.mark.parametrize('check',[wound_routes,gui_routes,integration_routes,oxygen_routes])
def test_current_native_routing_is_explicit(check):
    check()


MUTATIONS=[
    (wound_routes,'addons/damage/functions/fnc_setWoundState.sqf','!local _patient','false'),
    (wound_routes,'addons/damage/functions/fnc_setWoundState.sqf','_value isEqualType createHashMap','true'),
    (wound_routes,F+'fn_popClots.sqf','call ACM_damage_fnc_setWoundState;','call ACME_fnc_writeNativeDirectly;'),
    (wound_routes,F+'fn_transientStateReconcile.sqf','["cprProvider", objNull]','["wrongProvider", objNull]'),
    (gui_routes,'addons/gui/functions/fnc_retireMedicalMenuPFH.sqf','_acePFH != _protectedPFH','true'),
    (gui_routes,F+'fn_registerMedicalMenuOpenRuntime.sqf','_epoch != (uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", -1])','false'),
    (integration_routes,'addons/core/functions/fnc_registerDownedProtectionReason.sqf','isServer &&','true &&'),
    (integration_routes,F+'fn_carrierInventoryCreate.sqf','[_cargo, false, true]','[_cargo, true, true]'),
    (integration_routes,'addons/core/functions/fnc_suppressPhysicalBandageReopening.sqf','-1, false','0.1, false'),
    (oxygen_routes,F+'fn_preoxygenationTick.sqf','call ACM_core_fnc_setAceMedicalState;','call ACME_fnc_directSpO2;'),
]


@pytest.mark.parametrize('check,path,old,new',MUTATIONS,ids=[f'boundary-{i}' for i in range(len(MUTATIONS))])
def test_contract_rejects_missing_guards_and_direct_write_regressions(monkeypatch,check,path,old,new):
    check()
    target=ROOT/path;real=Path.read_text;text=real(target)
    assert old in text
    changed=text.replace(old,new)
    with monkeypatch.context() as m:
        m.setattr(Path,'read_text',lambda p,*a,**kw:changed if p==target else real(p,*a,**kw))
        with pytest.raises(AssertionError):check()


def test_strict_scan_now_covers_all_repaired_namespaces_without_exceptions():
    assert {'ACM_damage_','ACM_CBRN_','ace_'}<=set(PREFIXES)
    assert scan_directory(ROOT/F)==[]


def test_repaired_legacy_boundary_modules_are_mandatory():
    paths={'tools/test_fork_'+name+'.py' for name in (
        'phase53_no_extended_acm_writers','phase54_ace_medical_state_bridge',
        'phase55_gui_pfh_owner','phase56_no_extended_ace_writers')}
    assert paths<=set(current_selection(ROOT))
