// repaints the readout text from the current settings and shows the cyan selection highlight on the selected field.
// it is called after any value or selection change.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};

private _bpm  = uiNamespace getVariable ["ACME_vent_bpm", 12];
private _vt   = uiNamespace getVariable ["ACME_vent_vt", 500];
private _sel  = uiNamespace getVariable ["ACME_vent_sel", "none"];
private _edit = uiNamespace getVariable ["ACME_vent_editing", false];

// the BPM shows set(measured). the measured value is driven continuously, with a ramp, by the live tick, and here
// we only read the stored value. guard it to a real number and round it, so a stale or non-numeric value can never
// reach the display. a non-number here was what printed "(scalar)".
private _measRaw = uiNamespace getVariable ["ACME_vent_measBpm", _bpm];
if (!(_measRaw isEqualType 0) || {_measRaw != _measRaw}) then { _measRaw = _bpm };  // reject a non-number and a nan.
// build the readout from raw digits. a nan is type SCALAR, so isEqualType passes, and it is not equal to itself and
// is neither at or below 0 nor above 0, which is what let it slip through and print an empty "()". guard against
// it explicitly.
private _setInt  = round (parseNumber (str _bpm));      if (_setInt  != _setInt)  then { _setInt  = 0 };
private _measInt = round (parseNumber (str _measRaw));  if (_measInt != _measInt) then { _measInt = 0 };
_setInt = _setInt max 0; _measInt = _measInt max 0;
private _digits = ["0","1","2","3","4","5","6","7","8","9"];
private _toStr = {
    params ["_n"];
    if (!(_n isEqualType 0) || {_n != _n} || {_n <= 0}) exitWith {"0"};
    private _s = "";
    while {_n > 0} do { _s = (_digits select (_n mod 10)) + _s; _n = floor (_n / 10); };
    _s
};
private _setStr = [_setInt] call _toStr; if (_setStr isEqualTo "") then { _setStr = "0"; };
private _measStr = [_measInt] call _toStr; if (_measStr isEqualTo "") then { _measStr = "0"; };
(_dlg displayCtrl 87721) ctrlSetText (_setStr + " (" + _measStr + ")");

// the second live field is mode-dependent. SIMV VC/IMV VC show tidal volume; SIMV PC shows the actual
// pressure-control setting, PInsp. B17 displayed a VT value even in PC and the engine derived pressure from it,
// so the UI claimed PC while the control surface still behaved like volume control.
private _vTgt = uiNamespace getVariable ["ACME_vent_target", ACE_player];
private _driving = !isNull _vTgt && {_vTgt getVariable ["ACME_vent_driving", false]};
private _mode = if (isNull _vTgt) then {"SIMV VC PS"} else {_vTgt getVariable ["ACME_vent_mode", "SIMV VC PS"]};
private _simple = ((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])});
if (_simple) then {
    private _effective = [_vTgt] call ACME_fnc_ventEffectiveSettings;
    _mode = _effective select 1;
    _vt = _effective select 3;
};
if (_simple) then {
    // Retain a real sensor reading during delivery; this field has no edit state.
    private _showVti = (uiNamespace getVariable ["ACME_vent_dispType", "VTE"]) isEqualTo "VTI";
    private _measured = if (_driving) then {_vTgt getVariable [if (_showVti) then {"ACME_vent_vti"} else {"ACME_vent_vte"}, 0]} else {0};
    (_dlg displayCtrl 87726) ctrlSetText (if (_driving) then {str round _measured} else {"AUTO"});
    (_dlg displayCtrl 87724) ctrlSetText (if (_showVti) then {"VTi"} else {"VTe"});
} else { if (_mode == "SIMV PC") then {
    private _peep = if (isNull _vTgt) then {5} else {_vTgt getVariable ["ACME_vent_peep", 5]};
    private _floor = 11 max (_peep + 1);
    private _pinsp = if (isNull _vTgt) then {uiNamespace getVariable ["ACME_vent_pinsp", 20]} else {_vTgt getVariable ["ACME_vent_pinsp", uiNamespace getVariable ["ACME_vent_pinsp", 20]]};
    _pinsp = _pinsp max _floor min 60;
    uiNamespace setVariable ["ACME_vent_pinsp", _pinsp];
    private _pStr = str (round _pinsp);
    while {count _pStr < 3} do { _pStr = "0" + _pStr; };
    (_dlg displayCtrl 87726) ctrlSetText _pStr;
    (_dlg displayCtrl 87724) ctrlSetText "PInsp";
} else {
    private _vtShown = _vt;
    if (_driving && {!(_sel == "vt" && _edit)}) then {
        _vtShown = _vTgt getVariable ["ACME_vent_vte", _vt];
    } else {
        if (_driving && {_sel == "vt" && _edit}) then { _vtShown = _vTgt getVariable ["ACME_vent_vti", _vt]; };
    };
    private _vtStr = str round _vtShown;
    while { count _vtStr < 4 } do { _vtStr = "0" + _vtStr };
    (_dlg displayCtrl 87726) ctrlSetText _vtStr;
    private _vtLabel = if (_sel == "vt" && _edit) then { "VTi" } else {
        if ((uiNamespace getVariable ["ACME_vent_dispType", "VTE"]) isEqualTo "VTI") then { "VTi" } else { "VTe" }
    };
    (_dlg displayCtrl 87724) ctrlSetText _vtLabel;
}; };

// m.v, in l/min: the real delivered minute ventilation when running, which is the effective exhaled volume times
// the rate, and otherwise the set product. this is what makes an under-delivering pc mode visible.
private _mv = if (_driving) then {
    [_vTgt] call ACME_fnc_ventMinuteVolume
} else {
    if (_mode == "SIMV PC") then {
        private _peep = if (isNull _vTgt) then {5} else {_vTgt getVariable ["ACME_vent_peep", 5]};
        private _pinsp = if (isNull _vTgt) then {uiNamespace getVariable ["ACME_vent_pinsp", 20]} else {_vTgt getVariable ["ACME_vent_pinsp", 20]};
        (_bpm * (500 * (((_pinsp - _peep) max 0) / 15))) / 1000
    } else {
        (_bpm * _vt) / 1000
    }
};
private _mvValidAfter = uiNamespace getVariable ["ACME_vent_mvValidAfter", -1];
private _mvSettling = _driving && {_mvValidAfter > 0} && {diag_tickTime < _mvValidAfter};
private _mvStr = if (_mvSettling) then {
    "--.--"
} else {
    private _s = _mv toFixed 2;
    if ((_mv < 10) && {count _s < 5}) then { _s = "0" + _s; };
    _s
};
(_dlg displayCtrl 87723) ctrlSetText _mvStr;

// the selection and edit colors are owned entirely by fn_ventpanellistrefresh, which is the single source of truth
// for the hover against active color model. this function only sets the readout text and labels, not the
// colors.
