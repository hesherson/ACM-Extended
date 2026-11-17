/*
 * On every machine with a screen, once a second: show the SKED's carry bag slung from the right shoulder of
 * every nearby unit that has a SKED in its inventory, and take it off those that no longer do. The bag is a
 * simple object that exists on this machine only, attached to the unit's spine3 bone. Nothing is sent over
 * the network. It is hidden while its wearer is in a vehicle. The backpack slot is left alone.
 * Settings: acme_sked_slungShow, acme_sked_slungRange, acme_sked_slungX, Y and Z (see XEH_preInit.sqf).
 * Arguments: none.
 */
if (!hasInterface) exitWith {};
private _show = missionNamespace getVariable ["acme_sked_slungShow", true];
private _range = missionNamespace getVariable ["acme_sked_slungRange", 300];
// Where the top of the right shoulder is from the spine3 bone (X right, Y forward, Z up), plus the fine adjustment.
private _off = [
    0.16 + (missionNamespace getVariable ["acme_sked_slungX", 0]),
    -0.03 + (missionNamespace getVariable ["acme_sked_slungY", 0]),
    0.145 + (missionNamespace getVariable ["acme_sked_slungZ", 0])
];
private _eye = positionCameraToWorld [0, 0, 0];
private _want = [];
if (_show) then {
    _want = (nearestObjects [_eye, ["CAManBase"], _range]) select {"ACME_SKED_Item" in items _x};
};
// Take it off whoever no longer carries one (or has gone).
private _shown = missionNamespace getVariable ["acme_sked_slung", []];
private _keep = [];
{
    _x params ["_unit", "_bag"];
    if (isNull _unit || {isNull _bag} || {!(_unit in _want)}) then {
        if (!isNull _bag) then {
            detach _bag;
            deleteVehicle _bag;
        };
    } else {
        _keep pushBack _x;
    };
} forEach _shown;
// Put it on whoever carries one and does not have it yet.
private _have = _keep apply {_x select 0};
{
    if !(_x in _have) then {
        private _bag = createSimpleObject ["acme_sked\sked_slung.p3d", getPosWorld _x, true];
        _bag setVariable ["acme_sked_slungOff", []];
        _keep pushBack [_x, _bag];
    };
} forEach _want;
// Attach (again when the adjustment has changed), and hide in vehicles.
{
    _x params ["_unit", "_bag"];
    if !((_bag getVariable ["acme_sked_slungOff", []]) isEqualTo _off) then {
        _bag attachTo [_unit, _off, "spine3", true];
        _bag setVariable ["acme_sked_slungOff", +_off];
    };
    _bag hideObject !(isNull objectParent _unit);
} forEach _keep;
missionNamespace setVariable ["acme_sked_slung", _keep];
