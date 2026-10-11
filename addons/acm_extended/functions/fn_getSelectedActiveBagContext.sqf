params [["_pane", "auto"]];
// Some menu and PFH callers carry their own _this array. Only a string can select a pane.
if !(_pane isEqualType "") then {_pane = "auto";};
private _display = findDisplay 86000;
if (isNull _display) exitWith {[]};

private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (isNull _patient) exitWith {[]};

private _bodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _accessSite = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _selectedIV = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _selection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];

if (_pane == "auto") then {_pane = _display getVariable ["ACME_txActivePane", "transfusion"];};
if !(_pane in ["transfusion", "infusion"]) exitWith {[]};
private _list = _display displayCtrl ([86004, 86129] select (_pane == "infusion"));
private _menu = _display getVariable ["ACME_txActionMenu", ""];
private _ownsPopover = (_pane == "transfusion" && {_menu == "bag"}) || {_pane == "infusion" && {_menu == "infusion"}};
if (isNull _list || {!ctrlShown _list && {!_ownsPopover}}) exitWith {[]};
private _row = lbCurSel _list;
if (_row < 0) exitWith {[]};
private _selectionIndex = _list lbValue _row;

if (_selectionIndex < 0 || {_selectionIndex >= count _selection}) exitWith {[]};

private _bag = _selection select _selectionIndex;
private _trueIndex = _bag param [8, -1];
private _physicalUID = _bag param [9, ""];
private _latest = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_bodyPart, []];
if (_physicalUID != "") then {
    _trueIndex = _latest findIf {(_x param [8, ""]) == _physicalUID};
} else {
    // Legacy selection tuples have no captured UID. Only the immutable native
    // fields can authorize their original index; changing volume is expected.
    if (_trueIndex >= 0 && {_trueIndex < count _latest}) then {
        private _candidate = _latest select _trueIndex;
        if (([0,2,3,4,5,6,7] findIf {(_candidate param [_x, -1]) isNotEqualTo (_bag param [_x, -1])}) >= 0) then {_trueIndex = -1;};
    };
};
if (_trueIndex < 0 || {_trueIndex >= count _latest}) exitWith {[]};
_bag = _latest select _trueIndex;
_bag params ["_type", "_remainingVolume", "_accessType", "_bagAccessSite", "_bagIV", ["_bloodType", -1], ["_volume", 0], ["_freshBloodID", -1]];
if (_bagAccessSite != _accessSite || {_bagIV isNotEqualTo _selectedIV}) exitWith {[]};

[_patient, _bodyPart, _trueIndex, _type, _accessType, _bagAccessSite, _bagIV, _bloodType, _volume, _freshBloodID, _remainingVolume, _selectedIV, _accessSite]
