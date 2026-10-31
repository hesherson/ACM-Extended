[true, true] call ACME_fnc_suctionPublish;
// B52: the laryngoscopy provider pose belongs to this display. Stop it immediately on every real exit so no
// finite/held animation can keep replaying after the minigame is gone. Flashlight rebuilds are excluded below.
private _closingMedicB52 = uiNamespace getVariable ["ACME_laryngo_medic", ACE_player];
private _suctionRebuildB52 = (uiNamespace getVariable ["ACME_minigame_reopen", ""]) == "ACME_Laryngoscopy_Dialog";
if (!_suctionRebuildB52 && {!isNull _closingMedicB52}) then {[_closingMedicB52] call ACME_fnc_treatmentPoseStop;};
// The flashlight temporarily closes this display. Keep the same consumed bag and fill.
private _suctionRebuild = (uiNamespace getVariable ["ACME_minigame_reopen", ""]) == "ACME_Laryngoscopy_Dialog";
uiNamespace setVariable ["ACME_suction_resume", if (_suctionRebuild) then {[
    uiNamespace getVariable ["ACME_laryngo_medic", objNull],
    uiNamespace getVariable ["ACME_laryngo_patient", objNull],
    uiNamespace getVariable ["ACME_suction_bagOwner", []],
    uiNamespace getVariable ["ACME_suction_bagMl", 0],
    uiNamespace getVariable ["ACME_suction_totalMl", 0],
    uiNamespace getVariable ["ACME_suction_standalone", false]
]} else {[]}];
if (!_suctionRebuild) then {uiNamespace setVariable ["ACME_suction_bagOwner", []];};

// closing the screen puts the instrument down, so the light goes with it. without this a medic could close the
// dialog mid-procedure and walk away lit by a laryngoscope that is no longer in their hand.
["stow"] call ACME_fnc_laryngoFlash;
uiNamespace setVariable ["ACME_laryngo_held", ""];
uiNamespace setVariable ["ACME_laryngo_mp", nil];
uiNamespace setVariable ["ACME_laryngo_cl", nil];
// the dialog unload: stop the tick and clear all transient mini-game state.
private _pfh = uiNamespace getVariable ["ACME_laryngo_pfh", -1];
if (_pfh >= 0) then { [_pfh] call CBA_fnc_removePerFrameHandler; };
uiNamespace setVariable ["ACME_laryngo_pfh", -1];
// hand the airway back to the casualty. everything that describes them rather than the operator is written to the
// patient before the screen state is cleared, so the next person to open it, whoever they are, finds the airway
// exactly as it was left: the same mess, the same damage and the same count against it.
private _pat = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
// The render loop batches migration updates. Preserve the last real adjustment even when the screen closes
// before its next 0.20-second send or the final movement was smaller than the visual threshold.
// Ejection owns its own removal transaction; an abandoned new intubation is not an existing tube adjustment.
if (!isNull _pat && {(uiNamespace getVariable ["ACME_laryngo_state", "idle"]) == "migrated"}
    && {!(uiNamespace getVariable ["ACME_laryngo_ejecting", false])}
    && {_pat getVariable ["ACME_ETT_Inserted", false]}) then {
    private _depth = uiNamespace getVariable ["ACME_laryngo_tubeDepth", 0];
    private _epoch = uiNamespace getVariable ["ACME_suctionEpoch", -1];
    private _tubeTime = uiNamespace getVariable ["ACME_laryngo_migrationTubeTime", -1];
    private _last = uiNamespace getVariable ["ACME_laryngo_migrationSyncLast", [-1, -1, false]];
    if (_depth isEqualType 0 && {finite _depth} && {_depth > 0.001} && {_depth <= 1}
        && {(_last param [0, -1]) >= 0} && {_epoch == ([_pat] call ACME_fnc_clinicalEpoch)}
        && {_tubeTime == (_pat getVariable ["ACME_ETT_Time", -1])}) then {
        private _frame = 1 + round (_depth * 7);
        private _mainstem = _frame > (uiNamespace getVariable ["ACME_laryngo_idealFrame", 8]);
        if !([_depth, _frame, _mainstem] isEqualTo _last) then {
            [_pat, "placement", [_depth, _frame, _mainstem, _epoch, _tubeTime]] call ACME_fnc_ettMigrationStateCommit;
        };
    };
};
if (!isNull _pat) then {[_pat, "ui:laryngo:" + str clientOwner, false] call ACME_fnc_ecgJostleRequest;};
// leaving the screen stops the suction, so the clock stops with it.
// B13: release command above; physiology recovers on the patient owner.
if (!isNull _pat) then {
    // not written back. ACME_laryngo_teethBroken on the casualty is a count that fn_laryngoteeth increments, and
    // writing a bool over it made the next chip try to add 1 to true. the count is the record, and the screen derives
    // its flag from it on open.
    // Native obstruction state and the owner-approved emesis record are authoritative.
    // Do not publish an old local fluid snapshot or miss count while closing a view.

    // a tube that is in and not tied down. leaving without the collar does not undo the intubation: the tube is
    // through the cords and working. it is simply not secured, which is a real and recognized state, and the body
    // diagram has always had an icon for it that nothing ever set.
    if ((_pat getVariable ["ACME_ETT_Inserted", false]) && {!(_pat getVariable ["ACME_ETT_Secured", false])}) then {
        [_pat, -1, -1, -1, true, true, false] call ACME_fnc_ettAirwayStateCommit;
    } else {
        [_pat, -1, -1, -1, false, true, false] call ACME_fnc_ettAirwayStateCommit;
    };
};

