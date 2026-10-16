// save the unfinished state of this limb onto the patient, so the next open carries on where it left off.
// call it as [] call ACME_fnc_ivMinigameSaveState.
// the placed hubs already live on the patient as marks. what was missing is everything that is half done: a band
// still on the arm, a prepped site, and a catheter that went in but was never finished.
// it is keyed by body part and view, so each limb and each side of it keeps its own state.
// [false] records the just-loaded view without publishing an observation.
params [["_publish", true, [true]]];
if !([] call ACME_fnc_ivUiValid) exitWith {};
private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
if (isNull _patient) exitWith {};
private _bp = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
private _view = uiNamespace getVariable ["ACME_IV_View", ""];
private _key = format ["%1|%2", _bp, _view];

// a catheter in the middle of the needle withdraw is stored as fully threaded. the withdraw is a short automatic
// run and restoring it half way through would be a state nothing can leave.
private _stage = uiNamespace getVariable ["ACME_IV_InsStage", ""];
private _frame = uiNamespace getVariable ["ACME_IV_InsFrame", 0];
if ((uiNamespace getVariable ["ACME_IV_DLG",displayNull]) getVariable ["ACME_IV_FieldInserting",false]) then {_stage="";_frame=0;};
if (_stage == "retract") then { _stage = "thread"; _frame = 11; };
// the tubing is not a state worth saving on its own. fn_ivminigameinit hands it back whenever a bare hub is
// present, so a line left in hand comes back by itself.
if (_stage == "line") then { _stage = ""; };

private _band = [
    uiNamespace getVariable ["ACME_IV_BandOn", false],
    uiNamespace getVariable ["ACME_IV_Site", "middle"],
    uiNamespace getVariable ["ACME_IV_BandUV", []],
    uiNamespace getVariable ["ACME_IV_VeinUV", []],
    uiNamespace getVariable ["ACME_IV_Label", ""],
    uiNamespace getVariable ["ACME_IV_BandTex", ""]
];
private _ins = [
    _stage,
    _frame,
    uiNamespace getVariable ["ACME_IV_InsSuffix", ""],
    uiNamespace getVariable ["ACME_IV_InsGauge", 16],
    uiNamespace getVariable ["ACME_IV_InsU", 0.5],
    uiNamespace getVariable ["ACME_IV_InsV", 0.5],
    uiNamespace getVariable ["ACME_IV_InsHit", false],
    uiNamespace getVariable ["ACME_IV_InsProg", 0],
    // Store the site of the puncture with the coordinates of the puncture.
    // A medic can leave a catheter half in and continue at the next open.
    // That catheter must register at the site of its puncture.
    // This is element 8. A state from an older build stops at element 7.
    // fn_ivMinigameRestoreState then calculates the site again from insU and insV.
    uiNamespace getVariable ["ACME_IV_InsSite", ""],
    // Preserve the original miss/vein-wall outcome and anatomical EJ side.
    uiNamespace getVariable ["ACME_IV_StickAcc", 0],
    uiNamespace getVariable ["ACME_IV_InsEJSide", ""],
    // Optional element 11 retains the puncture angle across reopen/provider handoff.
    uiNamespace getVariable ["ACME_IV_InsAngle", 0]
];
// Tray choices do not constitute an insertion when no catheter is in progress.
if (_stage == "") then {_ins = ["",0,"",16,0.5,0.5,false,0,"",0,"",0];};
private _clean = [
    uiNamespace getVariable ["ACME_IV_Cleaned", false],
    uiNamespace getVariable ["ACME_IV_HoldCum", 0]
];

// nothing worth keeping. drop any old entry rather than storing an empty one.
private _worth = (_band select 0) || {_stage != ""} || {_clean select 0};

// The owner merges this one view. Never replace another provider's limb rows.
private _entry = if (_worth) then {[_key, _band, _ins, _clean]} else {[]};
// The owner's broadcast may arrive after a quick front/back round trip.
// This display-local journal is bounded by this limb's views; it is never broadcast.
private _display = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
private _changed = true;
if (!isNull _display) then {
    private _cache = _display getVariable ["ACME_IV_ViewCache", createHashMap];
    _changed = !(_entry isEqualTo (_cache getOrDefault [_key, []]));
    _cache set [_key, +_entry];
    _display setVariable ["ACME_IV_ViewCache", _cache];
};
// An untouched observer view must not replace a newer provider snapshot.
if (!_publish || {!_changed}) exitWith {};
[_patient, "ivState", [_patient, "view", [_key, _entry],
    [_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;
