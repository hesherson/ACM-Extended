// Toggle a held tool from the thoracostomy tray.  B120 keeps chest tube and chest seal as direct clinical
// identities in separate full-width rows; there is no sealSlot proxy or dynamic shared-row mode.
params ["_tool", ["_explicitClosure", false]];
disableSerialization;
private _display = uiNamespace getVariable ["ACME_Thora_DLG", displayNull];
if (isNull _display) exitWith {};

private _held = uiNamespace getVariable ["ACME_Thora_Held", ""];
private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];

// Placement cleanup historically calls ["tube"] after either closure. Preserve that internal one-argument
// behavior as "put down the closure currently in hand" while real tray clicks pass _explicitClosure=true.
if (_tool == "tube" && {!_explicitClosure} && {_held in ["seal", "tube"]}) then {_tool = _held;};
if (_held isEqualTo _tool) then {_tool = "";};

private _repeatFinger = _tool == "finger" && {[_medic, _patient,
    uiNamespace getVariable ["ACME_Thora_Side", "right"]] call ACME_fnc_thoraCanSweep};
if (_tool in ["scalpel", "kelly", "finger"] && {!_repeatFinger} && {
    !([_medic, "thoracostomy"] call ACME_fnc_procedureAllowed)
    || {([_medic, _patient] call ACME_fnc_thoraKitItem) == ""}
}) exitWith {};
// Reject before touching the current tool/step. A nested exitWith would only leave its inner block.
if (_tool == "tube" && {isNull _medic || {!([_medic, "chestTube"] call ACME_fnc_procedureAllowed)}
    || {([_medic, "ACM_ChestTubeKit"] call ACME_fnc_itemCount) < 1}}) exitWith {};
if (_tool == "seal" && {isNull _medic || {!([_medic, "thoracostomySeal"] call ACME_fnc_procedureAllowed)}
    || {([_medic, "ACM_ChestSeal"] call ACME_fnc_itemCount) < 1}}) exitWith {};

uiNamespace setVariable ["ACME_Thora_Held", _tool];
uiNamespace setVariable ["ACME_Thora_TubeSnap", false];
uiNamespace setVariable ["ACME_Thora_SealMode", _tool == "seal"];
uiNamespace setVariable ["ACME_Thora_Palpating", false];
uiNamespace setVariable ["ACME_Thora_Cutting", false];
uiNamespace setVariable ["ACME_Thora_Prepping", false];
uiNamespace setVariable ["ACME_Thora_KellyArmed", false];
[] call ACME_fnc_thoraUpdateTrayIcons;
