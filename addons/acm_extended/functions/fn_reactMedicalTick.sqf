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
[_browser,"show",_shown] call ACME_fnc_transfusionUiSet;
[_browser,"enable",_shown] call ACME_fnc_transfusionUiSet;
_display setVariable ["ACME_reactActive",true];
if (!_shown) exitWith {};
private _rect = +(_layout select 0);
// Match the original card viewport/gutter; do not cover native buttons or the body map.
private _canvasW = safeZoneW min (safeZoneH * 1.7777778);
private _viewportW = (_rect select 2) min (_canvasW * 0.202);
private _gap = (safeZoneH * 0.006 * (pixelW / pixelH)) max (5 * pixelW);
_rect set [0,(_rect select 0) + (((_rect select 2) - _viewportW) / 2)];
_rect set [2,(_viewportW - 3 * pixelW - _gap) max (10 * pixelW)];
[_browser,"position",_rect] call ACME_fnc_transfusionUiSet;
private _state = [_display] call ACME_fnc_reactMedicalSnapshot;
if (count _state == 0) exitWith {[_display] call ACME_fnc_reactMedicalFallback;};
private _signature = str _state;
private _now = diag_tickTime;
if (_signature == (_display getVariable ["ACME_reactSignature",""])
    && {_now - (_display getVariable ["ACME_reactLastSend",-10]) < 2}) exitWith {};
private _sequence = (_display getVariable ["ACME_reactStateSequence",0]) + 1;
_display setVariable ["ACME_reactStateSequence",_sequence];
_display setVariable ["ACME_reactSignature",_signature];
_display setVariable ["ACME_reactLastSend",_now];
private _packet = createHashMapFromArray [["version",2],["session",_display getVariable ["ACME_reactSession",""]],
    ["sequence",_sequence],["capturedAt",CBA_missionTime],["state",_state]];
_browser ctrlWebBrowserAction ["ExecJS",format ["window.ACMEUI && window.ACMEUI.receive(%1);",toJSON _packet]];
