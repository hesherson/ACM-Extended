/* Save the current face, suspend its input, and restore the destination face.
   A view change cannot remove a physical band or complete a catheter. */
disableSerialization;
if !([] call ACME_fnc_ivUiValid) exitWith {};
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _dlg) exitWith {};
private _siteList = uiNamespace getVariable ["ACME_IV_SiteList", []];
if (_siteList isEqualTo []) exitWith {};

private _views = [];
{ _x params ["_s", "_vTex"]; _views pushBackUnique _vTex; } forEach _siteList;
if (count _views < 2) exitWith {};

private _cur = uiNamespace getVariable ["ACME_IV_View", _views select 0];
private _idx = _views find _cur;
private _next = _views select ((_idx + 1) % (count _views));
// Save even without a band. A blind stick still owns a partial catheter.
[] call ACME_fnc_ivMinigameSaveState;
["leave"] call ACME_fnc_ivMinigamePrepView;
[] call ACME_fnc_ivMinigameResetView;
uiNamespace setVariable ["ACME_IV_View", _next];

(_dlg displayCtrl 86501) ctrlSetText _next;
(_dlg displayCtrl 86501) ctrlCommit 0;

private _snap = [];
// The flip uses the same rule as the launch view. Every site on the new face is a snap target.
// An occupied location is a target too. The band goes on a limb that already holds an IV.
private _occPatient  = uiNamespace getVariable ["ACME_IV_Patient", objNull];
private _occBodyPart = toLower (uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"]);
{
    _x params ["_s", "_vTex", "_bU", "_bV", "_vU", "_vV", "_lbl", "_bTex"];
    if (_vTex == _next) then { _snap pushBack [_s, _bU, _bV, _vU, _vV, _lbl, _bTex]; };
} forEach _siteList;
uiNamespace setVariable ["ACME_IV_SnapSites", _snap];

uiNamespace setVariable ["ACME_IV_BandOn", false];

// Seed the destination's first mapped site. Restored band and catheter state keep
// their own site identities; old face defaults cannot reach a new stick.
if !(_snap isEqualTo []) then {
    (_snap select 0) params ["_nsName", "_nsbU", "_nsbV", "_nsvU", "_nsvV", "_nsLbl", "_nsTex"];
    uiNamespace setVariable ["ACME_IV_Site", _nsName];
    uiNamespace setVariable ["ACME_IV_ProbeSite", _nsName];
    uiNamespace setVariable ["ACME_IV_BandUV", [_nsbU, _nsbV]];
    uiNamespace setVariable ["ACME_IV_VeinUV", [_nsvU, _nsvV]];
    uiNamespace setVariable ["ACME_IV_VeinSet",
        [_occPatient, _occBodyPart, _nsName, _nsvU, _nsvV] call ACME_fnc_ivVeinSet];
    uiNamespace setVariable ["ACME_IV_Label", _nsLbl];
    uiNamespace setVariable ["ACME_IV_BandTex", _nsTex];
    uiNamespace setVariable ["ACME_IV_SnapUV", [_nsbU, _nsbV]];
    (_dlg displayCtrl 86504) ctrlSetText _nsLbl;
};

// The insertion site was saved with its own face. The new face starts idle
// until RestoreState loads its own catheter. No hidden insertion may block clicks.
uiNamespace setVariable ["ACME_IV_Cleaned", false];
uiNamespace setVariable ["ACME_IV_HoldCum", 0];
// Wiping controls remain hidden with the old face until it is shown again.
uiNamespace setVariable ["ACME_IV_PrepPts", []];
uiNamespace setVariable ["ACME_IV_WipeSwipes", 0];
uiNamespace setVariable ["ACME_IV_WipeDir", 0];
uiNamespace setVariable ["ACME_IV_WipeLastX", -1e9];
uiNamespace setVariable ["ACME_IV_WipeTravel", 0];
uiNamespace setVariable ["ACME_IV_CleanAt", nil];
uiNamespace setVariable ["ACME_IV_HoldLast", -1e9];
(_dlg displayCtrl 86502) ctrlShow false;  // Hide this face's art only; SyncBand reads physical presence.
(_dlg displayCtrl 86505) ctrlShow false;
(_dlg displayCtrl 86506) ctrlShow false;
(_dlg displayCtrl 86507) ctrlShow false;
private _cath = uiNamespace getVariable ["ACME_IV_CathCtrl", controlNull];
if (!isNull _cath) then { _cath ctrlShow false; };
private _dot = uiNamespace getVariable ["ACME_IV_DotCtrl", controlNull];
if (!isNull _dot) then { _dot ctrlShow false; };
private _stain = uiNamespace getVariable ["ACME_IV_CleanCtrl", controlNull];
if (!isNull _stain) then { _stain ctrlShow false; };
[] call ACME_fnc_ivMinigameRenderMarks;
[] call ACME_fnc_ivMinigameRestoreState;
["enter"] call ACME_fnc_ivMinigamePrepView;
[true] call ACME_fnc_ivMinigameSyncBand;
[false] call ACME_fnc_ivMinigameSaveState;  // A restored view is not a new treatment write.
[] call ACME_fnc_ivMinigameRefreshBandSlot;
// Reapply local NV treatment after restoration without changing input geometry.
[_dlg, [], "ACME_IV_Shade"] call ACME_fnc_darknessShade;
[_dlg] call ACME_fnc_minigameVisionTick;
