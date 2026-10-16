#include "..\script_component.hpp"
/* Server-serialized registration in ACE's shared effect reason table.
 * Keep ACE's existing indices; clients only observe, never append independently.
 * ACE's effect implementation still owns aggregation and patient hidden state.
 */
private _reasons = missionNamespace getVariable ["ace_common_statusEffects_setHidden", []];
if (isServer && {!(_reasons isEqualTo [])} && {!("acme_medical_downed" in _reasons)}) then {
    _reasons = +_reasons;
    _reasons pushBack "acme_medical_downed";
    missionNamespace setVariable ["ace_common_statusEffects_setHidden", _reasons, true];
};
"acme_medical_downed" in _reasons
