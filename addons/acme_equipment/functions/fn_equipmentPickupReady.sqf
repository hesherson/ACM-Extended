/* Read actual custody at admission and commit; a stale ACME claim cannot authorize external carry. */
params ["_device"];
if (isNull _device || {_device getVariable ["ACME_eq_restoreStaged",false]}) exitWith {false};
private _parent=attachedTo _device;
if (isNull _parent) exitWith {true};
private _mount=_device getVariable ["ACME_eq_mount",objNull];
!isNull _mount && {_parent isEqualTo _mount}
    && {_device getVariable ["ACME_eq_mounted",false]}
    && {(_mount getVariable ["ACME_eq_device",objNull]) isEqualTo _device}

