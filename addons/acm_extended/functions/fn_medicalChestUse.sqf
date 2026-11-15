/* ACE actions send the current chest revision to the server. */
params ["_target", "_actor", "_opening"];
if (!local _actor || {!alive _actor} || {_actor distance _target > 4}
    || {!([_target, _actor, _opening] call ACME_fnc_medicalChestCanUse)}) exitWith {};
private _chest = if (_opening) then {_target} else {
    _target getVariable ["ACME_medicalChestAnchor", objNull]
};
if (isNull _chest) exitWith {};
private _revision = (_chest getVariable ["ACME_medicalChestState", [-1, false]]) select 0;
[_target, _actor, _opening, _revision, false] remoteExecCall ["ACME_fnc_medicalChestRequest", 2];
