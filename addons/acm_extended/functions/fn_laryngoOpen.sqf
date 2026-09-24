// opens the laryngoscopy intubation mini-game. it is called from the "Intubate (Orotracheal)" treatment action.
// _this is [_medic, _patient, _bodyPart].
params ["_medic", "_patient", ["_bodyPart", "head"]];
if !([_medic, "intubation", _patient getVariable ["ACME_ETT_Inserted", false]] call ACME_fnc_procedureAllowed) exitWith {};
if (!hasInterface) exitWith {};
if (isNull _patient) exitWith {};
if (_patient getVariable ["ACM_airway_RecoveryPosition_State", false]) exitWith {
    ["Move the patient out of the recovery position before intubating.", 2] call ace_common_fnc_displayTextStructured;
};

// Fresh intubation and NRB are mutually exclusive. Existing intubated patients may still reopen the airway view
// for tube management, but a new ETT procedure requires the mask off first.
if (!(_patient getVariable ["ACME_ETT_Inserted", false]) && {_patient getVariable ["ACME_nrb_on", false]}) exitWith {
    ["Remove the NRB before intubation. An ET tube requires BVM or ventilator support.", 2.5] call ace_common_fnc_displayTextStructured;
};

// clear the mode flags first, before anything reads them. these are set by other entry points and cleared on close,
// so if a close is ever missed the next intubation inherits them. a stale standalone-suction flag hides the entire
// tray, which is exactly the case of the tray icons never coming back.
uiNamespace setVariable ["ACME_suction_standalone", false];
uiNamespace setVariable ["ACME_suction_bagOwner", []];
uiNamespace setVariable ["ACME_suction_resume", []];
uiNamespace setVariable ["ACME_suction_type", -2];
uiNamespace setVariable ["ACME_laryngo_reopenSecured", false];
uiNamespace setVariable ["ACME_laryngo_resume", false];
uiNamespace setVariable ["ACME_laryngo_snap", []];
uiNamespace setVariable ["ACME_LG_Shade", []];

// they must carry both a laryngoscope and an et tube.
// the laryngoscope is required on every path, including coming back to a tube that has moved. it used to be waived
// for a resume, on the reasoning that a displaced tube is pushed back by hand. that is no longer true: the blade is
// what moves the tube now, in both directions, so arriving without one means standing over a displaced tube unable
// to touch it.
// the tube check below is still waived for a resume, because the tube is already in the patient rather than in the
// kit.
if ((_patient getVariable ["ACME_ETT_Inserted", false])) then { uiNamespace setVariable ["ACME_laryngo_resume", true]; };
if (([_medic, "ACME_Laryngoscope"] call ACME_fnc_itemCount) < 1) exitWith {
    ["You need a laryngoscope to intubate.", 2] call ace_common_fnc_displayTextStructured;
};
if (!(uiNamespace getVariable ["ACME_laryngo_resume", false])
    && {([_medic, "ACME_ETTube"] call ACME_fnc_itemCount) < 1}) exitWith {
    ["You need an endotracheal tube to intubate.", 2] call ace_common_fnc_displayTextStructured;
};
// already intubated?
// already intubated, and is it still where it should be? a tube that has worked its way out is exactly what this
// screen is for: come in, push it back to depth and tie it down. only a tube that is both fully seated and
// secured has nothing to do here.
if (_patient getVariable ["ACME_ETT_Inserted", false]) then {
    // a secured airway still opens and simply cannot be disturbed. refusing outright meant that once the screen was
    // closed there was no way back into it at all, so a mouth full of vomit or a cuff that was never inflated could be
    // seen on the body diagram and never actually worked on. the screen locks a secured tube by itself, so opening it
    // is safe and suction still works.
    uiNamespace setVariable ["ACME_laryngo_resume", true];
    if (_patient getVariable ["ACME_ETT_Secured", false]) then {
        uiNamespace setVariable ["ACME_laryngo_resume", false];
        uiNamespace setVariable ["ACME_laryngo_reopenSecured", true];
    };
};
// can this airway be attempted right now? this covers the ventilation lock after a failed attempt and the grade-4
// wall, where a mallampati iv or cormack-lehane iv has no identifiable airway and a supraglottic device is the
// answer. both say why.
([_patient] call ACME_fnc_laryngoCanAttempt) params ["_ok", "_why"];
if (!_ok) exitWith { [_why, 3] call ace_common_fnc_displayTextStructured; };

// stash the target for the dialog and the engine.
// the two mode flags are NOT cleared here. they are cleared once at the top of this function, before anything
// reads them, and then computed by the already-intubated block above. clearing them again at this point wiped
// that work one line before the dialog opened, so fn_laryngoinit always saw a fresh idle screen.
// what that looked like in game: open airway view on a patient who was already tubed and the screen forgot the
// tube, so the medic had to intubate again on someone who was already intubated.
// resume means the tube is in and not finished, so the screen comes up at "migrated" with the tube in hand at its
// saved depth. reopensecured means it is seated and tied, so the screen comes up at "complete", locked, with
// suction still available, which is the main reason to come back in.
uiNamespace setVariable ["ACME_laryngo_patient", _patient];
uiNamespace setVariable ["ACME_laryngo_medic", _medic];
// defer the dialog open by a short beat. when launched from a treatment action, ACE runs its own dialog cleanup
// right after this callback returns, because it closes the medical menu through closedialog. opening immediately
// here meant that cleanup closed the just-opened laryngoscopy dialog instead, giving a one-frame flash. deferring
// lets ACE's closedialog fire first, so it closes the medical menu and leaves the mini-game up. it is the same
// pattern the iv and chest-seal mini-games use.
[{ createDialog "ACME_Laryngoscopy_Dialog"; }, [], 0.1] call CBA_fnc_waitAndExecute;
