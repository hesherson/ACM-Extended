from historical_source import assert_release_identity as _assert_current_build
from pathlib import Path
import re
from source_scan import code_streams, matching, split_args

ROOT = Path(__file__).resolve().parents[3]
ACME = ROOT / "addons" / "acm_extended"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def function(name: str) -> str:
    return read(f"addons/acm_extended/functions/fn_{name}.sqf")


def network_ops(source: str):
    """Inspect code tokens, including executable callbacks, never prose/comments."""
    identifiers = set()
    zero_targets = []
    for tokens in code_streams(source):
        identifiers.update(t.value.lower() for t in tokens if t.kind == "ident")
        pairs = matching(tokens)
        for i, token in enumerate(tokens[:-1]):
            if token.kind != "ident" or token.value.lower() not in {"remoteexec", "remoteexeccall"}:
                continue
            opening = i + 1
            if tokens[opening].value != "[" or opening not in pairs:
                continue
            args = split_args(tokens, opening + 1, pairs[opening], pairs)
            if len(args) >= 2 and len(args[1]) == 1 and args[1][0].value == "0":
                zero_targets.append(token.line)
    return identifiers, zero_targets


def test_network_scan_detects_real_commands_and_ignores_comment_and_string_decoys():
    live = '''
        // a preceding comment must not hide the live commands below
        publicVariableServer "state";
        [] remoteExecCall ["handler", 0];
        [] remoteExec ["handler", 0, true];
        {call process} forEach allUnits;
        ["event", []] call CBA_fnc_globalEvent;
    '''
    ids, broadcasts = network_ops(live)
    assert {"publicvariableserver", "allunits", "cba_fnc_globalevent"} <= ids
    assert len(broadcasts) == 2
    decoys = '''
        /* [] remoteExecCall ["handler", 0]; publicVariable "state"; */
        // allUnits; call CBA_fnc_globalEvent;
        private _label = "publicVariable allUnits CBA_fnc_globalEvent";
        [] remoteExecCall ["handler", owner _patient];
    '''
    ids, broadcasts = network_ops(decoys)
    assert not {"publicvariable", "allunits", "cba_fnc_globalevent"} & ids
    assert not broadcasts
    ids, broadcasts = network_ops("compile \"[] remoteExecCall ['handler', 0];\";")
    assert len(broadcasts) == 1


def test_approximate_network_helper_rejects_non_finite_scalars():
    s = function("setVarNetApprox")
    assert "if !(finite _value) exitWith" in s
    assert "ACME_net_nonFiniteSuppressed" in s
    assert "_epsilon = abs _epsilon;" in s
    assert "_maxAge = _maxAge max 0;" in s


def test_jip_events_have_explicit_cleanup_in_same_runtime_module():
    offenders = []
    for path in (ACME / "functions").glob("*.sqf"):
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        identifiers, _ = network_ops(text)
        if "cba_fnc_globaleventjip" in identifiers and "cba_fnc_removeglobaleventjip" not in identifiers:
            offenders.append(path.name)
    assert offenders == [], offenders


def test_network_publication_helpers_dedupe_structured_mutable_state():
    net = function("setVarNet")
    native = read("addons/circulation/functions/fnc_setRuntimeState.sqf")
    iv = read("addons/circulation/functions/fnc_setIVBagsState.sqf")

    for s in (net, native):
        assert '"ARRAY", "HASHMAP"' in s
        assert "str _value" in s
        assert '[_type, str _old] isEqualTo _fingerprint' in s
        assert "Published" in s or "scalarCache" in s
    assert 'case "NIL": {["NIL"]};' in net
    assert "ACME_ivBagsPublishedSig" in iv
    assert "str _bags" in iv


def test_large_hot_state_maps_are_owner_local_and_bounded_on_wire():
    circ = function("circStateCommit")
    tbi = function("tbiStateCommit")
    infusion = function("infusionMedicationStateCommit")

    assert '_patient setVariable ["ACME_circ_State", _state, false];' in circ
    assert 'ACME_circ_stateNetInterval' in circ
    assert '(_now - _lastAt) >= _interval' in circ

    assert '_patient setVariable ["ACME_tbi_State", _state, false];' in tbi
    assert 'ACME_tbi_stateNetInterval' in tbi
    assert '(_now - _lastAt) >= _interval' in tbi

    assert '_patient setVariable ["ACME_infusion_BagMedications", _entries, false];' in infusion
    assert 'ACME_infusion_stateNetInterval' in infusion
    assert '(_now - _lastAt) >= _interval' in infusion


def test_network_snapshot_cadences_are_bounded():
    cfg = function("initNetworkSyncConfig")
    assert "ACME_circ_stateNetInterval = 2.0;" in cfg
    assert "ACME_tbi_stateNetInterval = 1.0;" in cfg
    infusion = function("infusionMedicationStateCommit")
    assert '["ACME_infusion_stateNetInterval", 1.0]' in infusion


