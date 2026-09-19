#include "..\script_component.hpp"
// Clear a hands-on reservation only if this exact provider episode still owns it.
params ["_medic", "_patient", "_epoch", "_state"];
if (isNull _patient || {!(_state in ["ACM_airway_HeadTilt_State", "ACM_core_CarryAssist_State"])}) exitWith {false};
private _key = _state + "_Session";
if !((_patient getVariable [_key, []]) isEqualTo [_medic, _epoch]) exitWith {false};
_patient setVariable [_key, [], true];
// Recovery position independently maintains head tilt after the provider lets go.
if (_state != "ACM_airway_HeadTilt_State" || {!(_patient getVariable ["ACM_airway_RecoveryPosition_State", false])}) then {
    _patient setVariable [_state, false, true];
};
true
