/* An empty-line card represents installed apparatus, never a zero-volume fluid bag. */
private _display = findDisplay 86000;
if (isNull _display) exitWith {[]};
private _list = _display displayCtrl 86004;
if (isNull _list) exitWith {[]};
private _row = lbCurSel _list;
if (_row < 0) exitWith {[]};
private _value = _list lbValue _row;
private _selection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];
if (_value < 0 || {_value >= count _selection}) exitWith {[]};
private _selected = _selection select _value;
if ((_selected param [0, ""]) != "ACME_Line") exitWith {[]};
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _uid = _selected param [9, ""];
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
if ((_selected param [3, -1]) != _site || {(_selected param [4, false]) isNotEqualTo _iv}
    || {(_selected param [10, -1]) != _epoch}) exitWith {[]};
if (([_patient, _part, _iv, _site, _uid] call ACME_fnc_ivLineSlot) isEqualTo []) exitWith {[]};
[_patient, _part, _iv, _site, _uid, _epoch]
