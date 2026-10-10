from historical_source import assert_release_identity as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")


def acme(rel: str) -> str:
    return read(ROOT / rel)


def addon(component: str, rel: str) -> str:
    return read(ADDONS / component / rel)


def test_iv_tray_centers_visible_art_and_fans_up_only():
    init = acme("functions/fn_ivMinigameInit.sqf")
    hover = acme("functions/fn_ivTrayHover.sqf")

    tray = init.split('// four needle slots,', 1)[1].split('// the saline line slot is off.', 1)[0]
    assert 'ctrlSetAngle' not in '\n'.join(line for line in tray.splitlines() if not line.strip().startswith('//'))
    assert 'ctrlSetAngle' not in hover
    assert 'private _iconX = _colX + (_slotW / 2) - (_iconW / 2);' in init
    assert 'private _iconScale = missionNamespace getVariable ["ACME_iv_trayIconScale", 2.45];' in init
    assert 'private _iconW = _iconH * _af;' in init
    assert 'private _iconY = _ry + (_slotH / 2) - (_iconH / 2);' in init
    assert 'iv_tray_%1g_0_ca.paa' in init
    # Current tray deliberately renders one centered catheter per gauge. Hover
    # never resurrects the retired fan copies/badge or changes their geometry.
    assert 'iv_tray_%1g_%2_ca.paa' not in hover
    assert 'ACME_IV_TrayFan_%1' in hover
    assert '_layer ctrlShow false;' in hover
    assert '_logo ctrlSetPosition _base;' in hover
    assert 'private _rise =' not in hover
    assert "ctrlCreate ['RscStructuredText',-1]" not in hover


def test_tibial_io_and_iv_flow_respect_tourniquet_and_aajt_occlusion():
    flow = addon("circulation", "functions/fnc_getIVFlowRate.sqf")
    assert 'call ACME_fnc_aajtOccludes) exitWith {0};' in flow
    assert 'ace_medical_tourniquets' in flow
    assert 'private _tqOnPart' in flow
    assert '_tqOnPart && {_iv || {_partIndex in [4,5]}}' in flow


def test_carousel_hover_never_repaints_or_promotes_opacity():
    hover = acme("functions/fn_skCarouselHover.sqf")
    render = acme("functions/fn_skCarouselRender.sqf")
    tick = acme("functions/fn_skUiTick.sqf")
    action = acme("functions/fn_skBodyActionRender.sqf")
    assert "ACME_fnc_skCarouselRender" not in hover
    assert "_hoverOffset" not in render
    assert "then {_alpha = 1;}" not in render
    assert 'private _durationEditing = (uiNamespace getVariable ["ACME_SK_PushDurationEditing",false])' in tick
    assert '|| {!isNull _actionFocus && {(ctrlIDC _actionFocus) == 84831}};' in tick
    assert 'ACME_SK_NextBodyAction' in tick
    assert 'call ACME_fnc_skBodyActionRender;' in render
    assert 'if (!_durFocused || {_durationFor == ""}) then {' in action
    assert 'ACME_SK_PushDurationDrafts' in action


def test_nonempty_blood_on_exact_line_blocks_every_medication_commit_path():
    cfg = acme("config.cpp")
    helper = acme("functions/fn_medicationLineBloodBusy.sqf")
    request = acme("functions/fn_medicationRequest.sqf")
    owner = acme("functions/fn_medicationLineLocal.sqf")
    site = acme("functions/fn_skInjectSite.sqf")
    confirm = acme("functions/fn_skConfirmInjection.sqf")
    hc_start = acme("functions/fn_hardcorePushStart.sqf")
    hc_tick = acme("functions/fn_hardcorePushTick.sqf")

    assert "class medicationLineBloodBusy {};" in cfg
    assert '(_type in ["Blood","FreshBlood","FBTK"])' in helper
    assert '_remaining > 0.01' in helper
    assert '_bagIV isEqualTo _iv' in helper
    assert '!_iv || {_bagSite == _site}' in helper

    for src in (request, owner, site, confirm, hc_start, hc_tick):
        assert "ACME_fnc_medicationLineBloodBusy" in src
    assert '"blood-line"] call ACME_fnc_hardcorePushStop' in hc_tick


