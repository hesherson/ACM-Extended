// Hold-to-contact bell with frame-rate independent drag resistance and continuous audio mixing.
disableSerialization;
params ["_patient"];
private _display = findDisplay 81000;
if (isNull _display || {isNull _patient}) exitWith {};
private _now = diag_tickTime;
private _dt = ((_now - (_display getVariable ["ACME_stethLastFrame",_now])) max 0) min 0.1;
_display setVariable ["ACME_stethLastFrame",_now];
if (!isGameFocused) then {_display setVariable ["ACME_stethPressed",false];};
private _pressed = _display getVariable ["ACME_stethPressed",false];
private _mouse = getMousePosition;
private _center = _display getVariable ["ACME_stethCursor",_mouse];
private _follow = if (_pressed) then {1 - exp (-_dt / 0.11)} else {1};
_center = [
    (_center select 0) + ((_mouse select 0) - (_center select 0)) * _follow,
    (_center select 1) + ((_mouse select 1) - (_center select 1)) * _follow
];
_display setVariable ["ACME_stethCursor",_center];
private _size = _display getVariable ["ACME_stethBellSize",[0.05,0.08]];
private _scale = if (_pressed) then {0.88} else {1};
private _width = (_size select 0) * _scale;
private _height = (_size select 1) * _scale;
private _bell = _display displayCtrl 81002;
_bell ctrlSetPosition [(_center select 0) - _width/2,(_center select 1) - _height/2,_width,_height];
_bell ctrlCommit 0;

// Recover the original grid from a geometry control, avoiding resolution-specific pixel thresholds.
(ctrlPosition (_display displayCtrl 81003)) params ["_rx","_ry","_rw","_rh"];
private _gridW = (_rw / 11.5) max 0.00001;
private _gridH = (_rh / 22) max 0.00001;
private _gx = ((_center select 0) - _rx) / _gridW + 8.5;
private _gy = ((_center select 1) - _ry) / _gridH - 5.3;
private _view = _display getVariable ["ACME_stethView","front"];
private _gains = [_gx,_gy,_view] call ACME_fnc_stethoscopeWeights;
if (!_pressed || {!alive _patient}) then {_gains = [0,0,0];};

private _hr = _patient getVariable ["ace_medical_heartRate",80];
private _rr = _patient getVariable ["ACM_breathing_RespirationRate",18];
if (_hr <= 0 || {_patient getVariable ["ace_medical_inCardiacArrest",false]}) then {_gains set [2,0];};
if (_rr < 1) then {_gains set [0,0]; _gains set [1,0];};
private _channels = _display getVariable ["ACME_stethChannels",[]];
if (count _channels != 5) exitWith {};
// Refresh dynamic findings on the patient owner, including fluid gained/drained while this display is open.
if (_now >= (_display getVariable ["ACME_stethNextLungUpdate",-1])) then {
    _display setVariable ["ACME_stethNextLungUpdate",_now + 1];
    [_patient,"stethoscopeLungs",[[_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;
};
private _lungStates = +(_patient getVariable ["ACM_breathing_Stethoscope_LungState",[0,0]]);
private _overload = _patient getVariable ["ACM_circulation_Overload_Volume",0];
private _aspEdema = (_patient getVariable ["ACME_aspiration_edema",0]) max 0 min 1;
private _crackles = (_patient getVariable ["ACME_edema_crackles",false])
    || {_overload > (missionNamespace getVariable ["ACME_edema_threshold",0.5])}
    || {_aspEdema >= (missionNamespace getVariable ["ACME_aspiration_edemaCrackleThreshold",0.12])};
// ACM stores pooled pleural fluid in liters and one native affected lung, not separate per-side volumes.
private _fluid = (_patient getVariable ["ACM_breathing_Hemothorax_Fluid",0]) max 0;
private _affected = _lungStates findIf {_x in [1,2]};
private _fluidBlend = sqrt (linearConversion [0.3,1.1,_fluid,0,1,true]);
private _basal = linearConversion [6.8,10.0,_gy,0,1,true];
_basal = _basal * _basal * (3 - 2 * _basal);
_gains append [0,0];
for "_i" from 0 to 1 do {
    if ((_lungStates param [_i,0]) == 0 && {_crackles}) then {_lungStates set [_i,3];};
    private _modifier = switch (_lungStates param [_i,0]) do {
        case 1: {0.8}; case 2: {0.3}; default {1};
    };
    private _gain = _gains select _i;
    private _blend = if (_i == _affected) then {_fluidBlend * _basal} else {0};
    // Keep the underlying upper-lung finding; crossfade to crackles only at the affected lung's base.
    _gains set [_i,_gain * _modifier * (1 - _blend)];
    _gains set [3 + _i,_gain * _blend];
};

// Keep the currently playing sounds running while moving. Native distance attenuation mixes
// these five local sources continuously; no global fadeSound or per-frame stop/restart is used.
{
    _x params ["_emitter","_sound","_gain"];
    private _target = _gains select _forEachIndex;
    _gain = _gain + (_target - _gain) * (1 - exp (-_dt / 0.08));
    // Zero means actual silence, including the lower lateral chest and a lifted bell.
    if (_target <= 0.0001) then {_gain = 0;};
    _x set [2,_gain];
    private _distance = if (_gain <= 0.0001) then {22} else {1 + 19 * (1 - _gain)};
    _emitter setPosASL (AGLToASL (positionCameraToWorld [0,_distance,0]));
} forEach _channels;

private _play = {
    params ["_index","_class",["_pitch",1]];
    private _channel = _channels select _index;
    _channel params ["_emitter","_oldSound"];
    if (!isNull _oldSound) then {deleteVehicle _oldSound;};
    // Speech routing bypasses ACE's environmental fadeSound while retaining distance crossfades.
    private _sound = _emitter say3D [_class,20,_pitch,true];
    _channel set [1,_sound];
};
if (alive _patient && {_hr > 0} && {!(_patient getVariable ["ace_medical_inCardiacArrest",false])}
    && {_now >= (_display getVariable ["ACME_stethNextBeat",-1])}) then {
    private _delay = 60 / (_hr max 1);
    _display setVariable ["ACME_stethNextBeat",_now + _delay];
    private _rate = if (_delay < 0.5) then {"Fast"} else {if (_delay > 1.2) then {"Slow"} else {"Normal"}};
    [2,format ["ACM_Stethoscope_HeartBeat_%1_%2",_rate,1 + floor random 3],1 + random 0.1] call _play;
};
if (alive _patient && {_rr >= 1} && {_now >= (_display getVariable ["ACME_stethNextBreath",-1])}) then {
    private _delay = 60 / _rr;
    _display setVariable ["ACME_stethNextBreath",_now + _delay];
    for "_i" from 0 to 1 do {
        private _state = _lungStates param [_i,0];
        private _type = ["Normal","Shallow","Dull","Crackles"] param [_state,"Normal"];
        private _rate = if (_delay < 2) then {"Fast"} else {if (_delay > 5) then {"Slow"} else {"Normal"}};
        [3 + _i,format ["ACM_Stethoscope_Breath_%1_Crackles",_rate]] call _play;
        if (_state == 3) then {
            private _fast = _overload >= (missionNamespace getVariable ["ACME_edema_crackleFastVol",0.5])
                || {_aspEdema >= (missionNamespace getVariable ["ACME_aspiration_edemaCrackleFast",0.55])};
            _rate = if (_fast) then {"Fast"} else {"Normal"};
        };
        [_i,format ["ACM_Stethoscope_Breath_%1_%2",_rate,_type]] call _play;
    };
};
_display setVariable ["ACME_stethChannels",_channels];
