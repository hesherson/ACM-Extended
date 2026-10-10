/* One service control, fixed above Move/Pull. Repaint without rebuilding controls or changing selection. */
disableSerialization;
params ["_display", "_patient", "_part", "_iv", "_site", "_isY"];
private _flush = _display displayCtrl 86143;
_flush ctrlShow _isY;
if (!_isY || {isNull _patient}) exitWith {};
private _state = [_patient,_part,_iv,_site] call ACME_fnc_yServiceState;
_state params ["_reserve","_reserved","_blood","_dirty","_primed","_kind","_id","_job"];
private _mode = ["prime", "flush"] select _primed;
private _plan = [_mode,_reserve,_reserved,_blood,_dirty,_primed,_kind] call ACME_fnc_yServicePlan;
private _canCancel = _kind == "flush" && {count (_job param [9,[]]) > 0};
_flush ctrlEnable ((_plan select 0) || {_canCancel});
private _count = if (_job isEqualTo []) then {0} else {1 + count (_job param [9,[]])};
private _text = if (_kind == "prime") then {"Priming..."} else {
    if (_kind == "flush") then {format ["Flush In Progress... (%1)",_count]} else {
        ["Prime Line (25 mL)", "Flush Line"] select _primed
    }
};
if (ctrlText _flush != _text) then {_flush ctrlSetText _text;};
private _tip = if (!_primed) then {"Prime with 25 mL from this line's saline reserve."} else {
    "Left-click: queue 50 mL. Right-click: remove one waiting flush. A required flush can use 25 mL when less than 50 mL remains."
};
_flush ctrlSetTooltip _tip;
// A dirty, empty blood limb needs attention, even if its reserve must be replaced first.
private _indicated = _primed && {_dirty} && {!_blood} && {_kind == ""};
private _primeIndicated = !_primed && {_kind == ""};
private _pulse = 0.5 + 0.5 * sin (360 * ((diag_tickTime * 1.1) % 1));
_flush ctrlSetTextColor (if (_indicated) then {[1,0.2 + 0.2 * _pulse,0.2 + 0.2 * _pulse,0.65 + 0.35 * _pulse]} else {
    if (_primeIndicated) then {[0.35,1,0.45,0.65 + 0.35 * _pulse]} else {[1,1,1,1]}
});
_flush ctrlSetBackgroundColor (if (_indicated) then {[0.25 + 0.45 * _pulse,0,0,0.7]} else {
    if (_primeIndicated) then {[0,0.15 + 0.35 * _pulse,0,0.8]} else {[0,0,0,1]}
});
if !(_flush getVariable ["ACME_serviceRightClick",false]) then {
    _flush setVariable ["ACME_serviceRightClick",true];
    _flush ctrlAddEventHandler ["MouseButtonDown", {
        params ["_control","_button"];
        if (_button != 1) exitWith {false};
        if (ctrlEnabled _control && {ctrlShown _control}) then {
            ["cancel"] call ACME_fnc_transfusionFlushLine;
            // Same inherited sound as a native LMB click; do not synthesize a left action.
            private _sound = getArray (configFile >> "ACM_circulation_TransfusionMenu_Dialog" >> "controls" >> "ACME_FlushLineButton" >> "soundClick");
            if (count _sound >= 3 && {(_sound select 0) != ""}) then {playSoundUI [_sound select 0,_sound select 1,_sound select 2];};
        };
        true
    }];
};
