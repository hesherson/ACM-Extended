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

// B233: the same in-place size switch used by ordinary syringes updates the
// captured native geometry and controls. Do not close/recreate the Narc Box.
if !([10, _flushClass] call ACME_fnc_skApplySize) exitWith {};
[_flushClass] call ACME_fnc_skWasteBegin;
