#include "..\script_component.hpp"
/* Core-owned ACE integration for the physical-dressing invariant. Advanced
 * bandage bookkeeping stays enabled; only explicit unsecured clots may reopen.
 * The startup caller reasserts this after CBA setting synchronization for JIP.
 */
missionNamespace setVariable ["ace_medical_treatment_woundReopenChance", -1, false];
