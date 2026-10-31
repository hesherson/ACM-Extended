/* Clear transient input only after the outgoing view has been saved.
   This never removes an IV, consumes an item or changes the physical band. */
disableSerialization;
private _display = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _display) exitWith {};
[] call ACME_fnc_ivFinishAbort;
private _extra=uiNamespace getVariable ["ACME_IV_PullExtra",controlNull];
if (!isNull _extra) then {ctrlDelete _extra;};
uiNamespace setVariable ["ACME_IV_PullExtra",controlNull];
_display setVariable ["ACME_IV_ViewGeneration", (_display getVariable ["ACME_IV_ViewGeneration", 0]) + 1];
private _retract = _display getVariable ["ACME_IV_RetractPFH", -1];
if (_retract >= 0) then {[_retract] call CBA_fnc_removePerFrameHandler;};
_display setVariable ["ACME_IV_RetractPFH", -1];
{
    _x params ["_name", "_value"];
    uiNamespace setVariable [_name, _value];
} forEach [
    ["ACME_IV_Held", "none"], ["ACME_IV_Dragging", false],
    ["ACME_IV_InsStage", ""], ["ACME_IV_InsFrame", 0], ["ACME_IV_InsSite", ""],
    ["ACME_IV_InsSuffix", ""], ["ACME_IV_InsGauge", 16], ["ACME_IV_InsHit", false],
    ["ACME_IV_InsProg", 0], ["ACME_IV_InsU", 0.5], ["ACME_IV_InsV", 0.5],
    ["ACME_IV_InsAngle", 0], ["ACME_IV_NeedleAngle", 0], ["ACME_IV_PullAngle", 0],
    ["ACME_IV_InsPin", []], ["ACME_IV_InsEJSide", ""],
    ["ACME_IV_StickTopLeft", []], ["ACME_IV_StickAcc", 0],
    ["ACME_IV_StickU", 0.5], ["ACME_IV_StickV", 0.5], ["ACME_IV_RegOK", false],
    ["ACME_IV_NeedleFrame", ""], ["ACME_IV_LastNeedleState", []],
    ["ACME_IV_NeedleTipPos", []], ["ACME_IV_NeedleTipUV", []],
    ["ACME_IV_PullLayers",[]], ["ACME_IV_PullLayerBases",[]], ["ACME_IV_PullUID",""], ["ACME_IV_PullKind","catheter"],
    ["ACME_IV_PullIdx", -1], ["ACME_IV_PullProg", 0], ["ACME_IV_PullPin", []],
    ["ACME_IV_PullBroke", false], ["ACME_IV_PullCtrl", controlNull],
    ["ACME_IV_PullBase", []], ["ACME_IV_PullSuffix", ""],
    ["ACME_IV_SnapActive", []], ["ACME_IV_ProbeSite", ""], ["ACME_IV_Stage", "ready"]
];
// Cancel any outgoing crossfade before the catheter control is reused.
{
    private _c = uiNamespace getVariable [_x, controlNull];
    if (!isNull _c) then {
        _c ctrlShow false;
        _c ctrlSetText "";
        _c ctrlSetTextColor [1,1,1,1];
        _c ctrlSetFade 0;
        _c ctrlCommit 0;
        {_c setVariable [_x, nil];} forEach ["ACME_NV_BaseTexture", "ACME_NV_Variant", "ACME_NV_BaseColor", "ACME_NV_LastColor"];
    };
} forEach ["ACME_IV_CathCtrl", "ACME_IV_CathGhost", "ACME_IV_HeldCursorCtrl"];
{(_display displayCtrl _x) ctrlShow false;} forEach [86505,86506,86507];
(uiNamespace getVariable ["ACME_IV_DotCtrl", controlNull]) ctrlShow false;
(_display displayCtrl 86503) ctrlSetText "";
