/* Read-only medical capture fence. A shield request is funded by its provider,
 * so the patient must also wait for a different actor's pending reservation.
 * Unresolved native supply is never represented as durable clinical equipment.
 */
params ["_patient"];
if (isNull _patient) exitWith {false};
private _incoming = _patient getVariable ["ACM_ophthalmology_shieldIncoming", createHashMap];
if (!(_incoming isEqualType createHashMap) || {count _incoming > 0}) exitWith {false};
private _shieldPending = missionNamespace getVariable ["ACM_ophthalmology_shieldPending", createHashMap];
if (!(_shieldPending isEqualType createHashMap) || {count _shieldPending > 0}) exitWith {false};
if (count (_patient getVariable ["ACM_ophthalmology_shieldBindings", []]) > 0) exitWith {false};
private _blocked = false;
{
    if (isNull _x) then {continue;};
    private _bindings = _x getVariable ["ACM_ophthalmology_shieldBindings", []];
    if !(_bindings isEqualType []) exitWith {_blocked = true;};
    if ((_bindings findIf {
        !(_x isEqualType []) || {count _x != 12} || {(_x select 0) isEqualTo _patient}
    }) >= 0) exitWith {_blocked = true;};
} forEach (allUnits + allDeadMen);
!_blocked