uiNamespace setVariable ["ACME_suction_bagMl", 0];
uiNamespace setVariable ["ACME_suction_sqT0", -1];
uiNamespace setVariable ["ACME_suction_sqBand", ["0000","0050"]];
uiNamespace setVariable ["ACME_suction_standalone", false];
uiNamespace setVariable ["ACME_laryngo_resume", false];
uiNamespace setVariable ["ACME_laryngo_reopenSecured", false];
uiNamespace setVariable ["ACME_laryngo_state", "idle"];
uiNamespace setVariable ["ACME_laryngo_held", ""];

uiNamespace setVariable ["ACME_laryngo_holding", false];
uiNamespace setVariable ["ACME_laryngo_lift", 0];
uiNamespace setVariable ["ACME_laryngo_reveal", 0];
uiNamespace setVariable ["ACME_laryngo_tubeDepth", 0];
uiNamespace setVariable ["ACME_laryngo_migrationSyncNext", 0];
uiNamespace setVariable ["ACME_laryngo_migrationSyncLast", [-1, -1, false]];
uiNamespace setVariable ["ACME_laryngo_migrationTubeTime", -1];
uiNamespace setVariable ["ACME_laryngo_tubeAim", ""];
uiNamespace setVariable ["ACME_laryngo_pryPressure", 0];
uiNamespace setVariable ["ACME_laryngo_pryReveal", 0];
uiNamespace setVariable ["ACME_laryngo_pryWarned", false];
uiNamespace setVariable ["ACME_laryngo_creakNext", 0];
uiNamespace setVariable ["ACME_laryngo_depth", 0.5];
uiNamespace setVariable ["ACME_laryngo_liftPending", 0];
uiNamespace setVariable ["ACME_laryngo_regripHeld", false];
uiNamespace setVariable ["ACME_laryngo_airwayOpen", false];
uiNamespace setVariable ["ACME_laryngo_gripStr", 0];
uiNamespace setVariable ["ACME_laryngo_tubeGrip", false];
uiNamespace setVariable ["ACME_laryngo_bladeYaw", 0];
uiNamespace setVariable ["ACME_laryngo_liftVel", 0];
uiNamespace setVariable ["ACME_laryngo_fulcUnsafe", false];
uiNamespace setVariable ["ACME_laryngo_tubeBalkUntil", 0];
uiNamespace setVariable ["ACME_laryngo_relSince", -1];
uiNamespace setVariable ["ACME_laryngo_collarSnapped", false];
uiNamespace setVariable ["ACME_laryngo_tubeInHand", false];
uiNamespace setVariable ["ACME_laryngo_tubeCanFeed", false];
uiNamespace setVariable ["ACME_laryngo_cuffSnap", false];
uiNamespace setVariable ["ACME_laryngo_cuffStart", 0];
uiNamespace setVariable ["ACME_laryngo_tubeAimLock", ""];
uiNamespace setVariable ["ACME_laryngo_cuffDone", false];
uiNamespace setVariable ["ACME_laryngo_bladePic", 0];
uiNamespace setVariable ["ACME_laryngo_fulcNext", 0];
// report what came out. the total covers both devices, and it is only shown if anything was actually removed.
private _sucTotal = round (uiNamespace getVariable ["ACME_suction_totalMl", 0]);
if (_sucTotal > 0 && {!_suctionRebuild}) then {
    [format ["Suctioned %1 ml.", _sucTotal], 3] call ace_common_fnc_displayTextStructured;
    private _sPat = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
    if (!isNull _sPat && {!isNil "ace_medical_treatment_fnc_addToLog"}) then {
        // The owner records the final actual ledger total, not a possibly delayed UI estimate.
    };
};
uiNamespace setVariable ["ACME_suction_totalMl", 0];

