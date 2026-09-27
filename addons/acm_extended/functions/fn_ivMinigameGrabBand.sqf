// Keep the active catheter in control until it is completed or this face is suspended.
if ((uiNamespace getVariable ["ACME_IV_InsStage", ""]) in ["advance", "thread", "retract"]) exitWith {};
// pick up or put down the constricting band, on a single click, and click again to return it. a grab is a no-op if
// it is already applied.
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (uiNamespace getVariable ["ACME_IV_Held", "none"] == "band") exitWith {
    uiNamespace setVariable ["ACME_IV_Held", "none"];
    (_dlg displayCtrl 86505) ctrlShow false;
    playSound "ACME_IVCap";  // cap click. placing the band BACK in its slot
    [] call ACME_fnc_ivMinigameRefreshBandSlot;
};
if (uiNamespace getVariable ["ACME_IV_BandOn", false]) exitWith {};
// it requires an actual NAR BOA constricting band in the kit to pick one up.
private _medic = uiNamespace getVariable ["ACME_IV_Medic", objNull];
if (isNull _medic || {([_medic, uiNamespace getVariable ["ACME_IV_Patient", objNull], "ACME_NARBOA"] call ACME_fnc_treatmentSupplyCount) < 1}) exitWith {
    ["No NAR BOA constricting band available.", 2, ACE_player] call ace_common_fnc_displayTextStructured;
    [] call ACME_fnc_ivMinigameRefreshBandSlot;
};
uiNamespace setVariable ["ACME_IV_PullIdx", -1];  // any pull in progress is abandoned here.
uiNamespace setVariable ["ACME_IV_Held", "band"];
[] call ACME_fnc_ivMinigameRefreshBandSlot;
