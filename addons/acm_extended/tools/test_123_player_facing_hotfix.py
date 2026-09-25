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

    assert 'private _visibleXOffset = (_artV - 0.5) * _iconH;' in init
    assert 'private _iconX = _colX + (_slotW / 2) - (_iconW / 2) - _visibleXOffset;' in init
    assert 'ACME_iv_trayIconBias", 0.56' in init

    for pose in (
        "[-0.018, -0.50, -94]",
        "[-0.006, -0.70, -98]",
        "[ 0.006, -0.90, -102]",
        "[ 0.018, -1.10, -106]",
    ):
        assert pose in hover
    assert "[14,[1,0.55,0.55,0.56]]" in hover
    assert "ctrlCreate ['RscStructuredText',-1]" in hover
    assert "private _px = _sx + _insetX;" in hover
    assert "private _py = _sy + _insetY;" in hover


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
    assert 'private _durationEditing = !isNull _actionFocus && {(ctrlIDC _actionFocus) == 84831};' in tick
    assert 'ACME_SK_NextBodyAction' in tick
    assert 'call ACME_fnc_skBodyActionRender;' in action
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
    assert 'if (_tool == "tube" && {!_canTube}) then {' in refresh
    assert '!([_medic, 2] call ace_medical_treatment_fnc_isMedic)' in select


def test_hotfix_keeps_stable_123_debug_identity():
    startup = acme("functions/fn_initForkStartupRuntime.sqf")
    assert 'ACME_buildBatch = "B152";' in startup
    assert 'ACME_debugRevision = "";' in startup


def test_patient_spawner_equips_plate_carrier_inside_spawn_transaction():
    generated = addon("mission", "functions/fnc_generatePatient.sqf")
    custom = addon("mission", "functions/fnc_spawnCustomPatient.sqf")
    for src in (generated, custom):
        assert 'private _patient = GVAR(TrainingCasualtyGroup) createUnit' in src
        assert 'ACME_patientSpawnerVestClass' in src
        assert '"V_PlateCarrier1_rgr"' in src
        assert '_patient addVest _spawnVestClass;' in src
        assert src.index('_patient addVest _spawnVestClass;') < src.index('ACEFUNC(medical,setUnconscious)')


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
    assert 'ACM_core_fnc_cprActive' in hold
    assert 'ACM_core_fnc_bvmActive' in hold
    assert '}, false, -1, true] call ACM_core_fnc_beginContinuousAction;' in hold

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


def test_direct_cpr_waits_for_single_semifowler_lower_and_never_resumes_it():
    cpr = addon("circulation", "functions/fnc_beginCPR.sqf")
    assert '["_headLowered", false, [false]]' in cpr
    assert 'ACME_headElevated' in cpr
    assert 'ACME_headElev_Suspended' in cpr
    assert 'ACME_headElev_lowerAnimTime' in cpr
    assert '[_m,_p,true] call ACM_circulation_fnc_beginCPR;' in cpr
    assert '"headElevStop", [objNull, _patient, false, false]' in cpr
