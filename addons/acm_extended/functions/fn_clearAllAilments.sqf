// Hard clinical reset for FullHeal/new-life initialization. Death does NOT call this function; fn_deathFreeze
// preserves the corpse's injury/intervention evidence and stops only runtime workers.
// _this may still arrive in the old [unit, preserveDeathInterventions] form for compatibility.
private _patient = if (_this isEqualType []) then { _this param [0, objNull] } else { _this };
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {};
private _preserveDeathInterventions = false;  // Full heal/respawn are real resets; death uses fn_deathFreeze instead.

if (!alive _patient && {
    (_patient getVariable ["ACME_headElevated", false])
    || {_patient getVariable ["ACME_headElev_vestRemoved", false]}
    || {(_patient getVariable ["ACME_headElev_propVest", ""]) != ""}
}) then {[_patient] call ACME_fnc_headElevDeathRelease;};
[_patient, "begin", _preserveDeathInterventions] call ACME_fnc_clinicalReset;
// This function is intentionally a hard reset; normal death no longer routes through it.
_patient setVariable ["ACME_NA2_resetTime", CBA_missionTime, true];
_patient setVariable ["ACME_CS_blockedEffectEpoch", _patient getVariable ["ACME_CS_netEpoch", ""], true];
_patient setVariable ["ACME_ncd_tensionEpoch", "", true];
if (_patient getVariable ["ACME_nrb_on", false]) then { [_patient, objNull, false, false, true] call ACME_fnc_nrbStateLocal; };
["ACME_CS_reset", [_patient, CBA_missionTime]] call CBA_fnc_serverEvent;

// Stop the active bleed sound on every teardown. Death, heal and respawn all use the same cleanup.
private _juncLeakSrc = _patient getVariable ["ACME_JuncLeakSfxSrc", objNull];
if (!isNull _juncLeakSrc) then {deleteVehicle _juncLeakSrc;};
_patient setVariable ["ACME_JuncLeakSfxSrc", objNull, true];
_patient setVariable ["ACME_JuncLeakNext", -1, true];
if (!isNil "ACME_fnc_junctionalFullHeal") then { [_patient] call ACME_fnc_junctionalFullHeal; };

// head elevation: a quiet teardown, with no pose forcing. the carrier that was propping the head returns to the
// body of the patient, the ground and wedge prop is deleted, the helper is released, and every elevation flag
// clears. a heal must never leave the casualty flagged elevated, because the stale flag made the next torso
// treatment, the chest-seal minigame or CPR, suspend a standing patient into the lying pose.
if (_patient getVariable ["ACME_headElevated", false]) then {
    if (!isNil "ACME_fnc_headElevateStop") then { [objNull, _patient, true] call ACME_fnc_headElevateStop; };
};
// a desync sweep. the prop or vest can outlive the flag, or the stop function may be unavailable. this gives the
// same guarantees independently: the carrier back on the body, the prop gone, the helper gone and the flags
// gone.
[_patient] call ACME_fnc_headElevVestRestore;
[_patient, true] call ACME_fnc_chestAccessVestRestore;
_patient setVariable ["ACME_chestAccess_leases", createHashMap, true];
private _hePropObj = _patient getVariable ["ACME_headElev_propObj", objNull];
if (!isNull _hePropObj) then { detach _hePropObj; deleteVehicle _hePropObj; };
private _heHelper = _patient getVariable ["ACME_headElev_helper", objNull];
if (!isNull _heHelper) then {
    if ((attachedTo _patient) == _heHelper) then { detach _patient; };
    deleteVehicle _heHelper;
};
_patient setVariable ["ACME_headElev_propObj", objNull, true];
_patient setVariable ["ACME_headElev_helper", objNull, true];
private _heMass = _patient getVariable ["ACME_headElev_mass", -1];
if (_heMass > 0) then {_patient setMass _heMass;};
{
    _patient setVariable [_x, nil, true];
} forEach [
    "ACME_headElevated", "ACME_headElev_Suspended", "ACME_headElev_ResumePending",
    "ACME_headElev_TransportPending", "ACME_headElev_basePosASL", "ACME_headElev_baseDir", "ACME_headElev_mass"
];

// Chest seal, NAR SPEAR and NCD evidence is reset with the rest of the casualty. The server-side chest-seal
// reset below clears hole data, seals and decompression evidence, so no discovered wound survives a hard reset.
{
    _patient setVariable [_x, nil, true];
} forEach [
    "ACME_CS_facing"
];

