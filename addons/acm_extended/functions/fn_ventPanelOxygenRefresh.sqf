/* Paint the existing O2 page from the attached source. This is read-only:
   verifying, drawing reserve and changing FiO2 stay on their respective owners. */
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg || {(uiNamespace getVariable ["ACME_vent_screen", ""]) != "o2"}) exitWith {};
private _target = uiNamespace getVariable ["ACME_vent_target", objNull];
([_target] call ACME_fnc_ventOxygenState) params ["_attached", "_usable", "_litres", "_item", "_status"];
if (!_usable) then { uiNamespace setVariable ["ACME_vent_editingFio2", false]; };
private _editing = uiNamespace getVariable ["ACME_vent_editingFio2", false];
private _sel = uiNamespace getVariable ["ACME_vent_selIdx", 0];
private _value = if (_editing && {_usable}) then {
    (uiNamespace getVariable ["ACME_vent_fio2", 21]) max 21 min 95
} else {
    if (_usable) then { (_target getVariable ["ACME_vent_fio2", 21]) max 21 min 95 } else {21}
};
private _val = uiNamespace getVariable ["ACME_vent_o2ValCtrl", controlNull];
if (!isNull _val) then {
    _val ctrlSetText format ["%1%2", round _value, "%"];
    _val ctrlEnable _usable;
    _val ctrlSetTextColor ([if (_usable) then {[0.92,0.92,0.92,1]} else {[0.55,0.58,0.62,1]}] call ACME_fnc_ventColor);
    _val ctrlSetBackgroundColor ([if (!_usable) then {[0.06,0.08,0.10,1]} else {
        if (_editing || {_sel == 0}) then {[0,0,0.996,1]} else {[0,0,0.62,1]}
    }] call ACME_fnc_ventColor);
};
private _action = uiNamespace getVariable ["ACME_vent_o2SourceCtrl", controlNull];
if (!isNull _action) then {
    _action ctrlSetText (if (_attached) then {"DISCONNECT OXYGEN"} else {"ATTACH OXYGEN"});
    _action ctrlSetTextColor ([if (_sel == 1 && {!_editing}) then {[0,0,0.996,1]} else {[0.92,0.92,0.92,1]}] call ACME_fnc_ventColor);
    _action ctrlSetBackgroundColor ([if (_sel == 1 && {!_editing}) then {[0,0.988,0.992,1]} else {[0.06,0.08,0.10,1]}] call ACME_fnc_ventColor);
};
private _supply = uiNamespace getVariable ["ACME_vent_o2SupplyCtrl", controlNull];
if (!isNull _supply) then {
    private _text = if (!_attached) then {"NO OXYGEN SUPPLY"} else {
        if (!_usable) then {_status} else {
            if (_litres < 0) then {"OXYGEN CONNECTED"} else {format ["OXYGEN: %1 L REMAINING", round (_litres max 0)]}
        }
    };
    if (ctrlText _supply != _text) then { _supply ctrlSetText _text; };
    _supply ctrlSetTextColor ([[0.72,0.76,0.80,1]] call ACME_fnc_ventColor);
};
(_dlg displayCtrl 87756) ctrlSetBackgroundColor ([if (_sel == 2 && {!_editing}) then {[0,0.988,0.992,1]} else {[0,0,0,0]}] call ACME_fnc_ventColor);
