#include "..\script_component.hpp"
/* Effective antibiotic coverage, using ACME's scalar/current-ACE compatibility boundary.
 * Ceftriaxone retains its own medication-record identity in the current fork.
 */
params ["_patient"];

private _coverage = 0;
{
    _coverage = _coverage + ([_patient, _x, false] call ACME_fnc_medicationCountCompat);
} forEach ["Ertapenem_IV", "Ertapenem", "Ceftriaxone_IV", "Ceftriaxone", "Moxifloxacin"];

_coverage max 0 min 2
