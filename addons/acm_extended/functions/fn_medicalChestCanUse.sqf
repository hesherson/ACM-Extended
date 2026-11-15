/* Give the pointed chest one ACE root and its current lid action. */
params ["_target", "_actor", ["_opening", -1]];
private _resolved = [_target] call ACME_fnc_medicalChestTarget;
if (_resolved isEqualTo []) exitWith {false};
if (_opening isEqualTo (_resolved select 2)) exitWith {false};

private _aim = cursorObject;
if (isNull _aim) then {_aim = cursorTarget;};
private _otherChestUnderCursor = !isNull _aim && {_aim isNotEqualTo _target} && {_actor distance _aim <= 4}
    && {([_aim] call ACME_fnc_medicalChestTarget) isNotEqualTo []};
!_otherChestUnderCursor && {[_actor, _target, []] call ace_common_fnc_canInteractWith}
