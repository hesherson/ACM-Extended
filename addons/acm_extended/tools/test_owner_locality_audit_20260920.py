from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8-sig', errors='strict')


def test_pressure_infuser_never_compares_provider_clock_to_owner_clock():
    s = src('functions/fn_pressureInfuserCommit.sqf')
    assert 'CBA_missionTime - _issued' not in s
    assert '_issued <= CBA_missionTime' not in s
    assert 'clinicalEpoch' in s and 'ACME_piReceipts' in s and '_bagId' in s


def test_direct_pressure_clot_is_patient_owner_mutation():
    tick = src('functions/fn_directPressureTick.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    assert '"directPressureClot"' in tick
    assert 'clotWoundsOnBodyPart' not in tick
    block = owner.split('case "directPressureClot"', 1)[1].split('case "junctionalPackStart"', 1)[0]
    assert 'ACME_DP_press_%1' in block
    assert 'ACM_damage_fnc_clotWoundsOnBodyPart' in block


def test_junctional_state_pain_and_hemostasis_commit_on_owner():
    owner = src('functions/fn_ownerDispatch.sqf')
    start = src('functions/fn_junctionalPackSfxStart.sqf')
    pack = src('functions/fn_junctionalPackDone.sqf')
    wrap = src('functions/fn_junctionalWrapDone.sqf')
    assert '"junctionalPackStart"' in start
    assert 'ACME_obtunded_wakeStimGraceUntil' not in start
    assert '"junctionalPackDone"' in pack and 'setVariable [format ["ACME_Junc_' not in pack
    assert '"junctionalWrapDone"' in wrap and 'clotWoundsOnBodyPart' not in wrap
    for case in ('junctionalPackStart', 'junctionalPackDone', 'junctionalWrapDone'):
        assert f'case "{case}"' in owner


def test_push_duration_renderer_never_resets_provider_draft():
    s = src('functions/fn_skBodyActionRender.sqf')
    assert 'ACME_SK_PushDurationDrafts' in s
    assert 'ACME_SK_PushDurationFor' in s
    assert 'ACME_HCMedPushDefaultFor' not in s
    pending = s.split('if (_pending isEqualType [] && {count _pending >= 3}) then {', 1)[1].split('private _total =', 1)[0]
    assert '_durHint ctrlSetText _suggested;' in pending
    assert '_durEdit ctrlSetText' not in pending


def test_hang_bag_claim_is_owner_serialized_and_gear_survives_death():
    start = src('functions/fn_hangBagStart.sqf')
    tick = src('functions/fn_hangBagTick.sqf')
    stop = src('functions/fn_hangBagStop.sqf')
    prep = src('functions/fn_hangBagPrep.sqf')
    restore = src('functions/fn_hangBagRestoreWeapons.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    assert '"hangBagClaim"' in start
    assert '_patient setVariable ["ACME_hang_Medic"' not in start
    assert '_patient setVariable ["ACME_hang_flowMult"' not in start
    assert 'ACME_hang_Claimed' in tick
    assert 'call ACME_fnc_setVarNet' not in tick
    assert 'case "hangBagClaim"' in owner and 'case "hangBagRelease"' in owner
    assert 'ACME_hang_savedWeaponSlots", [_ld select 0, _ld select 1], true' in prep
    assert 'alive _medic' not in restore
    assert 'setUnitLoadout _ld' in restore
    assert 'ACME_hangRestoreWeapons' in stop


def test_dead_airway_checks_are_not_paint_filtered_by_alive_state():
    s = (ROOT.parent / 'gui/overrides/fnc_updateActions.sqf').read_text(encoding='utf-8-sig')
    block = s.split("_menuActions = _menuActions select {", 1)[1].split('};', 1)[0]
    assert "checkairway" in block and "checkbreathing" in block
    assert 'alive _target' not in block
    assert '_bodyPart == 0' in block


def test_ett_durable_state_and_migration_are_owner_authoritative():
    airway = src('functions/fn_ettAirwayStateCommit.sqf')
    migration = src('functions/fn_ettMigrationStateCommit.sqf')
    migrate = src('functions/fn_ettMigrate.sqf')
    ext = src('functions/fn_laryngoExtubate.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    assert '!local _patient' in airway and '"ettAirwayState"' in airway
    assert '!local _patient' in migration and '"ettMigrationState"' in migration
    assert '!local _patient' in migrate and '"ettMigrate"' in migrate
    assert '"ettExtubate"' in ext and '_patient setVariable' not in ext
    for case in ('ettAirwayState', 'ettMigrationState', 'ettMigrate', 'ettCuffDone', 'ettExtubate'):
        assert f'case "{case}"' in owner


def test_iv_marks_and_compromise_are_owner_serialized():
    add = src('functions/fn_ivMinigameAddMark.sqf')
    connect = src('functions/fn_ivMinigameLineConnect.sqf')
    pull = src('functions/fn_ivMinigamePullStop.sqf')
    infiltrated = src('functions/fn_ivInfiltrated.sqf')
    render = src('functions/fn_ivMinigameRenderMarks.sqf')
    commit = src('functions/fn_ivMarkCommit.sqf')
    register = src('functions/fn_ivMinigameRegister.sqf')
    assert '"ivMarks"' in add and '_patient setVariable ["ACME_IV_Marks"' not in add
    assert '"connect"' in connect and '_patient setVariable ["ACME_IV_Marks"' not in connect
    assert '"remove"' in pull and '_patient setVariable ["ACME_IV_Marks"' not in pull
    assert 'serverTime' in infiltrated and 'CBA_missionTime' not in infiltrated.split('ivMinigameAddMark', 1)[0].splitlines()[-1]
    assert 'private _e = serverTime - _mmiss;' in render
    assert '!local _patient' in commit and 'ACME_IV_MarkVer' in commit
    assert '"ivCompromised"' in register


def test_shared_junctional_audio_windows_use_server_clock():
    mark = src('functions/fn_markImportantSfx.sqf')
    bleed = src('functions/fn_junctionalStartBleed.sqf')
    wrap = src('functions/fn_wrapSfxServer.sqf')
    assert 'private _now = serverTime;' in mark
    assert 'max (_now + (_duration max 0))' in mark
    assert 'private _audioNow = serverTime;' in bleed
    audio = bleed.split('// past the exit gate', 1)[1].split('// a junctional bleed is arterial', 1)[0]
    assert 'time >= _leakNext' not in audio
    assert 'time < _busyUntil' not in audio
    assert 'private _audioNow = serverTime;' in wrap
    assert 'ACME_SfxBusyUntil", 0]) - _audioNow' in wrap


def test_multiplayer_iv_anatomy_is_deterministic_and_not_public_first_writer():
    pheno = src('functions/fn_ivVenousPhenotype.sqf')
    veins = src('functions/fn_ivVeinSet.sqf')
    assert 'netId _patient' in pheno
    assert 'forEach (toArray _key)' in pheno
    assert 'ACME_iv_phenotype", _p, false' in pheno
    assert 'ACME_iv_phenotype", _p, true' not in pheno
    assert 'toArray (_key + ":dominant")' in veins
    assert 'ACME_iv_phenotypeSide", _side, false' in veins
    assert 'ACME_iv_phenotypeSide", [0, 1] select _cephDom, true' not in veins


def test_airway_anatomy_and_grade_are_owner_serialized():
    grade = src('functions/fn_airwayGrade.sqf')
    init = src('functions/fn_laryngoInit.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    assert '"airwayGradeState"' in grade
    assert '_patient setVariable ["ACME_airwayGrade"' not in grade
    assert 'netId _patient' in grade
    assert '"laryngoAnatomy"' in init
    anatomy = init.split('private _stableAirwayDraw = {', 1)[1].split('// Do not accept the tube', 1)[0]
    assert 'netId _p' in anatomy
    assert '_patient setVariable ["ACME_laryngo_fulcNeed"' not in anatomy
    assert '_patient setVariable ["ACME_ETT_IdealFrame"' not in anatomy
    assert 'case "airwayGradeState"' in owner
    assert 'case "laryngoAnatomy"' in owner


def test_ett_tip_persistence_is_owner_written_and_ejection_returns_tube_to_medic():
    migration = src('functions/fn_ettMigrationStateCommit.sqf')
    passed = src('functions/fn_laryngoPassTube.sqf')
    eject = src('functions/fn_laryngoTubeEject.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    assert 'case "tip"' in migration
    assert 'ACME_ETT_TipFrac' in migration
    assert '"tip", [_tipFrac]' in passed
    assert '_patient setVariable ["ACME_ETT_TipFrac"' not in passed
    assert '"tip", [[]]' in eject
    assert 'ACME_ettReturnTube' in eject
    assert '[_pat, "ACME_ETTube"] call ace_common_fnc_addToInventory' not in eject
    assert '"tip", [[]]' in owner


def test_shared_vent_alarm_silence_uses_server_time_and_emma_has_no_public_uid_breadcrumb():
    silence = src('functions/fn_ventAlarmSilence.sqf')
    panel = src('functions/fn_ventPanelTick.sqf')
    audio = src('functions/fn_registerVentilatorAudioRuntime.sqf')
    emma = src('functions/fn_emmaMarkContact.sqf')
    assert 'alarmSilencedUntil", serverTime + _dur' in silence
    assert 'serverTime < _silUntil' in panel
    assert 'serverTime >= _silA' in panel
    assert 'serverTime < _silUntil' in audio
    assert 'ACME_emma_contact_' not in emma
    assert 'getPlayerUID _medic' not in emma


def test_airway_checked_age_has_owner_native_clock_and_shared_server_clock():
    post = (ROOT.parent / 'airway/XEH_postInit.sqf').read_text(encoding='utf-8-sig')
    check = (ROOT.parent / 'airway/functions/fnc_checkAirway.sqf').read_text(encoding='utf-8-sig')
    suction = (ROOT.parent / 'airway/functions/fnc_getSuctionTime.sqf').read_text(encoding='utf-8-sig')
    clear = (ROOT.parent / 'airway/functions/fnc_clearAirwayCheckedTime.sqf').read_text(encoding='utf-8-sig')
    assert 'QGVAR(setAirwayCheckedTime)' in post
    assert 'local _patient' in post and 'ACME_airwayCheckedServer' in post
    assert 'CBA_fnc_targetEvent' in check and 'AirwayChecked_Time), CBA_missionTime' not in check
    assert 'serverTime - _checkedServer' in suction
    assert 'ACME_airwayCheckedServer", nil' in clear


def test_lozenge_state_is_patient_owner_local_and_shared_age_uses_server_time():
    set_action = (ROOT.parent / 'circulation/functions/fnc_setLozenge.sqf').read_text(encoding='utf-8-sig')
    local = (ROOT.parent / 'circulation/functions/fnc_setLozengeLocal.sqf').read_text(encoding='utf-8-sig')
    assert 'ACME_lozengeInsertServer' in set_action and 'serverTime - _insertServer' in set_action
    assert '_patient setVariable [QGVAR(LozengeItem' not in set_action
    assert 'local _patient' in local
    assert 'LozengeItem_InsertTime), _insertTime, true' in local
    assert 'ACME_lozengeInsertServer", serverTime, true' in local
    assert '[_patient, _insertTime, _type]' in local


def test_aajt_application_tamponade_clock_is_patient_owner_local():
    config = src('config.cpp')
    owner = src('functions/fn_ownerDispatch.sqf')
    apply = src('functions/fn_aajtApply.sqf')
    assert "setVariable ['ACME_Junc_AAJTApplying'" not in config
    assert config.count("'aajtApplying'") >= 6
    assert 'case "aajtApplying"' in owner
    block = owner.split('case "aajtApplying"', 1)[1].split('case "xstatApply"', 1)[0]
    assert '[serverTime, toLowerANSI _part]' in block
    assert '"aajtApplying", ["", false]' in apply


def test_xstat_commit_and_rebleed_state_are_owner_authoritative():
    xstat = src('functions/fn_xstatApply.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    bleed = src('functions/fn_junctionalStartBleed.sqf')
    injury = src('functions/fn_junctionalInjuryEntry.sqf')
    core = (ROOT.parent / 'core/overrides/fnc_updateWoundBloodLoss.sqf').read_text(encoding='utf-8-sig')
    assert '!local _patient' in xstat and '"xstatApply"' in xstat
    assert 'case "xstatApply"' in owner
    assert 'ACME_Junc_XStatRebled_%1' in bleed
    assert 'private _rebled = _target getVariable' in injury
    assert 'time - _at' not in injury
    assert 'ACME_Junc_XStatAt_%1", _part], time' in core



def test_shock_request_and_recent_shock_use_shared_server_clock_without_poisoning_sync_refractory():
    req = src('functions/fn_shockRequest.sqf')
    shock = src('functions/fn_shockLocal.sqf')
    recent = (ROOT.parent / 'circulation/functions/fnc_recentAEDShock.sqf').read_text(encoding='utf-8-sig')
    native_req = (ROOT.parent / 'circulation/functions/fnc_AED_AdministerShock.sqf').read_text(encoding='utf-8-sig')
    fields = src('functions/fn_clinicalFields.sqf')
    assert '_sync, serverTime]' in req and '_sync, CBA_missionTime]' not in req
    assert '_sync, serverTime]' in native_req and '_sync, CBA_missionTime]' not in native_req
    assert 'serverTime - _sentAtServer > 30' in shock
    assert '_sentAtServer - serverTime > 2' in shock
    assert 'if (!_expectedSync) then {_runtime pushBack ["aedLastShock", CBA_missionTime];};' in shock
    assert 'if (_expectedSync) then {_patient setVariable ["ACME_sync_lastShock", CBA_missionTime, true];};' in shock
    assert 'ACME_aed_lastShockServer", serverTime, true' in shock
    assert '(_sharedLast + _window) > serverTime' in recent
    assert '"ACME_aed_lastShockServer"' in fields
    # serverTime is presentation-only and must not be serialized/rebased like a CBA owner clock.
    block = fields.split('"ACME_aed_lastShockServer"', 1)[1].split('],', 1)[0]
    assert 'false' in block


def test_ecg_direct_pressure_artifact_requires_a_live_matching_hold():
    ecg = src('functions/fn_ecgArtifactStrength.sqf')
    block = ecg.split('private _provider = _patient getVariable', 1)[1].split('exitWith {_dp = true;};', 1)[0]
    assert 'alive _provider' in block
    assert 'ACME_DP_Active' in block
    assert 'ACME_DP_Paused' in block
    assert 'ACME_DP_Patient' in block
    assert 'ACME_DP_Part' in block



def test_lifepak_shock_uses_actual_dialog_operator_not_legacy_patient_provider_sentinel():
    monitor = (ROOT.parent / 'circulation/functions/fnc_displayAEDMonitor.sqf').read_text(encoding='utf-8-sig')
    button = (ROOT.parent / 'circulation/functions/fnc_AED_Button_Shock.sqf').read_text(encoding='utf-8-sig')
    shock = src('functions/fn_shockLocal.sqf')
    assert 'GVAR(AED_Monitor_Medic) = _medic;' in monitor
    assert 'QGVAR(AED_Monitor_Medic)' in button
    config = src('config.cpp')
    lifepak = config.split('class ACM_circulation_Lifepak_Monitor_Dialog', 1)[1].split('};', 1)[0]
    assert 'ACME_sync_localArmed' in lifepak and 'AED_Monitor_Medic' in lifepak
    assert 'getVariable [QGVAR(AED_Provider)' not in button
    operator_block = shock.split('// Base ACM', 1)[1].split('private _rhythm', 1)[0]
    assert 'getVariable ["ACM_circulation_AED_Provider"' not in operator_block
    assert 'getVariable [QGVAR(AED_Provider)' not in operator_block
    assert 'alive _medic' in shock and 'ace_common_fnc_isAwake' in shock
    assert 'ace_medical_gui_maxDistance' in shock



def test_sync_mode_uses_local_operator_intent_and_owner_authoritative_public_state():
    toggle = src('functions/fn_syncToggle.sqf')
    flags = src('functions/fn_syncFlagsTick.sqf')
    setup = src('functions/fn_aedSyncSetup.sqf')
    shock = src('functions/fn_shockLocal.sqf')
    req = src('functions/fn_shockRequest.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    set_aed = (ROOT.parent / 'circulation/functions/fnc_setAEDLocal.sqf').read_text(encoding='utf-8-sig')
    reset = (ROOT.parent / 'circulation/functions/fnc_resetVariables.sqf').read_text(encoding='utf-8-sig')
    assert 'ACME_sync_localArmed' in toggle and '"syncArmed"' in toggle
    assert '_tgt setVariable ["ACME_sync_armed"' not in toggle
    assert 'ACME_sync_localArmed' in flags and 'ACME_sync_localArmed' in setup
    assert 'ACME_sync_localArmed' in req
    assert 'case "syncArmed"' in owner and '_patient setVariable ["ACME_sync_armed", _armed, true]' in owner
    assert '(_patient getVariable ["ACME_sync_armed", false]) != _expectedSync' not in shock
    assert '_patient setVariable ["ACME_sync_armed", false, true]' in set_aed
    assert '_patient setVariable ["ACME_sync_armed", false, true]' in reset


def test_direct_pressure_marker_is_patient_owner_authoritative_and_disconnect_safe():
    start = src('functions/fn_directPressureStart.sqf')
    torso = src('functions/fn_directPressureTorso.sqf')
    limb = src('functions/fn_directPressureLimb.sqf')
    self_dp = src('functions/fn_directPressureSelf.sqf')
    stop = src('functions/fn_directPressureStop.sqf')
    tick = src('functions/fn_directPressureTick.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    runtime = src('functions/fn_initPressureAndAuscultationConfig.sqf')
    assert '"directPressureMarker"' not in start
    assert '"directPressureMarker"' in torso and '"directPressureMarker"' in limb and '"directPressureMarker"' in self_dp
    torso_active = '[_patient, "directPressureMarker", [_medic, _bodyPart, true]]'
    limb_active = '[_patient, "directPressureMarker", [_medic, _bodyPart, true]]'
    self_active = '[_medic, "directPressureMarker", [_medic, _bodyPart, true]]'
    assert torso.index('ACME_DP_Active", true') < torso.index(torso_active)
    assert limb.index('ACME_DP_Active", true') < limb.index(limb_active)
    assert self_dp.index('ACME_DP_Active", true') < self_dp.index(self_active)
    assert '"directPressureMarker"' in stop
    assert tick.count('"directPressureMarker"') >= 2
    assert '_patient setVariable [format ["ACME_DP_press_%1"' not in start
    assert '_patient setVariable [format ["ACME_DP_press_%1"' not in stop
    assert '_patient setVariable [format ["ACME_DP_press_%1"' not in tick
    block = owner.split('case "directPressureMarker"', 1)[1].split('case "directPressureClot"', 1)[0]
    assert '_patient setVariable [_key, _medic, true];' in block
    assert 'isEqualTo _medic' in block
    assert 'ACME_DP_ServerCleanupInstalled' in runtime
    assert 'HandleDisconnect' in runtime and 'EntityKilled' in runtime



def test_aajt_apply_remove_are_owner_serialized_and_refund_only_losers_or_winner():
    apply = src('functions/fn_aajtApply.sqf')
    remove = src('functions/fn_aajtRemove.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    init = src('functions/fn_ownerInit.sqf')
    assert '!local _patient' in apply and '"aajtApply"' in apply
    assert '!local _patient' in remove and '"aajtRemove"' in remove
    assert 'case "aajtApply"' in owner and 'case "aajtRemove"' in owner
    assert 'ACME_aajtReturnItem' in init
    assert apply.count('ACME_aajtReturnItem') >= 2
    assert remove.count('ACME_aajtReturnItem') == 1
    assert 'addItem "ACME_AAJT_S"' not in remove


def test_vent_rear_battery_exchange_is_owner_serialized_and_acknowledged():
    flip = src('functions/fn_ventFlip.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    init = src('functions/fn_ownerInit.sqf')
    assert '"ventBatteryExchange"' in flip
    assert 'case "ventBatteryExchange"' in owner
    assert 'ACME_vent_batterySwapReceipts' in owner
    assert 'ACME_vent_batterySwapLockUntil' in owner
    assert 'ACME_ventBatteryExchangeResult' in init
    remote = flip.split('if (local _holder) then {', 1)[1]
    assert '[_holder, "ventBatteryExchange"' in remote


def test_hpmk_prep_is_two_phase_and_loser_refunds_provider_item():
    prep = src('functions/fn_hpmkPrep.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    init = src('functions/fn_ownerInit.sqf')
    assert '"hpmkPrep"' in prep and 'true]] call ACME_fnc_ownerDispatch' in prep
    assert 'case "hpmkPrep"' in owner
    assert 'ACME_hpmkReturnItem' in prep and 'ACME_hpmkReturnItem' in init
    assert '_occupied' in prep and 'ACME_hpmk_provider' in prep


def test_vent_power_and_hard_stop_commit_on_patient_owner_with_custody_guard():
    flip = src('functions/fn_ventFlip.sqf')
    stop = src('functions/fn_ventStopHard.sqf')
    commit = src('functions/fn_ventHardStopCommit.sqf')
    panel = src('functions/fn_ventPanelOpen.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    config = src('config.cpp')
    assert 'class ventHardStopCommit {};' in config
    assert '"ventPowerState"' in flip and '"ventPowerState"' in panel
    assert 'case "ventPowerState"' in owner and 'case "ventHardStop"' in owner
    assert '"ventHardStop"' in stop
    assert '!local _patient' in commit and '"ventHardStop"' in commit
    assert 'ACME_vent_custodyId' in commit
    assert 'ACME_vent_connected' in commit and 'ACME_vent_configured' in commit
    assert 'ACM_breathing_BVM_provider' in commit
    # Remote patient clinical shutdown is no longer performed directly by the operator UI function.
    assert '[_tgt, "ACME_vent_connected"' not in stop
    assert '[_tgt, "ACME_vent_driving"' not in stop


def test_native_transfusion_remove_and_flow_toggle_are_owner_serialized():
    remove = src("../circulation/functions/fnc_TransfusionMenu_RemoveBag.sqf")
    toggle = src("../circulation/functions/fnc_TransfusionMenu_ToggleIVFlow.sqf")
    owner = src("functions/fn_ownerDispatch.sqf")
    commit = src("functions/fn_transfusionRemoveBagCommit.sqf")
    flow = src("functions/fn_transfusionFlowToggleCommit.sqf")
    result = src("functions/fn_transfusionRemoveBagResult.sqf")
    assert '"transfusionRemoveBag"' in remove and 'setVariable [QGVAR(IV_Bags)' not in remove
    assert '"transfusionFlowToggle"' in toggle and 'setVariable [VAR_FLUIDBAG_FLOW_' not in toggle
    assert 'case "transfusionRemoveBag"' in owner and 'case "transfusionFlowToggle"' in owner
    assert '!local _patient' in commit and 'ACME_txRemoveReceipts' in commit
    assert 'Use Remove Infusion for a medicated bag.' in commit
    assert 'ACME_transfusionRemoveResult' in commit and 'addToInventory' in result
    assert '!local _patient' in flow and 'fluidBagsFlowIV' in flow and 'fluidBagsFlowIO' in flow


def test_pull_bag_and_y_discard_are_owner_serialized_before_salvage():
    pull = src('functions/fn_transfusionPullBag.sqf')
    discard = src('functions/fn_discardYTubing.sqf')
    pc = src('functions/fn_transfusionPullCommit.sqf')
    dc = src('functions/fn_discardYTubingCommit.sqf')
    pr = src('functions/fn_transfusionPullResult.sqf')
    dr = src('functions/fn_discardYTubingResult.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    pull_runtime = "\n".join(line for line in pull.splitlines() if not line.lstrip().startswith("//"))
    discard_runtime = "\n".join(line for line in discard.splitlines() if not line.lstrip().startswith("//"))
    assert '"transfusionPull"' in pull_runtime and 'ACME_fnc_ivBagsCommit' not in pull_runtime and 'ACME_usedBags' not in pull_runtime
    assert '"discardYTubing"' in discard_runtime and 'ACME_fnc_ivBagsCommit' not in discard_runtime and 'ACME_usedBags' not in discard_runtime
    assert '!local _patient' in pc and 'ACME_txPullReceipts' in pc and 'ACME_transfusionPullResult' in pc
    assert '!local _patient' in dc and 'ACME_yDiscardReceipts' in dc and 'ACME_discardYTubingResult' in dc
    assert 'ACME_usedBags' in pr and 'ACME_txPullSeen' in pr
    assert 'ACME_usedBags' in dr and 'ACME_yDiscardSeen' in dr
    assert 'case "transfusionPull"' in owner and 'case "discardYTubing"' in owner


def test_used_bag_rehang_is_owner_serialized_and_preserves_fresh_blood_id():
    ui = src('functions/fn_transfusionSpikeOrAdd.sqf')
    commit = src('functions/fn_rehangUsedBagCommit.sqf')
    result = src('functions/fn_rehangUsedBagResult.sqf')
    pull_result = src('functions/fn_transfusionPullResult.sqf')
    discard_result = src('functions/fn_discardYTubingResult.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    block = ui.split('if (_fromUsed) exitWith {',1)[1].split('\n};',1)[0]
    assert '"rehangUsedBag"' in block and 'ACME_fnc_ivBagsCommit' not in block
    assert '_used deleteAt _ui' in block and 'ACME_usedRehangPending' in block
    assert '!local _patient' in commit and 'ACME_usedRehangReceipts' in commit
    assert '_freshBloodID' in commit and '_entry=[_type,_remVol,_accessType,_site,_iv,_bloodType,_origVol,_freshBloodID,_bagUid]' in commit
    assert 'ACME_usedRehangPending' in result and 'ACME_usedBags' in result
    assert '_freshBloodID' in pull_result and '_freshBloodID' in discard_result
    assert 'case "rehangUsedBag"' in owner


def test_y_refill_claims_access_before_native_addbag_and_finalizes_on_owner():
    ui = src('functions/fn_transfusionSpikeOrAdd.sqf')
    commit = src('functions/fn_yRefillCommit.sqf')
    result = src('functions/fn_yRefillResult.sqf')
    addbag = src('../circulation/functions/fnc_TransfusionMenu_AddBag.sqf')
    owner = src('functions/fn_ownerDispatch.sqf')
    init = src('functions/fn_ownerInit.sqf')
    yblock = ui.split('// the in-place Y refill, "Add Bag".',1)[1].split('// spike into stage.',1)[0]
    assert '"claim"' in yblock and 'ACME_yRefillPending' in yblock
    assert 'call ACM_circulation_fnc_TransfusionMenu_AddBag' not in yblock
    assert 'ACME_fnc_ivBagsCommit' not in yblock
    assert '!local _patient' in commit and 'ACME_yRefillClaims' in commit
    assert 'Another provider is already replacing a bag on this Y line.' in commit
    assert 'CBA_fnc_waitUntilAndExecute' in commit and 'ACME_fnc_ivBagsCommit' in commit
    assert 'call ACM_circulation_fnc_TransfusionMenu_AddBag' in result
    assert 'ACME_yRefillActive' in result
    assert '"finalize"' in addbag and '"cancel"' in addbag
    assert 'case "yRefill"' in owner and 'ACME_yRefillResult' in init
