// a tray click. one tool in the hand at a time.
// call it as ['scope', 'tube', 'collar' or 'syringe'] call ACME_fnc_laryngoGrab.
// clicking any slot stows whatever is currently held and picks up the new thing instead. without that the tools
// simply stacked on top of each other on screen. clicking the slot you are already holding puts it away.
// every slot is live at every point. whether a thing is useful yet is discovered by trying to use it rather than
// by the tray refusing to hand it over.
params ["_which"];
private _held = uiNamespace getVariable ["ACME_laryngo_held", ""];

// B115: once an ET tube is in the airway, the tray icon can never re-spawn, re-grab or reposition it. Use both
// the UI depth and authoritative patient state so a reopened airway view is protected even before its local depth
// reconstruction finishes. If the cuff is up, explain why the tube cannot be manipulated.
private _tubePatient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
private _tubePlaced = (uiNamespace getVariable ["ACME_laryngo_tubeDepth", 0]) > 0.001
    || {!isNull _tubePatient && {_tubePatient getVariable ["ACME_ETT_Inserted", false]}};
if (_which == "tube" && {_tubePlaced}) exitWith {
    if (!isNull _tubePatient && {_tubePatient getVariable ["ACME_ETT_CuffInflated", false]}) then {
        ["Deflate the ET tube cuff before adjusting or extubating the tube.", 2.5] call ace_common_fnc_displayTextStructured;
    };
};

// a secured airway is not touched. once the tube is in and the collar is on, the tray stops handing anything out
// and stops taking anything back: the tube cannot be lifted off, the collar cannot be unclipped, and the blade
// cannot be reintroduced. the only way it comes out is the extubate action in airway adjuncts.
// a secured airway can still be worked on and simply cannot be moved. suction clears it, the collar comes off to
// allow adjustment, and the syringe lets the cuff down. everything else stays locked out.
if ((uiNamespace getVariable ["ACME_laryngo_state", ""]) == "complete"
    && {!(_which in ["suction", "collar", "syringe"])}) exitWith {
    ["The airway is secured. Take the collar off if it has to be adjusted.", 3] call ace_common_fnc_displayTextStructured;
};

// clicking the suction slot cancels a pinned yankauer, wherever it is and whatever else is in hand.
if (_which == "suction" && {uiNamespace getVariable ["ACME_laryngo_sucPinned", false]}) exitWith {
    uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
    uiNamespace setVariable ["ACME_laryngo_sucOn", false];
    [uiNamespace getVariable ["ACME_laryngo_medic", ACE_player]] call ACME_fnc_suctionSfxStop;
    playSound "ACME_VentDial";
    [] call ACME_fnc_laryngoRefreshSlots;
};

// a used consumable is gone. it is not in the tray to be picked up again.
if (_which == "syringe" && {uiNamespace getVariable ["ACME_laryngo_syringeUsed", false]}) exitWith {
    ["That syringe is spent.", 1.5] call ace_common_fnc_displayTextStructured;
};
if (_which == "collar" && {uiNamespace getVariable ["ACME_laryngo_collarUsed", false]}) exitWith {
    ["The collar is already on the tube.", 1.5] call ace_common_fnc_displayTextStructured;
};

// A suction input resolves the provider's current equipment before testing availability.
if (_which == "suction" && {([true] call ACME_fnc_suctionSelectDevice) < 0}) exitWith {
    ["No suction device carried.", 2] call ace_common_fnc_displayTextStructured;
};

