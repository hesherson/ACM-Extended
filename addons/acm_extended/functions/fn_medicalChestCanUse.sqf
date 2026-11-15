/* ACE displays an action only on this chest's current visible model. */
params ["_target", "_actor", "_opening"];
if (isNull _target || {isObjectHidden _target}) exitWith {false};
private _chest = if (_opening) then {_target} else {_target getVariable ["ACME_medicalChestAnchor", objNull]};
if (isNull _chest) exitWith {false};
private _state = _chest getVariable ["ACME_medicalChestState", []];
if (count _state != 2 || {(_state select 1) == _opening}) exitWith {false};
if (!_opening && {(_chest getVariable ["ACME_medicalChestCabinet", objNull]) isNotEqualTo _target}) exitWith {false};

// When cases sit next to one another, give the actual case under the reticle its own action.
private _aim = cursorObject;
private _otherChestUnderCursor = !isNull _aim && {_aim isNotEqualTo _target} && {!isObjectHidden _aim} && {_actor distance _aim <= 4} && {
    private _aimAnchor = _aim getVariable ["ACME_medicalChestAnchor", objNull];
    _aim isKindOf "ACME_MedicalChest" || {!isNull _aimAnchor
        && {(_aimAnchor getVariable ["ACME_medicalChestCabinet", objNull]) isEqualTo _aim}}
};
!_otherChestUnderCursor && {[_actor, _target, []] call ace_common_fnc_canInteractWith}