def test_recovered_casualty_is_not_pinned_in_hot_circulation_registries():
    owner = function("ownerRegister")
    circ = function("circHandle")

    assert 'count (_patient getVariable ["ACME_circ_State", createHashMap]) > 0' not in owner
    assert "{count _circState > 0}" not in circ
    assert "private _circNeeds =" in owner
    assert "private _circStateNeedsTick = {" in circ
    assert 'ACME_circ_activePatients = ACME_circ_activePatients - [_patient];' in circ


def test_owner_recovery_is_event_driven_with_only_slow_missing_event_audit():
    owner = function("ownerInit")
    register = function("ownerRegister")

    assert 'CBA_missionTime + 30' in owner
    assert "private _missingOwned = _actualOwned select" in owner
    assert 'ACME_ownerRegisterSeen' in owner
    assert 'ACME_clinical_ownedUnits' in register
    assert 'ACME_ownerRegisterSeen' in register


def test_hot_tick_files_do_not_use_global_broadcast_primitives():
    offenders = []
    for path in (ACME / "functions").glob("fn_*Tick.sqf"):
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        identifiers, zero_targets = network_ops(text)
        if {"cba_fnc_globalevent", "cba_fnc_globaleventjip"} & identifiers or zero_targets:
            offenders.append(path.name)
    assert offenders == [], offenders


def test_acme_networking_does_not_use_raw_publicvariable_commands():
    offenders = []
    for path in (ACME / "functions").glob("*.sqf"):
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        identifiers, _ = network_ops(text)
        if {"publicvariable", "publicvariableserver", "publicvariableclient"} & identifiers:
            offenders.append(path.name)
    assert offenders == [], offenders


def test_hot_medical_ticks_do_not_world_scan_every_run():
    allowed = {
        "fn_bloodColdChainTick.sqf",  # server cold-chain inventory discovery; registered at 60 s
        "fn_clotPopTick.sqf",         # server rare-clot candidate discovery; registered at 60 s
    }
    offenders = []
    for path in (ACME / "functions").glob("fn_*Tick.sqf"):
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        identifiers, _ = network_ops(text)
        if "allunits" in identifiers and path.name not in allowed:
            offenders.append(path.name)
    assert offenders == [], offenders


def test_ui_only_high_frequency_runtimes_never_register_on_dedicated_server():
    for name in (
        "registerTransfusionUiRuntime",
        "registerThoracicMenuPresentationRuntime",
        "registerVentilatorKeybindRuntime",
        "initMinigameInteractionRuntime",
    ):
        s = function(name)
        assert "if (!hasInterface) exitWith {};" in s, name

    consciousness = function("registerConsciousnessRuntime")
    emma = function("initEmmaRuntime")
    bvm = function("registerBvmVentRuntime")
    pose = function("treatmentPoseSync")
    post = function("postInit")

    assert "if (hasInterface) then {" in consciousness
    assert "if (hasInterface) then" in emma
    assert "if (hasInterface) then" in bvm
    assert 'if (!hasInterface && {!local _medic}) exitWith {};' in pose
    visual = function("registerVisualEffectsRuntime")
    assert "call ACME_fnc_registerVisualEffectsRuntime;" in post
    assert "class registerVisualEffectsRuntime {};" in read("addons/acm_extended/config.cpp")
    assert "if (hasInterface) then {" in visual and "ACME_fnc_visualFxTick" in visual


def test_every_frame_cheyne_stokes_server_worker_was_bounded():
    runtime = function("registerTbiRuntime")
    assert '[{call ACME_fnc_cheyneStokesTick}, 0.10, []]' in runtime
    assert '[{call ACME_fnc_cheyneStokesTick}, 0, []]' not in runtime


def test_thoracostomy_painting_never_publishes_a_growing_array_per_frame():
    tick = function("thoraTick")
    mouse = function("thoraMouseUp")
    owner = function("ownerDispatch")
    side = function("thoraSideStateCommit")

    paint = tick.split('if (uiNamespace getVariable ["ACME_Thora_Prepping", false]) exitWith {', 1)[1]
    paint = paint.split('if !(uiNamespace getVariable ["ACME_Thora_Palpating", false])', 1)[0]
    assert "ACME_Thora_PrepLocal" in paint
    assert "ACME_fnc_setVarNet" not in paint
    assert "setVariable [_key" not in paint

    flush = function("thoraPrepFlush")
    assert "call ACME_fnc_thoraPrepFlush" in mouse
    assert '"thoraPrepCommit"' in flush
    assert 'case "thoraPrepCommit"' in owner
    assert 'call ACME_fnc_thoraSideStateCommit;' in owner
    assert 'call ACME_fnc_thoraBumpVer;' in owner
    assert '!local _patient' in side and '"thoraSideState"' in side


