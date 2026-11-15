/* The server serializes the visual swap; the native cargo object never changes. */
params [
    ["_target", objNull, [objNull]], ["_actor", objNull, [objNull]],
    ["_opening", false, [false]], ["_revision", -1, [0]]
];
if (!isServer || {isNull _actor} || {isNull _target} || {!alive _actor}
    || {_actor getVariable ["ACE_isUnconscious", false]} || {_actor distance _target > 4}
    || {isRemoteExecuted && {remoteExecutedOwner != owner _actor}}) exitWith {};

private _chest = if (_opening) then {_target} else {_target getVariable ["ACME_medicalChestAnchor", objNull]};
if (isNull _chest || {!(_chest isKindOf "ACME_MedicalChest")}
    || {_chest getVariable ["ACME_medicalChestTransition", false]}) exitWith {};
if ((_chest getVariable ["ACME_medicalChestState", []]) isNotEqualTo [_revision, !_opening]) exitWith {};
private _cabinet = _chest getVariable ["ACME_medicalChestCabinet", objNull];
if (!_opening && {_target isNotEqualTo _cabinet}) exitWith {};
private _cargo = _chest getVariable ["ACME_medicalChestCargo", objNull];
if (isNull _cargo) exitWith {};

[_chest, _opening, _revision, false, _actor] call ACME_fnc_medicalChestSetOpen;
