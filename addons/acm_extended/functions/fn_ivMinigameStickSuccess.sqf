// a clean stick. the catheter seats at the stick location and advances on its own, from flash to catheter in to
// hub, then registers the real ACM iv and drops a persistent hub marker that survives re-opening the limb. there
// are no clicks and no prompts. the band stays on so another iv can be placed, above the used and removed sites.
// call it as [_stickU, _stickV] call ACME_fnc_ivMinigameStickSuccess.
params ["_su", "_sv"];
if ((uiNamespace getVariable ["ACME_IV_DLG",displayNull]) getVariable ["ACME_IV_FieldInserting",false]) exitWith {
    [] call ACME_fnc_ivFieldInsertEnd;
};
if !([] call ACME_fnc_ivUiValid) exitWith {};
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _dlg) exitWith {};
private _rect = uiNamespace getVariable ["ACME_IV_BodyRect", []];
if (_rect isEqualTo []) exitWith {};
_rect params ["_bx", "_by", "_bw", "_bh"];
private _af = uiNamespace getVariable ["ACME_IV_AspectFix", 0.5625];

uiNamespace setVariable ["ACME_IV_Stage", "cath"];
uiNamespace setVariable ["ACME_IV_Held", "none"];
uiNamespace setVariable ["ACME_IV_Dragging", false];
uiNamespace setVariable ["ACME_IV_StickU", _su];
uiNamespace setVariable ["ACME_IV_StickV", _sv];

(_dlg displayCtrl 86506) ctrlShow false;
private _heldC = uiNamespace getVariable ["ACME_IV_HeldCursorCtrl", controlNull];
if (!isNull _heldC) then { _heldC ctrlShow false; };
private _dot = uiNamespace getVariable ["ACME_IV_DotCtrl", controlNull];
if (!isNull _dot) then { _dot ctrlShow false; };

playSound "ACE_Sound_Click";

// a live catheter sprite at the stick site, tip-anchored, going from base to inserted. it seats at the angle it was
// committed at, so the hover tilt carries through the seat animation and into the persistent hub.
private _frame = uiNamespace getVariable ["ACME_IV_InsSuffix", ""];
// ej: lock the patient, anatomical, side into the registration site now, before the cursor can drift during the
// seat delay. do not derive this from the art frame, because the ej art is opposite-named so the needle points
// toward the midline. "left" is head access site 0 and "right" is head access site 1, in
// fn_ivminigameregister.
if ((_frame find "_ej_") == 0) then {
    private _ejAnat = toLower (uiNamespace getVariable ["ACME_IV_InsEJSide", ""]);
    if !(_ejAnat in ["left", "right"]) then {
        // a fallback for old saved ui state: frame-left art means patient-right, and frame-right art means
        // patient-left.
        _ejAnat = (["left", "right"] select ((_frame find "left") >= 0));
    };
    uiNamespace setVariable ["ACME_IV_Site", _ejAnat];
};

// reset the skin-prep state after every successful stick. the cleaned flag and the wipe accumulators only reset on
// init, flip and band placement, and the ej flow has no band, so after the first jugular the pad went dead, with
// no red prep spot, and a bilateral ej could not be prepped. each new site starts unprepped with a fresh pad
// state.
uiNamespace setVariable ["ACME_IV_Cleaned", false];
uiNamespace setVariable ["ACME_IV_CleanAt", nil];
uiNamespace setVariable ["ACME_IV_WipeSwipes", 0];
uiNamespace setVariable ["ACME_IV_WipeDir", 0];
uiNamespace setVariable ["ACME_IV_WipeTravel", 0];
uiNamespace setVariable ["ACME_IV_HoldCum", 0];
// the sprite is already on screen and already showing the needle captured frame, because the medic drove it
// there by hand. this function only commits the result.

// register the line, drop the persistent hub and hand the tubing over. it runs one beat later, so the last
// withdraw frame is on screen before the sprite gives way to the marker.
private _context = [_dlg, +(uiNamespace getVariable ["ACME_IV_Session", []]),
    _dlg getVariable ["ACME_IV_ViewGeneration", 0],
    uiNamespace getVariable ["ACME_IV_BodyPart", ""], uiNamespace getVariable ["ACME_IV_View", ""]];