def test_laryngoscopy_render_frame_does_not_publish_tube_state_every_frame():
    tick = function("laryngoTick")
    migration = function("ettMigrationStateCommit")

    migrated = tick.split('case "migrated": {', 1)[1].split('case "seated": {', 1)[0]
    assert "ACME_laryngo_migrationSyncNext" in migrated
    assert "_syncNow + 0.20" in migrated
    assert 'call ACME_fnc_ettMigrationStateCommit' in migrated
    for forbidden in (
        '[_pt, "ACME_ETT_Depth"',
        '[_pt9, "ACME_ETT_Frame"',
        '[_pt9, "ACME_ETT_Mainstem"',
    ):
        assert forbidden not in migrated

    assert '"placement"' in migration
    assert "ACME_fnc_setVarNet" in migration


def test_chest_seal_presence_is_motion_driven_not_idle_fourteen_hz_heartbeat():
    s = function("chestSealPresenceSend")
    assert '["ACME_CS_presenceRate", 0.10]' in s
    assert '["ACME_CS_presenceHeartbeat", 0.35]' in s
    assert "private _ptsSig = _pts apply" in s
    assert "_moved && {_age >= _rate}" in s
    assert "_age >= _heartbeat" in s


def test_iv_and_y_flush_structured_state_are_bounded():
    native = read("addons/circulation/functions/fnc_getBloodVolumeChange.sqf")
    y = function("yFlushTick")

    assert "ACME_transfusionUiBagStructSig" in native
    assert "(CBA_missionTime - _acmeBagUiLastAt) >= 1" in native
    assert ">= 0.25" not in native.split("ACME_transfusionUiBagStructSig", 1)[1].split("};", 1)[0]

    assert '_p setVariable ["ACME_yFlushJobs", _jobs, false];' in y
    assert "ACME_yFlushJobsNetAt" in y
    assert "diag_tickTime - _lastNet >= 1" in y


def test_continuously_changing_telemetry_uses_threshold_publication():
    expected = {
        "altitudeTick": (
            "ACME_alt_m", "ACME_alt_pRatio", "ACME_flightG_stress",
            "ACME_flightG_resistAdd", "ACME_alt_hypoxia",
        ),
        "ventDriveTick": (
            "ACME_vent_dyssync", "ACME_vent_spontRR", "ACME_vent_effectiveRR",
            "ACME_vent_autoPEEP", "ACME_vent_vti", "ACME_vent_vte", "ACME_vent_pip",
            "ACME_vent_recruit", "ACME_vent_baroInjury", "ACME_vent_mvDelivered",
            "ACME_vent_mvAdequacy", "ACME_vent_baroDose",
        ),
        "suctionPhysiologyTick": (
            "ACME_suctionExposure", "ACME_o2Drain_suction",
        ),
        "tbiApplyVitals": (
            "ACME_tbi_resistAdd", "ACME_hrTarget_tbi", "ACME_rrDrive_tbi",
        ),
    }
    for fn, fields in expected.items():
        s = function(fn)
        for field in fields:
            rows = [line for line in s.splitlines() if f'"{field}"' in line]
            assert any("setVarNetApprox" in line for line in rows), (fn, field, rows)


def test_hpmk_server_safety_uses_registry_not_repeated_world_scan():
    tick = function("hpmkBlanketTick")
    runtime = function("registerHpmkVisualRuntime")
    state = function("hpmkStateCommit")

    assert "allUnits" not in tick
    assert "ACME_hpmk_serverPatients" in tick
    assert "ACME_hpmk_serverPatients" in runtime
    assert '"ACME_hpmkServerTrack"' in runtime
    assert '"ACME_hpmkServerTrack"' in state


def global_sound_calls(source):
    found = []
    for tokens in code_streams(source):
        pairs = matching(tokens)
        for i, token in enumerate(tokens[:-1]):
            if token.kind != "ident" or token.value.lower() not in {"remoteexec", "remoteexeccall"}:
                continue
            opening = i + 1
            if tokens[opening].value != "[" or opening not in pairs:
                continue
            args = split_args(tokens, opening + 1, pairs[opening], pairs)
            if (len(args) >= 2 and len(args[0]) == 1 and len(args[1]) == 1
                    and args[0][0].kind == "string"
                    and args[0][0].value.lower() in {"say3d", "acme_fnc_remotesay3d"}
                    and args[1][0].value == "0"):
                found.append(token.line)
    return found


