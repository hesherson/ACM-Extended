/* Match the chest-seal panel: five notches lift a corner; reverse the wheel to lay it down. */
params ["", ["_delta", 0]];
if (_delta == 0 || {!(call ACME_fnc_thoraSealAt)}) exitWith {false};
private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
if !([_medic, "thoracostomySeal", true] call ACME_fnc_procedureAllowed) exitWith {false};
private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
private _dir = if (_delta > 0) then {1} else {-1};
private _burp = uiNamespace getVariable ["ACME_Thora_Burp", ["", 0, 0, false]];
_burp params ["_burpSide", "_frame", "_openDir", "_fired"];
if (_burpSide != _side) then {_frame = 0; _openDir = _dir; _fired = false;};
if (_frame == 0 && {!([_patient] call ACME_fnc_chestSealBurpReady)}) exitWith {false};
// Start another peel after cooldown even when the cursor stayed on the fully lifted corner.
if (_frame >= 5 && {_fired} && {_dir == _openDir}
    && {[_patient] call ACME_fnc_chestSealBurpReady}) then {
    _frame = 0;
    _fired = false;
};
if (_dir == _openDir) then {_frame = (_frame + 1) min 5;} else {_frame = (_frame - 1) max 0;};
if (_frame >= 5 && {!_fired}) then {
    [_patient, "thoraAftercare", [_patient, _medic, _side, "burp",
        [_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;
    _fired = true;
};
if (_frame == 0) then {_fired = false;};
uiNamespace setVariable ["ACME_Thora_Burp", [_side, _frame, _openDir, _fired]];
[] call ACME_fnc_chestSealSnd;
[] call ACME_fnc_thoraRenderTube;
true
