#include "..\script_component.hpp"
/*
 * Return the ACE medication summary shape for ACM medication records.
 *
 * Arguments:
 * 0: The patient <OBJECT>
 * 1: Get effective count (true) or effect ratio (false) <BOOL> (default: true)
 *
 * Return Value:
 * Array of [medication classname, recorded dose, requested effectiveness].
 * Recorded dose is the sum of ACM normalized reference-dose equivalents at
 * record index 12. Index 7 contains the administration route, not a dose.
 * It remains undecayed while its medication record remains in the system.
 *
 * Public: Yes
 */
params ["_target", ["_getCount", true]];

private _medications = _target getVariable [VAR_MEDICATIONS, []];
private _medicationClasses = _medications apply {_x select 0};
_medicationClasses = _medicationClasses arrayIntersect _medicationClasses;

_medicationClasses apply {
    private _medication = _x;
    private _dose = 0;
    {
        if ((_x select 0) == _medication) then {
            _dose = _dose + (_x select 12);
        };
    } forEach _medications;

    [_medication, _dose, [_target, _medication, _getCount] call ACEFUNC(medical_status,getMedicationCount)]
}