def test_medic_thoracostomy_and_doctor_only_chest_tube_tray():
    proc = acme("functions/fn_procedureAllowed.sqf")
    thora = acme("functions/fn_thoraInit.sqf")
    refresh = acme("functions/fn_thoraUpdateTrayIcons.sqf")
    select = acme("functions/fn_thoraSelectTool.sqf")
    breathing = addon("breathing", "XEH_preInit.sqf")

    # Native ACM thoracostomy defaults to ACE Medic (tier 1), while ACME chest tubes default to Doctor (tier 2).
    assert 'case "thoracostomy": {["ACME_allowThoracostomy", "ACM_breathing_allowThoracostomy", 1]};' in proc
    assert '[SETTING_DROPDOWN_SKILL, 1]' in breathing

    # The tube row is not constructed for a non-doctor; the remaining five rows reflow to fill the tray.
    assert 'private _isDoctor = !isNull _medic && {[_medic, 2] call ace_medical_treatment_fnc_isMedic};' in thora
    assert 'private _toolCount = if (_canTube) then {6} else {5};' in thora
    assert 'if (_canTube) then {_tools pushBack ["tube"' in thora
    # A held tool remains available only for stowing after permission changes.
    assert 'if (_tool == "tube" && {!_canTube} && {_held != "tube"}) then {' in refresh
    assert '!([_medic, 2] call ace_medical_treatment_fnc_isMedic)' in select


def test_hotfix_keeps_stable_123_debug_identity():
    startup = acme("functions/fn_initForkStartupRuntime.sqf")
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


def test_patient_spawner_creates_configured_armored_unit_without_gear_replacement():
    generated = addon("mission", "functions/fnc_generatePatient.sqf")
    custom = addon("mission", "functions/fnc_spawnCustomPatient.sqf")
    vehicles = addon("mission", "CfgVehicles.hpp")
    config = addon("mission", "config.cpp")

    # The loadout is part of the class passed to createUnit, not a later repair.
    patient_class = vehicles.split("class GVAR(TrainingPatient): B_Survivor_F {", 1)[1].split("\n    };", 1)[0]
    assert 'linkedItems[] = {"V_PlateCarrier1_rgr"};' in patient_class
    assert 'respawnLinkedItems[] = {"V_PlateCarrier1_rgr"};' in patient_class
    assert 'scope = 1;' in patient_class
    assert 'scopeCurator = 0;' in patient_class
    assert '"A3_Characters_F"' in config.split('requiredAddons[] = {', 1)[1].split('};', 1)[0]
    assert 'QGVAR(TrainingPatient)' in config.split('units[] = {', 1)[1].split('};', 1)[0]

    for src in (generated, custom):
        assert 'createUnit [QGVAR(TrainingPatient),' in src
        assert 'removeVest' not in src
        assert 'addVest' not in src
        assert 'setUnitLoadout' not in src
        # No mission override can replace the required plate carrier with an
        # empty, missing, non-vest or unarmored class.
        assert 'missionNamespace getVariable ["ACME_patientSpawnerVestClass"' not in src
        done = src.index('setVariable ["ACME_acmSpawnerPlateCarrierDone", true, true]')
        assert done < src.index('ACEFUNC(medical,setUnconscious)')
        assert 'setVariable ["ACME_patientSpawnerVestClass", vest _patient, true]' in src


def test_semifowler_passive_support_requires_backpack_or_armored_carrier():
    start = acme("functions/fn_headElevateStart.sqf")
    assert 'private _hasBag = ((backpack _patient) isNotEqualTo "");' in start
    assert 'private _hasCarrier = false;' in start
    assert 'HitpointsProtectionInfo' in start
    assert 'private _carrierArmor = (((_legacyArmor max _chestArmor) max _diaArmor) max _abdArmor);' in start
    assert '_hasCarrier = _carrierArmor > 0;' in start
    assert 'private _manual = !_hasBag && {!_hasCarrier} && {!_manualCarrierSupport};' in start