// thoracostomy and chest tube: stop the passive heimlich drain and remove the blood staining.
private _drainPFH = _patient getVariable ["ACME_thora_drainPFH", -1];
if (_drainPFH != -1) then { [_drainPFH] call CBA_fnc_removePerFrameHandler; };
_patient setVariable ["ACME_thora_drainPFH", -1];
// the chest tube output tally and the surgical flag clear with everything else. a healed casualty has not bled
// 1500 ml into a chest they no longer have an injury in.
// Output totals/history now have one server writer. Local copies clear immediately;
// the reset event publishes the same baseline without a second public writer.
[_patient, "ml", 0, false] call ACME_fnc_thoraOutputStateCommit;
[_patient, "perHour", 0, false] call ACME_fnc_thoraOutputStateCommit;
[_patient, "start", -1, false] call ACME_fnc_thoraOutputStateCommit;
[_patient, "hist", nil, false] call ACME_fnc_thoraOutputStateCommit;
[_patient, "fluidSeen", nil, false] call ACME_fnc_thoraOutputStateCommit;
{
    private _decal = _x param [0, objNull];
    if (!isNull _decal) then { deleteVehicle _decal; };
} forEach (_patient getVariable ["ACME_thora_bloodDecals", []]);
_patient setVariable ["ACME_thora_bloodDecals", nil, true];

// the surgical and evac gates, for a bilateral chest tube casualty and the ceftriaxone evac requirement.
// altitude.
_patient setVariable ["ACME_alt_hypoxia", 0, true];
_patient setVariable ["ACME_alt_expanding", false, true];
_patient setVariable ["ACME_flightG_resistAdd", 0, true];
_patient setVariable ["ACME_flightG_stress", 0, true];

// PEEP and oxygenation.
_patient setVariable ["ACME_vent_peep", nil, true];
[_patient, 0, true, false] call ACME_fnc_ventShuntCommit;
_patient setVariable ["ACME_vent_mlPerKg", nil, true];

// the i:e ratio and trapped gas.
_patient setVariable ["ACME_vent_ie", nil, true];
_patient setVariable ["ACME_vent_autoPEEP", 0, true];
_patient setVariable ["ACME_vent_recruit", 0, true];

// the ventilator alert settings.
_patient setVariable ["ACME_vent_alertRRLow", nil, true];
_patient setVariable ["ACME_vent_alertRRHigh", nil, true];
_patient setVariable ["ACME_vent_alertPLimit", nil, true];
_patient setVariable ["ACME_vent_alertPAlert", nil, true];
_patient setVariable ["ACME_vent_alertInvIE", nil, true];
_patient setVariable ["ACME_vent_pLimited", false, true];

// the ventilator status box: t, z or c.
_patient setVariable ["ACME_vent_status", "", true];
_patient setVariable ["ACME_vent_nextZeroT", nil, true];
_patient setVariable ["ACME_vent_zeroUntilT", nil, true];
_patient setVariable ["ACME_vent_coughUntilT", nil, true];
_patient setVariable ["ACME_vent_nextCoughCheckT", nil, true];

// the ventilator alarms.
_patient setVariable ["ACME_vent_alarms", [], true];
_patient setVariable ["ACME_vent_alarmsPrev", [], true];
_patient setVariable ["ACME_vent_alarmSilencedUntil", 0, true];

// manual breath, the rolling rate window.
_patient setVariable ["ACME_vent_manualBreathTimes", nil, true];
_patient setVariable ["ACME_vent_manualRR", nil, true];
_patient setVariable ["ACME_vent_manualBreathT", nil, true];

// the ventilator running sound. never strand a looping source on a healed patient.
if (isServer) then {
    private _vSrc = _patient getVariable ["ACME_vent_sndSrc", objNull];
    if (!isNull _vSrc) then { detach _vSrc; deleteVehicle _vSrc; };
};
_patient setVariable ["ACME_vent_sndSrc", objNull, true];
_patient setVariable ["ACME_vent_sndState", 0, true];
_patient setVariable ["ACME_vent_sndLoopAt", nil, true];

// sugammadex reversal.
_patient setVariable ["ACME_sug_onsetT0", nil, true];
_patient setVariable ["ACME_sug_ramp", nil, true];
_patient setVariable ["ACME_sug_reversalEffective", nil, true];
_patient setVariable ["ACME_sug_mgPerKg", nil, true];
_patient setVariable ["ACME_sug_fullReversal", nil, true];
_patient setVariable ["ACME_sug_boundCapacity", nil, true];

// midazolam sedation onset.
_patient setVariable ["ACME_midaz_onsetT0", nil, true];
_patient setVariable ["ACME_midaz_sedRamp", nil, true];
_patient setVariable ["ACME_midaz_sedEffective", nil, true];

