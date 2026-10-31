#include "..\script_component.hpp"
/*
 * Author: Blue
 * Return if patient has active BVM
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * Is BVM being used on unit <BOOL>
 *
 * Example:
 * [player] call ACM_core_fnc_bvmActive;
 *
 * Public: No
 */

params ["_patient"];

private _provider = _patient getVariable [QEGVAR(breathing,BVM_provider),objNull];
// Mechanical ventilation uses the unconscious patient as its native provider sentinel.
alive _provider && {_provider isEqualTo _patient || {!(_provider getVariable ["ACE_isUnconscious",false])}}
