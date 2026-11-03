params ["_box"];
if (!hasInterface || {isNull _box}) exitWith {};
private _boxes=missionNamespace getVariable ["ACME_eqCoolerVisuals",[]];_boxes pushBackUnique _box;missionNamespace setVariable ["ACME_eqCoolerVisuals",_boxes];
if !(_box getVariable ["ACME_eqDeleteTracked",false]) then {
    _box setVariable ["ACME_eqDeleteTracked",true];
    _box addEventHandler ["Deleted",{params ["_box"];deleteVehicle (_box getVariable ["ACME_eqOpenVisual",objNull]);}];
};