// awake paralysis, the RSI awareness event.
[_patient, "KEEP", "CLEAR", "CLEAR", "CLEAR", true, false] call ACME_fnc_rocStressStateCommit;
[_patient, "CLEAR", "CLEAR", "CLEAR", true, false] call ACME_fnc_rocAwarenessStateCommit;
_patient setVariable ["ACME_roc_awakeBPbump", nil, true];  // a legacy dead variable.

// blast lung.
[_patient, 0, true, false, true] call ACME_fnc_blastLungStateCommit;
[_patient, "CLEAR", "CLEAR", "CLEAR", true] call ACME_fnc_blastLungEpisodeCommit;
_patient setVariable ["ACME_blastLung_rrDrive", nil, true];
[_patient, objNull, objNull, true, false, true] call ACME_fnc_blastLungArdsCommit;
if (_patient getVariable ["ACME_blastLung_ownsBreathVar", false]) then {
    [_patient, 1, true] call ACM_CBRN_fnc_setBreathingAbilityState;
};
_patient setVariable ["ACME_blastLung_ownsBreathVar", nil, true];

// the ventilator barotrauma and VILI state.
_patient setVariable ["ACME_vent_baroDose", nil, true];
_patient setVariable ["ACME_vent_baroEvents", nil, true];
_patient setVariable ["ACME_vent_baroInjury", nil, true];
_patient setVariable ["ACME_vent_baroPTX", nil, true];
_patient setVariable ["ACME_vent_pipState", nil, true];

// B57: every visible/procedural thoracostomy mark is per-patient state and must disappear at every reset boundary.
{
    private _side = _x;
    {
        [_patient, _side, _x, nil] call ACME_fnc_thoraSideStateCommit;
    } forEach ["incision", "incisionScore", "prep", "infection", "open", "ribTarget", "site", "tube", "sealed"];
} forEach ["left", "right"];
_patient setVariable ["ACME_thora_ver", 0, true];
[_patient, false] call ACME_fnc_surgicalCasualtyCommit;
[_patient, false, true, false, true] call ACME_fnc_evacuationRequirementCommit;

// cheyne-stokes respiration cycling.
{
    _patient setVariable [_x, nil, true];
} forEach ["ACME_cs_active", "ACME_cs_cycleStart", "ACME_cs_savedRR", "ACME_cs_rrDrive"];

// B57: cosmetic vascular injury evidence is part of the hard reset too. Zeus/full-heal, death and respawn all
// start from clean skin; no old IV/EJ bruise/puncture record is carried forward.
_patient setVariable ["ACME_IV_Marks", nil, true];
_patient setVariable ["ACME_EJTransfusionSite", nil, true];

// obtundation: lift the pose first, then clear all of its state.
if (!isNil "ACME_fnc_obtundedSet" && {_patient getVariable ["ACME_obtunded", false]}) then {
    [_patient, false, false] call ACME_fnc_obtundedSet;
};
// Phase 59: scrub the canonical tuple even if the casualty was already off but retained stale/manual snapshot state.
[_patient, false, false, "", -1, true] call ACME_fnc_obtundedStateCommit;
private _dirHolder = _patient getVariable ["ACME_obtunded_dirHolder", objNull];
if (!isNull _dirHolder) then {
    if ((attachedTo _patient) == _dirHolder) then { detach _patient; };
    deleteVehicle _dirHolder;
};
{
    _patient setVariable [_x, nil, true];
} forEach [
    "ACME_obtunded_forcedBack", "ACME_obtunded_treatmentHold",
    "ACME_obtunded_lockDir", "ACME_obtunded_firedManEH", "ACME_obtunded_poseRetryAt",
    "ACME_obtunded_transitioning", "ACME_obtunded_transitionToken", "ACME_obtunded_wakeStimGraceUntil",
    "ACME_obtunded_blurWaveCur", "ACME_obtunded_blurWaveNext", "ACME_obtunded_blurWaveTgt",
    "ACME_obtunded_uprightSince", "ACME_obtunded_landedFaceDown", "ACME_obtunded_dirHolder"
];

// seizure: stop the convulsion driver, which restores the heading, before its state is wiped below.
if (!isNil "ACME_fnc_seizureMotion") then { [_patient, false] call ACME_fnc_seizureMotion; };