uiNamespace setVariable ["ACME_laryngo_gagMisses", 0];
uiNamespace setVariable ["ACME_laryngo_gagNext", 0];
uiNamespace setVariable ["ACME_laryngo_fluidKind", ""];
uiNamespace setVariable ["ACME_laryngo_fluidStage", 0];
uiNamespace setVariable ["ACME_laryngo_fluidPhase", 0];
uiNamespace setVariable ["ACME_laryngo_fluidMode", "rest"];
uiNamespace setVariable ["ACME_laryngo_sucMode", "clear"];
uiNamespace setVariable ["ACME_laryngo_sucFrame", 0];
uiNamespace setVariable ["ACME_laryngo_sucOn", false];
uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
[uiNamespace getVariable ["ACME_laryngo_medic", ACE_player]] call ACME_fnc_suctionSfxStop;
uiNamespace setVariable ["ACME_laryngo_sucNext", 0];
uiNamespace setVariable ["ACME_laryngo_sucDrainNext", 0];
uiNamespace setVariable ["ACME_laryngo_sucLastX", -999];
uiNamespace setVariable ["ACME_laryngo_sucSweepDir", 0];
uiNamespace setVariable ["ACME_laryngo_sucSweepAmp", 0];
uiNamespace setVariable ["ACME_laryngo_sucSweepUntil", 0];
uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
uiNamespace setVariable ["ACME_laryngo_sucPinRel", []];
uiNamespace setVariable ["ACME_laryngo_fluidCap", 10];
uiNamespace setVariable ["ACME_laryngo_fluidPersist", false];
uiNamespace setVariable ["ACME_laryngo_syringeUsed", false];
uiNamespace setVariable ["ACME_laryngo_collarUsed", false];
uiNamespace setVariable ["ACME_laryngo_fluidReturnAt", 0];
uiNamespace setVariable ["ACME_laryngo_sucHint", 0];
uiNamespace setVariable ["ACME_laryngo_fluidPhaseNext", 0];
uiNamespace setVariable ["ACME_laryngo_fluidFillNext", 0];
{ uiNamespace setVariable [_x, false]; } forEach ["ACME_laryngo_kUp","ACME_laryngo_kDown","ACME_laryngo_kLeft","ACME_laryngo_kRight","ACME_laryngo_kFulcBack","ACME_laryngo_kFulcFwd"];
uiNamespace setVariable ["ACME_laryngo_overPressure", 0];
uiNamespace setVariable ["ACME_laryngo_tubeCatch", -1];
uiNamespace setVariable ["ACME_laryngo_tubeClicks", []];
uiNamespace setVariable ["ACME_laryngo_tubeRammed", false];
uiNamespace setVariable ["ACME_laryngo_tubePassed", false];
uiNamespace setVariable ["ACME_laryngo_cuffAmt", 0];
uiNamespace setVariable ["ACME_laryngo_cuffGrab", false];
uiNamespace setVariable ["ACME_laryngo_tubeTipPos", []];
uiNamespace setVariable ["ACME_laryngo_tubeAng", 0];
uiNamespace setVariable ["ACME_laryngo_tubeAngVel", 0];
uiNamespace setVariable ["ACME_laryngo_attemptStarted", false];
uiNamespace setVariable ["ACME_laryngo_attemptClock", 0];

// drop the captured resting layout, or the next open would shake from stale positions.
uiNamespace setVariable ["ACME_Laryngo_ShakeBase", []];
// release the beam, or every other screen would keep lighting the blade tip that is no longer there.
uiNamespace setVariable ["ACME_Laryngo_ShakeBase_off", [0, 0]];

// the darkness shade belongs to the display that is closing. drop the handle, or the next open inherits a dead
// control and never draws the shade again, a bug that would only show up at night, days later.
// it is an array rather than a control. fn_darknessshade keeps a list of controls under this key and calls count
// on it, so handing it a controlnull meant the next open could not read its own state and the shade never came
// back. that is why the flashlight worked once and then did nothing in this screen.
uiNamespace setVariable ["ACME_LG_Shade", []];

// drop back into the medical menu, at the airway category, rather than exiting to the game. it is a no-op during
// the flashlight close and reopen, which is guarded inside the helper.
[uiNamespace getVariable ["ACME_laryngo_patient", objNull], "airway"] call ACME_fnc_reopenMedicalMenu;

uiNamespace setVariable ["ACME_suctionToken", ""];