def test_no_acme_treatment_audio_broadcasts_to_every_client():
    # The fork's core overrides are runtime code too. Limiting this to the Extended
    # folder previously missed a second global Direct Pressure sound in treatment.
    paths = [p for p in (ROOT / "addons").rglob("*") if p.suffix in {".sqf", ".cpp", ".hpp"}]
    offenders = [str(p.relative_to(ROOT)) for p in paths
                 if global_sound_calls(p.read_text(encoding="utf-8-sig", errors="strict"))]
    assert offenders == [], offenders

    helper = function("worldSfxNearby")
    owner = function("ownerInit")
    assert "allPlayers select" in helper
    assert '"ACME_worldSfx"' in helper
    assert '["ACME_worldSfx"' in owner


def test_cold_chain_and_fridge_network_requests_are_debounced():
    init = function("initBloodStorageRuntime")
    poll = function("bloodFridgeMenuPoll")
    tick = function("bloodFridgeTick")

    assert "ACME_ccNudgeSentAt" in init
    assert "_nudgeNow - _nudgeLast >= 0.5" in init
    assert "(diag_tickTime - _last) < 0.4" in poll
    assert '["ACME_bf_viewTimeout", 0.9]' in tick
    assert '"ACME_worldSfx"' in tick


def test_no_accidental_literal_newline_escape_in_hpmk_runtime_registration():
    s = function("registerHpmkVisualRuntime")
    assert r"\n[{call ACME_fnc_hpmkBlanketTick}" not in s
    assert "[{call ACME_fnc_hpmkBlanketTick}, 2, []]" in s



def test_ventilator_server_audio_has_no_recurring_world_scan_or_global_log_broadcast():
    audio = function("registerVentilatorAudioRuntime")
    alarm = function("ventAlarmTick")
    ack = function("ventCustodyAck")
    clear = function("ventPatientClear")

    # One legacy/hot-load seed is acceptable; the 10 Hz worker itself must iterate only the active registry.
    assert audio.count("allUnits select") == 1
    hot = audio.split("ACME_vent_soundSources = _keptSources;", 1)[1]
    assert '} forEach (+(missionNamespace getVariable ["ACME_vent_serverPatients", []]));' in hot
    assert "allUnits select" not in hot
    assert '"ACME_ventServerTrack"' in audio
    assert '"ACME_vent_serverPatients"' in audio
    assert 'call CBA_fnc_globalEvent;' not in "\n".join(
        line for line in audio.splitlines() if "ACME_ventSndFade" in line
    )
    assert '"ACME_ventAlarmLog"' in alarm
    log_line = next(line for line in alarm.splitlines() if '"ACME_ventAlarmLog"' in line)
    assert "CBA_fnc_targetEvent" in log_line
    assert "CBA_fnc_globalEvent" not in log_line
    assert "ACME_vent_serverPatients pushBackUnique _patient" in ack
    assert '"ACME_ventServerTrack"' in clear


def test_native_hot_vitals_publications_are_bounded_or_transition_only():
    vitals = read("addons/core/overrides/fnc_handleUnitVitals.sqf")
    circ_state = read("addons/circulation/functions/fnc_updateCirculationState.sqf")
    cbrn = function("medicationCBRNTick")

    assert 'Vasoconstriction_State), _vasoconstriction, 0.25, 2] call ACME_fnc_setVarNetApprox;' in vitals
    assert 'private _syncValues = (CBA_missionTime - _lastTimeValuesSynced) >= (10 + floor(random 10));' in vitals
    assert 'if ((_patient getVariable ["ACME_rosc_blockedBy", ""]) != _blocked)' in circ_state
    assert 'isNotEqualTo _circulationState' in circ_state
    assert cbrn.count("ACME_fnc_setVarNetApprox") >= 2


def test_cbrn_ai_hazard_scan_is_spatially_bounded():
    s = read("addons/cbrn/functions/fnc_initHazardZone.sqf")
    worker = s.split("private _PFH = [{", 1)[1]
    assert 'nearestObjects [getPosATL _hazardRadius, ["CAManBase"], _scanRadius]' in worker
    assert "allUnits inAreaArray" not in worker
    assert '"+_radiusDimensions"' not in worker
    assert '"+_radiusDimensions"' not in s
    assert '+_radiusDimensions' in s


def test_medication_drive_queue_is_local_between_bounded_snapshots():
    add = function("medicationDriveAdd")
    tick = function("medicationDriveTick")
    assert '[_patient, "ACME_medicationDriveQueue", _queue] call ACME_fnc_setVarNet;' in add
    assert '_patient setVariable ["ACME_medicationDriveQueue", _keep, false];' in tick
    assert '(_driveNow - _driveLast) >= 1' in tick
    assert '_patient setVariable ["ACME_medicationDriveQueue",_keep,true];' not in tick


def test_network_config_contains_real_newlines_not_escaped_comment_text():
    cfg = function("initNetworkSyncConfig")
    assert "\\nACME_" not in cfg
    assert "ACME_tbi_stateNetInterval = 1.0;" in cfg.splitlines()

def test_b204_network_audit_identity():
    startup = function("initForkStartupRuntime")
    config = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    _assert_current_build()
