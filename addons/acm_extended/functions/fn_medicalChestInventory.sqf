/* Native and ACE Inventory both reach the same Gear container after the lid opens. */
params ["_target", "_actor"];
if (isNull _actor || {!local _actor} || {!alive _actor}
    || {_actor getVariable ["ACE_isUnconscious", false]} || {_actor distance _target > 4}) exitWith {};
private _resolved = [_target] call ACME_fnc_medicalChestTarget;
if (_resolved isEqualTo []) exitWith {};
_resolved params ["_chest", "_revision", "_open"];
if (!_open) exitWith {
    [_chest, _actor, true, _revision, true] remoteExecCall ["ACME_fnc_medicalChestRequest", 2];
};
private _cargo = _chest getVariable ["ACME_medicalChestCargo", objNull];
if (!isNull _cargo) then {
    ["ACME_medicalChestOpened", [_actor, _chest, _cargo, _revision]] call CBA_fnc_localEvent;
};
