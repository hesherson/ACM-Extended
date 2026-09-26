// All input, audio and cursor state belongs to this display instance.
disableSerialization;
params ["_display", ["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]]];
if (isNull _display) exitWith {};
_display setVariable ["ACME_stethPatient", _patient];
_display setVariable ["ACME_stethMedic", _medic];
[_display,"front"] call ACME_fnc_stethoscopeSetView;
_display setVariable ["ACME_stethNextLungUpdate",-1];
_display setVariable ["ACME_stethCursor",getMousePosition];
_display setVariable ["ACME_stethLastFrame",diag_tickTime];
_display setVariable ["ACME_stethNextBeat",-1];
_display setVariable ["ACME_stethNextBreath",-1];
_display setVariable ["ACME_stethHeartVoice",0];
_display setVariable ["ACME_stethFlipActive",false];
_display setVariable ["ACME_stethFlipToken",""];
_display setVariable ["ACME_stethFlipPFH",-1];
private _bell = _display displayCtrl 81002;
private _size = (ctrlPosition _bell) select [2,2];
_display setVariable ["ACME_stethBellSize",_size];
getMousePosition params ["_x","_y"];
_bell ctrlSetPosition [_x - (_size select 0)/2,_y - (_size select 1)/2];
_bell ctrlCommit 0;
_bell ctrlEnable false;
private _down = {
    params ["_source","_button"];
    if (_button != 0) exitWith {false};
    private _d = if (_source isEqualType controlNull) then {ctrlParent _source} else {_source};

    // Use the same absolute GUI cursor source as the original working bell implementation.
    // Do not consume LMB: contact state is ours, cursor motion remains Arma's.
    (ctrlPosition (_d displayCtrl 81006)) params ["_bx","_by","_bw","_bh"];
    getMousePosition params ["_mx","_my"];
    if (_mx >= _bx && {_mx <= _bx + _bw} && {_my >= _by} && {_my <= _by + _bh}) exitWith {false};

    _d setVariable ["ACME_stethPressed",true];

    // Restore the pre-regression input contract from the last stable held-bell implementation. Consuming only
    // the press prevents an underlying RscButton/RscPicture from capturing LMB and freezing Arma's GUI cursor
    // while the bell is held. This does NOT restore click-to-pick-up: the bell still follows the cursor at all
    // times and MouseButtonUp still releases contact normally.
    true
};
private _up = {
    params ["_source","_button"];
    if (_button != 0) exitWith {false};
    private _d = if (_source isEqualType controlNull) then {ctrlParent _source} else {_source};
    _d setVariable ["ACME_stethPressed",false];
    false
};
_display displayAddEventHandler ["MouseButtonDown",_down];
_display displayAddEventHandler ["MouseButtonUp",_up];
// Static picture/text controls cover the panel. Receive releases over any of them too.
{
    _x ctrlAddEventHandler ["MouseButtonDown",_down];
    _x ctrlAddEventHandler ["MouseButtonUp",_up];
} forEach ((allControls _display) select {!(ctrlIDC _x in [81002,81006])});

// A stethoscope is a local diagnostic transducer, not a sound source in world space. World-space emitters made
// diagnostic audio subject to camera position, stereo spatialization and chest/gear geometry. Store only local UI
// sound IDs plus the bell-derived gain. Right/left anatomy still selects the clinical clip; playback itself is
// centered in the listener's headset.
private _channels = [];
// Right/left breath, heart A, right/left basal crackles, then heart B/C/D.
for "_i" from 0 to 7 do {
    _channels pushBack [-1,0];
};
_display setVariable ["ACME_stethChannels",_channels];

// The scope display owns cursor/audio ticking. The generic continuous-action controller is allowed to be
// superseded without stranding a frozen bell: as long as this exact dialog exists, its bell follows the GUI
// cursor and its diagnostic audio cadence continues.
private _oldTick = _display getVariable ["ACME_stethTickPFH", -1];
if (_oldTick isEqualType 0 && {_oldTick >= 0}) then {[_oldTick] call CBA_fnc_removePerFrameHandler;};
private _tickPFH = [{
    params ["_args", "_handle"];
    _args params ["_display", "_patient"];
    if (isNull _display || {isNull _patient} || {!((findDisplay 81000) isEqualTo _display)}) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        if (!isNull _display) then {_display setVariable ["ACME_stethTickPFH", -1];};
    };
    [_patient] call ACME_fnc_stethoscopeTick;
}, 0, [_display, _patient]] call CBA_fnc_addPerFrameHandler;
_display setVariable ["ACME_stethTickPFH", _tickPFH];
