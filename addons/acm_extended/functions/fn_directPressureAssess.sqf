// MMB on the torso maneuver: toggle a pause and read out the bleeding on the held part. while paused the clot tick
// is skipped, because you have eased off to look, and the mouse hint reflects it.
private _medic = (call ACME_fnc_controlledProvider);
if !(_medic getVariable ["ACME_DP_Active", false]) exitWith {};
private _patient = _medic getVariable ["ACME_DP_Patient", objNull];
private _part    = _medic getVariable ["ACME_DP_Part", ""];

private _paused = !(_medic getVariable ["ACME_DP_Paused", false]);
_medic setVariable ["ACME_DP_Paused", _paused];

if (_paused) then {
    private _desc = [_patient, _part] call ACME_fnc_assessBleeding;
    [format ["Eased off. %1: %2. MMB to resume.", _part, _desc], 4, _medic] call ace_common_fnc_displayTextStructured;
    ["", "Stop", "Resume"] call ace_interaction_fnc_showMouseHint;
} else {
    ["Resuming pressure.", 1.5, _medic] call ace_common_fnc_displayTextStructured;
    ["", "Stop", "Pause / assess"] call ace_interaction_fnc_showMouseHint;
};
