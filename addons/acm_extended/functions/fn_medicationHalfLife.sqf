/* Route suffixes share parent-drug clearance. Unknown classes and synthetic effects use native kinetics. */
params ["_class"];
private _table = missionNamespace getVariable "ACME_medicationKinetics";
if (isNil "_table") then {
    _table = call ACME_fnc_medicationKinetics;
    missionNamespace setVariable ["ACME_medicationKinetics",_table];
};
private _parts = toLower _class splitString "_";
private _base = _parts param [0,""];
private _route = _parts param [1,""];
if ((_base == "atropine" && {_route in ["iv","l"]}) || {count _parts <= 2 && {_route in ["","iv","buc"]}}) exitWith {
    _table getOrDefault [_base,[]]
};
[]