[{
    params ["_frame", "_context"];
    if !(_context call ACME_fnc_ivMinigameViewValid) exitWith {};
    if ((uiNamespace getVariable ["ACME_IV_InsStage", ""]) != "retract") exitWith {};
    private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
    if (isNull _dlg) exitWith {};
    if ((uiNamespace getVariable ["ACME_IV_Stage", ""]) != "cath") exitWith {};
    private _cath = uiNamespace getVariable ["ACME_IV_CathCtrl", controlNull];
    if (!isNull _cath) then { _cath ctrlShow false; };  // the persistent marker takes over.
    [] call ACME_fnc_ivMinigameRegister;
    // The registration refuses a puncture with an unknown site.
    // No IV means no hub and no bruise. A hub and a bruise show an access that does not exist.
    // Give the dialog back to the medic and stop here.
    if !(uiNamespace getVariable ["ACME_IV_RegOK", false]) exitWith {
        uiNamespace setVariable ["ACME_IV_Stage", "ready"];
        uiNamespace setVariable ["ACME_IV_InsStage", ""];
        uiNamespace setVariable ["ACME_IV_Held", "none"];
        uiNamespace setVariable ["ACME_IV_InsSite", ""];
        [] call ACME_fnc_ivMinigameRefreshBandSlot;
        [] call ACME_fnc_ivMinigameSaveState;
    };
    [] call ACME_fnc_ivMinigameRefreshBandSlot;  // the needle is consumed, so update the slot count.
    private _su = uiNamespace getVariable ["ACME_IV_StickU", 0.5];
    private _sv = uiNamespace getVariable ["ACME_IV_StickV", 0.5];
    // the persistent mini-game marker is the catheter hub for every iv, the ej included. rendermarks builds it
    // from the frame and the gauge as supercath frame 14, so the ej gets its own upside-down hub. this is the
    // close-up seated catheter the medic sees in the establish-iv view, identical in kind to a limb iv. the flat
    // iv_ej_<side> art is not used here, because that is the body-diagram overlay, in fn_updateejimage.
    // the hub art is gauge colored now, so the mark carries the gauge. a mark saved by an older build has
    // gauge 0 and falls back to 16g when it is drawn.
    [_su, _sv, "hub", "", _frame, (uiNamespace getVariable ["ACME_IV_InsGauge", 16])] call ACME_fnc_ivMinigameAddMark;

    // Resolve the original puncture. A view flip cannot change its gauge, accuracy or hit result.
    private _bpB = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
    private _stB = uiNamespace getVariable ["ACME_IV_InsSite", ""];
    if (_stB isEqualTo "") then { _stB = uiNamespace getVariable ["ACME_IV_Site", ""]; };
    private _gB = uiNamespace getVariable ["ACME_IV_InsGauge", 18];
    private _hitB = uiNamespace getVariable ["ACME_IV_InsHit", true];
    private _accB = uiNamespace getVariable ["ACME_IV_StickAcc", 1];
    // A clean successful venous hit is visually CLEAN. Do not manufacture a bruise merely because the catheter
    // was large or slightly off-center. Immediate IV-site bruising belongs to an actual missed vessel; later
    // infiltration/extravasation is driven by its own live complication state.
    if (!_hitB && {[_bpB, _stB, _gB, _hitB, _accB] call ACME_fnc_ivStickBlows}) then {
        [_su, _sv, _gB, _bpB, _stB] call ACME_fnc_ivInfiltrated;
    };

    uiNamespace setVariable ["ACME_IV_Stage", "ready"];
    // the needle is out and the hub is in the vein. the tubing is not forced into the medic's hand. they take it
    // from the LINE slot in the tray when they want it.
    uiNamespace setVariable ["ACME_IV_InsStage", ""];
    uiNamespace setVariable ["ACME_IV_Held", "none"];
    // refresh again, because the first refresh ran while the needle was still in hand and hid its slot button.
    [] call ACME_fnc_ivMinigameRefreshBandSlot;
    if (!isNull _dlg) then { (_dlg displayCtrl 86503) ctrlSetText "Catheter seated. Connect the extension, check with saline, then secure it."; };
    // the catheter is in and the insertion is over, so clear the saved half-done state for this limb.
    [] call ACME_fnc_ivMinigameSaveState;
    playSound "ACE_Sound_Click";
}, [_frame, _context], 0.15] call CBA_fnc_waitAndExecute;
