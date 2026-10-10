enableSaving [false, false];
// This is local to the packaged testing mission, never a global mod loadout override.
if (hasInterface) then {
    [{!isNull player && {local player}}, {
        private _unit = player;
        if (_unit getVariable ["ACME_testZoneKitApplied", false]) exitWith {};
        private _kit = call compile preprocessFileLineNumbers "defaultLoadout.sqf";
        [_unit, _kit, false] call CBA_fnc_setLoadout;
        _unit setVariable ["ACME_testZoneKitApplied", true, false];
    }, [], 30] call CBA_fnc_waitUntilAndExecute;
};
