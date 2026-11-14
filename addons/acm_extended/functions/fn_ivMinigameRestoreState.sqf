// restore this limb to how it was left. call it as [] call ACME_fnc_ivMinigameRestoreState.
// it runs late in fn_ivminigameinit, after the layout and the marks, so it can position a sprite.
// it puts back a band, a prepped site and a catheter that was left part way in.
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _dlg) exitWith {};
private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
if (isNull _patient || {!( [] call ACME_fnc_ivUiValid)}) exitWith {};
private _rect = uiNamespace getVariable ["ACME_IV_BodyRect", []];
if (_rect isEqualTo []) exitWith {};
_rect params ["_bx", "_by", "_bw", "_bh"];

private _bp = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
private _view = uiNamespace getVariable ["ACME_IV_View", ""];
private _key = format ["%1|%2", _bp, _view];

private _entry = [];
{
    if ((_x select 0) == _key) exitWith { _entry = _x; };
} forEach (_patient getVariable ["ACME_IV_SiteState", []]);
private _cache = _dlg getVariable ["ACME_IV_ViewCache", createHashMap];
if (_key in _cache) then {_entry = +(_cache get _key);};
if (_entry isEqualTo []) exitWith {};
if !(_entry isEqualType [] && {count _entry == 4}) exitWith {};
_entry = +_entry;

_entry params ["_k", "_band", "_ins", "_clean"];

// the band. it goes back on the limb at the site it was tied at, with its own art.
_band params ["_bandOn", "_site", "_bandUV", "_veinUV", "_label", "_bandTex"];
if (_bandOn) then {
    uiNamespace setVariable ["ACME_IV_Site", _site];
    uiNamespace setVariable ["ACME_IV_BandUV", _bandUV];
    uiNamespace setVariable ["ACME_IV_VeinUV", _veinUV];
    uiNamespace setVariable ["ACME_IV_Label", _label];
    (_dlg displayCtrl 86504) ctrlSetText _label;
    uiNamespace setVariable ["ACME_IV_BandOn", true];
    uiNamespace setVariable ["ACME_IV_BandTex", _bandTex];
    if (_bandTex != "") then {
        private _bC = _dlg displayCtrl 86502;
        _bC ctrlSetText _bandTex;
        _bC ctrlSetPosition [_bx, _by, _bw, _bh];
        _bC ctrlCommit 0;
        _bC ctrlShow true;
    };
    // re-seed the difficulty from the site, so palpation and the hit radius match what they were.
    private _diff = [_patient, _bp, (uiNamespace getVariable ["ACME_IV_Gauge", 16]), _site] call ACME_fnc_ivSiteDifficulty;
    _diff params ["_pat", "_feel", "_hit", "_hot"];
    uiNamespace setVariable ["ACME_IV_Patency", _pat];
    uiNamespace setVariable ["ACME_IV_FeelRadius", _feel];
    uiNamespace setVariable ["ACME_IV_HitRadius", _hit];
    uiNamespace setVariable ["ACME_IV_MaxHot", _hot];
    uiNamespace setVariable ["ACME_IV_Stage", "ready"];
    // Physical presence is read by ivMinigameSyncBand; restoring a view never reapplies it.
};

// the antiseptic prep.
_clean params ["_cleaned", "_holdCum"];
uiNamespace setVariable ["ACME_IV_Cleaned", _cleaned];
uiNamespace setVariable ["ACME_IV_HoldCum", _holdCum];
// A fresh mouse stroke must not bridge the two faces of the limb.
uiNamespace setVariable ["ACME_IV_PrepLast", []];

// the catheter that was left in the arm. put the sprite back on the puncture at the frame it was left at, and
// hand control straight back to the medic.
_ins params ["_stage", "_frame", "_suffix", "_gauge", "_insU", "_insV", "_hit2", "_prog", ["_insSite", ""], ["_accuracy", 0], ["_ejSide", ""], ["_angle", 0], ["_funded", false, [false]]];
uiNamespace setVariable ["ACME_IV_InsFunded", _funded];
// Older snapshots can contain a withdrawn needle state. Resume from fully threaded.
if (_stage == "retract") then {_stage = "thread"; _frame = 11;};
if (_stage in ["advance", "thread"]) then {
    private _cath = uiNamespace getVariable ["ACME_IV_CathCtrl", controlNull];
    if (isNull _cath) then {
        _cath = _dlg ctrlCreate ["ACME_IV_Catheter", -1];
        uiNamespace setVariable ["ACME_IV_CathCtrl", _cath];
        [_cath] call ACME_fnc_ivMinigameHookCtrl;
    };
    _cath ctrlSetText ([_gauge, _suffix, _frame] call ACME_fnc_ivCathTex);
    // A previous crossfade or NV pass must not leave the restored sprite transparent.
    _cath ctrlSetTextColor [1,1,1,1];
    _cath ctrlSetFade 0;
    {_cath setVariable [_x, nil];} forEach ["ACME_NV_BaseTexture", "ACME_NV_Variant", "ACME_NV_BaseColor", "ACME_NV_LastColor"];
    private _pose = [_cath, _bx + _bw * _insU, _by + _bh * _insV, _suffix, _angle] call ACME_fnc_ivCathPose;
    uiNamespace setVariable ["ACME_IV_StickTopLeft", _pose select [0,2]];
    uiNamespace setVariable ["ACME_IV_InsAngle", _angle];
    uiNamespace setVariable ["ACME_IV_NeedleAngle", _angle];
    _cath ctrlShow true;

    uiNamespace setVariable ["ACME_IV_InsStage", _stage];
    uiNamespace setVariable ["ACME_IV_InsFrame", _frame];
    uiNamespace setVariable ["ACME_IV_InsSuffix", _suffix];
    uiNamespace setVariable ["ACME_IV_InsGauge", _gauge];
    uiNamespace setVariable ["ACME_IV_Gauge", _gauge];
    uiNamespace setVariable ["ACME_IV_StickAcc", _accuracy];
    uiNamespace setVariable ["ACME_IV_InsEJSide", _ejSide];
    uiNamespace setVariable ["ACME_IV_InsU", _insU];
    uiNamespace setVariable ["ACME_IV_InsV", _insV];
    uiNamespace setVariable ["ACME_IV_InsHit", _hit2];
    uiNamespace setVariable ["ACME_IV_InsProg", _prog];
    // Restore the site of the puncture.
    // A state from an older build has no element 8.
    // Calculate the site again from the puncture coordinates.
    // These are the same two values that fn_ivSiteAtPoint used at the stick.
    // The EJ stores "". The EJ keeps its own locked side.
    if (_insSite isEqualTo "" && {!(uiNamespace getVariable ["ACME_IV_EJMode", false])}) then {
        _insSite = [_insU, _insV] call ACME_fnc_ivSiteAtPoint;
    };
    uiNamespace setVariable ["ACME_IV_InsSite", _insSite];
    uiNamespace setVariable ["ACME_IV_InsPin", []];
    uiNamespace setVariable ["ACME_IV_NeedleFrame", _suffix];
    uiNamespace setVariable ["ACME_IV_Stage", "cath"];
    uiNamespace setVariable ["ACME_IV_Held", "none"];
    uiNamespace setVariable ["ACME_IV_Dragging", false];
    (_dlg displayCtrl 86503) ctrlSetText (if (_stage == "thread") then {
        if (_frame >= 11) then {"Catheter is hubbed. Right click to separate the needle from it."} else {"Catheter is still in. Scroll to thread it."}
    } else {
        "Catheter is still in. Hold and push to seat it."
    });
};
