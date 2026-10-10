/* Uses the existing UI tick; no owner writes or additional refresh worker. */
private _display = findDisplay 86190;
if (isNull _display) exitWith {};
private _context = uiNamespace getVariable ["ACME_TransfusionDetailsContext", []];
if (count _context < 5) exitWith {_display closeDisplay 0;};
_context params ["_patient", "_part", "_iv", "_site", "_caption"];
if (isNull _patient || {isNull (findDisplay 86000)}) exitWith {_display closeDisplay 0;};
private _bags = ((_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]]) select {
    (_x param [3,-1]) == _site && {(_x param [4,false]) isEqualTo _iv}
};
private _key = toLowerANSI format ["%1#%2#%3",_part,_iv,_site];
private _isY = _key in ((_patient getVariable ["ACME_YLines",[]]) apply {toLowerANSI _x});
private _lines = [];
if (_isY) then {
    ([_patient,_part,_iv,_site] call ACME_fnc_yServiceState) params ["_reserve","_reserved","_blood","_dirty","_primed","_service"];
    _lines pushBack format ["Y line: %1",if (_primed) then {"Primed"} else {"Prime needed"}];
    _lines pushBack format ["Saline reserve: %1 mL (clamped)",round _reserve];
    if (_service != "") then {_lines pushBack format ["%1 in progress: %2 mL reserved",_service,round _reserved];};
    if (_primed && {_dirty} && {!_blood} && {_service == ""}) then {_lines pushBack "Flush required before the next unit";};
};
{
    private _type = _x param [0, ""];
    if !(_type in ["ACME_Empty","ACME_EmptySaline","ACME_SalineY"]) then {
        private _name = getText (configFile >> "CfgWeapons" >> ([_type,_x param [6,0],_x param [5,-1]] call ACM_circulation_fnc_formatFluidBagName) >> "displayName");
        if (_name == "") then {_name = _type;};
        _lines pushBack format ["%1: %2 mL remaining",_name,round (_x param [1,0])];
    };
} forEach _bags;
{
    if ((toLowerANSI (_x param [1, ""])) == toLowerANSI _part && {(_x param [4,-1]) == _site} && {(_x param [5,false]) isEqualTo _iv}) then {
        _lines pushBack format ["%1 remaining",[_x param [11, ""],_x param [14,0]] call ACME_fnc_formatDose];
    };
} forEach (_patient getVariable ["ACME_infusion_BagMedications",[]]);
_lines pushBack format ["LifeWarmer Quantum: %1",if ([_patient,_part,_iv,_site] call ACME_fnc_lineWarmer) then {"Inline"} else {"Not fitted"}];
private _cuffs = _patient getVariable ["ACME_piCuffs",createHashMap];
{
    private _cuff = _cuffs getOrDefault [_x param [8,""],[]];
    if (_cuff isNotEqualTo []) then {_lines pushBack format ["Pressure cuff: %1%2",round (([_cuff] call ACME_fnc_pressureLevel) * 100),"%"];};
} forEach _bags;
if (_bags isEqualTo []) then {_lines = ["No bag connected"] + _lines;};
[(_display displayCtrl 86191),"text","Line Details"] call ACME_fnc_transfusionUiSet;
_lines = [_caption] + _lines;
private _content = _lines joinString "<br/>";
if ((_display getVariable ["ACME_detailsContent", ""]) != _content) then {
    (_display displayCtrl 86192) ctrlSetStructuredText parseText _content;
    _display setVariable ["ACME_detailsContent", _content];
};
