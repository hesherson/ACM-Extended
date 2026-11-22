// begin an insertion. the needle is now in the skin and the medic must work it in by hand.
// call it as [_stickU, _stickV, _hit, _stickSite] call ACME_fnc_ivMinigameInsertStart.
// _stickSite is the site of the puncture. fn_ivSiteAtPoint finds that site at the click.
// This function stores the site at the moment of the stick. The site is correct only at that moment.
// The registration runs a short time later.
// The registration read ACME_IV_Site before. By then that value is the band site or a default.
// _stickU and _stickV are the body fractions of the puncture. _hit is true if the bevel found the vein.
// the outcome is decided here, at the moment of the stick, but the medic cannot see it yet. the flashback
// frames only play on a hit, so a miss simply never flashes.
params ["_stickU", "_stickV", ["_hit", false], ["_stickSite", ""]];
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _dlg) exitWith {};
private _rect = uiNamespace getVariable ["ACME_IV_BodyRect", []];
if (_rect isEqualTo []) exitWith {};
_rect params ["_bx", "_by", "_bw", "_bh"];

private _frame = uiNamespace getVariable ["ACME_IV_NeedleFrame", ""];
private _gauge = uiNamespace getVariable ["ACME_IV_Gauge", 16];
private _usesStock = !(_dlg getVariable ["ACME_IV_FieldInserting", false]);
if (_usesStock && {!(_stickSite in ["upper", "middle", "lower"])} && {!(uiNamespace getVariable ["ACME_IV_EJMode", false])}) exitWith {};
private _receipt = [];
if (_usesStock) then {
    private _medic = uiNamespace getVariable ["ACME_IV_Medic", objNull];
    private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
    _receipt = [_medic, _patient, [format ["ACME_IV_%1g", _gauge]]] call ACME_fnc_treatmentSupplyTake;
};
if (_usesStock && {_receipt isEqualTo []}) exitWith {
    (_dlg displayCtrl 86503) ctrlSetText "No catheter available.";
    [] call ACME_fnc_ivMinigameRefreshBandSlot;
};
// The puncture uses the catheter even if it is missed or left partly inserted.
if (_usesStock) then {[_receipt, false] call ACME_fnc_treatmentSupplyRefund;};
uiNamespace setVariable ["ACME_IV_InsFunded", _usesStock];
private _angle = uiNamespace getVariable ["ACME_IV_NeedleAngle", 0];
uiNamespace setVariable ["ACME_IV_InsAngle", _angle];

private _cath = uiNamespace getVariable ["ACME_IV_CathCtrl", controlNull];
if (isNull _cath) then {
    _cath = _dlg ctrlCreate ["ACME_IV_Catheter", -1];
    uiNamespace setVariable ["ACME_IV_CathCtrl", _cath];
    [_cath] call ACME_fnc_ivMinigameHookCtrl;
};
_cath ctrlSetText ([_gauge, _frame, 1] call ACME_fnc_ivCathTex);
_cath ctrlSetTextColor [1,1,1,1];
_cath ctrlSetFade 0;
private _pose = [_cath, _bx + _bw * _stickU, _by + _bh * _stickV, _frame, _angle] call ACME_fnc_ivCathPose;
uiNamespace setVariable ["ACME_IV_StickTopLeft", _pose select [0,2]];
_cath ctrlShow true;

// the held cursor hands the catheter over to the locked sprite.
private _heldC = uiNamespace getVariable ["ACME_IV_HeldCursorCtrl", controlNull];
if (!isNull _heldC) then { _heldC ctrlShow false; };

uiNamespace setVariable ["ACME_IV_InsStage", "advance"];
uiNamespace setVariable ["ACME_IV_InsFrame", 1];
uiNamespace setVariable ["ACME_IV_InsHit", _hit];
uiNamespace setVariable ["ACME_IV_InsProg", 0];
uiNamespace setVariable ["ACME_IV_InsSuffix", _frame];
uiNamespace setVariable ["ACME_IV_InsGauge", _gauge];
uiNamespace setVariable ["ACME_IV_InsU", _stickU];
uiNamespace setVariable ["ACME_IV_InsV", _stickV];
// Store the site of this puncture with the coordinates of the puncture.
// The EJ stores "". fn_ivMinigameStickSuccess locks the anatomical side of the EJ instead.
// Capture the anatomical EJ side explicitly; later cursor motion must not change registration.
uiNamespace setVariable ["ACME_IV_InsSite", _stickSite];
// Freeze the anatomical side at puncture; cursor motion cannot move the catheter.
uiNamespace setVariable ["ACME_IV_InsEJSide", if (uiNamespace getVariable ["ACME_IV_EJMode", false]) then {
    uiNamespace getVariable ["ACME_IV_EJAnatomicalSide", ""]
} else {""}];
// pin the mouse where the stick happened, which is the needle tip. the drag resets it here every frame, so the
// medic can push as far as the catheter goes without running the cursor off the screen.
uiNamespace setVariable ["ACME_IV_InsPin", getMousePosition];
uiNamespace setVariable ["ACME_IV_Stage", "cath"];
(_dlg displayCtrl 86503) ctrlSetText "Push the catheter in.";
