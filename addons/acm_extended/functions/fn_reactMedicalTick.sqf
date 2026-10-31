params ["_args","_pfh"];
_args params ["_display"];
if (isNull _display) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
private _context = _display getVariable ["ACME_reactContext",[]];
if (!(_display isEqualTo findDisplay 89300) || {!([_context] call ACME_fnc_reactMedicalValid)}) exitWith {_display closeDisplay 0;};
if (!(_display getVariable ["ACME_reactReady",false])) exitWith {
    if (diag_tickTime > (_display getVariable ["ACME_reactDeadline",0])) then {[_display] call ACME_fnc_reactMedicalFallback;};
};
private _state = [_context] call ACME_fnc_reactMedicalSnapshot;
if (count _state == 0) exitWith {_display closeDisplay 0;};
private _signature = str _state;
private _now = diag_tickTime;
if (_signature == (_display getVariable ["ACME_reactSignature",""])
    && {_now - (_display getVariable ["ACME_reactLastSend",-10]) < 2}) exitWith {};
private _sequence = (_display getVariable ["ACME_reactStateSequence",0]) + 1;
_display setVariable ["ACME_reactStateSequence",_sequence];
_display setVariable ["ACME_reactSignature",_signature];
_display setVariable ["ACME_reactLastSend",_now];
private _packet = createHashMapFromArray [
    ["version",1],["session",_display getVariable ["ACME_reactSession",""]],
    ["sequence",_sequence],["capturedAt",CBA_missionTime],["state",_state]
];
(_display displayCtrl 89301) ctrlWebBrowserAction ["ExecJS",format ["window.ACMEUI && window.ACMEUI.receive(%1);",toJSON _packet]];
