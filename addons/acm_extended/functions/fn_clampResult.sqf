// Rejections may retire only the exact edit on the originating display.
// Acceptance is confirmed by the receipt in replicated medication state.
params ["_patient","_medic","_stamp","_accepted"];
if (_accepted || {_medic isNotEqualTo ACE_player}) exitWith {};
private _edit = uiNamespace getVariable ["ACME_RollerClamp_Edit",[]];
private _display = uiNamespace getVariable ["ACME_RollerClamp_DLG",displayNull];
if (count _edit != 10 || {isNull _display} || {(_edit select 0) isNotEqualTo _display}
    || {(_edit select 1) isNotEqualTo _medic} || {(_edit select 2) isNotEqualTo _patient}
    || {(_edit select 5) isNotEqualTo _stamp}) exitWith {};
uiNamespace setVariable ["ACME_RollerClamp_Edit",[]];
call ACME_fnc_updateClampDialog;
["Clamp adjustment was not accepted. Check the selected infusion.",2,ACE_player,13] call ace_common_fnc_displayTextStructured;
