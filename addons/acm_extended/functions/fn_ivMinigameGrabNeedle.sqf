// pick up or put down a needle of the given gauge, on a single click, and click again, or click another gauge, to
// switch. it recomputes the stick difficulty for the gauge, and grabbing plays the catheter uncap and peel sfx,
// ACME_IVUncap.
params [["_gauge", 16]];
["needle",_gauge,false] call ACME_fnc_ivTrayHover;  // collapse the fan immediately on pickup/return.
// Keep the active catheter in control until it is completed or this face is suspended.
if ((uiNamespace getVariable ["ACME_IV_InsStage", ""]) in ["advance", "thread", "retract"]) exitWith {};
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (uiNamespace getVariable ["ACME_IV_Held", "none"] == "needle") exitWith {
    uiNamespace setVariable ["ACME_IV_Held", "none"];
    (_dlg displayCtrl 86506) ctrlShow false;
    playSound "ACME_IVCap";  // cap click. placing the catheter BACK in its slot
    [] call ACME_fnc_ivMinigameRefreshBandSlot;
};
uiNamespace setVariable ["ACME_IV_PullIdx", -1];  // any pull in progress is abandoned here.
// the needle settles from wherever it is picked up, not from where the last one was left.
uiNamespace setVariable ["ACME_IV_NeedleTipPos", []];
uiNamespace setVariable ["ACME_IV_NeedleTipUV", []];

// only allow grabbing a gauge the medic is actually carrying. any size works, 14, 16, 18 or 20, and you simply need at
// least one of that size on hand. putting a needle down, handled above, is always allowed.
private _grabMedic = uiNamespace getVariable ["ACME_IV_Medic", objNull];
if (isNull _grabMedic || {([_grabMedic, format ["ACM_IV_%1g", _gauge]] call ACME_fnc_itemCount) < 1}) exitWith {
    [format ["No %1g catheter on hand.", _gauge], 2, ACE_player] call ace_common_fnc_displayTextStructured;
};

uiNamespace setVariable ["ACME_IV_Gauge", _gauge];
uiNamespace setVariable ["ACME_IV_Held", "needle"];

private _patient  = uiNamespace getVariable ["ACME_IV_Patient", objNull];
private _bodyPart = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
// the site goes in too, so the difficulty is for the vein actually being stuck rather than an average of the limb.
private _siteN = uiNamespace getVariable ["ACME_IV_ProbeSite", ""];
if !(_siteN in ["upper","middle","lower","left","right"]) then {
    _siteN = uiNamespace getVariable ["ACME_IV_Site", 1];
};
private _diff = [_patient, _bodyPart, _gauge, _siteN] call ACME_fnc_ivSiteDifficulty;
_diff params ["_patency", "_feelRadius", "_hitRadius", "_maxHot"];
uiNamespace setVariable ["ACME_IV_Patency", _patency];
uiNamespace setVariable ["ACME_IV_FeelRadius", _feelRadius];
uiNamespace setVariable ["ACME_IV_HitRadius", _hitRadius];
uiNamespace setVariable ["ACME_IV_MaxHot", _maxHot];

// the grab sound: the catheter un-cap and peel.
uiNamespace setVariable ["ACME_IV_NeedleFrame", ""];  // start straight; tick tilts it by off-center
playSound "ACME_NARSPEAR_Open";
[] call ACME_fnc_ivMinigameRefreshBandSlot;