if (_which == "suction" && {(uiNamespace getVariable ["ACME_suction_type",-1]) == 1}
    && {!([uiNamespace getVariable ["ACME_laryngo_medic",objNull],_tubePatient] call ACME_fnc_equipmentAvailable)}) exitWith {
    private _medic = uiNamespace getVariable ["ACME_laryngo_medic",objNull];
    private _dialog = uiNamespace getVariable ["ACME_laryngo_dlg",displayNull];
    [_medic,_tubePatient,{
        params ["_dialog","_patient"];
        if (!isNull _dialog && {_dialog isEqualTo (uiNamespace getVariable ["ACME_laryngo_dlg",displayNull])}
            && {_patient isEqualTo (uiNamespace getVariable ["ACME_laryngo_patient",objNull])}
            && {(uiNamespace getVariable ["ACME_laryngo_held",""]) != "suction"}) then {
            ["suction"] call ACME_fnc_laryngoGrab;
        };
    },[_dialog,_tubePatient]] call ACME_fnc_equipmentUseAccuvac;
};

// taking the collar back. if one is already fastened, clicking its tray slot removes it rather than refusing. the
// collar is a strap, so putting it on and taking it off are the same act in reverse and it costs nothing.
if (_which == "collar"
    && {!isNull (uiNamespace getVariable ["ACME_laryngo_patient", objNull])}
    && {(uiNamespace getVariable ["ACME_laryngo_patient", objNull]) getVariable ["ACME_ETT_Secured", false]}) exitWith {
    [] call ACME_fnc_laryngoCollarRemove;
};

private _stow = {
    params ["_what"];
    switch (_what) do {
        case "scope": {
            uiNamespace setVariable ["ACME_laryngo_lift", 0];
            uiNamespace setVariable ["ACME_laryngo_liftVel", 0];
            uiNamespace setVariable ["ACME_laryngo_bladePic", 0];
            // putting the blade away is the only thing that hands the mouse back control of it.
            uiNamespace setVariable ["ACME_laryngo_bladeLocked", false];
            if ((uiNamespace getVariable ["ACME_laryngo_state", ""]) in ["scopeHeld","inserted","lifting","held"]) then {
                uiNamespace setVariable ["ACME_laryngo_state", "idle"];
                uiNamespace setVariable ["ACME_laryngo_airwayOpen", false];
            };
            ["stow"] call ACME_fnc_laryngoFlash;
        };
        case "tube": {
            uiNamespace setVariable ["ACME_laryngo_tubeInHand", false];
            uiNamespace setVariable ["ACME_laryngo_tubeGrip", false];
            // a seated tube is not in your hand any more. this used to wipe the depth to zero unconditionally, which is
            // correct for putting an unused tube back in the tray and catastrophic for one already through the cords,
            // because reaching for the syringe silently pulled the tube straight out of the patient. past the minimum seating
            // frame the tube belongs to the casualty, and letting go of it means letting go of the free end rather than
            // extubating them.
            // return to tray is gone. it only ever existed to tidy up an unused tube, and every version of the frame threshold
            // that tried to protect a placed one has still found a way to pull a tube out of a patient. a tube leaves the
            // airway by being withdrawn on the wheel or by extubate, and by nothing else. putting it down is letting go of
            // the free end.
            uiNamespace setVariable ["ACME_laryngo_tubeVel", 0];
        };
        case "collar":  {};
        case "syringe": {
            ["release"] call ACME_fnc_laryngoCuff;
            uiNamespace setVariable ["ACME_laryngo_cuffGrab", false];
            private _dS = uiNamespace getVariable ["ACME_laryngo_dlg", displayNull];
            if (!isNull _dS) then {{(_dS displayCtrl _x) ctrlSetTextColor [1,1,1,0];} forEach [87814,87817,87818];};
        };
        case "suction": {
            uiNamespace setVariable ["ACME_laryngo_sucOn", false];
            uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
            [uiNamespace getVariable ["ACME_laryngo_medic", ACE_player]] call ACME_fnc_suctionSfxStop;
        };
    };
    uiNamespace setVariable ["ACME_laryngo_held", ""];
};

if (_held == _which) exitWith {
    [_held] call _stow;
    playSound "ACME_VentDial";
    [] call ACME_fnc_laryngoRefreshSlots;
};

