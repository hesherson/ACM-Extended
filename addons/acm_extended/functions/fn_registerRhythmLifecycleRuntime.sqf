// custom cardiac rhythms.
// the three ACM waveform generators are overridden at compile time through CfgFunctions, because ACM compiles
// its functions final and a runtime reassignment is ignored silently. the ekg override delegates codes of 100
// and above to ACME_fnc_genRhythmEKG. the pleth and capno overrides render a custom code as sinus. there is
// nothing to install here at runtime.

// sustain the active custom rhythms. this holds the display rhythm and drives hr to the target.
[{call ACME_fnc_rhythmTick}, 0.5, []] call CBA_fnc_addPerFrameHandler;
// physical awake-but-lying state change. it runs where the patient is local.
["ACME_obtundedApply", {_this call ACME_fnc_obtundedApply}] call CBA_fnc_addEventHandler;

// reset our per-life patient state on respawn. these vars live on the unit and otherwise bleed into the next
// life, so an obtunded or arrhythmic prior life carries over. this clears both units and force-removes the
// client-side obtundation screen effects on the fresh life.
// the mission-level handler is "EntityRespawned", with params [newentity, oldentity]. the "Respawn" enum exists
// only as a unit event handler. EntityRespawned fires for every entity, so we guard to humans only.
addMissionEventHandler ["EntityRespawned", {
    params ["_newUnit", "_oldUnit"];
    if !(_newUnit isKindOf "CAManBase") exitWith {};

    // The old body remains a corpse snapshot. Stop any residual local workers without deleting its injuries,
    // airway devices, vascular access, chest interventions, AAJT-S, dressings or other treatment evidence.
    if (!isNull _oldUnit && {local _oldUnit}) then {[_oldUnit] call ACME_fnc_deathFreeze;};

    // Initialize through the current owner once. The retry carries the original
    // issue time and completion/clinical-epoch fence, so damage or medication
    // acquired between this event and the retry can never be full-healed again.
    private _issuedAt = serverTime;
    [_newUnit, _issuedAt] call ACME_fnc_respawnClinicalReset;
    [{
        params ["_u", "_issuedAt"];
        [_u, _issuedAt] call ACME_fnc_respawnClinicalReset;
    }, [_newUnit, _issuedAt], 2.0] call CBA_fnc_waitAndExecute;

    if (!isNil "ACME_hpmk_activePatients") then {ACME_hpmk_activePatients = ACME_hpmk_activePatients - [_oldUnit];};
}];


// clear the native rhythm persistence after a confirmed ROSC. vt, vf and PVT must not self-clear from an hr
// wobble, but ACM's successful resuscitation pathway must be able to restore an organized rhythm.
["ace_medical_CPRSucceeded", {
    params ["_patient"];
    if (isNull _patient) exitWith {};
    [_patient, CBA_missionTime + (missionNamespace getVariable ["ACME_rhythmNativeShockGraceSec", 10]), true, false] call ACME_fnc_rhythmNativeShockGraceCommit;
    [_patient, "", -1, true, false] call ACME_fnc_rhythmNativeHoldCommit;
    [_patient, 0, false, false, false] call ACME_fnc_rhythmNativeHighHRFloorCommit;
    if (local _patient) then {
        _patient setVariable ["ACME_peaElectricalHR", nil, true];
        _patient setVariable ["ACME_peaElectricalState", nil, true];
    };
}] call CBA_fnc_addEventHandler;
