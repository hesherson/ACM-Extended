/* Read accepted contents, never an optimistic count of presses. */
disableSerialization;
private _display = findDisplay 84000;
if (isNull _display) exitWith {};
private _ctrl = _display displayCtrl 84361;
if (isNull _ctrl) exitWith {};
private _ctx = missionNamespace getVariable ["ACME_infusion_pendingContext", []];
if (_ctx isEqualTo []) exitWith {};
private _rows = [];
private _vol = 0;
if ((_ctx select 0) == "prepared") then {
    private _id = _ctx param [20, ""];
    private _entries = ACE_player getVariable ["ACME_infusion_PreparedBags", []];
    private _i = _entries findIf {(_x select 0) == _id};
    if (_i >= 0) then {_rows = [_entries select _i] call ACME_fnc_preparedComponents; _vol = (_entries select _i) select 10;};
} else {
    private _patient = _ctx select 1;
    private _id = _ctx param [21, ""];
    {
        if ((_x param [23, ""]) == _id) then {
            _rows pushBack [_x select 11, _x select 13, _x param [27, 1]];
            _vol = _x select 10;
        };
    } forEach (_patient getVariable ["ACME_infusion_BagMedications", []]);
};
private _lines = [];
{
    _x params ["_med", "_dose", "_count"];
    _lines pushBack format ["<t color='#eeeeee'>%1: %2 added</t><br/><t color='#8fd18f'>%3 injections</t>", _med, [_med, _dose] call ACME_fnc_formatDose, _count];
} forEach _rows;
if (_lines isEqualTo []) then {_lines pushBack "No medication injected yet.";} else {_lines pushBack format ["Solution remaining: %1 mL", _vol toFixed 1];};
if ((missionNamespace getVariable ["ACME_infusion_pendingInject", ""]) != "") then {_lines pushBack "Confirming injection...";};
_ctrl ctrlSetStructuredText parseText (_lines joinString "<br/>");
private _group = _display displayCtrl 84362;
if (!isNull _group) then {
    private _r = ctrlPosition _ctrl; _r set [3, (ctrlTextHeight _ctrl + safeZoneH / 100) max ((ctrlPosition _group) select 3)];
    _ctrl ctrlSetPosition _r; _ctrl ctrlCommit 0;
};
