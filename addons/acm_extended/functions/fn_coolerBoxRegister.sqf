// InitPost covers Eden, Zeus and scripted native cooler creation.
params ["_box"];
if (!isServer || {is3DEN} || {isNull _box}) exitWith {};
private _deployed = missionNamespace getVariable ["ACME_ccDeployedCoolers", []];
_deployed pushBackUnique _box;
missionNamespace setVariable ["ACME_ccDeployedCoolers", _deployed];
