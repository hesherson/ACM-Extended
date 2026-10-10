#include "..\script_component.hpp"
/* B216: mass-casualty choices use the same faction and case catalog. */
params ["_object", "_spawnLocation"];
[_object, _spawnLocation, 0] call FUNC(spawnPatient_childActions)