// rhythm. on a live patient, from a debug clear, restore the saved hr target and force sinus. on a dead patient,
// leave ACM's death rhythm, asystole at hr 0, alone. restoring sinus and a live hr here was pinning the vitals
// of dead patients at their last value instead of letting everything flatline.
if (alive _patient) then {
    [_patient, 0] call ACME_fnc_rhythmSet;  // sinus.
    [_patient, 0] call ACM_circulation_fnc_setCardiacArrestTargetRhythm;
};
[_patient, [["aedPadsLastSync", -1]], true] call ACM_circulation_fnc_setRuntimeState;  // refresh the monitor, both of them.
[_patient, "", -1, true, false] call ACME_fnc_rhythmNativeHoldCommit;
[_patient, 0, true, false, true] call ACME_fnc_rhythmNativeHighHRFloorCommit;
[_patient, 0, true, true] call ACME_fnc_rhythmNativeShockGraceCommit;
{
    _patient setVariable [_x, nil, true];
} forEach [
    "ACME_rhythm_active", "ACME_rhythm_targetHR", "ACME_rhythm_bpOffset", "ACME_rhythm_savedTargetHR", "ACME_peaElectricalHR", "ACME_peaElectricalState",
    "ACM_circulation_AED_RhythmTransition",
    "ACME_rhythm_amioCum", "ACME_rhythm_obtundUntil", "ACME_rhythm_torsadesRefractoryUntil", "ACME_rhythm_torsadesNonPerfusing", "ACME_rhythm_torsadesPerfusion", "ACME_rhythm_torsadesArrestRequestAt",
    "ACME_rhythm_epiDripEarliest", "ACME_rhythm_magTerminatedLogged", "ACME_rhythm_magSuppressUntil",
    "ACME_rhythm_magLevel", "ACME_rhythm_lidoLastTherapeutic", "ACME_rhythm_lidoEffectiveness", "ACME_lido_serumLevel",
    "ACME_lido_seizureState", "ACME_lido_seizurePhaseEnd", "ACME_seizure_rrDrive",
    "ACME_seizure_drive", "ACME_seizure_suppression", "ACME_seizure_suppressed",
    "ACME_sarinSeizureCause", "ACME_debugSeizureUntil",
    "ACME_seizure_motionActive", "ACME_seizure_motionGestureEH", "ACME_seizure_motionCurrentGesture",
    "ACME_seizure_motionRetryPending", "ACME_seizure_motionAdvancePending",
    "ACME_seizure_motionSession", "ACME_seizure_motionReadyAt", "ACME_stethNextLungUpdate",
    // Legacy motion fields remain in the scrub list so a hot-reloaded casualty can never keep the old jitter worker.
    "ACME_seizure_motionPFH", "ACME_seizure_motionBaseDir", "ACME_seizure_motionAnimIdx",
    "ACME_seizure_motionPhase", "ACME_seizure_motionPhaseEnd",
    "ACME_lidoTox_hrTarget", "ACME_lidoTox_resistDelta", "ACME_lidoTox_arrestFired",
    "ACME_esmolol_serumLevel", "ACME_esmolol_driveMgMin", "ACME_esmololTox_resistDelta", "ACME_infusionTox_resistDelta",
    "ACME_rhythmNativeHoldSince",
    "ACME_rhythmNativeClearStart", "ACME_rhythmNativeLastSeen",
    "ACME_rhythmPressorSurgeKind", "ACME_rhythmPressorSurgeStart",
    "ACME_rhythmPressorSurgeRefractoryUntil", "ACME_rhythmThresholdForced", "ACME_rhythmThresholdKind",
    "ACME_rhythmThresholdStart",
    "ACME_amio_serumLevel",
    "ACME_hrTarget_circ", "ACME_hrTarget_tbi", "ACME_rrDrive_tbi", "ACME_vent_rrDrive", "ACME_vent_measRR", "ACME_vent_spontRR", "ACME_vent_backupActive",
    "ACME_vent_breathTimes", "ACME_vent_breathAcc",
    "ACME_hrDrive_ventRelief",
    "ACME_hrArrestSeenAt", "ACME_hrWrapLast",
    "ACME_ko_holdUntil", "ACME_ko_since",
    "ACME_tempReading",
    "ACME_hpmk_dropped"
];

// TBI and ICP.
[_patient, createHashMap] call ACME_fnc_tbiStateCommit;
{
    _patient setVariable [_x, nil, true];
} forEach [
    "ACME_tbi_HasTBI", "ACME_tbi_evacRequired", "ACME_tbi_evacFlagged",
    "ACME_tbi_bpSysOffset", "ACME_tbi_bpDiaOffset", "ACME_tbi_resistAdd", "ACME_tbi_savedRRTarget"
];

