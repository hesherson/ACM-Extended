/* B224: reversible same-corner peeling. Hover exit alone unlocks the corner. */
params [["_src", displayNull], ["_scroll", 0]];
if (!hasInterface || {_scroll == 0}
    || {(uiNamespace getVariable ["ACME_CS_FlipLockedUntil", 0]) > diag_tickTime}
    || {uiNamespace getVariable ["ACME_CS_Held", false]}
    || {uiNamespace getVariable ["ACME_CS_SpearHeld", false]}) exitWith {false};
private _onSeal = [] call ACME_fnc_chestSealSealAt;
if (_onSeal < 0) exitWith {false};
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
private _oldIndex = uiNamespace getVariable ["ACME_CS_BurpIdx", -1];
private _frame = uiNamespace getVariable ["ACME_CS_BurpFrame", 0];
private _direction = uiNamespace getVariable ["ACME_CS_BurpDir", 0];
private _fired = uiNamespace getVariable ["ACME_CS_BurpFired", false];
if (_oldIndex != _onSeal) then {_frame = 0; _direction = 0; _fired = false;};
if (_frame == 0 && {_direction == 0 || {([1, -1] select (_scroll < 0)) == _direction}} && {!([_patient] call ACME_fnc_chestSealBurpReady)}) exitWith {false};
([_frame, _direction, _fired, _scroll] call ACME_fnc_chestSealScrollStep) params ["_next", "_locked", "_done", "_complete"];
if (_next == _frame) exitWith {true};
uiNamespace setVariable ["ACME_CS_BurpIdx", _onSeal];
uiNamespace setVariable ["ACME_CS_BurpFrame", _next];
uiNamespace setVariable ["ACME_CS_BurpDir", _locked];
uiNamespace setVariable ["ACME_CS_BurpSide", ["right", "left"] select (_locked > 0)];
// Latch BEFORE dispatch: duplicate/bubbled wheel input cannot submit another completed action.
uiNamespace setVariable ["ACME_CS_BurpFired", _done];
if (_complete && {!isNull _patient}) then {
    [uiNamespace getVariable ["ACME_CS_Medic", objNull], _patient, "body"] call ACME_fnc_chestSealBurp;
};
[] call ACME_fnc_chestSealSnd;
[] call ACME_fnc_chestSealRender;
true
