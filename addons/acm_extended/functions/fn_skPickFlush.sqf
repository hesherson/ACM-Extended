// the flushes list of the narc box. selecting the 10 ml saline flush enters waste mode on the draw dialog: the
// syringe is treated as already full of 10 ml of normal saline, with the plunger at the bottom, the drug menu is
// grayed, and the draw button becomes "Waste".
// you drag the plunger up to waste fluid, so 10 down to 7 ml wastes 3 ml. that floor then locks, the drug menu
// ungrays, the button becomes "Draw", and you can pull up to the wasted volume of a drug on top of the remaining
// saline. drawing saves the mixed syringe to the drawn medications and resets.
// _this, from LBSelChanged, is [_ctrl, _index].
disableSerialization;
params ["_ctrl", "_index"];
private _display = ctrlParent _ctrl;
if (isNull _display || {!(_display isEqualTo findDisplay 84000)}) exitWith {};
if !((_display getVariable ["ACME_SK_Return", []]) isEqualTo []) exitWith {};
if (_index < 0) exitWith {};

private _flushClass = _ctrl lbData _index;
if (_flushClass isEqualTo "") then { _flushClass = "ACM_SalineFlush_10"; };

if (([ACE_player, uiNamespace getVariable ["ACME_SK_Patient",objNull], _flushClass] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
    ["No 10 mL saline flush in inventory.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    _ctrl lbSetCurSel -1;
};

private _saveFailed = false;
if ((uiNamespace getVariable ["ACME_SK_WasteStage", ""]) == "compound" && {!((uiNamespace getVariable ["ACME_SK_CompoundComponents", []]) isEqualTo [])}) then {_saveFailed = !(call ACME_fnc_skCompoundCommit);};
if (_saveFailed) exitWith {};
// ACM captures both sprite geometry and _size in its continuous-action closure.
// Reopen at 10 mL so a previous 1/3/5 mL selection cannot control a flush.
private _patient = uiNamespace getVariable ["ACME_SK_Patient", objNull];
private _bodyPart = uiNamespace getVariable ["ACME_SK_BodyPart", ""];
[] call ACME_fnc_skWasteEnd;
uiNamespace setVariable ["ACME_SK_RestoreMouse", getMousePosition];
_display closeDisplay 0;
[{
    params ["_size", "_patient", "_part", "_flush"];
    if (dialog) exitWith {uiNamespace setVariable ["ACME_SK_RestoreMouse", []];};
    [_size, _patient, _part, _flush] call ACME_fnc_skOpenDraw;
}, [10, _patient, _bodyPart, _flushClass], 0.05] call CBA_fnc_waitAndExecute;