// the exception: a laryngoscope pinned in the mouth is not stowed by reaching for something else. that is the
// entire two-handed idea. once the blade is locked in place with the grip key it stays there and your other hand
// is free to pick up the tube, the collar or the syringe. every other combination still auto-stows, and clicking
// the laryngoscope slot itself still puts it away.
// the two things that are allowed to keep working while you pick up something else are the ones that are
// physically pinned: a blade locked in the mouth with the grip key, and a yankauer pinned with the middle button.
// everything else auto-stows, so tools cannot pile up just by clicking tray icons.
private _pinned = (_held == "scope")
    && {uiNamespace getVariable ["ACME_laryngo_bladeLocked", false]}
    && {(uiNamespace getVariable ["ACME_laryngo_state", ""]) in ["inserted","lifting","held","seated"]};
if (_held != "" && {!_pinned}) then { [_held] call _stow; };
if (_pinned) then {
    // the blade keeps the mouth open and simply stops being the thing in the tray hand.
    uiNamespace setVariable ["ACME_laryngo_held", ""];
};

switch (_which) do {
    case "scope": {
        uiNamespace setVariable ["ACME_laryngo_held", "scope"];
        uiNamespace setVariable ["ACME_laryngo_state", "scopeHeld"];
        uiNamespace setVariable ["ACME_laryngo_bladeLocked", false];
        ["grab"] call ACME_fnc_laryngoFlash;
    };
    case "tube": {
        uiNamespace setVariable ["ACME_laryngo_held", "tube"];
        uiNamespace setVariable ["ACME_laryngo_tubeInHand", true];
        uiNamespace setVariable ["ACME_laryngo_tubeGrip", false];
        // only a fresh tube starts at zero. wiping the depth unconditionally meant that once a tube was in the patient,
        // any touch of the tray slot pulled it straight back out. a tube that is already in stays where it is and simply
        // comes back under the hand.
        private _tubeDepthB39 = uiNamespace getVariable ["ACME_laryngo_tubeDepth", 0];
        if (_tubeDepthB39 <= 0.001) then {
            uiNamespace setVariable ["ACME_laryngo_tubeAnchored", false];
            uiNamespace setVariable ["ACME_laryngo_tubeDepth", 0];
            uiNamespace setVariable ["ACME_laryngo_tubeTipPos", []];
            uiNamespace setVariable ["ACME_laryngo_tubeAng", 0];
            uiNamespace setVariable ["ACME_laryngo_tubeAngVel", 0];
        } else {
            // B39: touching the tube tray icon while a tube is already in the airway means
            // grabbing its free end, not respawning it at the cursor. Reconstruct the anchor
            // from the patient-space tip fraction saved at placement/reopen.
            private _ptB39 = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
            private _fracB39 = if (!isNull _ptB39) then {_ptB39 getVariable ["ACME_ETT_TipFrac", []]} else {[]};
            if ((count _fracB39) >= 2) then {
                uiNamespace setVariable ["ACME_laryngo_tubeAnchorRel", +_fracB39];
                uiNamespace setVariable ["ACME_laryngo_tubeAnchored", true];
                uiNamespace setVariable ["ACME_laryngo_tubeAimLock", "cords"];
            };
        };
    };
    case "collar": {
        uiNamespace setVariable ["ACME_laryngo_held", "collar"];
    };
    case "syringe": {
        uiNamespace setVariable ["ACME_laryngo_held", "syringe"];
        ["show"] call ACME_fnc_laryngoCuff;
    };
    case "suction": {
        uiNamespace setVariable ["ACME_laryngo_held", "suction"];
        uiNamespace setVariable ["ACME_laryngo_sucMode", "clear"];
        uiNamespace setVariable ["ACME_laryngo_sucFrame", 0];
        uiNamespace setVariable ["ACME_laryngo_sucOn", false];
    };
};
playSound "ACME_VentDial";

[] call ACME_fnc_laryngoRefreshSlots;
