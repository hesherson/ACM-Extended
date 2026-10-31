/* One dose selector, no secondary dialog: 1 mL, 2 mL, or ALL remaining volume. */
disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
params [["_cycle", false]];
private _d = findDisplay 84000;
if (isNull _d) exitWith {};
private _button = _d displayCtrl 84320;
if (isNull _button) then {
    _button = _d ctrlCreate ["ACME_SK_StyledButton", 84320];
    _button ctrlAddEventHandler ["ButtonClick", {[true] call ACME_fnc_skEpinephrineDose;}];
};
private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _index = [_store, false] call ACME_fnc_skSelectedIndex;
private _entry = if (_index >= 0) then {_store param [_index, []]} else {[]};
private _show = _index >= 0 && {(_entry param [6, ""]) == "epiMixB12"}
    && {(uiNamespace getVariable ["ACME_SK_View", "syringe"]) == "body"}
    && {(uiNamespace getVariable ["ACME_SK_SelFlush", ""]) == ""};
_button ctrlShow _show;
_button ctrlEnable _show;
if (!_show) exitWith {};
private _choice = uiNamespace getVariable ["ACME_SK_EpiDoseChoice", 0];
if (_cycle) then {_choice = (_choice + 1) mod 3; uiNamespace setVariable ["ACME_SK_EpiDoseChoice", _choice];};
private _total = (_entry param [2, 0]) + (_entry param [4, 0]);
private _ml = ([1, 2, _total] select _choice) min _total;
_button ctrlSetText format ["%1%2 mL = %3 mcg", ["Push ", "ALL: "] select (_choice == 2), _ml toFixed 1, (_ml * 10) toFixed 0];
_button ctrlSetTooltip "Click to cycle 1 mL (10 mcg), 2 mL (20 mcg), or ALL. Then click an IV/IO icon. A full 10 mL syringe contains 100 mcg, not a routine 10 mcg push.";
// The dose button starts after the complete IV/IO + IM selector. Anchoring it
// after IV/IO covered the IM button whenever a diluted epinephrine syringe was selected.
(ctrlPosition (_d displayCtrl 84154)) params ["_x", "_y", "_w", "_h"];
_button ctrlSetPosition [_x + _w + _uiW / 200, _y, _w * 2.4, _h];
_button ctrlCommit 0;
