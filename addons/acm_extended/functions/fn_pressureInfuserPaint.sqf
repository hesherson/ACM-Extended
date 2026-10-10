/* B227: no extra PFH and no animation timer. Each press pumps the selected physical UID. */
disableSerialization;
params ["_display", "_button", "_context", "_idc"];
if (isNull _display || {isNull _button}) exitWith {};
private _bar = _display displayCtrl _idc;
if (isNull _bar) then {
    _bar = _display ctrlCreate ["RscProgress",_idc];
    _bar ctrlEnable false;
    _bar ctrlSetTextColor [0.25,0.7,0.95,0.95];
};
private _visible = ctrlShown _button;
_bar ctrlShow _visible;
if (!_visible) exitWith {};
private _pos = ctrlPosition _button;
private _height = (4 * pixelH) max ((_pos select 3) * 0.12);
_bar ctrlSetPosition [_pos select 0,(_pos select 1)+(_pos select 3)-_height,_pos select 2,_height];
_bar ctrlCommit 0;
private _level = 0; private _fitted = false;
if (count _context >= 11) then {
    _context params ["_patient","_part","_index"];
    private _bag = ((_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]]) param [_index,[]];
    private _uid = _bag param [8,""];
    private _cuff = (_patient getVariable ["ACME_piCuffs",createHashMap]) getOrDefault [_uid,[]];
    _fitted = _cuff isNotEqualTo [];
    _level = [_cuff] call ACME_fnc_pressureLevel;
};
_bar progressSetPosition _level;
private _text = if (_fitted) then {format ["Pump (%1%2)",round (_level * 100),"%"]} else {"Pressure Infuse"};
if (ctrlText _button != _text) then {_button ctrlSetText _text;};
