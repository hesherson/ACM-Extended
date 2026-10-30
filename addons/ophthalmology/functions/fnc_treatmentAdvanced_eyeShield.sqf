#include "..\script_component.hpp"
/*
 * ACME 1.3.0 eye-shield treatment.
 * Placement is dispatched to the casualty owner. Recovery/stabilization belongs to the single
 * global structural worker, never to a per-treatment PFH.
 */
["finish",_this] call FUNC(shieldSource);
