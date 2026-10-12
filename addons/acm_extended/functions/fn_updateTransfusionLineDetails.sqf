/* B275: inline selected-access information, using the existing UI tick only. */
disableSerialization;
params [["_display", findDisplay 86000]];
// Preserve the roller-clamp and medication workspaces: no main-menu text leaks into their popups.
if (isNull _display || {!isNull (findDisplay 86200)} || {!isNull (findDisplay 84000)}) exitWith {};
private _group = _display displayCtrl 86171;
if (isNull _group) exitWith {};
private _ctrl = _group controlsGroupCtrl 86192;
if (isNull _ctrl) exitWith {};
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
if (isNull _patient || {!([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid)}) exitWith {
    [_group,"show",false] call ACME_fnc_transfusionUiSet;
};
private _bags = ((_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]]) select {
    (_x param [3,-1]) == _site && {(_x param [4,false]) isEqualTo _iv}
};
private _key = toLowerANSI format ["%1#%2#%3",_part,_iv,_site];
private _isY = _key in ((_patient getVariable ["ACME_YLines",[]]) apply {toLowerANSI _x});
private _lines = [];
if (_isY) then {
    ([_patient,_part,_iv,_site] call ACME_fnc_yServiceState) params ["_reserve","_reserved","_blood","_dirty","_primed","_service"];
    _lines pushBack format ["Y line: %1",if (_primed) then {"Primed"} else {"Prime needed"}];
    _lines pushBack format ["Reserve Flush Saline: %1 mL",round _reserve];
    if (_service != "") then {_lines pushBack format ["%1 in progress: %2 mL reserved",_service,round _reserved];};
    if (_primed && {_dirty} && {!_blood} && {_service == ""}) then {_lines pushBack "Flush required before the next unit";};
};
private _thermalLines = [];
{
    ([_patient,_part,_x] call ACME_fnc_transfusionBagPresentation) params ["_label","_color","_thermal","_role","_flowing"];
    if (_role != "") then {
        private _status = if (_flowing) then {["Running","Gravity flow"] select (_role == "Secondary")} else {["Held","Paused"] select (_role == "Secondary")};
        _lines pushBack format ["<t color='#c9b9e4'>Piggyback %1</t>: %2",_role,_status];
    };
    if (_thermal != "") then {
        private _line = if (_flowing && {(_thermal find "Warming") >= 0}) then {format ["<t color='#ff8c21'>%1</t>",_thermal]} else {_thermal};
        _thermalLines pushBackUnique _line;
    };
} forEach _bags;
// One downstream device has one status even though either connected bag can pass through it.
private _warmingThermal = _thermalLines select {(_x find "Warming") >= 0};
_lines append (if (_warmingThermal isEqualTo []) then {_thermalLines} else {_warmingThermal});
{
    if ((toLowerANSI (_x param [1, ""])) == toLowerANSI _part && {(_x param [4,-1]) == _site} && {(_x param [5,false]) isEqualTo _iv}) then {
        _lines pushBack format ["%1: %2 remaining",[_x param [11, ""]] call ACME_fnc_infusionName,[_x param [11, ""],_x param [14,0]] call ACME_fnc_formatDose];
    };
} forEach (_patient getVariable ["ACME_infusion_BagMedications",[]]);

private _cuffs = _patient getVariable ["ACME_piCuffs",createHashMap];
{
    private _cuff = _cuffs getOrDefault [_x param [8,""],[]];
    if (_cuff isNotEqualTo []) then {_lines pushBack format ["Pressure cuff: %1%2",round (([_cuff] call ACME_fnc_pressureLevel) * 100),"%"];};
} forEach _bags;
if (_bags isEqualTo []) then {_lines = ["No bag connected"] + _lines;};
private _content = _lines joinString "<br/>";
if ((_display getVariable ["ACME_detailsContent", ""]) != _content) then {
    _ctrl ctrlSetStructuredText parseText _content;
    _display setVariable ["ACME_detailsContent", _content];
    // A vertical scrollbar keeps every detail directly available when long names or many rows wrap.
    private _rect = ctrlPosition _ctrl;
    _rect set [0,safeZoneH * 0.007 * (pixelW / pixelH)];
    _rect set [1,safeZoneH * 0.005];
    _rect set [2,((ctrlPosition _group) select 2) - safeZoneH * 0.014 * (pixelW / pixelH)];
    _rect set [3, (ctrlTextHeight _ctrl + safeZoneH * 0.006) max ((ctrlPosition _group) select 3)];
    [_ctrl,"position",_rect] call ACME_fnc_transfusionUiSet;
};
[_group,"show",true] call ACME_fnc_transfusionUiSet;
