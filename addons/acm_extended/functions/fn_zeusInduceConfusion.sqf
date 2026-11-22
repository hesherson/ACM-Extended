/* B391 Zeus module: toggle the confused state (garbled speech) on a player. */
params ["_logic"];
if (isNull _logic) exitWith {};
private _unit = effectiveCommander (attachedTo _logic);
if (isNull _unit) then {_unit = attachedTo _logic;};
private _cleanup = {if (!isNull _logic) then {deleteVehicle _logic;};};
if (isNull _unit || {!(_unit isKindOf "CAManBase")} || {!alive _unit} || {!isPlayer _unit}) exitWith {
    ["Confusion module: place it on a living player.", 2] call ace_common_fnc_displayTextStructured;
    call _cleanup;
};
private _want = !(_unit getVariable ["ACME_confused", false]);
[_unit, _want, true, "zeus"] call ACME_fnc_confusedSet;
[format ["Confusion %1 %2.", ["cleared on", "induced on"] select _want, name _unit], 2] call ace_common_fnc_displayTextStructured;
call _cleanup;
