/* Presentation only: a quiet shared bracket, leaving both native bag rows selectable. */
params ["_display"];
private _list = _display displayCtrl 86004;
if (isNull _list) exitWith {};
private _controls = [];
{
    private _c = _display displayCtrl _x;
    if (isNull _c) then {
        _c = _display ctrlCreate ["RscText", _x];
        _c ctrlEnable false;
        _c ctrlSetBackgroundColor [0.63,0.68,0.75,0.7];
    };
    _controls pushBack _c;
} forEach [86184,86185,86186];
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _values = [];
for "_row" from 0 to ((lbSize _list) - 1) do {_values pushBack (_list lbValue _row);};
private _relation = [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []],
    _values,_part,_iv,_site,if (isNull _patient) then {[]} else {_patient getVariable ["ACME_YLines", []]}]
    call ACME_fnc_transfusionYRows;
_relation params ["_rows", "_key"];
[(_display displayCtrl 86160),"text",if (_key == "") then {"Fluids"} else {"Fluids | Y line"}] call ACME_fnc_transfusionUiSet;
(ctrlPosition _list) params ["_x", "_y", "_w", "_h"];
private _rowH = safeZoneH / 20;
// Native listboxes have no reliable exposed row-scroll offset. Never draw a
// fixed bracket beside a scrolled row: overflowing lists retain their native Y tags.
private _fits = ((lbSize _list) * _rowH) <= _h && {ctrlShown _list};
private _show = _fits && {count _rows > 0};
{[_x,"show",_show] call ACME_fnc_transfusionUiSet;} forEach _controls;
if (!_show) exitWith {};
private _uiW = safeZoneW min (safeZoneH * 1.7777778);
private _railX = _x - _uiW * 0.006;
private _top = _y + ((_rows select 0) + 0.5) * _rowH;
private _bottom = _y + ((_rows select ((count _rows) - 1)) + 0.5) * _rowH;
if (count _rows == 1) then {_top = _top - _rowH * 0.18;};
[(_controls select 0),"position",[_railX,_top,pixelW max 0.0005,(_bottom - _top) max pixelH]] call ACME_fnc_transfusionUiSet;
{
    private _hook = _controls select (_forEachIndex + 1);
    [_hook,"position",[_railX,_y + (_x + 0.5) * _rowH,_uiW * 0.006,pixelH max 0.0005]] call ACME_fnc_transfusionUiSet;
} forEach _rows;
if (count _rows == 1) then {[(_controls select 2),"show",false] call ACME_fnc_transfusionUiSet;};