def test_unsupported_semifowler_is_provider_held_active_maneuver():
    start = acme("functions/fn_headElevateStart.sqf")
    hold = acme("functions/fn_headElevHoldStart.sqf")
    cont = addon("core", "functions/fnc_beginContinuousAction.sqf")
    stop = acme("functions/fn_headElevateStop.sqf")

    assert 'ACME_headElev_manualUnsupported' in start
    assert '"AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown"' in hold
    assert '"AinvPknlMstpSnonWnonDnon_Putdown"' in hold
    assert '"AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon"' in hold
    assert 'setAnimSpeedCoef 0' in hold
    assert 'ACME_headElev_manualAnimPFH' in hold
    assert 'inputAction _x' in hold
    assert '[0xF0, [false,false,false], _cancelCode' in hold
    assert 'ACM_core_ContinuousAction_Epoch' in hold
    assert 'ACME_headElev_manualCancelID' in hold
    assert 'ACM_core_fnc_cprActive' in hold
    assert 'ACM_core_fnc_bvmActive' in hold
    assert '}, false, -1, true, true] call ACM_core_fnc_beginContinuousAction;' in hold

    assert '["_suppressProviderAnim", false, [false]]' in cont
    assert '_notInVehicle && {!_suppressProviderAnim}' in cont
    assert '&& {!_suppressProviderAnim}) then {' in cont

    assert 'private _wasSuspended = _patient getVariable ["ACME_headElev_Suspended", false];' in stop
    assert 'private _visibleLower = !_quiet && {!_wasSuspended}' in stop


def test_manual_semifowler_never_auto_resumes_after_provider_yields():
    resume = acme("functions/fn_headElevTryResume.sqf")
    runtime = acme("functions/fn_registerHeadElevationTreatmentRuntime.sqf")
    bvm = addon("breathing", "functions/fnc_useBVM.sqf")

    assert 'if (_patient getVariable ["ACME_headElev_manualUnsupported", false]) exitWith {' in resume
    assert 'if (_patient getVariable ["ACME_headElev_manualUnsupported", false]) exitWith {' in runtime
    assert 'ACME_headElev_manualUnsupported' in bvm
    assert '"headElevStop"' in bvm


def test_direct_cpr_waits_for_owner_acknowledged_semifowler_lower_and_never_resumes_it():
    cpr = addon("circulation", "functions/fnc_beginCPR.sqf")
    stop = acme("functions/fn_headElevateStop.sqf")
    assert 'private _needsLower = true;' in cpr
    assert 'private _lowerOwner = clientOwner;' in cpr
    assert 'private _lowerRetries = 3;' in cpr
    assert '"headElevStop", [_medic, _patient, false, false, true, true, _epoch, _lowerOwner]' in cpr
    assert 'ACME_cprLowerReady' in cpr
    assert 'serverTime < (_lowerReady param [2, -1])' in cpr
    assert '_patient getVariable ["ACME_headElevated", false]' in cpr
    assert '2 ^ (3 - _lowerRetries)' in cpr
    assert '[_m,_p,true] call ACM_circulation_fnc_beginCPR;' not in cpr

    assert '["_preserveSupportForChest", false, [false]]' in stop
    assert 'private _chestOwnsAfterCancel = _preserveSupportForChest' in stop
    assert '_patient setVariable ["ACME_chestAccess_vestLoadout", +_headSupportSaved, true];' in stop
    assert '_patient setVariable ["ACME_chestAccess_vestProp", _headSupportProp, true];' in stop
    assert '_patient setVariable ["ACME_headElev_vestRemoved", false, true];' in stop


def test_direct_cpr_waits_for_single_semifowler_lower_and_never_resumes_it():
    """Historical identity retained for the owner-acknowledged Semi-Fowler lower."""
    test_direct_cpr_waits_for_owner_acknowledged_semifowler_lower_and_never_resumes_it()
