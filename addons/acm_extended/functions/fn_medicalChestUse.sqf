/* ACE actions and the native InventoryOpened gate share the same chest state. */
params ["_target", "_actor", "_action"];
if (!local _actor || {!alive _actor} || {_actor distance _target > 4}) exitWith {};
private _chest = if (_action == "open") then {_target} else {
    _target getVariable ["ACME_medicalChestAnchor", objNull]
};
if (isNull _chest) exitWith {};
(_chest getVariable ["ACME_medicalChestState", [-1, false]]) params ["_revision", "_open"];
if (_action == "supplies") exitWith {
    private _cargo = _chest getVariable ["ACME_medicalChestCargo", objNull];
    if (!isNull _cargo && {_open}) then {
        _actor action ["Gear", _cargo];
    };
};
[_target, _actor, _action == "open", _revision]
    remoteExecCall ["ACME_fnc_medicalChestRequest", 2];
