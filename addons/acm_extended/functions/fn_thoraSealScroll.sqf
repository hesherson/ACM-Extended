/* B224: reversible same-corner peeling. Hover exit alone unlocks the corner. */
params ["", ["_delta", 0]];
if (_delta == 0 || {!(call ACME_fnc_thoraSealAt)}) exitWith {false};
private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
if !([_medic, "thoracostomySeal", true] call ACME_fnc_procedureAllowed) exitWith {false};
private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
private _burp = uiNamespace getVariable ["ACME_Thora_Burp", ["", 0, 0, false]];
_burp params ["_burpSide", "_frame", "_openDir", "_fired"];
if (_burpSide != _side) then {_frame = 0; _openDir = 0; _fired = false;};
if (_frame == 0 && {_openDir == 0 || {([1, -1] select (_delta < 0)) == _openDir}} && {!([_patient] call ACME_fnc_chestSealBurpReady)}) exitWith {false};
([_frame, _openDir, _fired, _delta] call ACME_fnc_chestSealScrollStep) params ["_next", "_locked", "_done", "_complete"];
if (_next == _frame) exitWith {true};
uiNamespace setVariable ["ACME_Thora_Burp", [_side, _next, _locked, _done]];
if (_complete) then {[_patient, _medic, _side, "burp"] call ACME_fnc_thoraAftercareRequest;};
[] call ACME_fnc_chestSealSnd;
[] call ACME_fnc_thoraRenderTube;
true
