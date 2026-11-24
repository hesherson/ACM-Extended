/* B397: draw (or remove) a staged set's bag on an IV stand's hook on this machine (fn_ivStandServer.sqf "stage",
 * a JIP event per hook). A local, collision-free prop made from the bag's class, so its fluid's picture shows; it
 * goes with the stand when the stand is dragged (attached to it).
 * [stand, hook, show, fluid ("blood", "plasma", "plasmalyte", "fluid"), volume] */
if (!hasInterface) exitWith {};
params ["_stand", "_slot", "_show", ["_fluid", "fluid"], ["_volume", 500]];
if (isNil "ACME_ivStand_stagedLocal") then {ACME_ivStand_stagedLocal = createHashMap;};
private _key = format ["%1_%2", if (isNull _stand) then {""} else {netId _stand}, _slot];
private _old = ACME_ivStand_stagedLocal getOrDefault [_key, objNull];
if (!isNull _old) then {detach _old; deleteVehicle _old;};
ACME_ivStand_stagedLocal deleteAt _key;
// (and any whose stand is gone)
{if (isNull attachedTo _y) then {deleteVehicle _y; ACME_ivStand_stagedLocal deleteAt _x;};} forEach +ACME_ivStand_stagedLocal;
if (!_show || {isNull _stand}) exitWith {};

private _vol = if (_volume <= 375) then {250} else {if (_volume <= 750) then {500} else {1000}};
private _model = switch (_vol) do {case 250: {"ACME_IVBagObject_250"}; case 1000: {"ACME_IVBagObject_1000"}; default {"ACME_IVBagObject"};};
private _tex = if (_fluid == "plasmalyte") then {format ["\acm_extended\data\iv_bag\IVBag_plasmalyte_%1ml_ca.paa", _vol]} else {
    format ["\z\ace\addons\medical_treatment\data\IVBag_%1_%2ml_ca.paa", switch (_fluid) do {case "blood": {"blood"}; case "plasma": {"plasma"}; default {"saline"};}, _vol]};
private _hook = (missionNamespace getVariable ["ACME_ivStand_hooks", [[0, 0.13, 0.76], [0, -0.13, 0.76]]]) param [_slot, [0, 0.13, 0.76]];
private _bag = createSimpleObject [_model, [0, 0, 0], true];
_bag setObjectTexture [0, _tex];
_bag attachTo [_stand, _hook];
(missionNamespace getVariable ["ACME_ivStand_bagVectors", [[0, 1, 0], [0, 0, -1]]]) params ["_dir", "_up"];
_bag setVectorDirAndUp [_dir, _up];
ACME_ivStand_stagedLocal set [_key, _bag];
