/* Query the effective server policy; defaults also cover startup before the JIP packet. */
params ["_key"];
private _policy = missionNamespace getVariable ["ACME_clinicalTiming",[]];
private _realTime = _policy param [1,true];
switch (_key) do {
    case "real": {_realTime};
    case "enabled": {_policy param [3,true]};
    case "spoil": {(_policy param [3,true]) && {_policy param [2,true]}};
    case "warm": {if (_realTime) then {3600 * (_policy param [7,4])} else {1800}};
    case "fresh": {if (_realTime) then {3600 * (_policy param [8,24])} else {1800}};
    case "spiked": {3600 * (_policy param [9,4])};
    case "fridge": {86400 * (_policy param [10,21])};
    default {0};
}