// hypothermia and the HPMK.
[_patient, "", true, false] call ACME_fnc_hpmkStateCommit;
[_patient, 37, true, false, true] call ACME_fnc_hypothermiaTemperatureCommit;
{
    _patient setVariable [_x, nil, true];
} forEach [
    "ACME_hypo_cumLoss", "ACME_hypo_lastBV",
    "ACME_hpmk_blanket", "ACME_hpmk_isBlanket"
];

// over-resuscitation pulmonary edema.
[_patient, [["overloadVolume", 0]], true] call ACM_circulation_fnc_setRuntimeState;
{
    _patient setVariable [_x, nil, true];
} forEach ["ACME_edema_crackles", "ACME_edema_savedRRTarget", "ACME_edema_debugForce"];

// vesicant and extravasation.
[_patient, "records", []] call ACME_fnc_vesicantRegistryCommit;
_patient setVariable ["ACME_vesicant_painApplied", nil, true];
// clear the per-iv placed-distal-to-a-compromised-site flags for every body part and access site.
// note that a foreach over an array exposes _x only. _y exists solely when iterating a hashmap, with a key and a
// value. the outer _x is saved into _cbp first, so the _x of the inner loop, the access site, can shadow it
// safely.
{
    private _cbp = _x;
    {
        _patient setVariable [format ["ACME_ivCompromised_%1_%2", _cbp, _x], nil, true];
        if (_cbp != "head") then {
            _patient setVariable [format ["ACME_ivInfiltrationVisual_%1_%2", _cbp, _x], nil, true];
        };
    } forEach [0, 1, 2];
} forEach ["leftarm", "rightarm", "leftleg", "rightleg", "head"];

// shock, plus the circulation chemistry and state, which fn_circhandle rebuilds fresh.
[_patient, createHashMap] call ACME_fnc_circStateCommit;
_patient setVariable ["ACME_ca_coagMult", 1, true];
[_patient, 0, "clear", true, false] call ACME_fnc_calciumCreditCommit;
{
    _patient setVariable [_x, nil, true];
} forEach [
    "ACME_circ_bpOffset", "ACME_circ_salineGivenMl",
    "ACME_ca_mapDropEased",
    "ACME_circ_salineTrackLastAt", "ACME_circ_salineTrackLastMl", "ACME_circ_salineTrackLastSource",
    "ACME_circ_respAcidosisBaselineRR", "ACME_ioPainFlowing", "ACME_ioPainStates", "ACME_ioPainWatchSerial",
    "ACME_ioFlowWatchSerial", "ACME_ioSyncopeSerial", "ACME_ioSyncopeToken", "ACME_hrRestBaseline", "ACME_pressorResistAdd"
];

// the active infusions and bag medications.
[_patient, []] call ACME_fnc_infusionMedicationStateCommit;

// the pressure infuser off, and the stale temperature reading cleared, for a fresh body or a full heal.
_patient setVariable ["ACME_pressureInfuserMult", 1, true];
_patient setVariable ["ACME_tempReadingAt", -1, true];

// drop the unit from every per-tick active list, so the handlers stop processing stale state.
{
    private _list = missionNamespace getVariable [_x, []];
    if (_list isEqualType []) then {
        missionNamespace setVariable [_x, _list - [_patient]];
    };
} forEach ["ACME_circ_activePatients", "ACME_tbi_activePatients", "ACME_infusion_activePatients"];

// the forced animation and lying-state release. a fully healed casualty ends the heal free. lying_state ownership
// is dropped, and if the body is still parked in any forced grounded pose, ACM's lying state, the ACME fixed
// poses, or an injured or unconscious-family settle, the ACM get up roll-over plays so they finish standing. it
// is skipped for dead or unconscious casualties, in vehicles, attached, or in an ACE drag or carry, because the
// release then belongs to those systems.
[_patient, false, true] call ACM_core_fnc_setLyingState;
if (alive _patient && {!(_patient getVariable ["ACE_isUnconscious", false])}
    && {isNull objectParent _patient} && {isNull attachedTo _patient}
    && {!(_patient call ace_common_fnc_isBeingDragged)} && {!(_patient call ace_common_fnc_isBeingCarried)}) then {
    private _asHeal = toLower animationState _patient;
    private _forced = ((_asHeal find "ainj") >= 0) || {(_asHeal find "unconscious") >= 0} || {(_asHeal find "lying") >= 0}
        || {(_asHeal find "acts_") == 0} || {_asHeal == "acm_lyingstate"};
    if (_forced && {(_asHeal find "unconsciousoutprone") < 0}) then {
        [_patient, "UnconsciousOutProne", 2] call ACME_fnc_doAnim;
    };
};

[_patient, "finish", _preserveDeathInterventions] call ACME_fnc_clinicalReset;
