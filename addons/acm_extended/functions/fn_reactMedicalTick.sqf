/* Run from the existing native card refresh, with no extra per-frame worker. */
params ["_display"];
private _browser = _display displayCtrl 89301;
if (isNull _browser) exitWith {};
private _context = _display getVariable ["ACME_reactContext",[]];
if (!(_display isEqualTo findDisplay 86000) || {!([_context] call ACME_fnc_reactMedicalValid)}
    || {(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Medic",objNull]) isNotEqualTo (_context select 0)}
    || {(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull]) isNotEqualTo (_context select 1)}) exitWith {
    [_display] call ACME_fnc_reactMedicalFallback;
};
if (!(_display getVariable ["ACME_reactReady",false])) exitWith {
    if (diag_tickTime > (_display getVariable ["ACME_reactDeadline",0])) then {[_display] call ACME_fnc_reactMedicalFallback;};
};
private _layout = (_display getVariable ["ACME_txCardLayout",createHashMap]) getOrDefault [86004,[]];
if (count _layout != 5) exitWith {[_display] call ACME_fnc_reactMedicalFallback;};
private _shown = _layout select 4;
private _painted = _display getVariable ["ACME_reactPainted",false];
if (!_painted && {diag_tickTime > (_display getVariable ["ACME_reactDeadline",0])}) exitWith {[_display] call ACME_fnc_reactMedicalFallback;};
private _rect = [_layout] call ACME_fnc_reactMedicalRect;
// Cache the requested rectangle. Engine ctrlPosition can round it, causing a
// perpetual resize/recommit loop if compared directly with authored floats.
if ((_display getVariable ["ACME_reactRect",[]]) isNotEqualTo _rect) then {
    _display setVariable ["ACME_reactRect",_rect];
    [_browser,"position",_rect] call ACME_fnc_transfusionUiSet;
};
[_browser,"show",_shown && {_painted}] call ACME_fnc_transfusionUiSet;
[_browser,"enable",_shown && {_painted}] call ACME_fnc_transfusionUiSet;
_display setVariable ["ACME_reactActive",_painted];
if (!_shown) exitWith {};
private _now = diag_tickTime;
// Native volume updates can arrive each frame; the embedded view needs at most 10 Hz.
if (_now - (_display getVariable ["ACME_reactLastSend",-10]) < 0.1) exitWith {};
private _state = [_display] call ACME_fnc_reactMedicalSnapshot;
if (count _state == 0) exitWith {[_display] call ACME_fnc_reactMedicalFallback;};
private _signature = str _state;
if (_signature == (_display getVariable ["ACME_reactSignature",""])
    && {_now - (_display getVariable ["ACME_reactLastSend",-10]) < 2}) exitWith {};
private _sequence = (_display getVariable ["ACME_reactStateSequence",0]) + 1;
_display setVariable ["ACME_reactStateSequence",_sequence];
_display setVariable ["ACME_reactSignature",_signature];
_display setVariable ["ACME_reactLastSend",_now];
private _packet = createHashMapFromArray [["version",2],["session",_display getVariable ["ACME_reactSession",""]],
    ["sequence",_sequence],["capturedAt",CBA_missionTime],["state",_state]];
_browser ctrlWebBrowserAction ["ExecJS",format ["window.ACMEUI && window.ACMEUI.receive(%1);",toJSON _packet]];
