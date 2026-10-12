/* B275: selectable native rows keep their identity; quiet solid Y and dashed purple PiB rails show topology. */
params ["_display"];
private _list = _display displayCtrl 86004;
if (isNull _list) exitWith {};
private _ensure = {
    params ["_idc","_color"];
    private _c = _display displayCtrl _idc;
    if (isNull _c) then {_c = _display ctrlCreate ["RscText",_idc];_c ctrlEnable false;_c ctrlSetBackgroundColor _color;};
    _c
};
private _controls = [86184,86185,86186] apply {[_x,[0.63,0.68,0.75,0.7]] call _ensure};
private _pibControls = [86220,86221,86222,86223,86224,86225,86226,86227] apply {[_x,[0.79,0.73,0.89,0.85]] call _ensure};
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _selection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[]];
private _values = [];
for "_row" from 0 to ((lbSize _list) - 1) do {_values pushBack (_list lbValue _row);};
private _relation = [_selection,_values,_part,_iv,_site,if (isNull _patient) then {[]} else {_patient getVariable ["ACME_YLines", []]}] call ACME_fnc_transfusionYRows;
_relation params ["_rows", "_key"];
private _piggyback = [_patient,_part,_iv,_site] call ACME_fnc_piggybackLine;
[(_display displayCtrl 86160),"text",if (_key != "") then {"Fluids | Y line"} else {if (_piggyback isNotEqualTo []) then {"Fluids | Piggyback"} else {"Fluids"}}] call ACME_fnc_transfusionUiSet;
(ctrlPosition _list) params ["_listX", "_listY", "_listW", "_listH"];
private _rowH = safeZoneH / 20;
// Native listboxes do not expose a stable row-scroll offset. Overflow keeps textual [Y]/[PiB] roles.
private _fits = ((lbSize _list) * _rowH) <= _listH && {ctrlShown _list};
private _cardsReady = _display getVariable ["ACME_txCardsReady",false];
private _cardEndpoints = _display getVariable ["ACME_txCardEndpoints",createHashMap];
private _cardPoints = [];
if (_cardsReady) then {
    {
        private _uid = (_selection param [_list lbValue _x,[]]) param [9,""];
        private _point = _cardEndpoints getOrDefault [_uid,[]];
        if (_point isNotEqualTo []) then {_cardPoints pushBack _point;};
    } forEach _rows;
};
private _show = if (_cardsReady) then {count _cardPoints > 0 && {count _cardPoints == count _rows}} else {_fits && {count _rows > 0}};
{[_x,"show",_show] call ACME_fnc_transfusionUiSet;} forEach _controls;
private _uiW = safeZoneW min (safeZoneH * 1.7777778);
if (_show) then {
    private _railX = _listX - _uiW * 0.006;
    private _top = if (_cardsReady) then {(_cardPoints select 0) select 1} else {_listY + ((_rows select 0) + 0.5) * _rowH};
    private _bottom = if (_cardsReady) then {(_cardPoints select ((count _cardPoints) - 1)) select 1} else {_listY + ((_rows select ((count _rows) - 1)) + 0.5) * _rowH};
    if (count _rows == 1) then {_top = _top - _rowH * 0.18;};
    [(_controls select 0),"position",[_railX,_top,pixelW max 0.0005,(_bottom - _top) max pixelH]] call ACME_fnc_transfusionUiSet;
    {
        [(_controls select (_forEachIndex + 1)),"position",[_railX,if (_cardsReady) then {(_cardPoints select _forEachIndex) select 1} else {_listY + (_x + 0.5) * _rowH},_uiW * 0.006,pixelH max 0.0005]] call ACME_fnc_transfusionUiSet;
    } forEach _rows;
    if (count _rows == 1) then {[(_controls select 2),"show",false] call ACME_fnc_transfusionUiSet;};
};
private _endpoints = [];
if (_piggyback isNotEqualTo []) then {
    private _physical = (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
    {
        private _uid = _x;
        private _endpoint = _cardEndpoints getOrDefault [_uid,[]];
        if (!_cardsReady) then {
        {
            private _pane = _display displayCtrl _x;
            if (!isNull _pane && {ctrlShown _pane}) then {
                (ctrlPosition _pane) params ["_px","_py","_pw","_ph"];
                private _paneRowH = safeZoneH / ([20,25] select ((ctrlIDC _pane) == 86129));
                if ((lbSize _pane) * _paneRowH <= _ph) then {
                    for "_r" from 0 to ((lbSize _pane) - 1) do {
                        private _value = _pane lbValue _r;
                        private _selected = _selection param [_value,[]];
                        private _bag = _physical param [_selected param [8,-1],[]];
                        if ((_bag param [8,""]) == _uid && {(_selected param [9,_uid]) == _uid}) exitWith {_endpoint = [_px,_py + (_r + 0.5) * _paneRowH];};
                    };
                };
            };
            if (_endpoint isNotEqualTo []) exitWith {};
        } forEach [86004,86129];
        };
        if (_endpoint isNotEqualTo []) then {_endpoints pushBack _endpoint;};
    } forEach (_piggyback select [0,2]);
};
private _showPib = count _endpoints == 2;
{[_x,"show",_showPib] call ACME_fnc_transfusionUiSet;} forEach _pibControls;
if (_showPib) then {
    private _railX = ((_endpoints select 0) select 0) min ((_endpoints select 1) select 0);
    _railX = _railX - _uiW * 0.006;
    private _a = (_endpoints select 0) select 1;
    private _b = (_endpoints select 1) select 1;
    private _top = _a min _b;
    private _span = abs (_b - _a);
    private _dash = (_span / 11) max pixelH;
    for "_i" from 0 to 5 do {
        [(_pibControls select _i),"position",[_railX,_top + (_i * 2 * _dash),pixelW max 0.0005,_dash]] call ACME_fnc_transfusionUiSet;
    };
    {
        _x params ["_px","_py"];
        [(_pibControls select (6 + _forEachIndex)),"position",[_railX,_py,(_px - _railX) max (_uiW * 0.006),pixelH max 0.0005]] call ACME_fnc_transfusionUiSet;
    } forEach _endpoints;
};
