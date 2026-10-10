// a direct click on a value field, the BPM or the vt. the first click selects it, and clicking the already-selected
// field toggles edit mode, where the mouse wheel changes the value. it mirrors the knob press.
params ["_field"];
// The second field remains a measured volume display in Simple mode.
if (((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])}) && {_field != "bpm"}) exitWith {};
playSound "ACME_VentClick";
private _sel  = uiNamespace getVariable ["ACME_vent_sel", "none"];
private _edit = uiNamespace getVariable ["ACME_vent_editing", false];
if (_sel == _field) then {
    uiNamespace setVariable ["ACME_vent_editing", !_edit];
} else {
    uiNamespace setVariable ["ACME_vent_sel", _field];
    uiNamespace setVariable ["ACME_vent_editing", true];  // direct-click jumps straight into edit
};
[] call ACME_fnc_ventPanelLiveRefresh;
