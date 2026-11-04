params ["_mount"];
if (!isServer || {isNull _mount} || {_mount getVariable ["ACME_eq_mountInitialized",false]}) exitWith {};
_mount setVariable ["ACME_eq_mountInitialized",true];
_mount enableSimulationGlobal false;
_mount addEventHandler ["Deleted",{
    params ["_mount"];
    private _device=_mount getVariable ["ACME_eq_device",objNull];
    if (!isNull _device) then {[_device] call ACME_fnc_equipmentMountRelease;};
}];
