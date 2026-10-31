if ((uiNamespace getVariable ["ACME_IV_DLG",displayNull]) getVariable ["ACME_IV_FinishBusy",false]) exitWith {};
// Keep the active catheter in control until it is completed or this face is suspended.
if ((uiNamespace getVariable ["ACME_IV_InsStage", ""]) in ["advance", "thread", "retract"]) exitWith {};
// pick up or put down the alcohol pad, on a single click, and click again to return it.
if (uiNamespace getVariable ["ACME_IV_Held", "none"] == "pad") exitWith {
    uiNamespace setVariable ["ACME_IV_Held", "none"];
    private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
    if (!isNull _dlg) then { (_dlg displayCtrl 86507) ctrlShow false; };
    playSound "ACME_IVCap";  // cap click. placing the pad BACK in its slot
    [] call ACME_fnc_ivMinigameRefreshBandSlot;
};
uiNamespace setVariable ["ACME_IV_PullIdx", -1];  // any pull in progress is abandoned here.
uiNamespace setVariable ["ACME_IV_Held", "pad"];
uiNamespace setVariable ["ACME_IV_WipeSwipes", 0];
// the scrub trail is NOT wiped here any more. antiseptic on skin does not vanish because you put the pad down
// or took the band off; it dries and fades. picking the pad up again should let you keep working the same
// area, and it did not, because this deleted everything first.
// only the stroke anchor resets, so the next dab starts a fresh stroke rather than drawing a line back from
// wherever the cursor was last time.
uiNamespace setVariable ["ACME_IV_PrepLast", []];
uiNamespace setVariable ["ACME_IV_WipeDir", 0];
uiNamespace setVariable ["ACME_IV_WipeLastX", -1e9];
uiNamespace setVariable ["ACME_IV_WipeTravel", 0];
[] call ACME_fnc_ivMinigameRefreshBandSlot;
