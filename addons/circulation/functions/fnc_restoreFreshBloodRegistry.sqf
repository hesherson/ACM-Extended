#include "..\script_component.hpp"
/* Native circulation owns its server registry. ACME validates portable rows
 * before asking this startup boundary to publish a reconstructed registry. */
params ["_registry"];
if (!isServer || {!(_registry isEqualType createHashMap)}) exitWith {false};
missionNamespace setVariable [QGVAR(FreshBloodList),_registry,true];
true
